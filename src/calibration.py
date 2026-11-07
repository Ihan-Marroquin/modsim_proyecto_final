"""Calibración de parámetros reales solo con entrenamiento (MA-04).

Modelo (identificable con la partición congelada, ver docs/particion_validacion.md):
    vuelta_normal = base_c + desgaste_c * edad + tendencia * (vuelta - 1)
con la tendencia FIJADA por una referencia externa y analizada en sensibilidad. Se estiman
base y desgaste por compuesto con mínimos cuadrados ordinarios sobre (tiempo - tendencia*(vuelta-1)).

Convenciones idénticas a src/simulation.py:
- edad = vueltas del juego al terminar la vuelta (tyre_life_laps);
- la pérdida adicional de pits es UNA cantidad que se suma tras la vuelta de entrada y cubre
  el exceso de la vuelta de entrada y la de salida sobre sus vueltas normales;
- la penalización de arranque se suma a la vuelta 1.

Este módulo NO calcula métricas de validación (LP-03) y nunca lee tiempos de vueltas de validación.
"""
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from .data import portable_sha256

# Cuantiles t de Student al 97.5 % (intervalos del 95 %), gl 1-30. Para gl > 30 se usa 1.96.
_T975 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.160,
         2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069, 2.064, 2.060, 2.056,
         2.052, 2.048, 2.045, 2.042]


def t975(df: int) -> float:
    return _T975[df - 1] if 1 <= df <= 30 else 1.96


def fit_line(x: list[float], y: list[float]) -> dict:
    """Recta por mínimos cuadrados con errores estándar clásicos."""
    n = len(x)
    if n < 3 or len(set(x)) < 2:
        raise ValueError('Se necesitan al menos 3 puntos con edades distintas')
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    slope = sum((a - mx) * (b - my) for a, b in zip(x, y)) / sxx
    intercept = my - slope * mx
    residuals = [b - (intercept + slope * a) for a, b in zip(x, y)]
    ssr = sum(r * r for r in residuals)
    sigma2 = ssr / (n - 2)
    se_slope = math.sqrt(sigma2 / sxx)
    se_intercept = math.sqrt(sigma2 * (1 / n + mx * mx / sxx))
    sst = sum((b - my) ** 2 for b in y)
    return {'intercept': intercept, 'slope': slope, 'se_intercept': se_intercept, 'se_slope': se_slope,
            'residuals': residuals, 'ssr': ssr, 'n': n, 'df': n - 2,
            'r2': 1 - ssr / sst if sst > 0 else None}


def lag1_autocorrelation(series: list[float]) -> float | None:
    if len(series) < 3:
        return None
    m = sum(series) / len(series)
    den = sum((v - m) ** 2 for v in series)
    return sum((a - m) * (b - m) for a, b in zip(series, series[1:])) / den if den > 0 else None


def fit_parameters(training: list[dict], trend_s_per_lap: float) -> dict:
    """Base y desgaste por compuesto con la tendencia fija. `training`: lap_number, compound, tyre_life_laps, lap_time_s."""
    compounds, all_residuals, ssr_total, n_total = {}, [], 0.0, 0
    for compound in sorted({r['compound'] for r in training}):
        rows = sorted((r for r in training if r['compound'] == compound), key=lambda r: r['lap_number'])
        ages = [float(r['tyre_life_laps']) for r in rows]
        adjusted = [r['lap_time_s'] - trend_s_per_lap * (r['lap_number'] - 1) for r in rows]
        fit = fit_line(ages, adjusted)
        t = t975(fit['df'])
        compounds[compound] = {
            'base_lap_s': fit['intercept'], 'degradation_s_per_lap': fit['slope'],
            'se_base_lap_s': fit['se_intercept'], 'se_degradation_s_per_lap': fit['se_slope'],
            'ci95_degradation_s_per_lap': [fit['slope'] - t * fit['se_slope'], fit['slope'] + t * fit['se_slope']],
            'ci95_base_lap_s': [fit['intercept'] - t * fit['se_intercept'], fit['intercept'] + t * fit['se_intercept']],
            'n_laps': fit['n'], 'laps': [r['lap_number'] for r in rows],
            'tyre_life_range': [int(min(ages)), int(max(ages))],
            'r2': fit['r2'], 'residual_sd_s': math.sqrt(fit['ssr'] / fit['df']),
            'residual_lag1_autocorrelation': lag1_autocorrelation(fit['residuals']),
        }
        all_residuals.extend(fit['residuals'])
        ssr_total += fit['ssr']
        n_total += fit['n']
    estimated = 2 * len(compounds)
    return {'race_trend_s_per_lap': trend_s_per_lap, 'compounds': compounds,
            'residual_sd_s': math.sqrt(ssr_total / (n_total - estimated)),
            'n_training_laps': n_total, 'n_estimated_parameters': estimated}


