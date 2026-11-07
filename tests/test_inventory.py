"""Pruebas del inventario (MA-05) con stints construidos a mano: prueban reglas, no el caso real."""
import unittest
from src.inventory import HISTORICAL, enumerate_feasible, reconstruct_sets, stint_limits_observed


def stint(n, compound, start, end, age):
    return {'stint_number': n, 'compound': compound, 'lap_start': start, 'lap_end': end, 'tyre_age_at_start': age}


class InventoryTests(unittest.TestCase):
    def test_age_continuity_links_stints_to_the_same_set(self):
        stints = {'P1': [stint(1, 'SOFT', 1, 3, 0), stint(2, 'SOFT', 4, 6, 3)],
                  'Q': [stint(1, 'SOFT', 1, 2, 0), stint(2, 'HARD', 3, 4, 7)]}
        sets, notes = reconstruct_sets(stints, ['P1', 'Q'])
        softs = [s for s in sets if s['compound'] == 'SOFT']
        self.assertEqual([s['laps'] for s in softs], [6, 2])
        self.assertEqual(sets[-1]['first_session'], 'previo_desconocido')  # HARD con edad 7 sin origen
        self.assertTrue(notes)

    def test_observed_limits_use_end_of_stint_age(self):
        race = [stint(1, 'SOFT', 1, 17, 3), stint(2, 'HARD', 18, 47, 0), stint(3, 'SOFT', 48, 57, 0)]
        self.assertEqual(stint_limits_observed(race), {'HARD': 30, 'SOFT': 20})

    def test_each_set_used_once_and_limits_respected(self):
        sets = [{'compound': 'SOFT', 'initial_age': 0}, {'compound': 'HARD', 'initial_age': 0}]
        feasible = enumerate_feasible(sets, 10, {'SOFT': 6, 'HARD': 6})
        self.assertTrue(feasible)
        for strategy in feasible:
            self.assertEqual(len(strategy['stints']), 2)  # dos juegos: no puede haber 2 paradas
            bounds = [0] + strategy['stops_after_lap'] + [10]
            for s, a, b in zip(strategy['stints'], bounds, bounds[1:]):
                self.assertLessEqual(s['initial_age'] + b - a, 6)

    def test_identical_sets_are_not_double_counted_and_single_compound_is_rejected(self):
        sets = [{'compound': 'SOFT', 'initial_age': 3}, {'compound': 'SOFT', 'initial_age': 3},
                {'compound': 'HARD', 'initial_age': 0}]
        feasible = enumerate_feasible(sets, 12, {'SOFT': 20, 'HARD': 20}, min_stops=1, max_stops=1)
        keys = [(tuple(s['stops_after_lap']), tuple((t['compound'], t['initial_age']) for t in s['stints']))
                for s in feasible]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(all(len({t['compound'] for t in s['stints']}) == 2 for s in feasible))

    def test_strict_coverage_leaves_only_the_historical_lengths(self):
        sets = [{'compound': 'SOFT', 'initial_age': 0}, {'compound': 'HARD', 'initial_age': 0},
                {'compound': 'SOFT', 'initial_age': 3}]
        feasible = enumerate_feasible(sets, 57, {'SOFT': 20, 'HARD': 20})
        self.assertIn(HISTORICAL, feasible)
        self.assertEqual(len(feasible), 6)  # solo reordenamientos con 17/20/20 vueltas


if __name__ == '__main__':
    unittest.main()
