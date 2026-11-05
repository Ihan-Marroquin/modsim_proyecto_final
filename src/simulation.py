"""Primer motor de eventos, solo validado con casos sintéticos de consistencia.

La penalización de pits es ADICIONAL al tiempo normal de vuelta. Se carga al
terminar la vuelta en que se para; el nuevo juego se usa en la siguiente.
La ubicación temporal exacta de los eventos debe refinarse para contrastar pits
reales. Este motor todavía NO representa una carrera calibrada de Bahréin.
"""
import math
import random
from .constraints import validate_strategy
from .domain import Constraints, ModelParameters, Strategy


def simulate(strategy: Strategy, params: ModelParameters, limits: Constraints,
             *, seed: int = 0, stochastic: bool = False,
             degradation_multiplier: float = 1.0) -> dict:
    violations = validate_strategy(strategy, limits)
    if violations:
        raise ValueError('; '.join(violations))
    scalar_values = [params.race_trend_s_per_lap, params.additional_pit_loss_s,
                     params.start_penalty_s, params.residual_sd_s, degradation_multiplier]
    for p in params.compounds.values():
        scalar_values.extend([p.base_lap_s, p.degradation_s_per_lap])
    if not all(math.isfinite(v) for v in scalar_values):
        raise ValueError('Todos los parámetros numéricos deben ser finitos')
    if min(params.additional_pit_loss_s, params.start_penalty_s,
           params.residual_sd_s, degradation_multiplier) < 0:
        raise ValueError('Pérdidas, dispersión y multiplicador no pueden ser negativos')
    if any(p.base_lap_s <= 0 for p in params.compounds.values()):
        raise ValueError('Los tiempos base deben ser positivos')
    if any(s.compound not in params.compounds for s in strategy.stints):
        raise ValueError('Faltan parámetros de un compuesto usado')
    rng = random.Random(seed)
    clock = 0.0
    stint_index = 0
    age = strategy.stints[0].initial_age
    stops = set(strategy.stops_after_lap)
    laps, events = [], []
    for lap in range(1, limits.race_laps + 1):
        compound = strategy.stints[stint_index].compound
        p = params.compounds[compound]
        age += 1  # Edad al terminar la vuelta, coherente con TyreLife.
        normal_s = (p.base_lap_s + p.degradation_s_per_lap * age * degradation_multiplier
                    + params.race_trend_s_per_lap * (lap - 1))
        noise_s = rng.gauss(0.0, params.residual_sd_s) if stochastic else 0.0
        start_s = params.start_penalty_s if lap == 1 else 0.0
        lap_s = normal_s + noise_s + start_s
        if lap_s <= 0:
            raise ValueError('El modelo produjo un tiempo de vuelta no positivo')
        clock += lap_s
        events.append({'event': 'lap_completed', 'lap': lap, 'clock_s': clock})
        pit_s = params.additional_pit_loss_s if lap in stops else 0.0
        clock += pit_s
        laps.append({'lap': lap, 'stint': stint_index + 1, 'compound': compound,
                     'tyre_age_end_laps': age, 'normal_lap_s': normal_s,
                     'noise_s': noise_s, 'start_penalty_s': start_s,
                     'additional_pit_loss_s': pit_s, 'elapsed_s': lap_s + pit_s,
                     'cumulative_s': clock})
        if lap in stops:
            stint_index += 1
            age = strategy.stints[stint_index].initial_age
            events.append({'event': 'tyres_changed', 'lap': lap, 'clock_s': clock,
                           'next_compound': strategy.stints[stint_index].compound})
    return {'strategy': strategy.name, 'seed': seed, 'stochastic': stochastic,
            'parameter_provenance': params.provenance, 'total_time_s': clock,
            'stop_count': len(stops), 'feasible': True, 'laps': laps, 'events': events}
