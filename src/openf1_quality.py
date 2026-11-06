"""Filtro de calidad propio de OpenF1 (MA-02).

OpenF1 no trae las banderas IsAccurate/Deleted/TrackStatus de FastF1. Este filtro
las sustituye con evidencia del propio proveedor (control de carrera, pits y clima)
y deja escrito el motivo de cada decisión. Nunca borra vueltas: solo marca cuáles
entran al ajuste de vueltas normales; todas siguen disponibles para reconstruir la carrera.
"""
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from .data import structural_reasons

FILTER_VERSION = 'openf1-v1'
YELLOW_FLAGS = {'YELLOW', 'DOUBLE YELLOW'}
# date_start de OpenF1 es aproximado (se observaron ±0.3 s); se amplía la ventana
# de cada vuelta para no dejar fuera un evento por ese desfase.
WINDOW_TOLERANCE_S = 1.0
RAIN_LOOKBACK_S = 60.0  # el clima se muestrea aproximadamente cada minuto
DELETED_PATTERN = re.compile(
    r'^CAR (\d+) \((\w+)\) TIME (\d+):(\d{2}\.\d{3}) DELETED\b.*?(?:\bLAP (\d+)\b|\(NEXT LAP\))')

RULES = {
    'missing_or_invalid_*': 'Excluye: falta o es inválido un campo necesario (no se imputa).',
    'first_lap': 'Excluye: vuelta de arranque; su pérdida se modela aparte.',
    'pit_in_lap': 'Excluye: vuelta de entrada a pits (registro en pit).',
    'pit_out_lap': 'Excluye: vuelta de salida de pits (is_pit_out_lap).',
    'unsupported_or_unknown_compound': 'Excluye: compuesto distinto de SOFT/MEDIUM/HARD.',
    'time_deleted_race_control': 'Excluye: control de carrera borró el tiempo del piloto en esa vuelta.',
    'track_neutralization': 'Excluye: la vuelta coincide con Safety Car, VSC, bandera roja o amarilla de pista completa.',
    'rainfall': 'Excluye: el clima registra lluvia durante la vuelta.',
    'missing_lap_window': 'Excluye: sin date_start/lap_duration no se pueden cruzar eventos.',
    'local_yellow_overlap': 'Advierte: amarilla local (un sector) activa durante la vuelta; no excluye.',
    'unpaired_clear_in_lap': 'Advierte: CLEAR de sector sin amarilla previa registrada; posible amarilla no publicada.',
    'deleted_time_mismatch': 'Advierte: el tiempo citado en el mensaje de borrado no coincide con lap_duration.',
    'unclosed_neutralization': 'Advierte: hay una neutralización sin cierre; se extendió hasta el final (conservador).',
}


def _t(value: str) -> datetime:
    return datetime.fromisoformat(value)


def lap_windows(laps_raw: list[dict]) -> dict[int, tuple[datetime, datetime]]:
    windows = {}
    for lap in laps_raw:
        if lap.get('date_start') and lap.get('lap_duration'):
            start = _t(lap['date_start'])
            windows[lap['lap_number']] = (start, start + timedelta(seconds=lap['lap_duration']))
    return windows


def deleted_laps(race_control: list[dict], driver_number: int, lap_durations: dict[int, float]) -> dict:
    """Vueltas con tiempo borrado según los mensajes de control de carrera.

    '(NEXT LAP)' se resuelve como la vuelta siguiente al último borrado del mismo auto.
    El tiempo citado en el mensaje se contrasta con lap_duration.
    """
    found, last_lap = {}, {}
    for message in sorted(race_control, key=lambda m: m['date']):
        match = DELETED_PATTERN.match(message.get('message') or '')
        if not match:
            continue
        car = int(match.group(1))
        time_s = int(match.group(3)) * 60 + float(match.group(4))
        lap = int(match.group(5)) if match.group(5) else (last_lap[car] + 1 if car in last_lap else None)
        if lap is not None:
            last_lap[car] = lap
        if car != driver_number:
            continue
        observed = lap_durations.get(lap)
        found[lap] = {'message': message['message'], 'date': message['date'], 'cited_time_s': time_s,
                      'time_matches_lap_duration': observed is not None and abs(observed - time_s) < 0.0005}
    return found


def flag_intervals(race_control: list[dict], session_end: datetime) -> tuple[list[dict], list[dict]]:
    """Intervalos de amarilla local y de neutralización de pista, más anomalías del registro.

    Regla conservadora: una neutralización de pista se cierra solo con GREEN o CHEQUERED
    de pista; si nunca se cierra, se extiende hasta el final de la sesión.
    """
    intervals, anomalies, open_local, open_track = [], [], {}, None

    def close_all(t):
        nonlocal open_track
        for key in list(open_local):
            intervals.append(dict(open_local.pop(key), end=t, closed=True))
        if open_track:
            intervals.append(dict(open_track, end=t, closed=True))
            open_track = None

    for message in sorted(race_control, key=lambda m: m['date']):
        t, flag, scope = _t(message['date']), message.get('flag'), message.get('scope')
        text = message.get('message') or ''
        is_track_neutralization = (
            flag == 'RED' or (flag in YELLOW_FLAGS and scope == 'Track')
            or (message.get('category') == 'SafetyCar' and 'DEPLOYED' in text))
        if is_track_neutralization:
            if open_track is None:
                open_track = {'kind': 'track_neutralization', 'start': t, 'label': text}
        elif flag in YELLOW_FLAGS and scope == 'Sector':
            key = message.get('sector')
            open_local.setdefault(key, {'kind': 'local_yellow', 'start': t, 'label': text})
        elif flag == 'CLEAR' and scope == 'Sector':
            key = message.get('sector')
            if key in open_local:
                intervals.append(dict(open_local.pop(key), end=t, closed=True))
            else:
                anomalies.append({'kind': 'unpaired_clear', 'date': t, 'label': text})
        elif flag in {'GREEN', 'CHEQUERED'} and scope == 'Track' and 'PIT EXIT' not in text:
            # 'GREEN LIGHT - PIT EXIT OPEN' solo abre la salida de pits; no reanuda la carrera.
            close_all(t)
    for key in list(open_local):
        intervals.append(dict(open_local.pop(key), end=session_end, closed=False))
    if open_track:
        intervals.append(dict(open_track, end=session_end, closed=False))
    return intervals, anomalies


