"""Pruebas de la partición (MA-03) con filas construidas a mano: prueban reglas, no el caso real."""
import unittest
from src.partition import build_partition, identifiability, matrix_rank


def row(lap, stint, compound, age, eligible=True, reasons=''):
    return {'lap_number': str(lap), 'stint': str(stint), 'compound': compound, 'tyre_life_laps': str(age),
            'calibration_eligible': str(eligible), 'exclusion_reasons': reasons}


def stint_rows(stint, compound, first_lap, last_lap, age_at_start):
    return [row(n, stint, compound, age_at_start + n - first_lap + 1) for n in range(first_lap, last_lap + 1)]


class PartitionTests(unittest.TestCase):
    def setUp(self):
        self.rows = (stint_rows(1, 'SOFT', 2, 6, 4) + stint_rows(2, 'HARD', 8, 12, 0)
                     + stint_rows(3, 'SOFT', 14, 20, 0) + [row(7, 1, 'SOFT', 9, False, 'pit_in_lap')])

    def test_every_lap_has_exactly_one_role_and_excluded_laps_stay_out_of_both_sets(self):
        split, summary = build_partition(self.rows, validation_stint=3)
        self.assertEqual(len(split), len(self.rows))
        training, validation = set(summary['training_laps']), set(summary['validation_laps'])
        self.assertFalse(training & validation)
        self.assertIn(7, summary['excluded_from_fit_laps'])
        self.assertNotIn(7, training | validation)
        self.assertEqual(validation, set(range(14, 21)))

    def test_validation_ages_outside_training_range_are_marked_as_extrapolated(self):
        # SOFT en entrenamiento: edades 5-9. Validación SOFT: edades 1-7.
        split, summary = build_partition(self.rows, validation_stint=3)
        coverage = {s['lap_number']: s['age_coverage'] for s in split if s['split'] == 'validation'}
        self.assertEqual(coverage[14], 'extrapolated_below')  # edad 1
        self.assertEqual(coverage[18], 'covered')             # edad 5
        self.assertEqual(summary['training_age_range_by_compound']['SOFT'], [5, 9])
        self.assertEqual(sorted(summary['validation_covered_laps'] + summary['validation_extrapolated_laps']),
                         summary['validation_laps'])

    def test_compound_missing_from_training_is_flagged(self):
        rows = stint_rows(1, 'SOFT', 2, 6, 4) + stint_rows(2, 'MEDIUM', 8, 12, 0)
        split, _ = build_partition(rows, validation_stint=2)
        self.assertTrue(all(s['age_coverage'] == 'compound_not_in_training' for s in split if s['split'] == 'validation'))

    def test_one_stint_per_compound_cannot_separate_wear_from_trend(self):
        # Hallazgo 7 del plan: edad - vuelta es constante dentro de cada stint.
        training = stint_rows(1, 'SOFT', 2, 6, 4) + stint_rows(2, 'HARD', 8, 12, 0)
        result = identifiability(training)
        self.assertFalse(result['plan_model']['identifiable'])
        self.assertFalse(result['common_wear_plus_trend']['identifiable'])
        self.assertTrue(result['trend_fixed_externally']['identifiable'])

    def test_two_stints_of_one_compound_make_the_plan_model_identifiable(self):
        rows = stint_rows(1, 'SOFT', 2, 6, 4) + stint_rows(2, 'HARD', 8, 12, 0) + stint_rows(3, 'SOFT', 14, 20, 0)
        self.assertTrue(identifiability(rows)['plan_model']['identifiable'])

    def test_exact_rank(self):
        self.assertEqual(matrix_rank([[1, 2], [2, 4]]), 1)
        self.assertEqual(matrix_rank([[1, 0], [0, 1], [1, 1]]), 2)


if __name__ == '__main__':
    unittest.main()
