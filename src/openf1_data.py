"""Alternativa histórica pública. Conserva desconocidos; no inventa banderas FastF1."""
import csv
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .data import is_missing, portable_sha256, write_csv
from .openf1_quality import apply_openf1_quality_filter

BASE = 'https://api.openf1.org/v1/'


def normalize_laps(laps: list[dict], stints: list[dict], pits: list[dict], driver: str) -> list[dict]:
    pit_laps = {p['lap_number'] for p in pits}
    result = []
    for lap in sorted(laps, key=lambda r: r['lap_number']):
        number = lap['lap_number']
        matching = [s for s in stints if s['lap_start'] <= number <= s['lap_end']]
        stint = matching[0] if len(matching) == 1 else None
        initial_age = stint.get('tyre_age_at_start') if stint else None
        age = initial_age + number - stint['lap_start'] + 1 if initial_age is not None else None
        result.append({
            'driver': driver, 'driver_number': lap['driver_number'], 'lap_number': number,
            'lap_time_s': lap.get('lap_duration'), 'stint': stint['stint_number'] if stint else None,
            'compound': stint.get('compound') if stint else None, 'tyre_life_laps': age,
            'fresh_tyre': initial_age == 0 if initial_age is not None else None,
            'pit_in_time_s': None, 'pit_out_time_s': None,
            'is_pit_in_lap': number in pit_laps, 'is_pit_out_lap': lap.get('is_pit_out_lap'),
            'session_time_s': None, 'lap_start_time_s': None,
            'date_start_utc': lap.get('date_start'), 'track_status': None,
            'deleted': None, 'is_accurate': None, 'fastf1_generated': None,
            'quality_note': 'PENDING_REVIEW_OPENF1_HAS_NO_FASTF1_QUALITY_FLAGS',
            'data_provider': 'OPENF1_PUBLIC_HISTORICAL',
        })
    return result


