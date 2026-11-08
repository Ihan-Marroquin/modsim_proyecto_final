"""LP-02: casos conocidos del modelo calibrado y de estrategias (convenciones, límites, pits y desgaste).

Solo usan configuraciones versionadas; no necesitan descargar datos.
"""
import json
import math
import unittest
from dataclasses import replace
from pathlib import Path

from src.constraints import validate_strategy
from src.domain import CompoundParameters, Constraints, ModelParameters, Strategy, TyreStint, strategy_from_dict
from src.experiments import difference_decomposition, lap_profile
from src.model import get_bahrain_constraints, get_historical_strategy, load_calibrated_parameters
from src.simulation import simulate

ROOT = Path(__file__).resolve().parents[1]
PARAMS = ROOT / 'configs/params_bahrain_2024.json'


def candidate() -> Strategy:
    return strategy_from_dict(json.loads((ROOT / 'docs/evidence/optimization/candidate.json').read_text(encoding='utf-8')))


class RealCaseConventionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.params = load_calibrated_parameters(PARAMS)
        cls.limits = get_bahrain_constraints('observed_race_feasibility')
        cls.historical = get_historical_strategy()
        cls.candidate = candidate()

    def test_total_equals_lap_breakdown_with_and_without_noise(self):
        for strategy in (self.historical, self.candidate):
            for stochastic in (False, True):
                with self.subTest(strategy=strategy.name, stochastic=stochastic):
                    run = simulate(strategy, self.params, self.limits, seed=3300, stochastic=stochastic)
                    parts = math.fsum(l['normal_lap_s'] + l['noise_s'] + l['start_penalty_s']
                                      + l['additional_pit_loss_s'] for l in run['laps'])
                    self.assertAlmostEqual(parts, run['total_time_s'], places=8)
                    self.assertEqual(len(run['laps']), 57)
                    self.assertEqual(sum(l['start_penalty_s'] > 0 for l in run['laps']), 1)
                    self.assertEqual(sum(l['additional_pit_loss_s'] > 0 for l in run['laps']), 2)

    def test_age_convention_of_observed_and_candidate_strategies(self):
        hist = {l['lap']: l for l in simulate(self.historical, self.params, self.limits)['laps']}
        self.assertEqual((hist[1]['compound'], hist[1]['tyre_age_end_laps']), ('SOFT', 4))
        self.assertEqual(hist[17]['tyre_age_end_laps'], 20)
        self.assertEqual((hist[18]['compound'], hist[18]['tyre_age_end_laps']), ('HARD', 1))
        self.assertEqual((hist[57]['compound'], hist[57]['tyre_age_end_laps']), ('SOFT', 20))
        cand = {l['lap']: l for l in simulate(self.candidate, self.params, self.limits)['laps']}
        self.assertEqual((cand[37]['compound'], cand[37]['tyre_age_end_laps']), ('HARD', 1))
        # La candidata extrapola: HARD edad 21 > 19 de entrenamiento y > 20 observado.
        self.assertEqual((cand[57]['compound'], cand[57]['tyre_age_end_laps']), ('HARD', 21))

    def test_shared_seed_gives_identical_noise_for_different_strategies(self):
        a = simulate(self.historical, self.params, self.limits, seed=3301, stochastic=True)
        b = simulate(self.candidate, self.params, self.limits, seed=3301, stochastic=True)
        self.assertEqual([l['noise_s'] for l in a['laps']], [l['noise_s'] for l in b['laps']])
        det = (simulate(self.historical, self.params, self.limits)['total_time_s']
               - simulate(self.candidate, self.params, self.limits)['total_time_s'])
        self.assertAlmostEqual(a['total_time_s'] - b['total_time_s'], det, places=8)

    def test_pit_loss_and_start_penalty_cancel_between_two_stop_strategies(self):
        def diff(p):
            return (simulate(self.historical, p, self.limits)['total_time_s']
                    - simulate(self.candidate, p, self.limits)['total_time_s'])
        reference = diff(self.params)
        for change in ({'additional_pit_loss_s': 0.0}, {'additional_pit_loss_s': 40.0}, {'start_penalty_s': 3.0}):
            with self.subTest(change=change):
                self.assertAlmostEqual(diff(replace(self.params, **change)), reference, places=8)

    def test_trend_cancels_when_compound_parameters_are_fixed(self):
        # Con base y desgaste fijos, la tendencia suma lo mismo a ambas estrategias de 57 vueltas.
        def diff(trend):
            p = replace(self.params, race_trend_s_per_lap=trend)
            return (simulate(self.historical, p, self.limits)['total_time_s']
                    - simulate(self.candidate, p, self.limits)['total_time_s'])
        self.assertAlmostEqual(diff(0.0), diff(-0.0888), places=8)

    def test_difference_matches_linear_decomposition_in_every_scenario(self):
        for scenario in ('trend_fuel_reference', 'trend_zero', 'trend_double'):
            params = load_calibrated_parameters(PARAMS, scenario)
            for m in (0.8, 1.0, 1.2):
                with self.subTest(scenario=scenario, multiplier=m):
                    sim = (simulate(self.historical, params, self.limits, degradation_multiplier=m)['total_time_s']
                           - simulate(self.candidate, params, self.limits, degradation_multiplier=m)['total_time_s'])
                    self.assertAlmostEqual(difference_decomposition(self.historical, self.candidate, params, m, 57)['mejora_s'],
                                           sim, places=8)

    def test_frozen_advantage_and_its_reversal_with_more_degradation(self):
        # Δ = (b_S − b_H) + μ(20 d_S − 21 d_H): 0.075 s con μ = 1 y −0.0624 s con μ = 1.2.
        profile_h, profile_c = lap_profile(self.historical, 57), lap_profile(self.candidate, 57)
        self.assertEqual(profile_h['laps'], {'SOFT': 37, 'HARD': 20})
        self.assertEqual(profile_c['laps'], {'SOFT': 36, 'HARD': 21})
        base = difference_decomposition(self.historical, self.candidate, self.params, 1.0, 57)
        stressed = difference_decomposition(self.historical, self.candidate, self.params, 1.2, 57)
        self.assertAlmostEqual(base['mejora_s'], 0.075, places=6)
        self.assertAlmostEqual(stressed['mejora_s'], -0.06244, places=6)
        self.assertAlmostEqual(base['break_even_degradation_multiplier'], 0.7622 / 0.6872, places=6)

    def test_strict_coverage_rejects_candidate_but_keeps_historical(self):
        strict = get_bahrain_constraints('strict_model_coverage')
        self.assertEqual(validate_strategy(self.historical, strict), [])
        self.assertEqual(validate_strategy(self.candidate, strict), ['Edad fuera de la cobertura configurada: HARD'])


