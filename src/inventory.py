"""Inventario de neumáticos y tamaño del espacio de estrategias (MA-05).

OpenF1 no identifica juegos físicos: solo da stints con compuesto y edad inicial. La
reconstrucción de juegos es una INFERENCIA por continuidad de edad (un stint con edad
inicial k continúa un juego del mismo compuesto que llevaba k vueltas). No certifica el
inventario histórico; Pirelli publica la lista oficial (art. 30.5j), que no se obtuvo.
"""
import itertools
import json
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .data import portable_sha256

OPENF1 = 'https://api.openf1.org/v1/'


def fetch_weekend(config: dict, root: Path) -> dict:
    """Sesiones del evento, stints del piloto por sesión y stints de todos en carrera (con caché)."""
    raw = root/'data/raw/openf1_weekend'
    raw.mkdir(parents=True, exist_ok=True)

    def get(endpoint, query, name):
        url = OPENF1 + endpoint + '?' + urlencode(query)
        path, url_path = raw/f'{name}.json', raw/f'{name}.url.txt'
        if path.exists() and url_path.exists() and url_path.read_text(encoding='utf-8') == url:
            return json.loads(path.read_text(encoding='utf-8'))
        request = Request(url, headers={'User-Agent': 'UVG-F1-academic-project/0.1'})
        with urlopen(request, timeout=30) as response:
            value = json.load(response)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        url_path.write_text(url, encoding='utf-8')
        time.sleep(2.1)  # límite gratuito de OpenF1: 30 solicitudes/minuto
        return value

    race = json.loads((root/'data/raw/openf1/sessions.json').read_text(encoding='utf-8'))[0]
    sessions = sorted(get('sessions', {'meeting_key': race['meeting_key']}, 'sessions'), key=lambda s: s['date_start'])
    driver_stints = {s['session_name']: get('stints', {'session_key': s['session_key'],
                                                        'driver_number': config['driver_number']},
                                            f"stints_{s['session_key']}") for s in sessions}
    race_all = get('stints', {'session_key': race['session_key']}, 'race_stints_all_drivers')
    return {'sessions': sessions, 'driver_stints': driver_stints, 'race_stints_all_drivers': race_all,
            'sha256_portable': {p.name: portable_sha256(p) for p in sorted(raw.glob('*.json'))}}


def reconstruct_sets(driver_stints: dict[str, list[dict]], session_order: list[str]) -> tuple[list[dict], list[str]]:
    """Juegos inferidos por continuidad de edad. Devuelve (juegos, avisos de ambigüedad)."""
    sets, notes = [], []
    for session in session_order:
        for stint in sorted(driver_stints.get(session, []), key=lambda s: s['stint_number']):
            compound, age = stint['compound'], stint['tyre_age_at_start']
            laps = stint['lap_end'] - stint['lap_start'] + 1
            if age == 0:
                sets.append({'id': len(sets) + 1, 'compound': compound, 'first_session': session,
                             'laps': laps, 'used_in': [session]})
                continue
            candidates = [s for s in sets if s['compound'] == compound and s['laps'] == age]
            if not candidates:
                sets.append({'id': len(sets) + 1, 'compound': compound, 'first_session': 'previo_desconocido',
                             'laps': age + laps, 'used_in': [session]})
                notes.append(f'{session} stint {stint["stint_number"]}: {compound} con edad {age} sin juego previo compatible')
                continue
            if len(candidates) > 1:
                notes.append(f'{session} stint {stint["stint_number"]}: {len(candidates)} juegos {compound} con '
                             f'{age} vueltas; se asigna el más reciente (ambigüedad sin efecto en conteos)')
            chosen = candidates[-1]
            chosen['laps'] += laps
            chosen['used_in'].append(session)
    return sets, notes


def stint_limits_observed(race_stints_all: list[dict]) -> dict[str, int]:
    """Edad máxima al final de un stint alcanzada por cualquier piloto en la carrera, por compuesto."""
    limits = {}
    for s in race_stints_all:
        if s.get('compound') and s.get('lap_start') and s.get('lap_end'):
            end_age = s['tyre_age_at_start'] + s['lap_end'] - s['lap_start'] + 1
            limits[s['compound']] = max(limits.get(s['compound'], 0), end_age)
    return dict(sorted(limits.items()))


