"""Pruebas de la calibración (MA-04) con datos construidos a mano: prueban el método, no el caso real."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from src.calibration import event_losses, fit_line, fit_parameters, load_inputs, predict_normal
from src.data import portable_sha256
from src.domain import Constraints, Strategy, TyreStint, parameters_from_dict
from src.simulation import simulate

TRUE = {'SOFT': (96.0, 0.08), 'HARD': (95.5, 0.05)}
TREND = -0.044


def lap_time(compound, age, lap):
    base, wear = TRUE[compound]
    return base + wear * age + TREND * (lap - 1)


def training_rows():
    rows = [{'lap_number': n, 'compound': 'SOFT', 'tyre_life_laps': n + 3} for n in range(2, 11)]
    rows += [{'lap_number': n, 'compound': 'HARD', 'tyre_life_laps': n - 11} for n in range(13, 21)]
    for r in rows:
        r['lap_time_s'] = lap_time(r['compound'], r['tyre_life_laps'], r['lap_number'])
    return rows


class CalibrationTests(unittest.TestCase):
    def test_fit_line_recovers_exact_line(self):
        fit = fit_line([1, 2, 3, 4], [10.5, 11.0, 11.5, 12.0])
        self.assertAlmostEqual(fit['intercept'], 10.0)
        self.assertAlmostEqual(fit['slope'], 0.5)
        self.assertAlmostEqual(fit['ssr'], 0.0)

    def test_correct_fixed_trend_recovers_true_parameters(self):
        fit = fit_parameters(training_rows(), TREND)
        for compound, (base, wear) in TRUE.items():
            self.assertAlmostEqual(fit['compounds'][compound]['base_lap_s'], base, places=6)
            self.assertAlmostEqual(fit['compounds'][compound]['degradation_s_per_lap'], wear, places=6)

    def test_trend_choice_does_not_change_training_predictions(self):
        # Falta de identificabilidad: dentro de los stints de entrenamiento todas las tendencias
        # predicen igual; solo cambian base y desgaste (y las predicciones fuera de esos stints).
        rows = training_rows()
        fits = [fit_parameters(rows, trend) for trend in (0.0, TREND, 2 * TREND)]
        for r in rows:
            values = [predict_normal(f, r['compound'], r['tyre_life_laps'], r['lap_number']) for f in fits]
            self.assertAlmostEqual(max(values) - min(values), 0.0, places=9)
        self.assertNotAlmostEqual(fits[0]['compounds']['SOFT']['degradation_s_per_lap'],
                                  fits[2]['compounds']['SOFT']['degradation_s_per_lap'])

    def test_losses_follow_simulator_convention_without_double_counting(self):
        fit = fit_parameters(training_rows(), TREND)
        start, pit = 0.6, 22.0
        laps = {1: {'compound': 'SOFT', 'tyre_life_laps': 4, 'lap_time_s': lap_time('SOFT', 4, 1) + start},
                11: {'compound': 'SOFT', 'tyre_life_laps': 14, 'lap_time_s': lap_time('SOFT', 14, 11) + pit - 1.0},
                12: {'compound': 'HARD', 'tyre_life_laps': 1, 'lap_time_s': lap_time('HARD', 1, 12) + 1.0}}
        losses = event_losses(fit, laps, laps[1]['lap_time_s'], pit_in_lap=11)
        self.assertAlmostEqual(losses['start_penalty_s'], start, places=6)
        self.assertAlmostEqual(losses['additional_pit_loss_s'], pit, places=6)
        # El simulador con esos parámetros reproduce la suma observada de las vueltas 1-12.
        params = parameters_from_dict({
            'compounds': {c: {'base_lap_s': fit['compounds'][c]['base_lap_s'],
                              'degradation_s_per_lap': fit['compounds'][c]['degradation_s_per_lap']} for c in TRUE},
            'race_trend_s_per_lap': TREND, 'additional_pit_loss_s': losses['additional_pit_loss_s'],
            'start_penalty_s': losses['start_penalty_s'], 'residual_sd_s': 0.0, 'provenance': 'TEST'})
        strategy = Strategy((11,), (TyreStint('SOFT', 3), TyreStint('HARD', 0)))
        result = simulate(strategy, params, Constraints(race_laps=12, allowed_compounds=('SOFT', 'HARD')))
        observed = sum(lap_time('SOFT', n + 3, n) for n in range(2, 11)) + sum(l['lap_time_s'] for l in laps.values())
        self.assertAlmostEqual(result['total_time_s'], observed, places=6)


class CalibrationInputGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        processed = self.root/'data/processed'
        processed.mkdir(parents=True)
        roles = {1: 'excluded_from_fit', 2: 'training', 3: 'training', 4: 'training', 5: 'validation'}
        self.write(processed/'partition_split.csv', [{'lap_number': k, 'split': v} for k, v in roles.items()])
        self.write(processed/'openf1_target_laps_annotated.csv',
                   [{'lap_number': n, 'compound': 'SOFT', 'tyre_life_laps': n + 3, 'lap_time_s': 90 + n} for n in roles])
        self.write(processed/'lap_time_reconciliation.csv', [{'lap_number': 1, 'reference_s': 91.0}])
        self.manifest = {'sha256_portable_split': portable_sha256(processed/'partition_split.csv'),
                         'frozen_at_utc': 'x', 'code_state': {'commit': 'x'}}
        (self.root/'manifest.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def write(path, rows):
        with path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def settings(self, event_laps):
        return {'partition_manifest': 'manifest.json', 'event_laps_read': event_laps}

    def test_reads_only_training_and_event_laps(self):
        training, rows, first, audit = load_inputs(self.root, self.settings([1]))
        self.assertEqual([r['lap_number'] for r in training], [2, 3, 4])
        self.assertNotIn(5, rows)
        self.assertEqual(audit['validation_laps_read'], [])
        self.assertEqual(first, 91.0)

    def test_refuses_validation_laps_as_events(self):
        with self.assertRaises(RuntimeError):
            load_inputs(self.root, self.settings([1, 5]))

    def test_refuses_partition_that_differs_from_frozen_one(self):
        self.write(self.root/'data/processed/partition_split.csv',
                   [{'lap_number': 5, 'split': 'training'}])
        with self.assertRaisesRegex(RuntimeError, 'congelada'):
            load_inputs(self.root, self.settings([]))


if __name__ == '__main__':
    unittest.main()
