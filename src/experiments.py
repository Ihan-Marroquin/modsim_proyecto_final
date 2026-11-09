"""Experimentos finales A/B/C/D con la candidata congelada (LP-04) y su análisis (LP-05).

| Condición | Estrategia | Entorno |
|---|---|---|
| A | Histórica (`get_historical_strategy`) | Parámetros base, degradación ×1.00 |
| B | Candidata congelada (`docs/evidence/optimization/candidate.json`) | Igual que A |
| C | Histórica | Degradación ×1.20 |
| D | La misma candidata de B | Degradación ×1.20 |

Cada condición usa las 30 semillas reservadas 3300–3329 de `configs/optimizer.json`, distintas
de las de pilotos y búsqueda. A y B comparten la semilla de cada réplica, igual que C y D, para
formar diferencias pareadas. Dentro de una condición las réplicas son independientes.

Signos del plan: mejora_s = tiempo_base − tiempo_candidata y
mejora_pct = 100 · mejora_s / tiempo_base. Una mejora positiva favorece a la candidata.

El ruido del simulador es aditivo, N(0, σ²) por vuelta, e igual para ambas estrategias. Con
la misma semilla ambas reciben las mismas 57 perturbaciones y el ruido se cancela en la
diferencia salvo redondeo. Por eso la dispersión pareada es casi cero y **no mide la
incertidumbre de los parámetros ni del modelo**. Este módulo añade aparte una propagación
analítica de los errores estándar de la calibración y la sensibilidad a la tendencia.
"""
import json
import math
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev

from .calibration import fit_parameters, load_inputs, t975
from .constraints import validate_strategy
from .data import portable_sha256, write_csv
from .domain import ModelParameters, Strategy, strategy_from_dict
from .model import get_historical_strategy, load_calibrated_parameters
from .optimization_case import build_catalog, strategy_key
from .partition import _git_state
from .simulation import simulate

CANDIDATE_FILE = 'docs/evidence/optimization/candidate.json'
SUMMARY_FILE = 'docs/evidence/optimization/summary.json'
PARAMS_FILE = 'configs/params_bahrain_2024.json'
SENSITIVITY_MULTIPLIER = 1.20
CONDITIONS = (
    {'condition': 'A', 'role': 'historical', 'degradation_multiplier': 1.0},
    {'condition': 'B', 'role': 'candidate', 'degradation_multiplier': 1.0},
    {'condition': 'C', 'role': 'historical', 'degradation_multiplier': SENSITIVITY_MULTIPLIER},
    {'condition': 'D', 'role': 'candidate', 'degradation_multiplier': SENSITIVITY_MULTIPLIER},
)
PAIRS = (('A', 'B'), ('C', 'D'))
TREND_SCENARIOS = ('trend_fuel_reference', 'trend_zero', 'trend_double')
MULTIPLIER_GRID = (0.80, 0.90, 1.00, 1.05, 1.10, 1.15, 1.20, 1.30)


def describe(values: list[float]) -> dict:
    """Media, desviación muestral e IC 95 % t de la media (gl = n − 1)."""
    n = len(values)
    if n < 2:
        raise ValueError('Se necesitan al menos dos valores')
    sd = stdev(values)
    m = mean(values)
    half = t975(n - 1) * sd / math.sqrt(n)
    return {'n': n, 'mean': m, 'sd': sd, 'min': min(values), 'max': max(values),
            'se_mean': sd / math.sqrt(n), 'ci95_mean': [m - half, m + half]}


