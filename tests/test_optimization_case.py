import json
import random
import unittest
from collections import Counter
from pathlib import Path

from src.domain import Strategy, TyreStint, strategy_from_dict
from src.model import get_historical_strategy, load_calibrated_parameters
from src.optimization import SearchSettings, anneal
from src.optimization_case import build_catalog, make_proposal, strategy_key

ROOT = Path(__file__).resolve().parents[1]


class CalibratedOptimizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tyres = json.loads(
            (ROOT / 'configs/tyre_inventory_bahrain_2024.json').read_text(encoding='utf-8'))
        cls.limits, cls.groups = build_catalog(cls.tyres, 57, 'inventory_main',
                                               cls.tyres['main_search_scenario'])

    def test_search_space_preserves_used_sets_and_no_one_stop(self):
        self.assertEqual({n: len(c) for n, c in self.groups.items()}, {1: 0, 2: 1323})
        catalog = self.groups[2]
        self.assertIn(strategy_key(get_historical_strategy()), catalog)
        # Dos SOFT nuevos pasarían el conteo por compuesto, pero solo hay uno en el inventario.
        impossible = Strategy((17, 37), (TyreStint('SOFT'), TyreStint('HARD'), TyreStint('SOFT')))
        self.assertNotIn(strategy_key(impossible), catalog)
        stock = Counter((t['compound'], t['initial_age']) for t in self.tyres['inventory_main']['sets'])
        for strategy in catalog.values():
            self.assertFalse(Counter((t.compound, t.initial_age) for t in strategy.stints) - stock)

    def test_annealing_reproducible_and_uses_real_catalog(self):
        catalog = self.groups[2]
        propose = make_proposal(catalog, 0.05)
        historical = get_historical_strategy()
        params = load_calibrated_parameters(ROOT / 'configs/params_bahrain_2024.json')
        settings = SearchSettings(iterations=120, initial_temperature_s=1, cooling_factor=.97)
        result = anneal(historical, params, self.limits, settings, random.Random(2100), propose)
        again = anneal(historical, params, self.limits, settings, random.Random(2100), propose)
        self.assertEqual(result, again)
        self.assertIn(strategy_key(result['strategy']), catalog)
        self.assertLessEqual(result['best_time_s'], result['initial_time_s'])
        self.assertEqual(result['objective_evaluations'],
                         1 + sum(row['candidate_feasible'] for row in result['history']))

    def test_frozen_candidate_is_usable_with_the_same_inventory(self):
        candidate = strategy_from_dict(json.loads(
            (ROOT / 'docs/evidence/optimization/candidate.json').read_text(encoding='utf-8')))
        self.assertIn(strategy_key(candidate), self.groups[2])
