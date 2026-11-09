"""LP-04/LP-05: diseño A/B/C/D, emparejamiento por semilla, signos y reproducibilidad."""
import csv
import tempfile
import unittest
from pathlib import Path

from src.experiments import describe, load_protocol, paired_differences, run_experiments

ROOT = Path(__file__).resolve().parents[1]


class ProtocolTests(unittest.TestCase):
    def test_reserved_seeds_are_disjoint_from_pilots_and_search(self):
        protocol = load_protocol(ROOT)
        self.assertEqual(protocol['seeds'], list(range(3300, 3330)))
        used = set(protocol['optimizer']['pilot_seeds']) | set(protocol['optimizer']['search_seeds'])
        self.assertFalse(used & set(protocol['seeds']))
        self.assertEqual(protocol['candidate'].stops_after_lap, (17, 36))
        self.assertEqual(protocol['candidate_search_seed'], 2100)

    def test_describe_known_values(self):
        d = describe([1.0, 2.0, 3.0])
        self.assertAlmostEqual(d['mean'], 2.0)
        self.assertAlmostEqual(d['sd'], 1.0)
        self.assertAlmostEqual(d['ci95_mean'][1] - d['mean'], 4.303 / 3 ** 0.5, places=6)

    def test_pairs_require_identical_seeds(self):
        rows = [{'trend_scenario': 't', 'condition': c, 'evaluation_seed': s, 'total_time_s': 1.0,
                 'deterministic_time_s': 1.0, 'noise_sum_s': 0.0, 'degradation_multiplier': 1.0}
                for c, s in (('A', 1), ('B', 2), ('C', 1), ('D', 1))]
        with self.assertRaises(ValueError):
            paired_differences(rows)


class FullExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.report = run_experiments(ROOT, cls.out)
        with (cls.out / 'replicas.csv').open(encoding='utf-8', newline='') as handle:
            cls.rows = list(csv.DictReader(handle))
        with (cls.out / 'diferencias_pareadas.csv').open(encoding='utf-8', newline='') as handle:
            cls.pairs = list(csv.DictReader(handle))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_120_replicates_with_30_reserved_seeds_per_condition(self):
        self.assertEqual(len(self.rows), 120)
        for condition in 'ABCD':
            seeds = [int(r['evaluation_seed']) for r in self.rows if r['condition'] == condition]
            self.assertEqual(seeds, list(range(3300, 3330)))
        self.assertTrue(all(r['feasible'] == 'True' for r in self.rows))
        self.assertEqual({r['degradation_multiplier'] for r in self.rows if r['condition'] in 'CD'}, {'1.2'})
        self.assertEqual({r['stops_after_lap'] for r in self.rows if r['condition'] in 'BD'}, {'[17, 36]'})

    def test_replicates_within_a_condition_differ(self):
        times = [float(r['total_time_s']) for r in self.rows if r['condition'] == 'A']
        self.assertEqual(len(set(times)), 30)

    def test_paired_sign_convention_and_noise_cancellation(self):
        self.assertEqual(len(self.pairs), 60)
        for p in self.pairs:
            self.assertAlmostEqual(float(p['mejora_s']), float(p['base_time_s']) - float(p['candidate_time_s']), places=9)
            self.assertAlmostEqual(float(p['mejora_s']), float(p['deterministic_mejora_s']), places=8)
            self.assertEqual(float(p['noise_sum_difference_s']), 0.0)
        main = self.report['results_by_trend_scenario']['trend_fuel_reference']['by_pair']
        self.assertAlmostEqual(main['A-B']['mejora_s']['mean'], 0.075, places=6)
        self.assertAlmostEqual(main['C-D']['mejora_s']['mean'], -0.06244, places=6)
        self.assertLess(main['A-B']['mejora_s']['sd'], 1e-9)

    def test_reproducible_with_same_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            again = run_experiments(ROOT, Path(tmp))
        first = self.report['results_by_trend_scenario']
        second = again['results_by_trend_scenario']
        self.assertEqual(first, second)

    def test_pit_loss_does_not_change_the_difference(self):
        self.assertLess(self.report['pit_loss_invariance']['max_spread_s'], 1e-8)


if __name__ == '__main__':
    unittest.main()
