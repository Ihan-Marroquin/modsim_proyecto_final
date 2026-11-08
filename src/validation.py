"""Validación del modelo congelado contra el stint 3 reservado (LP-03).

Separa dos comparaciones que no deben mezclarse:

1. **Validación reservada**: vueltas 39–57 sin la 46 (stint 3), que no se usaron para
   calibrar. Se reportan los tres conjuntos preregistrados en
   `docs/evidence/particion_manifiesto.json` con MAE, sesgo y error acumulado.
2. **Reconstrucción de la carrera completa**: las 57 vueltas con arranque y pits
   modelados. La vuelta 1 sigue la convención oficial FIA/Jolpica (97.284 s) y el total se
   compara con 5504.742 s. Incluye vueltas de entrenamiento, así que **no es validación**.

Convención de signo: error_i = tiempo_predicho_i − tiempo_observado_i (s). Un error
positivo significa que el modelo es más lento que la observación.

Reglas que este módulo hace cumplir: la partición debe coincidir con la huella congelada,
los parámetros deben coincidir con los que usó la optimización y nunca se reajusta nada.
La sensibilidad a la tendencia se reporta, pero la tendencia principal no se elige con
estos números.
"""
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from .data import portable_sha256, write_csv
from .model import get_bahrain_constraints, get_historical_strategy, load_calibrated_parameters
from .partition import _git_state
from .simulation import simulate

MAIN_SCENARIO = 'trend_fuel_reference'
TREND_SCENARIOS = ('trend_fuel_reference', 'trend_zero', 'trend_double')
VALIDATION_SETS = {
    'validation_all': 'validation_laps',
    'validation_covered_ages': 'validation_covered_laps',
    'validation_extrapolated_ages': 'validation_extrapolated_laps',
}
PARAMS_FILE = 'configs/params_bahrain_2024.json'
MANIFEST_FILE = 'docs/evidence/particion_manifiesto.json'
OPTIMIZATION_SUMMARY = 'docs/evidence/optimization/summary.json'
TOLERANCE_S = 0.0005  # las fuentes publican milésimas


def error_metrics(errors: list[float]) -> dict:
    """Métricas preregistradas (MAE, sesgo, acumulado) y dos descriptivas complementarias."""
    if not errors:
        raise ValueError('No hay errores que resumir')
    if not all(math.isfinite(e) for e in errors):
        raise ValueError('Todos los errores deben ser finitos')
    n = len(errors)
    return {
        'n_laps': n,
        'MAE_s': math.fsum(abs(e) for e in errors) / n,
        'bias_s': math.fsum(errors) / n,
        'cumulative_error_s': math.fsum(errors),
        # No preregistradas: solo describen la forma del error.
        'RMSE_s': math.sqrt(math.fsum(e * e for e in errors) / n),
        'max_abs_error_s': max(abs(e) for e in errors),
    }


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def check_frozen_inputs(root: Path) -> dict:
    """Comprueba la huella de la partición y que los parámetros sean los de la optimización."""
    manifest = json.loads((root / MANIFEST_FILE).read_text(encoding='utf-8'))
    split_path = root / 'data/processed/partition_split.csv'
    if not split_path.exists():
        raise FileNotFoundError('Falta data/processed/partition_split.csv: ejecutar '
                                '`python main.py download`, `reconcile` y `partition`.')
    split_hash = portable_sha256(split_path)
    if split_hash != manifest['sha256_portable_split']:
        raise RuntimeError('La partición no coincide con la congelada; no se valida.')
    params_hash = portable_sha256(root / PARAMS_FILE)
    summary = json.loads((root / OPTIMIZATION_SUMMARY).read_text(encoding='utf-8'))
    expected = summary['input_sha256_portable']['params_bahrain_2024']
    if params_hash != expected:
        raise RuntimeError('configs/params_bahrain_2024.json cambió respecto de la optimización; '
                           'una versión nueva del modelo exige repetir los experimentos afectados.')
    return {'manifest': manifest, 'partition_sha256_portable': split_hash,
            'params_sha256_portable': params_hash, 'params_match_optimization_inputs': True}


