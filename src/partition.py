"""Partición entrenamiento/validación congelada antes de calibrar (MA-03).

Esquema decidido el 2026-11-06 (opción A): se reserva completo el último stint para
validación. Este módulo solo usa números de vuelta, stints, compuestos y edades: no lee
tiempos de vuelta, así que construir la partición no filtra información de la validación.
"""
import csv
import json
import subprocess
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from .data import is_true, portable_sha256, write_csv

SCHEME = 'holdout_last_stint'


def matrix_rank(rows: list[list]) -> int:
    """Rango exacto con fracciones (sin errores de redondeo); matrices pequeñas."""
    matrix = [[Fraction(x) for x in row] for row in rows]
    rank = 0
    for col in range(len(matrix[0]) if matrix else 0):
        pivot = next((i for i in range(rank, len(matrix)) if matrix[i][col] != 0), None)
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        for i in range(len(matrix)):
            if i != rank and matrix[i][col] != 0:
                factor = matrix[i][col] / matrix[rank][col]
                matrix[i] = [a - factor * b for a, b in zip(matrix[i], matrix[rank])]
        rank += 1
    return rank


def _design(rows: list[dict], spec: str) -> list[list]:
    compounds = sorted({r['compound'] for r in rows})
    out = []
    for r in rows:
        base = [1 if r['compound'] == c else 0 for c in compounds]
        age, lap = int(r['tyre_life_laps']), int(r['lap_number'])
        wear_by_compound = [age if r['compound'] == c else 0 for c in compounds]
        out.append({'plan_model': base + wear_by_compound + [lap],
                    'common_wear_plus_trend': base + [age, lap],
                    'trend_fixed_externally': base + wear_by_compound}[spec])
    return out


MODEL_SPECS = {
    'plan_model': 'base_c + desgaste_c*edad + tendencia*vuelta',
    'common_wear_plus_trend': 'base_c + desgaste_comun*edad + tendencia*vuelta',
    'trend_fixed_externally': 'base_c + desgaste_c*edad (tendencia fijada con referencia externa)',
}


def identifiability(rows: list[dict]) -> dict:
    """¿Los datos determinan un único conjunto de parámetros? (rango completo de la matriz)."""
    result = {}
    for spec, label in MODEL_SPECS.items():
        design = _design(rows, spec)
        params, rank = len(design[0]), matrix_rank(design)
        result[spec] = {'model': label, 'parameters': params, 'rank': rank, 'identifiable': rank == params}
    return result


def build_partition(annotated: list[dict], validation_stint: int) -> tuple[list[dict], dict]:
    """Asigna cada vuelta a training/validation/excluded y clasifica la cobertura de edad."""
    def role(r):
        if not is_true(r['calibration_eligible']):
            return 'excluded_from_fit'
        return 'validation' if int(r['stint']) == validation_stint else 'training'

    training = [r for r in annotated if role(r) == 'training']
    age_range = {}
    for r in training:
        lo, hi = age_range.get(r['compound'], (10**9, -1))
        age = int(r['tyre_life_laps'])
        age_range[r['compound']] = (min(lo, age), max(hi, age))

    split = []
    for r in annotated:
        item = {'lap_number': int(r['lap_number']), 'stint': int(r['stint']), 'compound': r['compound'],
                'tyre_life_laps': int(r['tyre_life_laps']), 'split': role(r),
                'exclusion_reasons': r.get('exclusion_reasons', ''), 'age_coverage': ''}
        if item['split'] == 'validation':
            lo, hi = age_range.get(item['compound'], (None, None))
            if lo is None:
                item['age_coverage'] = 'compound_not_in_training'
            elif item['tyre_life_laps'] < lo:
                item['age_coverage'] = 'extrapolated_below'
            elif item['tyre_life_laps'] > hi:
                item['age_coverage'] = 'extrapolated_above'
            else:
                item['age_coverage'] = 'covered'
        split.append(item)

    def laps(selector):
        return [s['lap_number'] for s in split if selector(s)]

    coverage = []
    for name in ('training', 'validation'):
        for compound in sorted({s['compound'] for s in split if s['split'] == name}):
            items = [s for s in split if s['split'] == name and s['compound'] == compound]
            coverage.append({'split': name, 'compound': compound, 'laps': len(items),
                             'stints': sorted({s['stint'] for s in items}),
                             'lap_range': [min(s['lap_number'] for s in items), max(s['lap_number'] for s in items)],
                             'tyre_life_range': [min(s['tyre_life_laps'] for s in items),
                                                 max(s['tyre_life_laps'] for s in items)]})
    summary = {
        'training_laps': laps(lambda s: s['split'] == 'training'),
        'validation_laps': laps(lambda s: s['split'] == 'validation'),
        'excluded_from_fit_laps': laps(lambda s: s['split'] == 'excluded_from_fit'),
        'validation_covered_laps': laps(lambda s: s['age_coverage'] == 'covered'),
        'validation_extrapolated_laps': laps(lambda s: s['age_coverage'].startswith('extrapolated')
                                             or s['age_coverage'] == 'compound_not_in_training'),
        'training_age_range_by_compound': {c: list(v) for c, v in sorted(age_range.items())},
        'coverage': coverage,
        'identifiability_training': identifiability(training),
    }
    return split, summary


