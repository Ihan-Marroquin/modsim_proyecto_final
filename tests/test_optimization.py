import math
import unittest
from dataclasses import replace
from src.domain import CompoundParameters, Constraints, ModelParameters, Strategy, TyreStint
from src.constraints import validate_strategy
from src.optimization import SearchSettings, acceptance_probability, enumerate_reference, optimize


class OptimizationTests(unittest.TestCase):
    def setUp(self):
        self.limits = Constraints(12, ('SOFT', 'HARD'))
        self.strategy = Strategy((6,), (TyreStint('SOFT'), TyreStint('HARD')))
        self.params = ModelParameters({'SOFT': CompoundParameters(90, .3),
                                       'HARD': CompoundParameters(91, .1)}, additional_pit_loss_s=20)

    def test_acceptance_matches_metropolis_rule(self):
        self.assertEqual(acceptance_probability(-1, 5), 1)
        self.assertAlmostEqual(acceptance_probability(5, 5), math.exp(-1))
        with self.assertRaises(ValueError):
            acceptance_probability(1, 0)

    def test_small_case_matches_exhaustive_reference(self):
        reference = enumerate_reference(self.strategy, self.params, self.limits)
        result = optimize(self.strategy, self.params, self.limits, seed=42)
        self.assertAlmostEqual(result['best_time_s'], reference['best_time_s'])
        self.assertFalse(validate_strategy(result['strategy'], self.limits))
        scores = [r['best_s'] for r in result['history']]
        self.assertEqual(sorted(scores, reverse=True), scores)

    def test_reproducibility(self):
        settings = SearchSettings(iterations=30)
        a = optimize(self.strategy, self.params, self.limits, settings, seed=4)
        b = optimize(self.strategy, self.params, self.limits, settings, seed=4)
        self.assertEqual(a, b)

    def test_two_stops_and_compounds_never_return_invalid_candidate(self):
        initial = Strategy((3, 8), (TyreStint('SOFT'), TyreStint('HARD'), TyreStint('SOFT')))
        settings = SearchSettings(iterations=400, allow_compound_changes=True)
        result = optimize(initial, self.params, self.limits, settings, seed=5)
        self.assertFalse(validate_strategy(result['strategy'], self.limits))
        self.assertLessEqual(result['best_time_s'], result['initial_time_s'])

    def test_invalid_initial_and_unimplemented_used_set_mutations_raise(self):
        with self.assertRaises(ValueError):
            optimize(replace(self.strategy, stops_after_lap=(0,)), self.params, self.limits)
        initial = replace(self.strategy, stints=(TyreStint('SOFT', 2), TyreStint('HARD')))
        with self.assertRaises(ValueError):
            optimize(initial, self.params, self.limits, SearchSettings(allow_compound_changes=True))

    def test_reference_has_size_guard(self):
        with self.assertRaises(ValueError):
            enumerate_reference(self.strategy, self.params, replace(self.limits, race_laps=200001))