def download_openf1_case(config: dict, root: Path) -> dict:
    raw = root/'data/raw/openf1'
    raw.mkdir(parents=True, exist_ok=True)
    requests_log = []
    def get(endpoint, query):
        url = BASE+endpoint+'?'+urlencode(query)
        path = raw/(endpoint+'.json')
        url_path = raw/(endpoint+'.url.txt')
        if path.exists() and url_path.exists() and url_path.read_text(encoding='utf-8') == url:
            value = json.loads(path.read_text(encoding='utf-8'))
            requests_log.append({'url': url, 'cached': True})
            return value
        for attempt in range(3):
            try:
                request = Request(url, headers={'User-Agent': 'UVG-F1-academic-project/0.1'})
                with urlopen(request, timeout=30) as response:
                    value = json.load(response)
                if not isinstance(value, list):
                    raise ValueError(f'Respuesta inesperada: {endpoint}')
                path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
                url_path.write_text(url, encoding='utf-8')
                requests_log.append({'url': url, 'cached': False})
                time.sleep(2.1)  # Dentro del límite gratuito de 30 solicitudes/minuto.
                return value
            except HTTPError as exc:
                if exc.code == 401:
                    # Comprobado el 2026-11-06: durante una sesión de F1 en vivo OpenF1 exige
                    # cuenta incluso para datos históricos. No introducir credenciales en el repo.
                    raise RuntimeError(
                        'OpenF1 respondió 401: mientras hay una sesión de F1 en vivo el acceso '
                        'sin cuenta (incluso a datos históricos) queda restringido. Reintentar '
                        'cuando termine la sesión. Si data/raw/openf1 ya existe con los mismos '
                        'URL, la descarga usa esa caché y no necesita red.') from exc
                if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                    raise
                time.sleep(min(10, 3 * (attempt+1)))
        raise RuntimeError('No se obtuvo una respuesta')
    sessions = get('sessions', {'year': config['year'], 'country_name': config['event'], 'session_name': 'Race'})
    if len(sessions) != 1:
        raise ValueError('No se identificó una única sesión; revisar config sin elegir arbitrariamente')
    key = sessions[0]['session_key']
    driver_number = config['driver_number']
    query = {'session_key': key, 'driver_number': driver_number}
    laps = get('laps', query)
    stints = get('stints', query)
    pits = get('pit', query)
    weather = get('weather', {'session_key': key})
    race_control = get('race_control', {'session_key': key})
    if not laps or not stints:
        raise ValueError('No hay datos suficientes de vueltas/stints; no sustituir con datos sintéticos')
    records = normalize_laps(laps, stints, pits, config['driver'])
    write_csv(root/'data/raw/openf1_target_laps.csv', records)
    # Filtro propio de OpenF1 (MA-02): marca, no borra. Ver src/openf1_quality.py.
    annotated, exclusions, quality = apply_openf1_quality_filter(
        records, laps, race_control, weather, driver_number)
    write_csv(root/'data/processed/openf1_target_laps_annotated.csv', annotated)
    write_csv(root/'data/processed/openf1_exclusions.csv', exclusions)
    audit = {k: quality[k] for k in ('filter_version', 'rows_total', 'eligible_normal_laps',
                                     'excluded_laps', 'warning_laps', 'eligible_coverage')}
    # No particionar como si estuviera depurada una tabla sin revisión de calidad.
    observed_times = [float(r['lap_time_s']) for r in records if not is_missing(r['lap_time_s'])]
    complete = len(observed_times) == config['expected_laps']
    record_numbers = {int(r['lap_number']) for r in records}
    report = {
        'source_kind': 'PUBLIC_OBSERVATION_OPENF1', 'provider': 'OpenF1',
        'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
        'case': config, 'session_key': key, 'audit': audit,
        'target_laps_rows': len(records), 'timed_laps_count': len(observed_times),
        'missing_lap_numbers': sorted(set(range(1, config['expected_laps']+1))-record_numbers),
        'missing_lap_time_numbers': [r['lap_number'] for r in records if is_missing(r['lap_time_s'])],
        'observed_partial_lap_sum_s': math.fsum(observed_times),
        'time_sum_is_complete': complete,
        'difference_from_official_s': math.fsum(observed_times)-config['official_winner_time_s'] if complete else None,
        'stints_observed': stints, 'pits_observed': pits,
        'weather_rows': len(weather), 'race_control_rows': len(race_control),
        'requests': requests_log,
        # 'sha256' depende de los saltos de línea del sistema; se conserva por compatibilidad
        # con la evidencia anterior. Para verificar entre computadoras usar 'sha256_portable'.
        'sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(raw.glob('*.json'))},
        'sha256_portable': {p.name: portable_sha256(p) for p in sorted(raw.glob('*.json'))},
        'sha256_note': 'sha256_portable convierte CRLF a LF antes de calcular; coincide en Windows, macOS y Linux.',
        'quality_status': quality['status'],
        'split_status': 'NOT_FROZEN', 'validation_status': 'NO_MODEL_CALIBRATED_OR_VALIDATED',
        'provider_change_reason': 'FastF1 3.9.2 intentó autenticación y no descargó timing en este entorno.',
        'notes': [
            'No se transfieren ni inventan banderas IsAccurate/Deleted/TrackStatus de otro proveedor.',
            'Filtro propio de OpenF1 en results/data_audit/openf1_quality_filter.json; las exclusiones no borran filas.',
            'lane_duration o pit_duration no equivalen automáticamente a pérdida adicional frente a seguir por pista.',
            'Si faltan tiempos, no derivarlos restando del total oficial para luego llamar independiente esa validación.'
        ],
        'source_documentation': 'https://openf1.org/docs/',
    }
    out = root/'results/data_audit'
    out.mkdir(parents=True, exist_ok=True)
    (out/'openf1_acquisition.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (out/'openf1_quality_filter.json').write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding='utf-8')
    return report
