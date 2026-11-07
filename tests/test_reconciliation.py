import unittest
from src.reconciliation import compare_lap_times, parse_race_time


class ReconciliationTests(unittest.TestCase):
    def test_parse_lap_and_race_times(self):
        self.assertAlmostEqual(parse_race_time('1:37.284'), 97.284)
        self.assertAlmostEqual(parse_race_time('1:31:44.742'), 5504.742)
        self.assertAlmostEqual(parse_race_time('59.001'), 59.001)

    def test_difference_is_localized_to_the_lap_where_it_occurs(self):
        observed = {1: 97.759, 2: 96.296, 3: 96.753}
        reference = {1: 97.284, 2: 96.296, 3: 96.753}
        rows, summary = compare_lap_times(observed, reference)
        self.assertEqual(summary['differing_laps'], {1: 0.475})
        self.assertEqual(summary['laps_matching'], 2)
        self.assertAlmostEqual(summary['sum_of_differences_s'],
                               summary['sum_openf1_s'] - summary['sum_reference_s'], places=6)

    def test_missing_laps_are_reported_not_imputed(self):
        rows, summary = compare_lap_times({1: 90.0, 2: 91.0}, {1: 90.0, 3: 92.0})
        self.assertEqual(summary['laps_only_in_openf1'], [2])
        self.assertEqual(summary['laps_only_in_reference'], [3])
        self.assertEqual(summary['laps_compared'], 1)
        self.assertIsNone(next(r for r in rows if r['lap_number'] == 2)['difference_s'])


if __name__ == '__main__':
    unittest.main()
