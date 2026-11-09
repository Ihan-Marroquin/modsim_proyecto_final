"""LP-03: pruebas de la validación reservada y de la reconstrucción completa.

Las pruebas de método usan filas construidas a mano. La prueba de integración con el caso
real se omite si no se regeneraron los datos (`download`, `reconcile`, `partition`).
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.data import portable_sha256
from src.validation import (check_frozen_inputs, error_metrics, race_segments, reconstruct_full_race,
                            run_validation, second_pit_check, validate_reserved)

ROOT = Path(__file__).resolve().parents[1]
HAS_DATA = all((ROOT / p).exists() for p in ('data/processed/partition_split.csv',
                                              'data/processed/lap_time_reconciliation.csv',
                                              'data/processed/openf1_target_laps_annotated.csv'))


def sim_lap(lap, stint, elapsed, normal=None, pit=0.0, start=0.0):
    return {'lap': lap, 'stint': stint, 'compound': 'SOFT', 'tyre_age_end_laps': lap,
            'normal_lap_s': elapsed - pit - start if normal is None else normal,
            'additional_pit_loss_s': pit, 'start_penalty_s': start, 'elapsed_s': elapsed}


def obs_lap(lap, stint, observed, split):
    return {'lap': lap, 'stint': stint, 'split': split, 'observed_official_s': observed}


class MetricTests(unittest.TestCase):
    def test_preregistered_metrics_and_sign_convention(self):
        m = error_metrics([1.0, -0.5, 0.5])  # predicho − observado
        self.assertAlmostEqual(m['MAE_s'], 2 / 3)
        self.assertAlmostEqual(m['bias_s'], 1 / 3)
        self.assertAlmostEqual(m['cumulative_error_s'], 1.0)
        self.assertAlmostEqual(m['max_abs_error_s'], 1.0)
        self.assertEqual(m['n_laps'], 3)

    def test_empty_or_non_finite_errors_are_rejected(self):
        for bad in ([], [float('nan')]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                error_metrics(bad)


class FixtureTests(unittest.TestCase):
    def setUp(self):
        # Carrera de 6 vueltas: arranque, parada tras la 2, entrenamiento 3, validación 5–6.
        self.simulated = [sim_lap(1, 1, 100.5, start=0.5), sim_lap(2, 1, 120.0, normal=100.0, pit=20.0),
                          sim_lap(3, 2, 99.0), sim_lap(4, 2, 99.0), sim_lap(5, 2, 98.0), sim_lap(6, 2, 98.0)]
        self.observed = {1: obs_lap(1, 1, 100.5, 'excluded_from_fit'), 2: obs_lap(2, 1, 102.0, 'excluded_from_fit'),
                         3: obs_lap(3, 2, 117.0, 'excluded_from_fit'), 4: obs_lap(4, 2, 99.0, 'training'),
                         5: obs_lap(5, 2, 97.0, 'validation'), 6: obs_lap(6, 2, 98.5, 'validation')}
        clock = 0.0
        for lap in self.simulated:
            clock += lap['elapsed_s']
            lap['cumulative_s'] = clock
        for lap in self.observed.values():
            lap['observed_openf1_s'] = lap['observed_official_s']
        self.manifest = {'validation_laps': [5, 6], 'validation_covered_laps': [6],
                         'validation_extrapolated_laps': [5]}

    def test_reserved_sets_use_only_validation_laps(self):
        result = validate_reserved(self.observed, self.simulated, self.manifest)
        self.assertAlmostEqual(result['validation_all']['cumulative_error_s'], 1.0 - 0.5)
        self.assertAlmostEqual(result['validation_covered_ages']['bias_s'], -0.5)
        self.assertAlmostEqual(result['validation_extrapolated_ages']['MAE_s'], 1.0)
        leaked = dict(self.manifest, validation_covered_laps=[4])
        with self.assertRaises(ValueError):
            validate_reserved(self.observed, self.simulated, leaked)

    def test_segments_keep_each_pit_pair_together(self):
        labels = race_segments(self.simulated)
        self.assertEqual(labels[1], 'start_lap_1')
        self.assertEqual(labels[2], labels[3])
        self.assertEqual(labels[2], 'pit_2_3')
        self.assertEqual(labels[6], 'stint_2_normal')

    def test_reconstruction_segments_add_up_to_the_total_difference(self):
        official = sum(o['observed_official_s'] for o in self.observed.values())
        rec = reconstruct_full_race(self.observed, self.simulated, official)
        total = sum(s['cumulative_error_s'] for s in rec['by_segment'].values())
        self.assertAlmostEqual(total, rec['simulated_minus_official_s'])
        self.assertAlmostEqual(rec['by_segment']['pit_2_3']['cumulative_error_s'], (120 + 99) - (102 + 117))
        self.assertTrue(rec['lap_sum_matches_official_total'])

    def test_second_pit_check_compares_implied_and_calibrated_loss(self):
        check = second_pit_check(self.observed, self.simulated, in_lap=2)
        self.assertAlmostEqual(check['implied_additional_pit_loss_s'], (102 + 117) - (100 + 99))
        self.assertAlmostEqual(check['calibrated_minus_implied_s'], 0.0)


class FrozenInputTests(unittest.TestCase):
    def test_validation_stops_if_partition_differs_from_frozen_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ('configs/params_bahrain_2024.json', 'docs/evidence/optimization/summary.json'):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / rel, root / rel)
            split = root / 'data/processed/partition_split.csv'
            split.parent.mkdir(parents=True)
            split.write_text('lap_number,split\n1,training\n', encoding='utf-8')
            manifest = root / 'docs/evidence/particion_manifiesto.json'
            manifest.write_text(json.dumps({'sha256_portable_split': portable_sha256(split)}), encoding='utf-8')
            self.assertTrue(check_frozen_inputs(root)['params_match_optimization_inputs'])
            split.write_text('lap_number,split\n1,validation\n', encoding='utf-8')
            with self.assertRaises(RuntimeError):
                check_frozen_inputs(root)


@unittest.skipUnless(HAS_DATA, 'Requiere python main.py download, reconcile y partition')
class RealCaseValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.report = run_validation(ROOT, Path(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_preregistered_sets_and_sizes(self):
        sets = self.report['by_scenario']['trend_fuel_reference']['reserved_validation']
        self.assertEqual({k: v['n_laps'] for k, v in sets.items()},
                         {'validation_all': 18, 'validation_covered_ages': 14, 'validation_extrapolated_ages': 4})
        self.assertEqual(sorted(sets['validation_covered_ages']['laps'] + sets['validation_extrapolated_ages']['laps']),
                         sets['validation_all']['laps'])
        self.assertNotIn(46, sets['validation_all']['laps'])

    def test_reconstruction_is_reported_apart_and_matches_simulator(self):
        rec = self.report['by_scenario']['trend_fuel_reference']['full_race_reconstruction']
        self.assertAlmostEqual(rec['simulated_minus_official_s'], 9.9572, places=3)
        self.assertTrue(rec['lap_sum_matches_official_total'])
        self.assertAlmostEqual(rec['observed_lap_sum_openf1_s'] - rec['official_total_fia_s'], 0.475, places=3)

    def test_training_stints_are_identical_across_trend_scenarios(self):
        segments = {s: v['full_race_reconstruction']['by_segment'] for s, v in self.report['by_scenario'].items()}
        for name in ('stint_1_normal', 'stint_2_normal', 'pit_17_18'):
            values = [segments[s][name]['cumulative_error_s'] for s in segments]
            self.assertAlmostEqual(max(values) - min(values), 0.0, places=8)

    def test_versionable_summary_has_no_per_lap_source_times(self):
        text = (Path(self.tmp.name) / 'validacion.json').read_text(encoding='utf-8')
        self.assertNotIn('observed_openf1_s', text)
        self.assertTrue(self.report['frozen_inputs']['params_match_optimization_inputs'])


if __name__ == '__main__':
    unittest.main()