def _overlaps(a_start, a_end, b_start, b_end) -> bool:
    return a_start <= b_end and a_end >= b_start


def apply_openf1_quality_filter(records: list[dict], laps_raw: list[dict], race_control: list[dict],
                                weather: list[dict], driver_number: int) -> tuple[list[dict], list[dict], dict]:
    """Devuelve (filas anotadas, tabla de exclusiones, reporte). No modifica ni borra filas."""
    windows = lap_windows(laps_raw)
    tolerance = timedelta(seconds=WINDOW_TOLERANCE_S)
    session_end = max(end for _, end in windows.values()) if windows else datetime.max
    durations = {lap['lap_number']: lap.get('lap_duration') for lap in laps_raw}
    deleted = deleted_laps(race_control, driver_number, durations)
    intervals, anomalies = flag_intervals(race_control, session_end)
    rain = [_t(w['date']) for w in weather if (w.get('rainfall') or 0) > 0]

    annotated, table = [], []
    reason_counts, warning_counts = Counter(), Counter()
    for row in records:
        lap = int(row['lap_number'])
        reasons, warnings, evidence = structural_reasons(row), [], []
        window = windows.get(lap)
        if lap in deleted:
            reasons.append('time_deleted_race_control')
            evidence.append(deleted[lap]['message'])
            if not deleted[lap]['time_matches_lap_duration']:
                warnings.append('deleted_time_mismatch')
        if window is None:
            reasons.append('missing_lap_window')
        else:
            start, end = window[0] - tolerance, window[1] + tolerance
            for interval in intervals:
                if _overlaps(interval['start'], interval['end'], start, end):
                    if interval['kind'] == 'track_neutralization':
                        reasons.append('track_neutralization')
                    else:
                        warnings.append('local_yellow_overlap')
                    if not interval['closed']:
                        warnings.append('unclosed_neutralization')
                    evidence.append(f"{interval['label']} ({interval['start']:%H:%M:%S}-{interval['end']:%H:%M:%S} UTC)")
            for anomaly in anomalies:
                if start <= anomaly['date'] <= end:
                    warnings.append('unpaired_clear_in_lap')
                    evidence.append(f"{anomaly['label']} ({anomaly['date']:%H:%M:%S} UTC, sin amarilla previa)")
            if any(window[0] - timedelta(seconds=RAIN_LOOKBACK_S) <= t <= window[1] for t in rain):
                reasons.append('rainfall')
        reasons, warnings = list(dict.fromkeys(reasons)), list(dict.fromkeys(warnings))
        reason_counts.update(reasons)
        warning_counts.update(warnings)
        eligible = not reasons
        annotated.append(dict(row, calibration_eligible=eligible, exclusion_reasons=';'.join(reasons),
                              quality_warnings=';'.join(warnings),
                              track_limits_deleted_rc=lap in deleted,
                              quality_note=f'REVIEWED_{FILTER_VERSION}_PENDING_PEER_REVIEW'))
        table.append({'lap_number': lap, 'stint': row.get('stint'), 'compound': row.get('compound'),
                      'tyre_life_laps': row.get('tyre_life_laps'), 'calibration_eligible': eligible,
                      'exclusion_reasons': ';'.join(reasons), 'quality_warnings': ';'.join(warnings),
                      'evidence': ' | '.join(dict.fromkeys(evidence))})

    coverage = defaultdict(list)
    for row in annotated:
        if row['calibration_eligible']:
            coverage[(row['stint'], row['compound'])].append(row)
    report = {
        'filter_version': FILTER_VERSION,
        'rules': RULES,
        'window_tolerance_s': WINDOW_TOLERANCE_S,
        'rows_total': len(annotated),
        'eligible_normal_laps': sum(r['calibration_eligible'] for r in annotated),
        'excluded_laps': {r['lap_number']: r['exclusion_reasons'] for r in table if not r['calibration_eligible']},
        'warning_laps': {r['lap_number']: r['quality_warnings'] for r in table if r['quality_warnings']},
        'exclusion_reason_counts': dict(reason_counts),
        'warning_counts': dict(warning_counts),
        'eligible_coverage': [
            {'stint': stint, 'compound': compound, 'laps': len(rows),
             'lap_range': [min(int(r['lap_number']) for r in rows), max(int(r['lap_number']) for r in rows)],
             'tyre_life_range': [min(int(r['tyre_life_laps']) for r in rows), max(int(r['tyre_life_laps']) for r in rows)]}
            for (stint, compound), rows in sorted(coverage.items(), key=lambda kv: kv[0][0])],
        'deleted_laps': deleted,
        'flag_intervals': [dict(i, start=i['start'].isoformat(), end=i['end'].isoformat()) for i in intervals],
        'race_control_anomalies': [dict(a, date=a['date'].isoformat()) for a in anomalies],
        'rainfall_samples': len(rain),
        'not_used': ['Atípicos estadísticos: no se excluyen (decisión 2026-11-06; vueltas 39-40 son comportamiento real).',
                     'Banderas azules: no indican de forma verificable pérdida de VER.'],
        'status': 'PENDING_PEER_REVIEW_LUIS_PEDRO',
    }
    return annotated, table, report