class KnownCaseTests(unittest.TestCase):
    """Casos artificiales con respuesta conocida a mano."""

    def setUp(self):
        self.limits = Constraints(10, ('SOFT', 'HARD'), min_stops=1, max_stops=2)

    def params(self, wear, pit):
        return ModelParameters({'SOFT': CompoundParameters(90.0, wear), 'HARD': CompoundParameters(90.0, wear)},
                               additional_pit_loss_s=pit)

    def test_extra_stop_gains_only_when_wear_saving_exceeds_pit_loss(self):
        one = Strategy((5,), (TyreStint('SOFT'), TyreStint('HARD')))
        two = Strategy((3, 6), (TyreStint('SOFT'), TyreStint('HARD'), TyreStint('SOFT')))
        # Suma de edades: una parada 15 + 15 = 30; dos paradas 6 + 6 + 10 = 22. Ahorro = 8·d.
        for wear, pit in ((1.0, 5.0), (1.0, 10.0), (0.0, 5.0)):
            with self.subTest(wear=wear, pit=pit):
                p = self.params(wear, pit)
                gain = simulate(one, p, self.limits)['total_time_s'] - simulate(two, p, self.limits)['total_time_s']
                self.assertAlmostEqual(gain, 8 * wear - pit, places=9)

    def test_zero_degradation_multiplier_removes_age_effect(self):
        p = self.params(0.5, 20.0)
        fresh = Strategy((5,), (TyreStint('SOFT'), TyreStint('HARD')))
        used = Strategy((5,), (TyreStint('SOFT', 6), TyreStint('HARD', 3)))
        a = simulate(fresh, p, self.limits, degradation_multiplier=0.0)['total_time_s']
        b = simulate(used, p, self.limits, degradation_multiplier=0.0)['total_time_s']
        self.assertEqual(a, b)
        self.assertGreater(simulate(used, p, self.limits)['total_time_s'], simulate(fresh, p, self.limits)['total_time_s'])

    def test_used_set_costs_its_extra_age_times_wear(self):
        p = self.params(0.3, 20.0)
        fresh = Strategy((5,), (TyreStint('SOFT'), TyreStint('HARD')))
        used = Strategy((5,), (TyreStint('SOFT', 3), TyreStint('HARD')))
        extra = simulate(used, p, self.limits)['total_time_s'] - simulate(fresh, p, self.limits)['total_time_s']
        self.assertAlmostEqual(extra, 5 * 3 * 0.3, places=9)  # 5 vueltas con 3 vueltas más de edad


if __name__ == '__main__':
    unittest.main()