def load_protocol(root: Path) -> dict:
    """Carga y comprueba todo lo que debe quedar fijo antes de evaluar."""
    optimizer = json.loads((root / 'configs/optimizer.json').read_text(encoding='utf-8'))
    case = json.loads((root / 'configs/case_bahrain_2024.json').read_text(encoding='utf-8'))
    tyres = json.loads((root / 'configs/tyre_inventory_bahrain_2024.json').read_text(encoding='utf-8'))
    summary = json.loads((root / SUMMARY_FILE).read_text(encoding='utf-8'))
    seeds = list(optimizer['evaluation_seeds_reserved'])
    used = set(optimizer['pilot_seeds']) | set(optimizer['search_seeds'])
    if len(seeds) != 30 or len(set(seeds)) != 30:
        raise ValueError('Se requieren 30 semillas de evaluación distintas')
    if used & set(seeds):
        raise ValueError('Las semillas de evaluación se usaron en pilotos o búsqueda')
    if seeds != summary['evaluation_seeds_reserved']:
        raise ValueError('Las semillas no son las reservadas al congelar la candidata')
    params_hash = portable_sha256(root / PARAMS_FILE)
    if params_hash != summary['input_sha256_portable']['params_bahrain_2024']:
        raise RuntimeError('Los parámetros cambiaron desde la búsqueda; repetir la optimización primero')
    candidate_data = json.loads((root / CANDIDATE_FILE).read_text(encoding='utf-8'))
    if candidate_data != summary['frozen_candidate']['strategy']:
        raise RuntimeError('candidate.json no coincide con la candidata congelada del resumen')
    candidate = strategy_from_dict(candidate_data)
    historical = get_historical_strategy()
    if json.loads(json.dumps(asdict(historical))) != summary['historical']['strategy']:
        raise RuntimeError('La estrategia histórica no coincide con la de la búsqueda')
    limits, groups = build_catalog(tyres, case['expected_laps'], optimizer['inventory'],
                                   tyres['main_search_scenario'])
    for strategy in (historical, candidate):
        if strategy_key(strategy) not in groups[len(strategy.stops_after_lap)]:
            raise ValueError(f'{strategy.name} no pertenece al espacio factible de la búsqueda')
    strict_limits, _ = build_catalog(tyres, case['expected_laps'], optimizer['inventory'],
                                     'strict_model_coverage')
    return {
        'case': case, 'optimizer': optimizer, 'seeds': seeds, 'limits': limits,
        'strict_limits': strict_limits, 'historical': historical, 'candidate': candidate,
        'candidate_search_seed': summary['frozen_candidate']['seed'],
        'trend_scenario': optimizer['trend_scenario'],
        'hashes': {'params_bahrain_2024': params_hash,
                   'candidate': portable_sha256(root / CANDIDATE_FILE),
                   'optimizer': portable_sha256(root / 'configs/optimizer.json'),
                   'tyre_inventory_bahrain_2024': portable_sha256(root / 'configs/tyre_inventory_bahrain_2024.json'),
                   'optimization_summary': portable_sha256(root / SUMMARY_FILE)},
    }


def replicate_row(protocol: dict, spec: dict, strategy: Strategy, params: ModelParameters,
                  scenario: str, seed: int, replicate: int) -> tuple[dict, list[dict]]:
    run = simulate(strategy, params, protocol['limits'], seed=seed, stochastic=True,
                   degradation_multiplier=spec['degradation_multiplier'])
    deterministic = simulate(strategy, params, protocol['limits'],
                             degradation_multiplier=spec['degradation_multiplier'])['total_time_s']
    row = {
        'case': f"{protocol['case']['year']} {protocol['case']['event']}",
        'driver': protocol['case']['driver'],
        'condition': spec['condition'], 'strategy_role': spec['role'], 'strategy_name': strategy.name,
        'stops_after_lap': json.dumps(list(strategy.stops_after_lap)),
        'stints': json.dumps([asdict(s) for s in strategy.stints]),
        'trend_scenario': scenario, 'parameter_provenance': params.provenance,
        'degradation_multiplier': spec['degradation_multiplier'],
        'search_seed': protocol['candidate_search_seed'] if spec['role'] == 'candidate' else '',
        'evaluation_seed': seed, 'replicate': replicate,
        'total_time_s': run['total_time_s'], 'deterministic_time_s': deterministic,
        'noise_sum_s': math.fsum(lap['noise_s'] for lap in run['laps']),
        'stop_count': run['stop_count'], 'feasible': run['feasible'],
        'max_tyre_age_end_laps': max(lap['tyre_age_end_laps'] for lap in run['laps']),
        'laps_with_age_over_20': sum(lap['tyre_age_end_laps'] > 20 for lap in run['laps']),
    }
    laps = [{'condition': spec['condition'], 'trend_scenario': scenario, 'evaluation_seed': seed,
             **{k: lap[k] for k in ('lap', 'stint', 'compound', 'tyre_age_end_laps', 'normal_lap_s',
                                   'noise_s', 'start_penalty_s', 'additional_pit_loss_s',
                                   'elapsed_s', 'cumulative_s')}} for lap in run['laps']]
    return row, laps


