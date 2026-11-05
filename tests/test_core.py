import math
import unittest
from dataclasses import replace
from src.constraints import validate_strategy
from src.domain import CompoundParameters, Constraints, ModelParameters, Strategy, TyreStint
from src.simulation import simulate


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.limits = Constraints(10, ('SOFT', 'HARD'))
        self.strategy = Strategy((5,), (TyreStint('SOFT'), TyreStint('HARD')))
        self.params = ModelParameters({'SOFT': CompoundParameters(90, 0),
                                       'HARD': CompoundParameters(90, 0)},
                                      additional_pit_loss_s=20, residual_sd_s=1)

    def test_known_total_and_event_clock(self):
        r = simulate(self.strategy, self.params, self.limits)
        self.assertEqual(r['total_time_s'], 920)
        self.assertEqual(sum(l['elapsed_s'] for l in r['laps']), r['total_time_s'])
        self.assertEqual(r['laps'][5]['tyre_age_end_laps'], 1)
        self.assertEqual(sum(e['event'] == 'tyres_changed' for e in r['events']), 1)
        clocks = [e['clock_s'] for e in r['events']]
        self.assertEqual(sorted(clocks), clocks)

    def test_extra_stop_costs_exactly_one_pit_penalty_without_wear(self):
        extra = Strategy((3, 7), (TyreStint('SOFT'), TyreStint('HARD'), TyreStint('SOFT')))
        a = simulate(self.strategy, self.params, self.limits)['total_time_s']
        b = simulate(extra, self.params, self.limits)['total_time_s']
        self.assertEqual(b-a, 20)

    def test_seed_reproducibility_without_mutating_inputs(self):
        a = simulate(self.strategy, self.params, self.limits, stochastic=True, seed=2)
        b = simulate(self.strategy, self.params, self.limits, stochastic=True, seed=2)
        c = simulate(self.strategy, self.params, self.limits, stochastic=True, seed=3)
        self.assertEqual(a, b)
        self.assertNotEqual(a['total_time_s'], c['total_time_s'])
        self.assertEqual(self.strategy.stints[0].initial_age, 0)

    def test_used_tyres_keep_initial_age(self):
        s = replace(self.strategy, stints=(TyreStint('SOFT', 4), TyreStint('HARD', 2)))
        r = simulate(s, self.params, self.limits)
        self.assertEqual(r['laps'][0]['tyre_age_end_laps'], 5)
        self.assertEqual(r['laps'][5]['tyre_age_end_laps'], 3)

    def test_invalid_stops_and_noninteger_stops(self):
        for stops in [(0,), (10,), (4, 4), (7, 3), (4.5,), (True,)]:
            with self.subTest(stops=stops):
                bad = Strategy(stops, tuple(TyreStint('SOFT') for _ in range(len(stops)+1)))
                self.assertTrue(validate_strategy(bad, self.limits))

    def test_inventory_and_age_coverage(self):
        limits = replace(self.limits, max_age_by_compound={'SOFT': 3})
        self.assertTrue(validate_strategy(self.strategy, limits))
        limits = replace(self.limits, max_sets_by_compound={'HARD': 0})
        self.assertTrue(validate_strategy(self.strategy, limits))

    def test_bad_parameters_are_rejected(self):
        for kwargs in [{'additional_pit_loss_s': -1}, {'residual_sd_s': -1},
                       {'race_trend_s_per_lap': math.nan}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                simulate(self.strategy, replace(self.params, **kwargs), self.limits)


if __name__ == '__main__':
    unittest.main()