def load_observed(root: Path) -> dict[int, dict]:
    """Vueltas observadas de VER: OpenF1 para 2–57 y convención oficial para la vuelta 1."""
    roles = {int(r['lap_number']): r for r in _read_csv(root / 'data/processed/partition_split.csv')}
    reference = {int(r['lap_number']): r for r in
                 _read_csv(root / 'data/processed/lap_time_reconciliation.csv')}
    observed = {}
    for r in _read_csv(root / 'data/processed/openf1_target_laps_annotated.csv'):
        lap = int(r['lap_number'])
        openf1 = float(r['lap_time_s'])
        official = float(reference[lap]['reference_s'])
        if lap != 1 and abs(openf1 - official) > TOLERANCE_S:
            raise ValueError(f'La vuelta {lap} difiere entre OpenF1 y la referencia oficial')
        observed[lap] = {
            'lap': lap, 'stint': int(r['stint']), 'compound': r['compound'],
            'tyre_age_end_laps': int(r['tyre_life_laps']),
            'split': roles[lap]['split'], 'age_coverage': roles[lap]['age_coverage'],
            'observed_openf1_s': openf1,
            # Vuelta 1 desde la señal de salida, coherente con el total FIA (docs/conciliacion_tiempos.md).
            'observed_official_s': official,
        }
    return observed


def simulate_observed_strategy(root: Path, scenario: str) -> list[dict]:
    """Histórica de VER en modo determinista, con parámetros congelados y sin reajuste."""
    params = load_calibrated_parameters(root / PARAMS_FILE, scenario)
    limits = get_bahrain_constraints('observed_race_feasibility')
    return simulate(get_historical_strategy(), params, limits)['laps']


def check_strategy_matches_observation(observed: dict[int, dict], simulated: list[dict]) -> None:
    """La estrategia simulada debe reproducir compuesto y edad de cada vuelta observada."""
    if len(simulated) != len(observed):
        raise ValueError('La simulación y la observación no tienen las mismas vueltas')
    for lap in simulated:
        obs = observed[lap['lap']]
        if (obs['compound'], obs['tyre_age_end_laps']) != (lap['compound'], lap['tyre_age_end_laps']):
            raise ValueError(f"La vuelta {lap['lap']} no coincide en compuesto o edad")


def validate_reserved(observed: dict[int, dict], simulated: list[dict], manifest: dict) -> dict:
    """Métricas de los tres conjuntos preregistrados. En validación no hay pits ni arranque."""
    by_lap = {lap['lap']: lap for lap in simulated}
    result = {}
    for name, key in VALIDATION_SETS.items():
        laps = manifest[key]
        if any(observed[lap]['split'] != 'validation' for lap in laps):
            raise ValueError(f'{name} contiene vueltas que no son de validación')
        if any(by_lap[lap]['additional_pit_loss_s'] or by_lap[lap]['start_penalty_s'] for lap in laps):
            raise ValueError('Una vuelta de validación tiene pits o arranque modelados')
        errors = [by_lap[lap]['elapsed_s'] - observed[lap]['observed_official_s'] for lap in laps]
        result[name] = {'laps': laps, **error_metrics(errors)}
    return result


def race_segments(simulated: list[dict]) -> dict[int, str]:
    """Etiqueta cada vuelta: arranque, par entrada/salida de cada parada o tramo normal del stint.

    La pérdida de pits se carga en la vuelta de entrada y el exceso observado cae sobre todo en
    la de salida, así que solo el par completo es comparable con la observación.
    """
    stops = {lap['lap'] for lap in simulated if lap['additional_pit_loss_s']}
    labels = {}
    for lap in simulated:
        n = lap['lap']
        if n == 1:
            labels[n] = 'start_lap_1'
        elif n in stops:
            labels[n] = f'pit_{n}_{n + 1}'
        elif n - 1 in stops:
            labels[n] = f'pit_{n - 1}_{n}'
        else:
            labels[n] = f"stint_{lap['stint']}_normal"
    return labels