def run_conditions(protocol: dict, params: ModelParameters, scenario: str) -> tuple[list[dict], list[dict]]:
    """Las 4 condiciones × 30 réplicas para un escenario de tendencia."""
    strategies = {'historical': protocol['historical'], 'candidate': protocol['candidate']}
    rows, laps = [], []
    for spec in CONDITIONS:
        for i, seed in enumerate(protocol['seeds'], start=1):
            row, lap_rows = replicate_row(protocol, spec, strategies[spec['role']], params, scenario, seed, i)
            rows.append(row)
            laps.extend(lap_rows)
    return rows, laps


def paired_differences(rows: list[dict]) -> list[dict]:
    """Empareja A/B y C/D por semilla. mejora_s = base − candidata."""
    index = {(r['trend_scenario'], r['condition'], r['evaluation_seed']): r for r in rows}
    out = []
    for scenario in dict.fromkeys(r['trend_scenario'] for r in rows):
        for base, cand in PAIRS:
            seeds_base = [r['evaluation_seed'] for r in rows if (r['trend_scenario'], r['condition']) == (scenario, base)]
            seeds_cand = [r['evaluation_seed'] for r in rows if (r['trend_scenario'], r['condition']) == (scenario, cand)]
            if seeds_base != seeds_cand:
                raise ValueError(f'Las semillas de {base} y {cand} no coinciden; no se puede emparejar')
            for seed in seeds_base:
                b, c = index[(scenario, base, seed)], index[(scenario, cand, seed)]
                saving = b['total_time_s'] - c['total_time_s']
                out.append({
                    'trend_scenario': scenario, 'pair': f'{base}-{cand}',
                    'degradation_multiplier': b['degradation_multiplier'], 'evaluation_seed': seed,
                    'base_time_s': b['total_time_s'], 'candidate_time_s': c['total_time_s'],
                    'mejora_s': saving, 'mejora_pct': 100 * saving / b['total_time_s'],
                    'deterministic_mejora_s': b['deterministic_time_s'] - c['deterministic_time_s'],
                    'noise_sum_difference_s': b['noise_sum_s'] - c['noise_sum_s'],
                })
    return out


def lap_profile(strategy: Strategy, race_laps: int) -> dict:
    """Vueltas y suma de edades por compuesto: coeficientes lineales del tiempo total."""
    sim_laps, age, stint = [], strategy.stints[0].initial_age, 0
    stops = set(strategy.stops_after_lap)
    for lap in range(1, race_laps + 1):
        age += 1
        sim_laps.append((strategy.stints[stint].compound, age))
        if lap in stops:
            stint += 1
            age = strategy.stints[stint].initial_age
    laps, ages = Counter(), Counter()
    for compound, a in sim_laps:
        laps[compound] += 1
        ages[compound] += a
    return {'laps': dict(laps), 'age_sum': dict(ages), 'stops': len(stops)}


