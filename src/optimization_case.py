"""Búsqueda reproducible en el inventario inferido de Bahréin 2024."""
import json
import random
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from statistics import mean

from .constraints import validate_strategy
from .data import portable_sha256, write_csv
from .domain import Constraints, Strategy, strategy_from_dict
from .inventory import enumerate_feasible
from .model import get_historical_strategy, load_calibrated_parameters
from .optimization import SearchSettings, anneal
from .simulation import simulate


def strategy_key(strategy: Strategy) -> tuple:
    return strategy.stops_after_lap, strategy.stints


def build_catalog(tyres: dict, race_laps: int, inventory: str, scenario: str):
    """Conserva la multiplicidad de juegos por compuesto y edad antes de deduplicar."""
    sets = tyres[inventory]['sets']
    ages = tyres['max_age_scenarios'][scenario]['max_age_by_compound']
    min_distinct = tyres['regulation']['min_distinct_dry_specifications_in_race']
    limits = Constraints(
        race_laps=race_laps,
        allowed_compounds=tuple(tyres['allowed_compounds']),
        min_stops=tyres['min_stops'],
        max_stops=tyres['max_stops'],
        min_distinct_compounds=min_distinct,
        max_age_by_compound=ages,
        max_sets_by_compound=dict(Counter(item['compound'] for item in sets)),
    )
    available = {n: {} for n in range(limits.min_stops, limits.max_stops + 1)}
    eligible = [item for item in sets if item['compound'] in limits.allowed_compounds]
    for entry in enumerate_feasible(eligible, race_laps, ages, limits.min_stops,
                                    limits.max_stops, min_distinct):
        strategy = strategy_from_dict(dict(entry, name='candidate_ver_bahrain_2024'))
        violations = validate_strategy(strategy, limits)
        if violations:
            raise ValueError(f'El inventario y las restricciones discrepan: {violations}')
        available[len(strategy.stops_after_lap)][strategy_key(strategy)] = strategy
    return limits, available


def make_proposal(catalog: dict, global_probability: float):
    """Mueve un corte, cambia la secuencia de juegos o visita cualquier estado del grupo."""
    if not catalog or not 0 < global_probability <= 1:
        raise ValueError('Se requiere un catálogo no vacío y una probabilidad global en (0, 1]')
    strategies = tuple(catalog.values())
    sequences = tuple(dict.fromkeys(s.stints for s in strategies))

    def propose(current, rng):
        if rng.random() < global_probability:
            return rng.choice(strategies)
        stops, stints = strategy_key(current)
        slot = rng.randrange(len(stops) + 1)
        if slot == len(stops):
            stints = rng.choice(sequences)
        else:
            shifted = stops[slot] + rng.choice((-3, -2, -1, 1, 2, 3))
            stops = stops[:slot] + (shifted,) + stops[slot + 1:]
        return catalog.get((stops, stints))

    return propose