def predict_normal(fit: dict, compound: str, age: int, lap: int) -> float:
    c = fit['compounds'][compound]
    return c['base_lap_s'] + c['degradation_s_per_lap'] * age + fit['race_trend_s_per_lap'] * (lap - 1)


def event_losses(fit: dict, laps: dict[int, dict], first_lap_official_s: float, pit_in_lap: int) -> dict:
    """Penalización de arranque y pérdida adicional de pits con la convención del simulador."""
    one, pin, pout = laps[1], laps[pit_in_lap], laps[pit_in_lap + 1]
    normal_1 = predict_normal(fit, one['compound'], one['tyre_life_laps'], 1)
    normal_in = predict_normal(fit, pin['compound'], pin['tyre_life_laps'], pit_in_lap)
    normal_out = predict_normal(fit, pout['compound'], pout['tyre_life_laps'], pit_in_lap + 1)
    return {
        'start_penalty_s': first_lap_official_s - normal_1,
        'start_detail': {'lap_1_official_s': first_lap_official_s, 'predicted_normal_lap_1_s': normal_1,
                         'tyre': f"{one['compound']} edad {one['tyre_life_laps']}"},
        'additional_pit_loss_s': (pin['lap_time_s'] + pout['lap_time_s']) - (normal_in + normal_out),
        'pit_detail': {'in_lap': pit_in_lap, 'in_lap_s': pin['lap_time_s'], 'predicted_normal_in_s': normal_in,
                       'out_lap_s': pout['lap_time_s'], 'predicted_normal_out_s': normal_out,
                       'in_tyre': f"{pin['compound']} edad {pin['tyre_life_laps']}",
                       'out_tyre': f"{pout['compound']} edad {pout['tyre_life_laps']}"},
    }


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def load_inputs(root: Path, calibration: dict) -> tuple[list[dict], dict[int, dict], float, dict]:
    """Comprueba la partición congelada y lee SOLO los tiempos permitidos."""
    manifest = json.loads((root/calibration['partition_manifest']).read_text(encoding='utf-8'))
    split_path = root/'data/processed/partition_split.csv'
    if portable_sha256(split_path) != manifest['sha256_portable_split']:
        raise RuntimeError('La partición no coincide con la congelada; regenerar con `python main.py partition` '
                           'o revisar cambios antes de calibrar.')
    roles = {int(r['lap_number']): r['split'] for r in _read_csv(split_path)}
    event_laps = set(calibration['event_laps_read'])
    leaked = [lap for lap in event_laps if roles.get(lap) == 'validation']
    if leaked:
        raise RuntimeError(f'Vueltas de validación pedidas para eventos: {leaked}')
    allowed = {lap for lap, role in roles.items() if role == 'training'} | event_laps
    rows = {}
    for r in _read_csv(root/'data/processed/openf1_target_laps_annotated.csv'):
        lap = int(r['lap_number'])
        if lap in allowed:  # los tiempos de las demás vueltas no se convierten ni se usan
            rows[lap] = {'lap_number': lap, 'compound': r['compound'], 'tyre_life_laps': int(r['tyre_life_laps']),
                         'lap_time_s': float(r['lap_time_s'])}
    training = [rows[lap] for lap, role in sorted(roles.items()) if role == 'training']
    reconciliation = {int(r['lap_number']): r for r in _read_csv(root/'data/processed/lap_time_reconciliation.csv')}
    first_lap_official = float(reconciliation[1]['reference_s'])
    audit = {'laps_whose_times_were_read': sorted(rows), 'training_laps': [r['lap_number'] for r in training],
             'validation_laps_read': [lap for lap in rows if roles.get(lap) == 'validation'],
             'partition_hash_verified': manifest['sha256_portable_split'],
             'partition_frozen_at_utc': manifest['frozen_at_utc'],
             'partition_code_commit': manifest['code_state']['commit']}
    return training, rows, first_lap_official, audit