def difference_decomposition(base: Strategy, cand: Strategy, params: ModelParameters,
                             multiplier: float, race_laps: int) -> dict:
    """Δ = Σ_c Δn_c·b_c + μ·Σ_c ΔA_c·d_c + Δparadas·pérdida_pits. La tendencia se cancela.

    Δn_c y ΔA_c son diferencias (base − candidata) de vueltas y de suma de edades en el
    compuesto c. Como ambas estrategias corren las mismas 57 vueltas, el término de tendencia
    es idéntico y no aparece. Se comprueba contra el simulador.
    """
    pb, pc = lap_profile(base, race_laps), lap_profile(cand, race_laps)
    compounds = sorted(set(pb['laps']) | set(pc['laps']))
    terms = {}
    for c in compounds:
        dn = pb['laps'].get(c, 0) - pc['laps'].get(c, 0)
        da = pb['age_sum'].get(c, 0) - pc['age_sum'].get(c, 0)
        p = params.compounds[c]
        terms[c] = {'delta_laps': dn, 'delta_age_sum': da,
                    'base_term_s': dn * p.base_lap_s,
                    'degradation_term_s': multiplier * da * p.degradation_s_per_lap}
    pit_term = (pb['stops'] - pc['stops']) * params.additional_pit_loss_s
    total = math.fsum(t['base_term_s'] + t['degradation_term_s'] for t in terms.values()) + pit_term
    degradation_total = math.fsum(da['delta_age_sum'] * params.compounds[c].degradation_s_per_lap
                                  for c, da in terms.items())
    level_total = math.fsum(t['base_term_s'] for t in terms.values()) + pit_term
    break_even = -level_total / degradation_total if degradation_total else None
    return {'by_compound': terms, 'pit_term_s': pit_term, 'mejora_s': total,
            'break_even_degradation_multiplier': break_even}


def parameter_uncertainty(root: Path, protocol: dict, multiplier: float) -> dict:
    """Error estándar de Δ por la incertidumbre de base y desgaste, con la tendencia fija.

    Usa los ajustes por compuesto de MA-04 (independientes entre sí) y la covarianza exacta de
    MCO entre intercepto y pendiente: cov = −edad_media · se_pendiente². Solo lee las vueltas
    de entrenamiento y las de eventos, mediante `calibration.load_inputs`, que comprueba la
    huella de la partición. No incluye la incertidumbre de la tendencia (ver escenarios), de la
    forma lineal del modelo ni la autocorrelación de los residuos.
    """
    calibration = protocol['case']['calibration']
    training, _, _, audit = load_inputs(root, calibration)
    fit = fit_parameters(training, calibration['trend_scenarios_s_per_lap'][protocol['trend_scenario']])
    versioned = load_calibrated_parameters(root / PARAMS_FILE, protocol['trend_scenario'])
    for c, values in fit['compounds'].items():
        if (abs(values['base_lap_s'] - versioned.compounds[c].base_lap_s) > 5e-5 or
                abs(values['degradation_s_per_lap'] - versioned.compounds[c].degradation_s_per_lap) > 5e-5):
            raise RuntimeError('El reajuste de entrenamiento no reproduce los parámetros versionados')
    decomposition = difference_decomposition(protocol['historical'], protocol['candidate'], versioned,
                                             multiplier, protocol['case']['expected_laps'])
    variance, detail = 0.0, {}
    for c, term in decomposition['by_compound'].items():
        values = fit['compounds'][c]
        ages = [r['tyre_life_laps'] for r in training if r['compound'] == c]
        mean_age = sum(ages) / len(ages)
        se_b, se_d = values['se_base_lap_s'], values['se_degradation_s_per_lap']
        cov = -mean_age * se_d ** 2
        a, b = term['delta_laps'], multiplier * term['delta_age_sum']
        contribution = a * a * se_b ** 2 + b * b * se_d ** 2 + 2 * a * b * cov
        variance += contribution
        detail[c] = {'se_base_lap_s': se_b, 'se_degradation_s_per_lap': se_d,
                     'cov_base_degradation_s2': cov, 'training_mean_age': mean_age,
                     'variance_contribution_s2': contribution}
    se = math.sqrt(variance)
    estimate = decomposition['mejora_s']
    return {
        'degradation_multiplier': multiplier, 'mejora_s': estimate, 'se_s': se,
        'approx_ci95_s': [estimate - 1.96 * se, estimate + 1.96 * se],
        'z_mejora_over_se': estimate / se if se else None,
        'by_compound': detail,
        'training_laps_read': audit['training_laps'],
        'validation_laps_read': audit['validation_laps_read'],
        'assumptions': 'Normal aproximada; tendencia fija; residuos independientes (SOFT tiene '
                       'autocorrelación 0.21, así que el error estándar es optimista); modelo lineal correcto.',
    }