def reconstruct_full_race(observed: dict[int, dict], simulated: list[dict], official_total_s: float) -> dict:
    """Las 57 vueltas con eventos modelados. Desglosa el error total por rol y por segmento."""
    errors = {lap['lap']: lap['elapsed_s'] - observed[lap['lap']]['observed_official_s'] for lap in simulated}
    by_role = {}
    for role in ('training', 'excluded_from_fit', 'validation'):
        laps = [lap for lap in sorted(errors) if observed[lap]['split'] == role]
        by_role[role] = {'laps': laps, **error_metrics([errors[lap] for lap in laps])}
    labels = race_segments(simulated)
    by_segment = {}
    for label in dict.fromkeys(labels[lap] for lap in sorted(labels)):
        laps = [lap for lap in sorted(labels) if labels[lap] == label]
        by_segment[label] = {'lap_range': [laps[0], laps[-1]], 'n_laps': len(laps),
                             'cumulative_error_s': math.fsum(errors[lap] for lap in laps)}
    simulated_total = simulated[-1]['cumulative_s']
    observed_official = math.fsum(o['observed_official_s'] for o in observed.values())
    observed_openf1 = math.fsum(o['observed_openf1_s'] for o in observed.values())
    return {
        'note': 'Reconstrucción con parámetros ajustados a 33 de estas vueltas: no es validación independiente.',
        'all_laps': error_metrics(list(errors.values())),
        'by_partition_role': by_role,
        'by_segment': by_segment,
        'per_lap_note': 'El MAE de vueltas con eventos refleja la pérdida agrupada en la vuelta de entrada; '
                        'comparar el error acumulado de cada par de parada, no sus vueltas sueltas.',
        'simulated_total_s': simulated_total,
        'observed_lap_sum_official_convention_s': observed_official,
        'observed_lap_sum_openf1_s': observed_openf1,
        'official_total_fia_s': official_total_s,
        'simulated_minus_official_s': simulated_total - official_total_s,
        'lap_sum_matches_official_total': abs(observed_official - official_total_s) < TOLERANCE_S,
    }


def second_pit_check(observed: dict[int, dict], simulated: list[dict], in_lap: int = 37) -> dict:
    """Comprueba con la parada 37–38, no usada al calibrar, la pérdida estimada con la 17–18."""
    by_lap = {lap['lap']: lap for lap in simulated}
    pin, pout = by_lap[in_lap], by_lap[in_lap + 1]
    observed_sum = observed[in_lap]['observed_official_s'] + observed[in_lap + 1]['observed_official_s']
    normal_sum = pin['normal_lap_s'] + pout['normal_lap_s']
    implied = observed_sum - normal_sum
    return {
        'in_lap': in_lap, 'out_lap': in_lap + 1,
        'in_tyre': f"{pin['compound']} edad {pin['tyre_age_end_laps']}",
        'out_tyre': f"{pout['compound']} edad {pout['tyre_age_end_laps']}",
        'observed_in_plus_out_s': observed_sum,
        'predicted_normal_in_plus_out_s': normal_sum,
        'implied_additional_pit_loss_s': implied,
        'calibrated_additional_pit_loss_s': pin['additional_pit_loss_s'],
        'calibrated_minus_implied_s': pin['additional_pit_loss_s'] - implied,
        'caveat': 'La vuelta de salida usa SOFT edad 1 (fuera del rango de entrenamiento) y el '
                  'stint 3 tiene sesgo propio; la diferencia mezcla error de pits y de ritmo.',
    }


