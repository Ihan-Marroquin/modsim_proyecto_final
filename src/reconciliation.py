"""Conciliación de tiempos OpenF1 contra una referencia independiente (MA-02, +0.475 s).

Compara vuelta por vuelta los tiempos de OpenF1 con los de Jolpica (API compatible con
Ergast, derivada del cronometraje oficial) y contrasta la suma con el tiempo FIA.
No modifica los datos de OpenF1: produce una tabla y un reporte aparte.
"""
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .data import portable_sha256, write_csv

JOLPICA_BASE = 'https://api.jolpi.ca/ergast/f1/'
MATCH_TOLERANCE_S = 0.0005  # ambas fuentes publican milésimas


def parse_race_time(text: str) -> float:
    """'1:37.284' o '1:31:44.742' → segundos."""
    seconds = 0.0
    for part in text.strip().split(':'):
        seconds = seconds * 60 + float(part)
    return seconds


def compare_lap_times(observed: dict[int, float], reference: dict[int, float],
                      tolerance: float = MATCH_TOLERANCE_S) -> tuple[list[dict], dict]:
    """Diferencia por vuelta (observado − referencia) y resumen. No imputa vueltas faltantes."""
    rows = []
    for lap in sorted(set(observed) | set(reference)):
        a, b = observed.get(lap), reference.get(lap)
        diff = None if a is None or b is None else a - b
        rows.append({'lap_number': lap, 'openf1_s': a, 'reference_s': None if b is None else round(b, 3),
                     'difference_s': None if diff is None else round(diff, 3),
                     'matches': diff is not None and abs(diff) < tolerance})
    differing = [r for r in rows if r['difference_s'] is not None and not r['matches']]
    summary = {
        'laps_compared': sum(r['difference_s'] is not None for r in rows),
        'laps_matching': sum(r['matches'] for r in rows),
        'laps_only_in_openf1': [r['lap_number'] for r in rows if r['reference_s'] is None],
        'laps_only_in_reference': [r['lap_number'] for r in rows if r['openf1_s'] is None],
        'differing_laps': {r['lap_number']: r['difference_s'] for r in differing},
        'sum_openf1_s': round(math.fsum(v for v in observed.values()), 3),
        'sum_reference_s': round(math.fsum(v for v in reference.values()), 3),
        'sum_of_differences_s': round(math.fsum(r['difference_s'] for r in differing), 3),
    }
    return rows, summary


def _fetch_jolpica(path: str, query: dict, raw: Path, name: str, log: list) -> dict:
    url = JOLPICA_BASE + path + ('?' + urlencode(query) if query else '')
    file, url_file = raw/f'{name}.json', raw/f'{name}.url.txt'
    if file.exists() and url_file.exists() and url_file.read_text(encoding='utf-8') == url:
        log.append({'url': url, 'cached': True})
        return json.loads(file.read_text(encoding='utf-8'))
    for attempt in range(3):
        try:
            request = Request(url, headers={'User-Agent': 'UVG-F1-academic-project/0.1'})
            with urlopen(request, timeout=30) as response:
                value = json.load(response)
            file.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
            url_file.write_text(url, encoding='utf-8')
            log.append({'url': url, 'cached': False})
            time.sleep(1.0)  # límite público: 4 solicitudes/s y 500/hora
            return value
        except HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError('No se obtuvo respuesta de Jolpica')


def reconcile_case(config: dict, root: Path) -> dict:
    """Requiere haber ejecutado antes `python main.py download` (usa data/raw/openf1)."""
    openf1_laps = json.loads((root/'data/raw/openf1/laps.json').read_text(encoding='utf-8'))
    openf1_pits = json.loads((root/'data/raw/openf1/pit.json').read_text(encoding='utf-8'))
    raw = root/'data/raw/jolpica'
    raw.mkdir(parents=True, exist_ok=True)
    log = []
    season, rnd, driver = config['year'], config['jolpica_round'], config['jolpica_driver_id']
    laps_doc = _fetch_jolpica(f'{season}/{rnd}/drivers/{driver}/laps.json', {'limit': 100}, raw, 'laps', log)
    results_doc = _fetch_jolpica(f'{season}/{rnd}/results.json', {'limit': 30}, raw, 'results', log)
    pits_doc = _fetch_jolpica(f'{season}/{rnd}/drivers/{driver}/pitstops.json', {}, raw, 'pitstops', log)

    race = laps_doc['MRData']['RaceTable']['Races'][0]
    reference = {int(lap['number']): parse_race_time(lap['Timings'][0]['time']) for lap in race['Laps']}
    observed = {lap['lap_number']: lap['lap_duration'] for lap in openf1_laps}
    rows, summary = compare_lap_times(observed, reference)

    results = results_doc['MRData']['RaceTable']['Races'][0]['Results']
    target = next(r for r in results if r['Driver']['driverId'] == driver)
    official_s = int(target['Time']['millis']) / 1000
    pit_reference = {int(p['lap']): float(p['duration'])
                     for p in pits_doc['MRData']['RaceTable']['Races'][0]['PitStops']}
    pits = [{'lap_number': p['lap_number'], 'openf1_lane_duration_s': p.get('lane_duration'),
             'reference_duration_s': pit_reference.get(p['lap_number'])} for p in openf1_pits]

    write_csv(root/'data/processed/lap_time_reconciliation.csv', rows)
    report = {
        'source_kind': 'RECONCILIATION_OPENF1_VS_JOLPICA_AND_FIA',
        'computed_at_utc': datetime.now(timezone.utc).isoformat(),
        'reference_source': config.get('reference_lap_source'),
        'official_total_config_s': config['official_winner_time_s'],
        'official_total_jolpica_s': official_s,
        'lap_comparison': summary,
        'reference_sum_equals_official_total': abs(summary['sum_reference_s'] - config['official_winner_time_s']) < MATCH_TOLERANCE_S,
        'openf1_minus_official_s': round(summary['sum_openf1_s'] - config['official_winner_time_s'], 3),
        'differing_laps_detail': [r for r in rows if r['difference_s'] is not None and not r['matches']],
        'pit_durations': pits,
        'requests': log,
        'sha256_portable': {p.name: portable_sha256(p) for p in sorted(raw.glob('*.json'))},
        'note': 'Los datos OpenF1 no se modifican. Ver docs/conciliacion_tiempos.md para la interpretación.',
    }
    out = root/'results/data_audit'
    out.mkdir(parents=True, exist_ok=True)
    (out/'reconciliation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report