def _rounded(value, digits=4):
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, dict):
        return {k: _rounded(v, digits) for k, v in value.items()}
    if isinstance(value, list):
        return [_rounded(v, digits) for v in value]
    return value


def simulator_parameters(fit: dict, losses: dict, provenance: str) -> dict:
    """Mismo formato que acepta src/domain.py::parameters_from_dict."""
    return _rounded({
        'compounds': {c: {'base_lap_s': v['base_lap_s'], 'degradation_s_per_lap': v['degradation_s_per_lap']}
                      for c, v in fit['compounds'].items()},
        'race_trend_s_per_lap': fit['race_trend_s_per_lap'],
        'additional_pit_loss_s': losses['additional_pit_loss_s'],
        'start_penalty_s': losses['start_penalty_s'],
        'residual_sd_s': fit['residual_sd_s'],
        'provenance': provenance,
    })


def calibrate_case(config: dict, root: Path) -> dict:
    calibration = config['calibration']
    training, rows, first_lap_official, audit = load_inputs(root, calibration)
    scenarios = {}
    for name, trend in calibration['trend_scenarios_s_per_lap'].items():
        fit = fit_parameters(training, trend)
        losses = event_losses(fit, rows, first_lap_official, calibration['pit_in_lap_for_estimation'])
        scenarios[name] = {'fit': fit, 'losses': losses,
                           'parameters': simulator_parameters(fit, losses, f'CALIBRATED_MA04_TRAINING_ONLY_{name.upper()}')}
    main = calibration['main_scenario']
    output = {
        'task': 'MA-04', 'case': f"{config['year']} {config['event']} {config['driver']}",
        'calibrated_at_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'FROZEN_BEFORE_VALIDATION_PENDING_REVIEW',
        'model': 'vuelta_normal = base_c + desgaste_c*edad + tendencia*(vuelta-1); tendencia fija',
        'units': {'base_lap_s': 's', 'degradation_s_per_lap': 's por vuelta de edad',
                  'race_trend_s_per_lap': 's por vuelta de carrera', 'additional_pit_loss_s': 's por parada',
                  'start_penalty_s': 's', 'residual_sd_s': 's'},
        'trend_reference': calibration['trend_reference'],
        'main_scenario': main,
        'parameters': scenarios[main]['parameters'],
        'sensitivity_parameters': {k: v['parameters'] for k, v in scenarios.items() if k != main},
        'details': _rounded({k: {'compounds': v['fit']['compounds'], 'residual_sd_s': v['fit']['residual_sd_s'],
                                 'n_training_laps': v['fit']['n_training_laps'], **v['losses']}
                             for k, v in scenarios.items()}),
        'data_audit': audit,
        'not_done_here': ['Métricas de validación: LP-03 con estos parámetros congelados.',
                          'Comprobación de la pérdida de pits con la segunda parada (vueltas 37-38): LP-03.'],
    }
    out = root/'results/data_audit'
    out.mkdir(parents=True, exist_ok=True)
    (out/'calibration.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    (root/'configs/params_bahrain_2024.json').write_text(json.dumps(
        {'purpose': 'REAL_PARAMETERS_CALIBRATED_ON_TRAINING_ONLY', 'documentation': 'docs/calibracion.md',
         'units': output['units'], 'main_scenario': main, 'parameters': output['parameters'],
         'sensitivity_parameters': output['sensitivity_parameters']}, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')
    return output
