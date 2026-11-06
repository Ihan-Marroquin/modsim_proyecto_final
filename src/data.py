"""Adquisición del referente y auditoría conservadora; no ajusta el modelo."""
import csv
import hashlib
import json
import math
import platform
from collections import Counter, defaultdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path


def is_true(value) -> bool:
    return str(value).strip().lower() in {'true', '1', '1.0'}


def is_missing(value) -> bool:
    return value is None or str(value).strip().lower() in {'', 'nan', 'none', '<na>'}


def structural_reasons(row: dict) -> list[str]:
    """Comprobaciones válidas para cualquier proveedor: campos, arranque, pits y compuesto."""
    reasons = []
    for field in ('lap_number', 'lap_time_s', 'tyre_life_laps', 'stint'):
        try:
            if not math.isfinite(float(row[field])) or float(row[field]) <= 0:
                reasons.append(f'missing_or_invalid_{field}')
        except (KeyError, TypeError, ValueError):
            reasons.append(f'missing_or_invalid_{field}')
    if str(row.get('lap_number')) in {'1', '1.0'}:
        reasons.append('first_lap')
    if not is_missing(row.get('pit_in_time_s')):
        reasons.append('pit_in_lap')
    elif is_true(row.get('is_pit_in_lap')):
        reasons.append('pit_in_lap')
    if not is_missing(row.get('pit_out_time_s')):
        reasons.append('pit_out_lap')
    elif is_true(row.get('is_pit_out_lap')):
        reasons.append('pit_out_lap')
    if row.get('compound') not in {'SOFT', 'MEDIUM', 'HARD'}:
        reasons.append('unsupported_or_unknown_compound')
    return reasons


def exclusion_reasons(row: dict) -> list[str]:
    """Filtro conservador para FastF1: exige sus banderas de calidad. No usar con OpenF1."""
    reasons = structural_reasons(row)
    if is_true(row.get('deleted')):
        reasons.append('deleted_lap')
    if is_true(row.get('fastf1_generated')):
        reasons.append('fastf1_generated')
    if not is_true(row.get('is_accurate')):
        reasons.append('not_flagged_accurate')
    if str(row.get('track_status', '')).strip() != '1':
        reasons.append('not_exclusively_green')
    return reasons