def _git_state(root: Path) -> dict:
    try:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True,
                                text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(['git', 'status', '--porcelain', '--', 'src', 'configs'], cwd=root,
                                    capture_output=True, text=True, check=True).stdout.strip())
        return {'commit': commit, 'uncommitted_changes_in_src_or_configs': dirty}
    except (OSError, subprocess.CalledProcessError):
        return {'commit': None, 'uncommitted_changes_in_src_or_configs': None}


def freeze_partition(config: dict, root: Path) -> dict:
    """Genera el CSV de partición y el manifiesto con huellas. Requiere `python main.py download`."""
    settings = config['partition']
    annotated_path = root/'data/processed/openf1_target_laps_annotated.csv'
    with annotated_path.open(encoding='utf-8', newline='') as handle:
        annotated = list(csv.DictReader(handle))
    split, summary = build_partition(annotated, settings['validation_stint'])
    split_path = root/'data/processed/partition_split.csv'
    write_csv(split_path, split)
    inputs = sorted((root/'data/raw/openf1').glob('*.json')) + [annotated_path]
    manifest = {
        'task': 'MA-03', 'scheme': SCHEME, 'settings': settings,
        'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
        'frozen_before_calibration': not (root/'src/calibration.py').exists(),
        'code_state': _git_state(root),
        'reads_lap_times': False,
        **summary,
        'metrics_preregistered': {
            'error_definition': 'error_i = tiempo_predicho_i - tiempo_observado_i [s]',
            'metrics': {'MAE_s': 'media de |error_i|', 'bias_s': 'media de error_i (sesgo)',
                        'cumulative_error_s': 'suma de error_i sobre el conjunto'},
            'validation_sets': {
                'validation_all': 'todas las vueltas de validación (número principal)',
                'validation_covered_ages': 'edades dentro del rango de entrenamiento del compuesto',
                'validation_extrapolated_ages': 'edades fuera del rango de entrenamiento',
            },
            'reported_separately': 'reconstruction_full_race: las 57 vueltas con pits y arranque modelados; '
                                   'vuelta 1 con convención oficial (docs/conciliacion_tiempos.md). No es validación.',
        },
        'rules': [
            'Calibrar solo con training_laps. Las vueltas de validación no se usan para elegir ni ajustar parámetros.',
            'Congelar parámetros antes de calcular cualquier métrica de validación.',
            'Si el modelo cambia después de ver la validación: nueva versión, se reportan ambas y se repiten los experimentos afectados.',
            'Reportar los tres conjuntos de validación aunque algún resultado sea desfavorable.',
        ],
        'sha256_portable_inputs': {p.relative_to(root).as_posix(): portable_sha256(p) for p in inputs},
        'sha256_portable_split': portable_sha256(split_path),
        'status': 'FROZEN_PENDING_REVIEW_LUIS_PEDRO',
    }
    out = root/'results/data_audit'
    out.mkdir(parents=True, exist_ok=True)
    (out/'partition_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest
