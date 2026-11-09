"""Pruebas de LG-01/LG-02: las figuras salen de la evidencia y no de números escritos a mano."""
import json
import tempfile
import unittest
from pathlib import Path

try:
    import matplotlib  # noqa: F401
    HAS_MATPLOTLIB = True
except ImportError:  # el núcleo funciona sin bibliotecas opcionales
    HAS_MATPLOTLIB = False

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence'


@unittest.skipUnless(HAS_MATPLOTLIB, 'matplotlib no está instalado (requirements.txt)')
class VisualizationTests(unittest.TestCase):
    def test_make_figures_writes_every_committed_figure(self):
        from src.visualization import make_figures
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            produced = make_figures(ROOT, out)
            for key in ('fig2_stints', 'fig3_distribucion', 'fig4_sensibilidad', 'fig5_convergencia'):
                self.assertIsNotNone(produced[key], key)
                self.assertGreater((out / Path(produced[key]).name).stat().st_size, 10_000)
            validation_csv = ROOT / 'results/validation/validacion_vueltas.csv'
            self.assertEqual(produced['fig1_validacion'] is not None, validation_csv.exists())

    def test_stint_ranges_match_frozen_strategies(self):
        from src.visualization import _stint_ranges, read_csv
        rows = read_csv(EVIDENCE / 'experiments/vueltas_deterministas.csv')
        summary = json.loads((EVIDENCE / 'optimization/summary.json').read_text(encoding='utf-8'))
        expected = {'A': summary['historical']['strategy'], 'B': summary['frozen_candidate']['strategy']}
        for condition, strategy in expected.items():
            laps = sorted((r for r in rows if r['condition'] == condition), key=lambda r: int(r['lap']))
            ranges = _stint_ranges(laps)
            self.assertEqual([last for _, last, _, _ in ranges[:-1]], strategy['stops_after_lap'])
            self.assertEqual([comp for _, _, comp, _ in ranges], [s['compound'] for s in strategy['stints']])
            self.assertEqual(ranges[-1][1], 57)

    def test_paired_difference_in_figure_source_equals_summary(self):
        from src.visualization import MAIN_TREND, read_csv
        summary = json.loads((EVIDENCE / 'experiments/resumen.json').read_text(encoding='utf-8'))
        by_pair = summary['results_by_trend_scenario'][MAIN_TREND]['by_pair']
        rows = [r for r in read_csv(EVIDENCE / 'experiments/diferencias_pareadas.csv')
                if r['trend_scenario'] == MAIN_TREND]
        for pair in ('A-B', 'C-D'):
            values = [float(r['mejora_s']) for r in rows if r['pair'] == pair]
            self.assertEqual(len(values), 30)
            self.assertAlmostEqual(sum(values) / len(values), by_pair[pair]['mejora_s']['mean'], places=9)


class CompareCommandTests(unittest.TestCase):
    def test_compare_reproduces_frozen_saving(self):
        from src.domain import strategy_from_dict
        from src.model import simulate_bahrain_case
        summary = json.loads((EVIDENCE / 'optimization/summary.json').read_text(encoding='utf-8'))
        candidate = strategy_from_dict(json.loads((EVIDENCE / 'optimization/candidate.json').read_text(encoding='utf-8')))
        base = simulate_bahrain_case(root_dir=ROOT)['summary']['total_simulated_time_s']
        cand = simulate_bahrain_case(root_dir=ROOT, strategy=candidate)['summary']['total_simulated_time_s']
        self.assertAlmostEqual(base - cand, summary['predicted_saving_s'], places=3)


if __name__ == '__main__':
    unittest.main()
