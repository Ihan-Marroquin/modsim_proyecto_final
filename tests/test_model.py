"""Pruebas unitarias para el modelo matemático y la simulación de Bahréin 2024 (JO-01, JO-02, JO-03)."""
import json
import math
import unittest
from pathlib import Path

from src.domain import CompoundParameters, ModelParameters, Strategy, TyreStint
from src.model import (
    SimulationState,
    compute_lap_time_s,
    compute_normal_lap_s,
    decompose_pit_loss,
    decompose_start_penalty,
    get_bahrain_constraints,
    get_historical_strategy,
    load_calibrated_parameters,
    simulate_bahrain_case,
)
from src.simulation import simulate

ROOT = Path(__file__).resolve().parent.parent


class ModelUnitTests(unittest.TestCase):
    def setUp(self):
        self.hard_param = CompoundParameters(base_lap_s=95.6518, degradation_s_per_lap=0.1052)
        self.soft_param = CompoundParameters(base_lap_s=96.4140, degradation_s_per_lap=0.0761)

    def test_compute_normal_lap_formula(self):
        """Verifica la fórmula exacta: base + deg * age * mult + trend * (lap - 1)."""
        # Vuelta 1, edad 1, sin tendencia
        t = compute_normal_lap_s(self.soft_param, tyre_age_end=1, race_lap=1, race_trend_s_per_lap=0.0)
        self.assertAlmostEqual(t, 96.4140 + 0.0761 * 1, places=4)

        # Vuelta 10, edad 10, con tendencia -0.0444
        t10 = compute_normal_lap_s(self.soft_param, tyre_age_end=10, race_lap=10, race_trend_s_per_lap=-0.0444)
        expected = 96.4140 + 0.0761 * 10 + (-0.0444) * 9
        self.assertAlmostEqual(t10, expected, places=4)

        # Con multiplicador de degradación 1.20 (sensibilidad)
        t_mult = compute_normal_lap_s(
            self.soft_param, tyre_age_end=10, race_lap=10, race_trend_s_per_lap=-0.0444, degradation_multiplier=1.20
        )
        expected_mult = 96.4140 + 0.0761 * 10 * 1.20 + (-0.0444) * 9
        self.assertAlmostEqual(t_mult, expected_mult, places=4)

    def test_compute_lap_time_includes_start_penalty_only_on_lap_1(self):
        """La penalización de arranque solo se suma en la vuelta 1."""
        t1 = compute_lap_time_s(self.soft_param, tyre_age_end=4, race_lap=1, race_trend_s_per_lap=-0.0444,
                                start_penalty_s=0.5656, noise_s=0.0)
        t2 = compute_lap_time_s(self.soft_param, tyre_age_end=5, race_lap=2, race_trend_s_per_lap=-0.0444,
                                start_penalty_s=0.5656, noise_s=0.0)

        normal1 = compute_normal_lap_s(self.soft_param, tyre_age_end=4, race_lap=1, race_trend_s_per_lap=-0.0444)
        normal2 = compute_normal_lap_s(self.soft_param, tyre_age_end=5, race_lap=2, race_trend_s_per_lap=-0.0444)

        self.assertAlmostEqual(t1, normal1 + 0.5656, places=4)
        self.assertAlmostEqual(t2, normal2, places=4)

    def test_start_penalty_decomposition_recovers_calibrated_value(self):
        """JO-02: La descomposición de arranque recupera exactamente 0.5656 s contra la observación oficial."""
        # Vuelta 1 observada = 97.284 s (Jolpica/FIA)
        # Vuelta 1 normal (SOFT edad 4) = 96.4140 + 0.0761 * 4 = 96.7184 s
        dec = decompose_start_penalty(lap_1_observed_s=97.284, lap_1_normal_s=96.7184)
        self.assertAlmostEqual(dec["start_penalty_s"], 0.5656, places=4)

    def test_pit_loss_decomposition_without_double_counting(self):
        """JO-02: La descomposición de parada no cuenta dos veces la pérdida entre entrada y salida."""
        # Parada de la vuelta 17 observada
        # in_lap 17: obs 99.896 s, normal 97.2256 s -> exceso 2.6704 s
        # out_lap 18: obs 117.854 s, normal 95.0024 s -> exceso 22.8516 s
        dec = decompose_pit_loss(
            in_lap_observed_s=99.896,
            out_lap_observed_s=117.854,
            in_lap_normal_s=97.2256,
            out_lap_normal_s=95.0024,
        )
        self.assertAlmostEqual(dec["in_lap_excess_s"], 2.6704, places=4)
        self.assertAlmostEqual(dec["out_lap_excess_s"], 22.8516, places=4)
        self.assertAlmostEqual(dec["total_pit_loss_s"], 25.5220, places=4)

        # En el simulador, in_lap recibe la pérdida total y out_lap es normal:
        sim_in_lap = dec["in_lap_normal_s"] + dec["total_pit_loss_s"]
        sim_out_lap = dec["out_lap_normal_s"]
        sim_sum = sim_in_lap + sim_out_lap
        obs_sum = dec["in_lap_observed_s"] + dec["out_lap_observed_s"]
        self.assertAlmostEqual(sim_sum, obs_sum, places=3)

    def test_load_calibrated_parameters_all_scenarios(self):
        """JO-03: Carga correcta de los 3 escenarios de parámetros calibrados."""
        params_file = ROOT / "configs" / "params_bahrain_2024.json"
        p_main = load_calibrated_parameters(params_file, scenario="trend_fuel_reference")
        self.assertEqual(p_main.race_trend_s_per_lap, -0.0444)
        self.assertAlmostEqual(p_main.compounds["SOFT"].base_lap_s, 96.414, places=3)
        self.assertAlmostEqual(p_main.compounds["HARD"].base_lap_s, 95.652, places=3)

        p_zero = load_calibrated_parameters(params_file, scenario="trend_zero")
        self.assertEqual(p_zero.race_trend_s_per_lap, 0.0)
        self.assertAlmostEqual(p_zero.compounds["SOFT"].base_lap_s, 96.592, places=3)

        p_double = load_calibrated_parameters(params_file, scenario="trend_double")
        self.assertEqual(p_double.race_trend_s_per_lap, -0.0888)
        self.assertAlmostEqual(p_double.compounds["SOFT"].base_lap_s, 96.236, places=3)

        with self.assertRaises(ValueError):
            load_calibrated_parameters(params_file, scenario="non_existent_scenario")

    def test_historical_strategy_and_constraints_compatibility(self):
        """La estrategia histórica es válida bajo las restricciones observadas de Bahréin 2024."""
        strategy = get_historical_strategy()
        limits = get_bahrain_constraints(scenario="observed_race_feasibility")
        self.assertEqual(len(strategy.stops_after_lap), 2)
        self.assertEqual(strategy.stops_after_lap, (17, 37))
        self.assertEqual(strategy.stints[0].initial_age, 3)
        self.assertEqual(strategy.stints[1].initial_age, 0)
        self.assertEqual(strategy.stints[2].initial_age, 0)

        # Debe pasar la validación sin errores
        from src.constraints import validate_strategy
        violations = validate_strategy(strategy, limits)
        self.assertEqual(violations, [])

    def test_simulate_bahrain_case_deterministic(self):
        """JO-03: La simulación determinista de la carrera completa produce 57 vueltas y tiempo esperado."""
        report = simulate_bahrain_case(root_dir=ROOT, scenario="trend_fuel_reference", stochastic=False)
        summary = report["summary"]

        self.assertEqual(summary["total_laps"], 57)
        self.assertAlmostEqual(summary["total_simulated_time_s"], 5514.6992, places=3)
        self.assertAlmostEqual(summary["official_reference_time_s"], 5504.742, places=3)
        # La diferencia es +9.957 s (explicada por validación de stint 3)
        self.assertAlmostEqual(summary["simulated_minus_official_s"], 9.9572, places=3)

        # 3 stints: 17, 20, 20 vueltas
        self.assertEqual(len(summary["stints"]), 3)
        self.assertEqual(summary["stints"][0]["laps"], 17)
        self.assertEqual(summary["stints"][1]["laps"], 20)
        self.assertEqual(summary["stints"][2]["laps"], 20)

        # Penalizaciones aplicadas
        self.assertAlmostEqual(summary["total_start_penalty_s"], 0.5656, places=4)
        self.assertAlmostEqual(summary["total_pit_loss_s"], 25.5223 * 2, places=4)

    def test_stochastic_simulation_reproducibility_and_noise_dispersion(self):
        """JO-03: La simulación estocástica es reproducible con la misma semilla y dispersa según calibración."""
        run1 = simulate_bahrain_case(root_dir=ROOT, scenario="trend_fuel_reference", stochastic=True, seed=12345)
        run2 = simulate_bahrain_case(root_dir=ROOT, scenario="trend_fuel_reference", stochastic=True, seed=12345)
        run_other = simulate_bahrain_case(root_dir=ROOT, scenario="trend_fuel_reference", stochastic=True, seed=99999)

        # Misma semilla = resultado exactamente igual
        self.assertEqual(run1["summary"]["total_simulated_time_s"], run2["summary"]["total_simulated_time_s"])
        # Semilla distinta = resultado distinto
        self.assertNotEqual(run1["summary"]["total_simulated_time_s"], run_other["summary"]["total_simulated_time_s"])

        # Extraer ruidos y verificar dispersión
        noises = [lap["noise_s"] for lap in run1["laps"]]
        mean_noise = sum(noises) / len(noises)
        var_noise = sum((x - mean_noise) ** 2 for x in noises) / (len(noises) - 1)
        sd_noise = math.sqrt(var_noise)

        # Para 57 observaciones de N(0, 0.1631^2), la media muestral debe estar cerca de 0
        self.assertAlmostEqual(mean_noise, 0.0, delta=0.08)
        # y la desviación estándar debe ser del orden de 0.163 s
        self.assertAlmostEqual(sd_noise, 0.1631, delta=0.05)

    def test_degradation_multiplier_increases_race_time(self):
        """JO-03: Multiplicador de degradación +20% aumenta el tiempo total de carrera."""
        base_rep = simulate_bahrain_case(root_dir=ROOT, degradation_multiplier=1.0)
        sens_rep = simulate_bahrain_case(root_dir=ROOT, degradation_multiplier=1.20)

        t_base = base_rep["summary"]["total_simulated_time_s"]
        t_sens = sens_rep["summary"]["total_simulated_time_s"]
        self.assertGreater(t_sens, t_base)


if __name__ == "__main__":
    unittest.main()
