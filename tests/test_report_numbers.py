"""LG-03: las cifras del informe integrado salen de la evidencia versionada.

Cada número clave de `report/informe.md` se recalcula desde `docs/evidence/` y se busca
en el texto con el mismo redondeo. Si alguien cambia la evidencia o escribe una cifra a
mano, esta prueba falla.
"""
import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence'
REPORT = ROOT / 'report/informe.md'


def load(path):
    return json.loads((EVIDENCE / path).read_text(encoding='utf-8'))


def signed(value, decimals):
    """Formato del informe: signo explícito y menos tipográfico (−)."""
    return f'{value:+.{decimals}f}'.replace('-', '−')


def plain(value, decimals):
    return f'{value:.{decimals}f}'.replace('-', '−')


class ReportNumbersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = REPORT.read_text(encoding='utf-8')

    def assertInReport(self, fragment):
        self.assertTrue(fragment in self.text, f'No aparece en el informe: {fragment!r}')

    def test_reserved_validation_metrics(self):
        validation = load('validation/validacion.json')
        main = validation['by_scenario'][validation['main_scenario']]
        for name, metrics in main['reserved_validation'].items():
            row = (f'| {metrics["n_laps"]} | {plain(metrics["MAE_s"], 3)} | {signed(metrics["bias_s"], 3)} '
                   f'| {signed(metrics["cumulative_error_s"], 3)} |')
            self.assertInReport(row)
        reconstruction = main['full_race_reconstruction']
        self.assertInReport(plain(reconstruction['simulated_total_s'], 3))
        self.assertInReport(signed(reconstruction['simulated_minus_official_s'], 3))
        pit = main['second_pit_check']
        self.assertInReport(plain(pit['implied_additional_pit_loss_s'], 3))
        self.assertInReport(plain(pit['calibrated_additional_pit_loss_s'], 3))

    def test_trend_sensitivity_of_validation(self):
        with (EVIDENCE / 'validation/sensibilidad_tendencia_validacion.csv').open(encoding='utf-8') as handle:
            for row in csv.DictReader(handle):
                fragment = (f'| {plain(float(row["validation_all_MAE_s"]), 3)} '
                            f'| {signed(float(row["validation_all_bias_s"]), 3)} '
                            f'| {signed(float(row["validation_all_cumulative_error_s"]), 3)} '
                            f'| {signed(float(row["reconstruction_simulated_minus_official_s"]), 3)} |')
                self.assertInReport(fragment)

    def test_experiment_means_and_paired_differences(self):
        summary = load('experiments/resumen.json')
        results = summary['results_by_trend_scenario'][summary['design']['main_trend_scenario']]
        for condition, item in results['by_condition'].items():
            stats = item['total_time_s']
            low, high = stats['ci95_mean']
            row = (f'| {condition} | {plain(item["deterministic_time_s"], 3)} | {plain(stats["mean"], 3)} '
                   f'| {plain(stats["sd"], 3)} | {plain(low, 3)} – {plain(high, 3)} |')
            self.assertInReport(row)
        for pair, item in results['by_pair'].items():
            self.assertInReport(f'| {signed(item["mejora_s"]["mean"], 4)} | {signed(item["mejora_pct"]["mean"], 5)} % '
                                f'| {item["candidate_faster_in_replicates"]} / {item["mejora_s"]["n"]} |')

    def test_parameter_uncertainty_and_break_even(self):
        summary = load('experiments/resumen.json')
        for item in summary['parameter_uncertainty'].values():
            if not isinstance(item, dict) or 'se_s' not in item:
                continue
            low, high = item['approx_ci95_s']
            self.assertInReport(f'| {signed(item["mejora_s"], 3)} | {plain(item["se_s"], 3)} '
                                f'| {signed(low, 3)} – {signed(high, 3)} |')
        break_even = summary['difference_decomposition']['1.0']['break_even_degradation_multiplier']
        self.assertInReport(f'×{break_even:.3f}')

    def test_degradation_sensitivity_table(self):
        with (EVIDENCE / 'experiments/sensibilidad.csv').open(encoding='utf-8') as handle:
            rows = list(csv.DictReader(handle))
        for scenario in ('trend_zero', 'trend_fuel_reference', 'trend_double'):
            values = {float(r['degradation_multiplier']): float(r['mejora_s'])
                      for r in rows if r['trend_scenario'] == scenario}
            cells = ' | '.join(signed(values[m], 3) for m in (0.8, 1.0, 1.1, 1.2, 1.3))
            self.assertInReport(f'| `{scenario}` | {cells} |')

    def test_search_results(self):
        summary = load('optimization/summary.json')
        self.assertInReport(f'{summary["search_runs_at_reference"]} de {summary["search_run_count"]}')
        self.assertInReport(plain(summary['max_search_gap_s'], 4))
        self.assertInReport(str(summary['feasible_by_stops']['2']))
        self.assertInReport(plain(summary['historical']['time_s'], 4))
        self.assertInReport(plain(summary['frozen_candidate']['time_s'], 4))
        self.assertInReport(', '.join(map(str, summary['frozen_candidate']['strategy']['stops_after_lap'])))

    def test_calibrated_parameters(self):
        params = json.loads((ROOT / 'configs/params_bahrain_2024.json').read_text(encoding='utf-8'))['parameters']
        for compound, values in params['compounds'].items():
            self.assertInReport(f'{compound} base (s) | {plain(values["base_lap_s"], 3)}')
            self.assertInReport(f'{compound} desgaste (s/vuelta) | {plain(values["degradation_s_per_lap"], 4)}')
        self.assertInReport(f'{params["race_trend_s_per_lap"]} s/vuelta'.replace('-', '−'))


if __name__ == '__main__':
    unittest.main()