def enumerate_feasible(sets: list[dict], race_laps: int, max_age: dict[str, int], min_stops: int = 1,
                       max_stops: int = 2, min_distinct: int = 2) -> list[dict]:
    """Estrategias factibles con un inventario dado: cada juego se usa a lo sumo una vez.

    Juegos con igual compuesto y edad son intercambiables: se cuentan una sola vez.
    """
    feasible, seen = [], set()
    for stops in range(min_stops, max_stops + 1):
        for order in itertools.permutations(range(len(sets)), stops + 1):
            key_sets = tuple((sets[i]['compound'], sets[i]['initial_age']) for i in order)
            if len({c for c, _ in key_sets}) < min_distinct or any(c not in max_age for c, _ in key_sets):
                continue
            caps = [max_age[c] - a for c, a in key_sets]
            if min(caps) < 1 or sum(caps) < race_laps:
                continue
            for cuts in itertools.combinations(range(1, race_laps), stops):
                bounds = (0,) + cuts + (race_laps,)
                lengths = [b - a for a, b in zip(bounds, bounds[1:])]
                if all(l <= cap for l, cap in zip(lengths, caps)):
                    key = (key_sets, cuts)
                    if key not in seen:
                        seen.add(key)
                        feasible.append({'stops_after_lap': list(cuts),
                                         'stints': [{'compound': c, 'initial_age': a} for c, a in key_sets]})
    return feasible


def summarize_space(feasible: list[dict]) -> dict:
    by_stops = Counter(len(s['stops_after_lap']) for s in feasible)
    by_sequence = Counter('-'.join(f"{t['compound'][0]}{t['initial_age']}" for t in s['stints']) for s in feasible)
    return {'total': len(feasible), 'by_stops': dict(sorted(by_stops.items())),
            'by_set_sequence': dict(by_sequence.most_common())}


HISTORICAL = {'stops_after_lap': [17, 37], 'stints': [{'compound': 'SOFT', 'initial_age': 3},
                                                    {'compound': 'HARD', 'initial_age': 0},
                                                    {'compound': 'SOFT', 'initial_age': 0}]}


def inventory_report(config: dict, tyres: dict, root: Path) -> dict:
    """Reconstrucción del fin de semana, juegos sin usar y tamaño del espacio de búsqueda."""
    weekend = fetch_weekend(config, root)
    order = [s['session_name'] for s in weekend['sessions'] if s['session_name'] != 'Race']
    sets, notes = reconstruct_sets(weekend['driver_stints'], order)
    used_new = Counter(s['compound'] for s in sets if s['first_session'] != 'previo_desconocido')
    allocation = tyres['regulation']['dry_allocation_no_sprint']
    space = {}
    for inventory in ('inventory_main', 'inventory_alternative'):
        for scenario, data in tyres['max_age_scenarios'].items():
            feasible = enumerate_feasible(tyres[inventory]['sets'], config['expected_laps'],
                                          data['max_age_by_compound'], tyres['min_stops'], tyres['max_stops'])
            space[f'{inventory}/{scenario}'] = dict(summarize_space(feasible),
                                                    historical_is_feasible=HISTORICAL in feasible)
    report = {
        'task': 'MA-05', 'status': tyres['status'],
        'sessions': [s['session_name'] for s in weekend['sessions']],
        'driver_stints_by_session': {k: [{x: s[x] for x in ('stint_number', 'compound', 'lap_start', 'lap_end',
                                                              'tyre_age_at_start')} for s in v]
                                     for k, v in weekend['driver_stints'].items()},
        'sets_used_before_race': sets,
        'reconstruction_notes': notes,
        'new_sets_used_before_race': dict(sorted(used_new.items())),
        'new_sets_unused_before_race': {c: allocation[c] - used_new.get(c, 0) for c in sorted(allocation)},
        'race_stint_limits_observed': stint_limits_observed(weekend['race_stints_all_drivers']),
        'search_space': space,
        'sha256_portable_inputs': weekend['sha256_portable'],
    }
    out = root/'results/data_audit'
    out.mkdir(parents=True, exist_ok=True)
    (out/'tyre_inventory.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report
