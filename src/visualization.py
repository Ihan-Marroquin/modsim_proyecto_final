"""Figuras del informe (LG-01), generadas solo desde los CSV/JSON de evidencia.

Ningún número de las figuras se escribe a mano: todo sale de
``docs/evidence/`` o de ``results/validation/`` (este último se regenera con
``python main.py validate`` y no se versiona por la licencia CC BY-NC-SA de
OpenF1/Jolpica).

Convenciones que se conservan del trabajo de Luis Pedro:
- ``error = predicho − observado`` (positivo: el modelo es más lento).
- ``mejora_s = tiempo_base − tiempo_candidata`` (positivo: candidata más rápida).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

MAIN_TREND = 'trend_fuel_reference'
TREND_LABELS = {
    'trend_zero': 'Tendencia 0 s/vuelta',
    'trend_fuel_reference': 'Tendencia −0.0444 s/vuelta (principal)',
    'trend_double': 'Tendencia −0.0888 s/vuelta',
}
COMPOUND_COLORS = {'SOFT': '#d62728', 'MEDIUM': '#e8c21a', 'HARD': '#7f7f7f'}
CONDITION_LABELS = {
    'A': 'A: histórica ×1.00',
    'B': 'B: candidata ×1.00',
    'C': 'C: histórica ×1.20',
    'D': 'D: candidata ×1.20',
}
SIMULATED_NOTE = 'Valores simulados por el modelo (no observados).'

EVIDENCE = Path('docs/evidence')
VALIDATION_LAPS = Path('results/validation/validacion_vueltas.csv')


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def is_true(value: str) -> bool:
    return value.strip().lower() == 'true'


def _save(fig, out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    fig.savefig(path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    return path


def _style() -> None:
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'DejaVu Serif'],
        'font.size': 10,
        'axes.grid': True,
        'grid.alpha': 0.3,
        'axes.spines.top': False,
        'axes.spines.right': False,
    })


# ---------------------------------------------------------------- figura 1
def figure_validation(root: Path, out_dir: Path) -> Path | None:
    """Vueltas observadas y predichas; solo el stint 3 es validación reservada."""
    source = root / VALIDATION_LAPS
    if not source.exists():
        return None
    rows = read_csv(source)
    laps = [int(r['lap']) for r in rows]
    observed = [float(r['observed_official_s']) for r in rows]
    predicted = [float(r[f'predicted_{MAIN_TREND}_s']) for r in rows]
    validation = [r for r in rows if is_true(r['in_validation_all'])]
    val_laps = [int(r['lap']) for r in validation]
    val_error = [float(r[f'error_{MAIN_TREND}_s']) for r in validation]
    extrapolated = {int(r['lap']) for r in validation if is_true(r['in_validation_extrapolated_ages'])}
    cumulative = []
    total = 0.0
    for err in val_error:
        total += err
        cumulative.append(total)

    fig, (top, mid, bottom) = plt.subplots(3, 1, figsize=(8, 8.2), sharex=True,
                                           gridspec_kw={'height_ratios': [2.2, 1.3, 1.1]})
    top.axvspan(min(val_laps) - 0.5, max(val_laps) + 0.5, color='#1f77b4', alpha=0.08,
                label='Stint 3 reservado (validación)')
    top.plot(laps, observed, 'o', ms=3.5, color='black', label='Observado (FIA/Jolpica, OpenF1)')
    # Las vueltas de entrada a pits (17 y 37) saturan el eje; se recorta al ritmo normal
    # y esas vueltas quedan fuera de escala (se cortan en la línea predicha).
    normal = sorted(observed)[len(observed) // 2]
    upper = normal + 5.5
    visible = [p if p <= upper else float('nan') for p in predicted]
    top.plot(laps, visible, '-', lw=1.4, color='#1f77b4', label='Predicho por el modelo (simulado)')
    top.set_ylim(normal - 4.5, upper)
    off_observed = [str(lap) for lap, o in zip(laps, observed) if o > upper]
    off_predicted = [str(lap) for lap, p in zip(laps, predicted) if p > upper]
    if off_observed or off_predicted:
        top.text(0.01, 0.02, 'Fuera de escala por pérdida de pits: observado v' + ', '.join(off_observed)
                 + '; predicho v' + ', '.join(off_predicted) + ' (el modelo la agrupa en la vuelta de entrada)',
                 transform=top.transAxes, fontsize=7)
    top.set_ylabel('Tiempo de vuelta (s)')
    top.set_title('Figura 1. Validación del modelo congelado en el stint 3 reservado '
                  '(error = predicho − observado)')
    top.legend(loc='upper right', fontsize=8)

    colors = ['#ff7f0e' if lap in extrapolated else '#1f77b4' for lap in val_laps]
    mid.bar(val_laps, val_error, color=colors)
    mid.axhline(0, color='black', lw=0.8)
    mid.set_ylabel('Error por vuelta (s)')
    mid.legend(handles=[Patch(color='#1f77b4', label='Edad cubierta por entrenamiento'),
                        Patch(color='#ff7f0e', label='Edad extrapolada')], fontsize=8, loc='lower left')

    bottom.plot(val_laps, cumulative, '-o', ms=3, color='#2ca02c')
    bottom.axhline(0, color='black', lw=0.8)
    bottom.annotate(f'{cumulative[-1]:+.3f} s', (val_laps[-1], cumulative[-1]),
                    textcoords='offset points', xytext=(-40, 6), fontsize=9)
    bottom.set_ylabel('Error acumulado (s)')
    bottom.set_xlabel('Vuelta de carrera')
    fig.text(0.01, -0.01, 'Fuente: OpenF1 y Jolpica (CC BY-NC-SA 4.0), vuelta 1 con convención FIA. '
             'Escenario principal trend_fuel_reference, sin reajuste.', fontsize=7)
    return _save(fig, out_dir, 'fig1_validacion_stint3.png')


# ---------------------------------------------------------------- figura 2
def _stint_ranges(rows: list[dict[str, str]]) -> list[tuple[int, int, str, int]]:
    """(primera vuelta, última vuelta, compuesto, número de stint)."""
    ranges: list[tuple[int, int, str, int]] = []
    for row in rows:
        lap, compound = int(row['lap']), row['compound']
        if ranges and ranges[-1][2] == compound and int(row['stint']) == ranges[-1][3]:
            first, _, comp, stint = ranges[-1]
            ranges[-1] = (first, lap, comp, stint)
        else:
            ranges.append((lap, lap, compound, int(row['stint'])))
    return ranges


def figure_stints(root: Path, out_dir: Path) -> Path:
    rows = read_csv(root / EVIDENCE / 'experiments/vueltas_deterministas.csv')
    by_condition: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_condition.setdefault(row['condition'], []).append(row)
    for laps in by_condition.values():
        laps.sort(key=lambda r: int(r['lap']))

    fig, (bars, diff) = plt.subplots(2, 1, figsize=(8, 5.4), gridspec_kw={'height_ratios': [1.2, 1.5]})
    labels = {'A': 'Histórica (A)', 'B': 'Candidata (B, simulada)'}
    for y, condition in enumerate(['B', 'A']):
        laps = by_condition[condition]
        for first, last, compound, _ in _stint_ranges(laps):
            start_age = next(int(r['tyre_age_end_laps']) for r in laps if int(r['lap']) == first)
            end_age = next(int(r['tyre_age_end_laps']) for r in laps if int(r['lap']) == last)
            bars.barh(y, last - first + 1, left=first - 0.5, color=COMPOUND_COLORS[compound],
                      edgecolor='white', height=0.6)
            bars.text((first + last) / 2, y, f'{compound}\nv{first}–{last}, edad {start_age}→{end_age}',
                      ha='center', va='center', fontsize=7.5, color='white')
    bars.set_yticks([0, 1], [labels['B'], labels['A']])
    bars.set_xlim(0.5, 57.5)
    bars.grid(False)
    bars.set_title('Figura 2. Cronograma de stints: estrategia histórica y candidata congelada')

    a = {int(r['lap']): float(r['cumulative_s']) for r in by_condition['A']}
    b = {int(r['lap']): float(r['cumulative_s']) for r in by_condition['B']}
    for condition in ('C', 'D'):
        by_condition.setdefault(condition, [])
    laps = sorted(a)
    diff.plot(laps, [a[lap] - b[lap] for lap in laps], color='#1f77b4', label='Degradación ×1.00 (A − B)')
    if by_condition['C'] and by_condition['D']:
        c = {int(r['lap']): float(r['cumulative_s']) for r in by_condition['C']}
        d = {int(r['lap']): float(r['cumulative_s']) for r in by_condition['D']}
        diff.plot(laps, [c[lap] - d[lap] for lap in laps], color='#ff7f0e', label='Degradación ×1.20 (C − D)')
        final_cd = c[laps[-1]] - d[laps[-1]]
        diff.annotate(f'{final_cd:+.4f} s', (laps[-1], final_cd), textcoords='offset points',
                      xytext=(-60, -24), fontsize=8, color='#ff7f0e')
    final_ab = a[laps[-1]] - b[laps[-1]]
    diff.annotate(f'{final_ab:+.4f} s', (laps[-1], final_ab), textcoords='offset points',
                  xytext=(-55, 8), fontsize=8, color='#1f77b4')
    diff.axhline(0, color='black', lw=0.8)
    diff.set_xlim(0.5, 57.5)
    # La candidata para una vuelta antes (36 frente a 37): ese pico de pérdida de pits
    # domina la escala, así que se recorta y se indica.
    gaps = [a[lap] - b[lap] for lap in laps]
    floor = sorted(gaps)[1] if len(gaps) > 1 else min(gaps)
    spike_lap = laps[gaps.index(min(gaps))]
    diff.set_ylim(floor * 1.25, max(1.0, max(gaps)) + 1.0)
    diff.annotate(f'Vuelta {spike_lap}: la candidata ya entró a pits\n'
                  f'(pico de {min(gaps):.1f} s, fuera de escala)', (spike_lap, floor * 1.2),
                  textcoords='offset points', xytext=(-150, 10), fontsize=7.5,
                  arrowprops={'arrowstyle': '->', 'lw': 0.7})
    diff.set_xlabel('Vuelta de carrera')
    diff.set_ylabel('Ventaja acumulada\nbase − candidata (s)')
    diff.legend(fontsize=8, loc='lower left')
    fig.text(0.01, -0.02, 'Modo determinista, tendencia principal. ' + SIMULATED_NOTE
             + ' Positivo = la candidata va adelante.', fontsize=7)
    fig.tight_layout()
    return _save(fig, out_dir, 'fig2_cronograma_stints.png')


# ---------------------------------------------------------------- figura 3
def figure_distribution(root: Path, out_dir: Path) -> Path:
    replicas = [r for r in read_csv(root / EVIDENCE / 'experiments/replicas.csv')
                if r['trend_scenario'] == MAIN_TREND]
    pairs = [r for r in read_csv(root / EVIDENCE / 'experiments/diferencias_pareadas.csv')
             if r['trend_scenario'] == MAIN_TREND]
    conditions = ['A', 'B', 'C', 'D']
    totals = {c: [float(r['total_time_s']) for r in replicas if r['condition'] == c] for c in conditions}

    fig, (left, right) = plt.subplots(1, 2, figsize=(9.5, 4.4), gridspec_kw={'width_ratios': [1.3, 1]})
    left.boxplot([totals[c] for c in conditions], tick_labels=[CONDITION_LABELS[c] for c in conditions],
                 widths=0.5)
    for i, c in enumerate(conditions, start=1):
        left.scatter([i] * len(totals[c]), totals[c], s=8, alpha=0.5, color='#1f77b4', zorder=3)
    left.tick_params(axis='x', labelsize=7.5)
    left.set_ylabel('Tiempo total de carrera (s)')
    n = {c: len(totals[c]) for c in conditions}
    left.set_title(f'Tiempo total por condición ({n["A"]} réplicas cada una)', fontsize=10)

    for pair, color in (('A-B', '#1f77b4'), ('C-D', '#ff7f0e')):
        rows = sorted((r for r in pairs if r['pair'] == pair), key=lambda r: int(r['evaluation_seed']))
        seeds = [int(r['evaluation_seed']) for r in rows]
        values = [float(r['mejora_s']) for r in rows]
        right.plot(seeds, values, 'o', ms=4, color=color, label=f'{pair}: {values[0]:+.4f} s')
    right.axhline(0, color='black', lw=0.8)
    right.set_xlabel('Semilla de evaluación')
    right.set_ylabel('mejora_s = base − candidata (s)')
    right.set_title('Diferencias pareadas por semilla', fontsize=10)
    right.legend(fontsize=8)
    right.text(0.02, 0.5, 'Constante por construcción:\nlas dos estrategias de cada par\nreciben el mismo ruido,\n'
               'que se cancela. No mide\nincertidumbre del modelo.', transform=right.transAxes,
               fontsize=7.5, va='center', bbox={'facecolor': 'white', 'alpha': 0.85, 'edgecolor': '#999'})
    fig.suptitle('Figura 3. Experimentos A/B/C/D: distribución de tiempos y diferencias pareadas')
    fig.text(0.01, -0.03, SIMULATED_NOTE + ' Semillas reservadas, tendencia principal.', fontsize=7)
    fig.tight_layout()
    return _save(fig, out_dir, 'fig3_distribucion_ABCD.png')


# ---------------------------------------------------------------- figura 4
def figure_sensitivity(root: Path, out_dir: Path) -> Path:
    rows = read_csv(root / EVIDENCE / 'experiments/sensibilidad.csv')
    summary = read_json(root / EVIDENCE / 'experiments/resumen.json')
    uncertainty = summary['parameter_uncertainty']
    break_even = summary['difference_decomposition']['1.0']['break_even_degradation_multiplier']

    fig, ax = plt.subplots(figsize=(8, 4.6))
    styles = {'trend_zero': ('#2ca02c', '--'), MAIN_TREND: ('#1f77b4', '-'), 'trend_double': ('#9467bd', ':')}
    for scenario, (color, line) in styles.items():
        points = sorted((float(r['degradation_multiplier']), float(r['mejora_s']))
                        for r in rows if r['trend_scenario'] == scenario)
        ax.plot([p[0] for p in points], [p[1] for p in points], line, marker='o', ms=3.5,
                color=color, label=TREND_LABELS[scenario])
    multipliers, centers, half_widths = [], [], []
    for item in uncertainty.values():
        if isinstance(item, dict) and 'se_s' in item:
            multipliers.append(float(item['degradation_multiplier']))
            centers.append(float(item['mejora_s']))
            half_widths.append(1.96 * float(item['se_s']))
    ax.errorbar(multipliers, centers, yerr=half_widths, fmt='s', color='black', capsize=5, ms=5,
                label='±1.96·EE por parámetros de calibración', zorder=4)
    ax.axhline(0, color='black', lw=0.8)
    ax.axvline(break_even, color='#1f77b4', lw=0.8, ls='-.')
    ax.annotate(f'Equilibrio ×{break_even:.3f}', (break_even, 0), textcoords='offset points',
                xytext=(6, 40), fontsize=8, color='#1f77b4')
    ax.set_xlabel('Multiplicador de la degradación')
    ax.set_ylabel('mejora_s = histórica − candidata (s)')
    ax.set_title('Figura 4. Sensibilidad de la ventaja de la candidata a la degradación y a la tendencia')
    ax.legend(fontsize=8, loc='lower left', bbox_to_anchor=(0.0, 0.12))
    fig.text(0.01, -0.03, 'Modo determinista. ' + SIMULATED_NOTE
             + ' Positivo = candidata más rápida. EE condicional a tendencia fija.', fontsize=7)
    return _save(fig, out_dir, 'fig4_sensibilidad.png')


# ---------------------------------------------------------------- figura 5
def figure_convergence(root: Path, out_dir: Path) -> Path:
    trace = read_csv(root / EVIDENCE / 'optimization/candidate_trace.csv')
    runs = read_csv(root / EVIDENCE / 'optimization/search_runs.csv')
    summary = read_json(root / EVIDENCE / 'optimization/summary.json')
    reference = summary['reference_by_stops']['2']['time_s']
    historical = summary['historical']['time_s']

    fig, (left, right) = plt.subplots(1, 2, figsize=(9.5, 4.2), gridspec_kw={'width_ratios': [1.5, 1]})
    iterations = [int(r['iteration']) for r in trace]
    left.plot(iterations, [float(r['current_s']) for r in trace], color='#aec7e8', label='Solución actual')
    left.plot(iterations, [float(r['best_s']) for r in trace], color='#1f77b4', lw=1.8, label='Mejor visitada')
    left.axhline(reference, color='black', ls='--', lw=0.9,
                 label=f'Óptimo de la enumeración ({summary["reference_by_stops"]["2"]["objective_evaluations"]} estrategias)')
    left.axhline(historical, color='#d62728', ls=':', lw=1.0, label='Histórica simulada')
    left.set_xlabel('Iteración')
    left.set_ylabel('Tiempo simulado sin ruido (s)')
    left.set_title(f'Traza de la búsqueda {summary["frozen_candidate"]["seed"]}', fontsize=10)
    left.legend(fontsize=7.5)
    temp = left.twinx()
    temp.plot(iterations, [float(r['temperature_s']) for r in trace], color='#7f7f7f', lw=0.8, alpha=0.6)
    temp.set_ylabel('Temperatura (s)', color='#7f7f7f')
    temp.grid(False)

    gaps = [float(r['gap_to_reference_s']) for r in runs]
    at_reference = sum(is_true(r['reached_reference']) for r in runs)
    left_runs = [int(r['seed']) for r in runs]
    right.bar(left_runs, gaps, color=['#1f77b4' if is_true(r['reached_reference']) else '#ff7f0e' for r in runs])
    right.set_xlabel('Semilla de búsqueda')
    right.set_ylabel('Brecha contra la enumeración (s)')
    right.set_title(f'{at_reference} de {len(runs)} búsquedas llegan al óptimo', fontsize=10)
    fig.suptitle('Figura 5 (adicional). Convergencia del recocido simulado discreto')
    fig.text(0.01, -0.03, 'Objetivo determinista de entrenamiento. ' + SIMULATED_NOTE, fontsize=7)
    fig.tight_layout()
    return _save(fig, out_dir, 'fig5_convergencia_recocido.png')


def make_figures(root: Path, out_dir: Path) -> dict[str, str | None]:
    """Genera las figuras comprometidas y la adicional. Devuelve las rutas creadas."""
    _style()
    produced = {
        'fig1_validacion': figure_validation(root, out_dir),
        'fig2_stints': figure_stints(root, out_dir),
        'fig3_distribucion': figure_distribution(root, out_dir),
        'fig4_sensibilidad': figure_sensitivity(root, out_dir),
        'fig5_convergencia': figure_convergence(root, out_dir),
    }
    return {k: (_display_path(v, root) if v else None) for k, v in produced.items()}


def _display_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