def sensitivity_grid(root: Path, protocol: dict) -> list[dict]:
    """Diferencia determinista histórica − candidata por tendencia y multiplicador de degradación."""
    rows = []
    for scenario in TREND_SCENARIOS:
        params = load_calibrated_parameters(root / PARAMS_FILE, scenario)
        for m in MULTIPLIER_GRID:
            base = simulate(protocol['historical'], params, protocol['limits'], degradation_multiplier=m)['total_time_s']
            cand = simulate(protocol['candidate'], params, protocol['limits'], degradation_multiplier=m)['total_time_s']
            rows.append({'trend_scenario': scenario, 'degradation_multiplier': m,
                         'historical_time_s': base, 'candidate_time_s': cand,
                         'mejora_s': base - cand, 'mejora_pct': 100 * (base - cand) / base,
                         'candidate_faster': base - cand > 1e-9})
    return rows


def pit_loss_invariance(protocol: dict, params: ModelParameters) -> dict:
    """Con el mismo número de paradas la pérdida de pits no cambia la diferencia."""
    values = []
    for loss in (0.0, params.additional_pit_loss_s, 2 * params.additional_pit_loss_s):
        p = replace(params, additional_pit_loss_s=loss)
        values.append(simulate(protocol['historical'], p, protocol['limits'])['total_time_s']
                      - simulate(protocol['candidate'], p, protocol['limits'])['total_time_s'])
    return {'pit_losses_tested_s': [0.0, params.additional_pit_loss_s, 2 * params.additional_pit_loss_s],
            'mejora_s': values, 'max_spread_s': max(values) - min(values)}


def summarize(rows: list[dict], pairs: list[dict], scenario: str) -> dict:
    by_condition = {}
    for spec in CONDITIONS:
        values = [r['total_time_s'] for r in rows if (r['trend_scenario'], r['condition']) == (scenario, spec['condition'])]
        det = {r['deterministic_time_s'] for r in rows if (r['trend_scenario'], r['condition']) == (scenario, spec['condition'])}
        by_condition[spec['condition']] = {**spec, 'total_time_s': describe(values),
                                           'deterministic_time_s': det.pop()}
    by_pair = {}
    for base, cand in PAIRS:
        selected = [p for p in pairs if (p['trend_scenario'], p['pair']) == (scenario, f'{base}-{cand}')]
        saving = [p['mejora_s'] for p in selected]
        a = by_condition[base]['total_time_s']
        b = by_condition[cand]['total_time_s']
        unpaired_se = math.sqrt(a['sd'] ** 2 / a['n'] + b['sd'] ** 2 / b['n'])
        unpaired_mean = a['mean'] - b['mean']
        by_pair[f'{base}-{cand}'] = {
            'mejora_s': describe(saving),
            'mejora_pct': describe([p['mejora_pct'] for p in selected]),
            'deterministic_mejora_s': selected[0]['deterministic_mejora_s'],
            'candidate_faster_in_replicates': sum(s > 0 for s in saving),
            'max_abs_noise_sum_difference_s': max(abs(p['noise_sum_difference_s']) for p in selected),
            # Referencia: lo que se vería sin emparejar (Welch con gl ≈ 58, t ≈ 2.00).
            'unpaired_reference': {'mean_difference_s': unpaired_mean, 'se_s': unpaired_se,
                                   'approx_ci95_s': [unpaired_mean - 2.0 * unpaired_se,
                                                     unpaired_mean + 2.0 * unpaired_se]},
        }
    return {'by_condition': by_condition, 'by_pair': by_pair}


def run_experiments(root: Path, out: Path) -> dict:
    protocol = load_protocol(root)
    main = protocol['trend_scenario']
    all_rows, main_laps = [], []
    for scenario in TREND_SCENARIOS:
        params = load_calibrated_parameters(root / PARAMS_FILE, scenario)
        rows, laps = run_conditions(protocol, params, scenario)
        all_rows.extend(rows)
        if scenario == main:
            main_laps = laps
    pairs = paired_differences(all_rows)
    main_params = load_calibrated_parameters(root / PARAMS_FILE, main)
    race_laps = protocol['case']['expected_laps']
    try:
        uncertainty = {str(m): parameter_uncertainty(root, protocol, m) for m in (1.0, SENSITIVITY_MULTIPLIER)}
    except FileNotFoundError as exc:
        uncertainty = {'not_computed': f'Requiere datos de entrenamiento regenerados ({exc}).'}
    strict = {name: validate_strategy(protocol[name], protocol['strict_limits'])
              for name in ('historical', 'candidate')}
    sigma = main_params.residual_sd_s
    report = {
        'task': 'LP-04/LP-05',
        'computed_at_utc': datetime.now(timezone.utc).isoformat(),
        'code_state': _git_state(root),
        'design': {
            'conditions': list(CONDITIONS), 'pairs': [f'{a}-{b}' for a, b in PAIRS],
            'replicates_per_condition': len(protocol['seeds']),
            'evaluation_seeds': protocol['seeds'],
            'pilot_seeds': protocol['optimizer']['pilot_seeds'],
            'search_seeds': protocol['optimizer']['search_seeds'],
            'candidate_search_seed': protocol['candidate_search_seed'],
            'mode': 'estocástico: ruido gaussiano aditivo independiente por vuelta',
            'residual_sd_s': sigma,
            'expected_sd_total_time_s': sigma * math.sqrt(race_laps),
            'main_trend_scenario': main,
            'sensitivity_trend_scenarios': [s for s in TREND_SCENARIOS if s != main],
            'constraints': 'inventory_main / observed_race_feasibility, iguales para ambas estrategias',
            'sign_convention': 'mejora_s = tiempo_base - tiempo_candidata; mejora_pct = 100*mejora_s/tiempo_base; '
                               'positivo = candidata más rápida',
        },
        'strategies': {'historical': asdict(protocol['historical']), 'candidate': asdict(protocol['candidate'])},
        'input_sha256_portable': protocol['hashes'],
        'results_by_trend_scenario': {s: summarize(all_rows, pairs, s) for s in TREND_SCENARIOS},
        'difference_decomposition': {
            str(m): difference_decomposition(protocol['historical'], protocol['candidate'], main_params, m, race_laps)
            for m in (1.0, SENSITIVITY_MULTIPLIER)},
        'parameter_uncertainty': uncertainty,
        'pit_loss_invariance': pit_loss_invariance(protocol, main_params),
        'strict_model_coverage_violations': strict,
        'notes': [
            'A/B y C/D comparten semilla: el ruido aditivo se cancela en la diferencia salvo redondeo; '
            'la dispersión pareada no cuantifica incertidumbre de parámetros ni del modelo.',
            'La candidata llega a HARD edad 21 en la vuelta 57: extrapolación fuera del rango de entrenamiento (2-19).',
            'El escenario principal es trend_fuel_reference; trend_zero y trend_double son sensibilidad.',
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / 'replicas.csv', [r for r in all_rows if r['trend_scenario'] == main])
    write_csv(out / 'replicas_sensibilidad_tendencia.csv', [r for r in all_rows if r['trend_scenario'] != main])
    write_csv(out / 'diferencias_pareadas.csv', [p for p in pairs if p['trend_scenario'] == main])
    write_csv(out / 'diferencias_pareadas_sensibilidad_tendencia.csv', [p for p in pairs if p['trend_scenario'] != main])
    write_csv(out / 'sensibilidad.csv', sensitivity_grid(root, protocol))
    write_csv(out / 'vueltas_replicas.csv', main_laps)
    deterministic_laps = []
    for spec in CONDITIONS:
        strategy = protocol[spec['role']]
        run = simulate(strategy, main_params, protocol['limits'], degradation_multiplier=spec['degradation_multiplier'])
        deterministic_laps.extend({'condition': spec['condition'], 'strategy_role': spec['role'],
                                   **{k: lap[k] for k in ('lap', 'stint', 'compound', 'tyre_age_end_laps',
                                                         'normal_lap_s', 'start_penalty_s',
                                                         'additional_pit_loss_s', 'elapsed_s', 'cumulative_s')}}
                                  for lap in run['laps'])
    write_csv(out / 'vueltas_deterministas.csv', deterministic_laps)
    (out / 'resumen.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report
