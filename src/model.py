"""Modelo matemático y formulación del simulador de carrera (JO-01, JO-02, JO-03).

Define la formulación matemática de los tiempos de vuelta, la máquina de estados del
simulador de eventos discretos, la descomposición de pérdidas de arranque y paradas en pits,
y la conexión con los parámetros reales calibrados en MA-04.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .domain import CompoundParameters, Constraints, ModelParameters, Strategy, TyreStint, parameters_from_dict


class SimulationState(str, Enum):
    """Estados del simulador de eventos discretos."""
    BEFORE_START = "BEFORE_START"
    ON_TRACK = "ON_TRACK"
    IN_PIT_LANE = "IN_PIT_LANE"
    FINISHED = "FINISHED"


def compute_normal_lap_s(
    compound_param: CompoundParameters,
    tyre_age_end: int,
    race_lap: int,
    race_trend_s_per_lap: float,
    degradation_multiplier: float = 1.0,
) -> float:
    """Calcula el tiempo de una vuelta normal bajo bandera verde sin incidentes.

    Ecuación central del modelo (JO-01):
        t_normal = b_c + d_c * edad * mu_deg + g * (vuelta - 1)

    Donde:
        b_c: tiempo base del compuesto c (s)
        d_c: tasa lineal de degradación del compuesto c (s / vuelta de edad)
        edad: vueltas completadas por el juego al terminar la vuelta (vueltas)
        mu_deg: multiplicador de degradación para análisis de sensibilidad (adimensional, 1.0 por defecto)
        g: tendencia de carrera por consumo de combustible y evolución de pista (s / vuelta)
        (vuelta - 1): índice de avance de carrera en base 0, preservando el intercepto en la vuelta 1
    """
    return (
        compound_param.base_lap_s
        + compound_param.degradation_s_per_lap * tyre_age_end * degradation_multiplier
        + race_trend_s_per_lap * (race_lap - 1)
    )


def compute_lap_time_s(
    compound_param: CompoundParameters,
    tyre_age_end: int,
    race_lap: int,
    race_trend_s_per_lap: float,
    start_penalty_s: float = 0.0,
    noise_s: float = 0.0,
    degradation_multiplier: float = 1.0,
) -> float:
    """Calcula el tiempo de vuelta completo incluyendo arranque y ruido estocástico."""
    normal_s = compute_normal_lap_s(
        compound_param=compound_param,
        tyre_age_end=tyre_age_end,
        race_lap=race_lap,
        race_trend_s_per_lap=race_trend_s_per_lap,
        degradation_multiplier=degradation_multiplier,
    )
    start_s = start_penalty_s if race_lap == 1 else 0.0
    return normal_s + start_s + noise_s


def decompose_start_penalty(lap_1_observed_s: float, lap_1_normal_s: float) -> dict[str, float]:
    """Descompone la penalización de arranque de la vuelta 1 (JO-02).

    La penalización es el exceso de tiempo entre el arranque desde parado (pole position)
    y una vuelta normal lanzada con el mismo compuesto y edad.
    """
    start_penalty_s = lap_1_observed_s - lap_1_normal_s
    return {
        "lap_1_observed_s": lap_1_observed_s,
        "lap_1_normal_s": lap_1_normal_s,
        "start_penalty_s": start_penalty_s,
    }


def decompose_pit_loss(
    in_lap_observed_s: float,
    out_lap_observed_s: float,
    in_lap_normal_s: float,
    out_lap_normal_s: float,
) -> dict[str, float]:
    """Descompone la pérdida adicional de una parada en boxes (JO-02).

    Verifica la convención del simulador sin doble conteo:
        exceso_entrada = in_lap_observed - in_lap_normal
        exceso_salida  = out_lap_observed - out_lap_normal
        perdida_total  = exceso_entrada + exceso_salida

    En el simulador por eventos, la pérdida total se aplica como una penalización agregada
    en la vuelta de entrada (in_lap). La vuelta de salida (out_lap) se modela como vuelta
    normal. De este modo, la suma in_lap + out_lap simulada coincide exactamente con la
    suma observada, sin duplicar tiempos de pit lane ni inventar retardos de calentamiento.
    """
    in_lap_excess_s = in_lap_observed_s - in_lap_normal_s
    out_lap_excess_s = out_lap_observed_s - out_lap_normal_s
    total_pit_loss_s = in_lap_excess_s + out_lap_excess_s
    return {
        "in_lap_observed_s": in_lap_observed_s,
        "in_lap_normal_s": in_lap_normal_s,
        "in_lap_excess_s": in_lap_excess_s,
        "out_lap_observed_s": out_lap_observed_s,
        "out_lap_normal_s": out_lap_normal_s,
        "out_lap_excess_s": out_lap_excess_s,
        "total_pit_loss_s": total_pit_loss_s,
    }


def get_historical_strategy() -> Strategy:
    """Estrategia histórica real ejecutada por Max Verstappen en Bahréin 2024."""
    return Strategy(
        name="historical_ver_bahrain_2024",
        stops_after_lap=(17, 37),
        stints=(
            TyreStint(compound="SOFT", initial_age=3),
            TyreStint(compound="HARD", initial_age=0),
            TyreStint(compound="SOFT", initial_age=0),
        ),
    )


def get_bahrain_constraints(scenario: str = "observed_race_feasibility") -> Constraints:
    """Restricciones reglamentarias y de inventario para Bahréin 2024 (MA-05 / JO-01).

    Args:
        scenario: 'observed_race_feasibility' (principal: SOFT 21, HARD 30) o
                  'strict_model_coverage' (estricto: SOFT 20, HARD 20).
    """
    if scenario == "observed_race_feasibility":
        max_age = {"SOFT": 21, "HARD": 30}
    elif scenario == "strict_model_coverage":
        max_age = {"SOFT": 20, "HARD": 20}
    else:
        raise ValueError(f"Escenario de restricciones desconocido: {scenario}")

    return Constraints(
        race_laps=57,
        allowed_compounds=("HARD", "SOFT"),
        min_stops=1,
        max_stops=2,
        min_distinct_compounds=2,
        max_age_by_compound=max_age,
        max_sets_by_compound={"SOFT": 4, "HARD": 1},
    )


def load_calibrated_parameters(
    params_path: Path | str,
    scenario: str = "trend_fuel_reference",
) -> ModelParameters:
    """Carga los parámetros reales calibrados en MA-04.

    Args:
        params_path: Ruta a configs/params_bahrain_2024.json.
        scenario: 'trend_fuel_reference' (principal, -0.0444 s/vuelta),
                  'trend_zero' (sensibilidad, 0.0 s/vuelta), o
                  'trend_double' (sensibilidad, -0.0888 s/vuelta).
    """
    path = Path(params_path)
    data = json.loads(path.read_text(encoding="utf-8"))

    if scenario == "trend_fuel_reference":
        return parameters_from_dict(data["parameters"])
    elif scenario in data.get("sensitivity_parameters", {}):
        return parameters_from_dict(data["sensitivity_parameters"][scenario])
    else:
        available = ["trend_fuel_reference"] + list(data.get("sensitivity_parameters", {}).keys())
        raise ValueError(f"Escenario '{scenario}' no encontrado. Disponibles: {available}")


def simulate_bahrain_case(
    root_dir: Path | str,
    scenario: str = "trend_fuel_reference",
    stochastic: bool = False,
    seed: int = 42,
    degradation_multiplier: float = 1.0,
    strategy: Strategy | None = None,
) -> dict[str, Any]:
    """Ejecuta la simulación completa de la carrera de Bahréin 2024 con parámetros reales (JO-03).

    Conecta los parámetros reales de MA-04 con el simulador determinista/estocástico,
    calcula diagnósticos por vuelta y genera la comparación con los datos observados.
    """
    from .simulation import simulate

    root = Path(root_dir)
    params_path = root / "configs" / "params_bahrain_2024.json"
    case_path = root / "configs" / "case_bahrain_2024.json"

    case_cfg = json.loads(case_path.read_text(encoding="utf-8"))
    params = load_calibrated_parameters(params_path, scenario=scenario)
    limits = get_bahrain_constraints(scenario="observed_race_feasibility")

    if strategy is None:
        strategy = get_historical_strategy()

    sim_result = simulate(
        strategy=strategy,
        params=params,
        limits=limits,
        seed=seed,
        stochastic=stochastic,
        degradation_multiplier=degradation_multiplier,
    )

    # Diagnósticos y métricas
    official_time_s = case_cfg.get("official_winner_time_s", 5504.742)
    sim_time_s = sim_result["total_time_s"]
    time_diff_s = sim_time_s - official_time_s

    # Resumen por stint
    stints_summary = []
    current_stint = 1
    stint_laps = 0
    stint_time_s = 0.0
    start_lap = 1
    for lap_info in sim_result["laps"]:
        if lap_info["stint"] != current_stint:
            stints_summary.append({
                "stint": current_stint,
                "laps": stint_laps,
                "lap_range": [start_lap, lap_info["lap"] - 1],
                "duration_s": round(stint_time_s, 4),
            })
            current_stint = lap_info["stint"]
            stint_laps = 0
            stint_time_s = 0.0
            start_lap = lap_info["lap"]
        stint_laps += 1
        stint_time_s += lap_info["elapsed_s"]

    stints_summary.append({
        "stint": current_stint,
        "laps": stint_laps,
        "lap_range": [start_lap, len(sim_result["laps"])],
        "duration_s": round(stint_time_s, 4),
    })

    # Verificación de pérdidas aplicadas
    total_start_penalty_s = sum(lap["start_penalty_s"] for lap in sim_result["laps"])
    total_pit_loss_s = sum(lap["additional_pit_loss_s"] for lap in sim_result["laps"])

    report = {
        "case": case_cfg.get("event", "Bahrain"),
        "year": case_cfg.get("year", 2024),
        "driver": case_cfg.get("driver", "VER"),
        "scenario": scenario,
        "stochastic": stochastic,
        "seed": seed,
        "degradation_multiplier": degradation_multiplier,
        "strategy": {
            "name": strategy.name,
            "stops_after_lap": list(strategy.stops_after_lap),
            "stints": [
                {"compound": s.compound, "initial_age": s.initial_age}
                for s in strategy.stints
            ],
        },
        "parameter_provenance": params.provenance,
        "race_trend_s_per_lap": params.race_trend_s_per_lap,
        "residual_sd_s": params.residual_sd_s,
        "summary": {
            "total_laps": len(sim_result["laps"]),
            "total_simulated_time_s": round(sim_time_s, 4),
            "official_reference_time_s": official_time_s,
            "simulated_minus_official_s": round(time_diff_s, 4),
            "total_start_penalty_s": round(total_start_penalty_s, 4),
            "total_pit_loss_s": round(total_pit_loss_s, 4),
            "stints": stints_summary,
        },
        "laps": sim_result["laps"],
        "events": sim_result["events"],
    }
    return report