def run_calibrated_search(root: Path, out: Path) -> dict:
    paths = {name: root / 'configs' / f'{name}.json' for name in
             ('optimizer', 'case_bahrain_2024', 'params_bahrain_2024', 'tyre_inventory_bahrain_2024')}
    config, case, tyres = (json.loads(paths[k].read_text(encoding='utf-8')) for k in
                          ('optimizer', 'case_bahrain_2024', 'tyre_inventory_bahrain_2024'))
    seeds = config['pilot_seeds'] + config['search_seeds'] + config['evaluation_seeds_reserved']
    if len(seeds) != len(set(seeds)):
        raise ValueError('Las semillas de pilotos, búsqueda y evaluación deben ser distintas')
    params = load_calibrated_parameters(paths['params_bahrain_2024'], config['trend_scenario'])
    inventory, scenario = config['inventory'], tyres['main_search_scenario']
    limits, groups = build_catalog(tyres, case['expected_laps'], inventory, scenario)
    baseline = get_historical_strategy()
    if strategy_key(baseline) not in groups.get(len(baseline.stops_after_lap), {}):
        raise ValueError('La histórica debe pertenecer al mismo espacio factible que la candidata')
    baseline_time = simulate(baseline, params, limits)['total_time_s']
    tolerance = config['exact_tolerance_s']
    out.mkdir(parents=True, exist_ok=True)
    pilot_rows, search_rows, references, pilot_summaries = [], [], {}, {}
    results = []
    for stops, catalog in groups.items():
        if not catalog:
            continue
        strategies = tuple(catalog.values())
        reference, reference_time = min(
            ((strategy, simulate(strategy, params, limits)['total_time_s']) for strategy in strategies),
            key=lambda pair: pair[1],
        )
        references[stops] = {'strategy': asdict(reference), 'time_s': reference_time,
                             'objective_evaluations': len(catalog)}
        propose = make_proposal(catalog, config['global_move_probability'])

        def run(seed, settings_name, settings):
            rng = random.Random(seed)
            initial = rng.choice(strategies)
            result = anneal(initial, params, limits, settings, rng, propose)
            best = result['strategy']
            gap = result['best_time_s'] - reference_time
            row = {
                'stops': stops, 'seed': seed, 'settings': settings_name,
                'iterations': settings.iterations,
                'initial_time_s': result['initial_time_s'], 'best_time_s': result['best_time_s'],
                'objective_evaluations': result['objective_evaluations'],
                'gap_to_reference_s': gap, 'reached_reference': abs(gap) <= tolerance,
                'initial_stop_laps': json.dumps(initial.stops_after_lap),
                'initial_stints': json.dumps([asdict(stint) for stint in initial.stints]),
                'stop_laps': json.dumps(best.stops_after_lap),
                'stints': json.dumps([asdict(stint) for stint in best.stints]),
            }
            return result, row

        pilots = []
        for name, values in config['pilot_settings'].items():
            settings = SearchSettings(**values)
            rows = [run(seed, name, settings)[1] for seed in config['pilot_seeds']]
            pilot_rows.extend(rows)
            pilots.append({
                'name': name, 'settings': asdict(settings),
                'exact_fraction': mean(row['reached_reference'] for row in rows),
                'mean_gap_s': mean(row['gap_to_reference_s'] for row in rows),
                'mean_evaluations': mean(row['objective_evaluations'] for row in rows),
            })
        qualified = [p for p in pilots if p['exact_fraction'] >= config['pilot_min_exact_fraction']]
        if qualified:
            selected = min(qualified, key=lambda p: (p['mean_evaluations'], p['mean_gap_s'], p['name']))
        else:
            selected = min(pilots, key=lambda p: (-p['exact_fraction'], p['mean_gap_s'],
                                                 p['mean_evaluations'], p['name']))
        pilot_summaries[stops] = {'profiles': pilots, 'selected': selected['name'],
                                  'met_pilot_threshold': bool(qualified)}
        settings = SearchSettings(**selected['settings'])
        for seed in config['search_seeds']:
            result, row = run(seed, selected['name'], settings)
            search_rows.append(row)
            write_csv(out / f'trace_{stops}_stops_{seed}.csv', result['history'])
            results.append((stops, seed, result))

    minimum = min(r['best_time_s'] for _, _, r in results)
    stops, seed, result = min(
        (entry for entry in results if entry[2]['best_time_s'] <= minimum + tolerance),
        key=lambda entry: (entry[0], entry[1]),
    )
    best_time = result['best_time_s']
    candidate = result['strategy']
    strict_limits, strict_groups = build_catalog(tyres, case['expected_laps'], inventory,
                                                 'strict_model_coverage')
    strict_times = [simulate(s, params, strict_limits)['total_time_s']
                    for catalog in strict_groups.values() for s in catalog.values()]
    candidate_run = simulate(candidate, params, limits)
    report = {
        'case': {'event': case['event'], 'year': case['year'], 'driver': case['driver']},
        'inventory': inventory, 'inventory_scenario': scenario, 'inventory_status': tyres['status'],
        'trend_scenario': config['trend_scenario'], 'parameter_provenance': params.provenance,
        'input_sha256_portable': {name: portable_sha256(path) for name, path in paths.items()},
        'objective': {'mode': 'deterministic', 'degradation_multiplier': 1.0},
        'feasible_by_stops': {n: len(catalog) for n, catalog in groups.items()},
        'reference_by_stops': references, 'pilot_by_stops': pilot_summaries,
        'strict_diagnostic': {'count_by_stops': {n: len(c) for n, c in strict_groups.items()},
                              'best_time_s': min(strict_times) if strict_times else None},
        'historical': {'strategy': asdict(baseline), 'time_s': baseline_time},
        'frozen_candidate': {'strategy': asdict(candidate), 'seed': seed, 'time_s': best_time,
                             'gap_to_reference_s': best_time - references[stops]['time_s'],
                             'laps_with_age_over_20': [r['lap'] for r in candidate_run['laps']
                                                       if r['tyre_age_end_laps'] > 20]},
        'predicted_saving_s': baseline_time - best_time,
        'search_run_count': len(search_rows),
        'search_runs_at_reference': sum(row['reached_reference'] for row in search_rows),
        'max_search_gap_s': max(row['gap_to_reference_s'] for row in search_rows),
        'evaluation_seeds_reserved': config['evaluation_seeds_reserved'],
    }
    write_csv(out / 'pilot_runs.csv', pilot_rows)
    write_csv(out / 'search_runs.csv', search_rows)
    write_csv(out / 'candidate_trace.csv', result['history'])
    for filename, data in [('candidate.json', asdict(candidate)), ('summary.json', report)]:
        (out / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report