def portable_sha256(path: Path) -> str:
    """Huella SHA-256 que no depende del sistema operativo.

    Windows guarda los saltos de línea como CRLF y macOS/Linux como LF, así que el
    mismo contenido produce bytes distintos. Se convierte CRLF a LF antes de calcular
    la huella para que Windows, macOS y Linux obtengan el mismo valor. Para archivos
    de texto (JSON/CSV) del proyecto; no usar en binarios.
    """
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def write_csv(path: Path, rows: list[dict], fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and fieldnames is None:
        raise ValueError(f'No se puede inferir esquema vacío: {path}')
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def audit_records(rows: list[dict]) -> tuple[list[dict], dict]:
    annotated, counts, stints = [], Counter(), defaultdict(list)
    for row in rows:
        reasons = exclusion_reasons(row)
        counts.update(reasons)
        record = dict(row, calibration_eligible=not reasons, exclusion_reasons=';'.join(reasons))
        annotated.append(record)
        stints[str(row.get('stint'))].append(row)
    summaries = []
    for key, values in stints.items():
        summaries.append({'stint': key, 'compounds': sorted({v['compound'] for v in values}),
                          'laps': [float(v['lap_number']) for v in values],
                          'eligible_rows': sum(not exclusion_reasons(v) for v in values)})
    laps = [r.get('lap_number') for r in rows]
    audit = {'rows_total': len(rows), 'eligible_normal_laps': sum(r['calibration_eligible'] for r in annotated),
             'exclusion_reason_counts': dict(counts), 'stints': summaries,
             'duplicate_lap_numbers': [x for x, n in Counter(laps).items() if n > 1],
             'track_status_counts': dict(Counter(str(r.get('track_status')) for r in rows)),
             'warning': 'Exclusiones solo para ajustar vueltas normales. Conservar todas para la reconstrucción.'}
    return annotated, audit


def download_case(config: dict, root: Path) -> dict:
    try:
        import fastf1
        import pandas as pd
    except ImportError as exc:
        raise SystemExit('Instale dependencias con python -m pip install -r requirements.txt') from exc
    cache = root/'data/cache'
    cache.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache))
    session = fastf1.get_session(config['year'], config['event'], config['session'])
    session.load(laps=True, telemetry=False, weather=True, messages=True)
    source = session.laps
    frame = pd.DataFrame(index=source.index)
    names = {'Driver': 'driver', 'DriverNumber': 'driver_number', 'LapNumber': 'lap_number',
             'Stint': 'stint', 'Compound': 'compound', 'TyreLife': 'tyre_life_laps',
             'FreshTyre': 'fresh_tyre', 'TrackStatus': 'track_status', 'Deleted': 'deleted',
             'IsAccurate': 'is_accurate', 'FastF1Generated': 'fastf1_generated'}
    times = {'LapTime': 'lap_time_s', 'PitInTime': 'pit_in_time_s', 'PitOutTime': 'pit_out_time_s',
             'Time': 'session_time_s', 'LapStartTime': 'lap_start_time_s'}
    for original, normalized in names.items():
        frame[normalized] = source[original] if original in source else None
    for original, normalized in times.items():
        frame[normalized] = source[original].dt.total_seconds() if original in source else None
    stem = f"{config['year']}_{config['event'].lower()}_{config['session'].lower()}"
    raw = root/'data/raw'
    raw.mkdir(parents=True, exist_ok=True)
    all_path = raw/f'{stem}_all_laps.csv'
    target_path = raw/f"{stem}_{config['driver'].lower()}_laps.csv"
    frame.to_csv(all_path, index=False)
    frame.loc[frame.driver == config['driver']].to_csv(target_path, index=False)
    session.weather_data.to_csv(raw/f'{stem}_weather.csv', index=False)
    session.track_status.to_csv(raw/f'{stem}_track_status.csv', index=False)
    with target_path.open(encoding='utf-8', newline='') as handle:
        target_rows = list(csv.DictReader(handle))
    if not target_rows:
        raise ValueError('No hay vueltas del piloto objetivo; no fabricar datos de reemplazo')
    annotated, audit = audit_records(target_rows)
    processed = root/'data/processed'
    write_csv(processed/'target_laps_annotated.csv', annotated)
    write_csv(processed/'normal_laps_candidate.csv', [r for r in annotated if r['calibration_eligible']],
              fieldnames=list(annotated[0]))
    # Propuesta de holdout: solo etiquetas. Mario y Luis Pedro deben confirmar cobertura.
    eligible = [r for r in annotated if r['calibration_eligible']]
    last_stint = max(float(r['stint']) for r in eligible) if eligible else None
    split_rows = [dict(r, proposed_split='validation' if float(r['stint']) == last_stint else 'training')
                  for r in eligible]
    write_csv(processed/'split_proposal_NOT_APPROVED.csv', split_rows,
              fieldnames=list(annotated[0])+['proposed_split'])
    observed_sum = math.fsum(float(r['lap_time_s']) for r in target_rows if not is_missing(r['lap_time_s']))
    report = {
        'source_kind': 'PUBLIC_OBSERVATION_FASTF1_PARSED_EXPORT',
        'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
        'python_version': platform.python_version(), 'fastf1_version': version('fastf1'),
        'case': config, 'audit': audit,
        'all_drivers_rows': len(frame),
        'target_lap_sum_s': observed_sum,
        'difference_from_official_s': observed_sum-config['official_winner_time_s'],
        'coverage_matches_expected': len(target_rows) == config['expected_laps'],
        'data_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [all_path, target_path]},
        'data_sha256_portable': {p.name: portable_sha256(p) for p in [all_path, target_path]},
        'split_status': 'PROPOSED_ONLY_NOT_FROZEN_OR_USED_FOR_CALIBRATION',
        'validation_status': 'NO_MODEL_CALIBRATED_OR_VALIDATED',
        'rights_note': 'FastF1 es un proveedor no oficial; su licencia de software no establece por sí sola derechos sobre los datos.'
    }
    result_dir = root/'results/data_audit'
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir/'acquisition.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report