def lap_rows(observed: dict[int, dict], simulations: dict[str, list[dict]], manifest: dict) -> list[dict]:
    """Tabla por vuelta para gráficas. Contiene tiempos de las fuentes: no se versiona."""
    membership = {name: set(manifest[key]) for name, key in VALIDATION_SETS.items()}
    rows = []
    for lap in sorted(observed):
        obs = observed[lap]
        row = {'lap': lap, 'stint': obs['stint'], 'compound': obs['compound'],
               'tyre_age_end_laps': obs['tyre_age_end_laps'], 'split': obs['split'],
               'age_coverage': obs['age_coverage'],
               'in_validation_all': lap in membership['validation_all'],
               'in_validation_covered_ages': lap in membership['validation_covered_ages'],
               'in_validation_extrapolated_ages': lap in membership['validation_extrapolated_ages'],
               'observed_openf1_s': obs['observed_openf1_s'],
               'observed_official_s': obs['observed_official_s']}
        for scenario, simulated in simulations.items():
            sim = simulated[lap - 1]
            row[f'predicted_{scenario}_s'] = sim['elapsed_s']
            row[f'error_{scenario}_s'] = sim['elapsed_s'] - obs['observed_official_s']
        rows.append(row)
    cumulative = {scenario: 0.0 for scenario in simulations}
    for row in rows:
        for scenario in simulations:
            cumulative[scenario] += row[f'error_{scenario}_s']
            row[f'cumulative_error_{scenario}_s'] = cumulative[scenario]
    return rows


def run_validation(root: Path, out: Path) -> dict:
    """Ejecuta LP-03 completo y escribe resultados en `out` (por defecto results/validation)."""
    frozen = check_frozen_inputs(root)
    manifest = frozen.pop('manifest')
    case = json.loads((root / 'configs/case_bahrain_2024.json').read_text(encoding='utf-8'))
    observed = load_observed(root)
    simulations = {scenario: simulate_observed_strategy(root, scenario) for scenario in TREND_SCENARIOS}
    for simulated in simulations.values():
        check_strategy_matches_observation(observed, simulated)
    by_scenario = {}
    for scenario, simulated in simulations.items():
        by_scenario[scenario] = {
            'reserved_validation': validate_reserved(observed, simulated, manifest),
            'full_race_reconstruction': reconstruct_full_race(observed, simulated, case['official_winner_time_s']),
            'second_pit_check': second_pit_check(observed, simulated),
        }
    sensitivity = [
        {'trend_scenario': scenario,
         'race_trend_s_per_lap': load_calibrated_parameters(root / PARAMS_FILE, scenario).race_trend_s_per_lap,
         **{f'{name}_{metric}': values[metric]
            for name, values in by_scenario[scenario]['reserved_validation'].items()
            for metric in ('MAE_s', 'bias_s', 'cumulative_error_s')},
         'reconstruction_simulated_minus_official_s':
             by_scenario[scenario]['full_race_reconstruction']['simulated_minus_official_s']}
        for scenario in TREND_SCENARIOS
    ]
    report = {
        'task': 'LP-03',
        'computed_at_utc': datetime.now(timezone.utc).isoformat(),
        'code_state': _git_state(root),
        'case': {'event': case['event'], 'year': case['year'], 'driver': case['driver']},
        'strategy': 'historical_ver_bahrain_2024 (estrategia observada)',
        'mode': 'determinista, sin ruido',
        'error_definition': 'error_i = tiempo_predicho_i - tiempo_observado_i [s]; positivo = modelo más lento',
        'observed_reference': 'Vueltas 2-57 de OpenF1 (iguales a Jolpica al milisegundo); vuelta 1 con '
                              'convención oficial FIA/Jolpica (docs/conciliacion_tiempos.md).',
        'frozen_inputs': frozen,
        'main_scenario': MAIN_SCENARIO,
        'rules_applied': [
            'Parámetros congelados: misma huella que la optimización; no se reajusta ningún parámetro.',
            'Se reportan los tres conjuntos preregistrados aunque sean desfavorables.',
            'La tendencia principal no se elige con estas métricas: los otros escenarios son sensibilidad.',
            'La reconstrucción completa se reporta aparte y no cuenta como validación.',
        ],
        'by_scenario': by_scenario,
        'trend_sensitivity': sensitivity,
    }
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / 'validacion_vueltas.csv', lap_rows(observed, simulations, manifest))
    write_csv(out / 'sensibilidad_tendencia_validacion.csv', sensitivity)
    (out / 'validacion.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report
