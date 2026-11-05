"""Contratos iniciales compartidos; todas las duraciones se expresan en segundos."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TyreStint:
    compound: str
    initial_age: int = 0  # Vueltas completadas ANTES del inicio del stint.


@dataclass(frozen=True)
class Strategy:
    stops_after_lap: tuple[int, ...]
    stints: tuple[TyreStint, ...]
    name: str = 'unnamed'


@dataclass(frozen=True)
class Constraints:
    race_laps: int
    allowed_compounds: tuple[str, ...]
    min_stops: int = 1
    max_stops: int = 2
    min_distinct_compounds: int = 2
    max_age_by_compound: dict[str, int] = field(default_factory=dict)
    max_sets_by_compound: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class CompoundParameters:
    base_lap_s: float
    degradation_s_per_lap: float


@dataclass(frozen=True)
class ModelParameters:
    compounds: dict[str, CompoundParameters]
    race_trend_s_per_lap: float = 0.0
    additional_pit_loss_s: float = 0.0
    start_penalty_s: float = 0.0
    residual_sd_s: float = 0.0
    provenance: str = 'SYNTHETIC_DEMO_NOT_CALIBRATED'


def strategy_from_dict(value: dict) -> Strategy:
    # No convertir float a int silenciosamente: la validación debe detectar errores.
    return Strategy(
        stops_after_lap=tuple(value['stops_after_lap']),
        stints=tuple(TyreStint(**stint) for stint in value['stints']),
        name=value.get('name', 'unnamed'),
    )


def parameters_from_dict(value: dict) -> ModelParameters:
    settings = dict(value)
    settings['compounds'] = {
        name: CompoundParameters(**data) for name, data in value['compounds'].items()
    }
    return ModelParameters(**settings)
