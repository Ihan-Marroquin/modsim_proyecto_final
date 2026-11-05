"""Recocido simulado discreto inicial de Ihan; objetivo determinista.

El número de paradas y las edades iniciales de cada slot son fijos en cada
búsqueda. Para comparar 1/2 paradas se ejecutan búsquedas independientes.
Cambiar compuestos solo está implementado para el supuesto de juegos nuevos.
La integración con el inventario histórico real sigue pendiente.
"""
import itertools
import math
import random
from dataclasses import dataclass, replace
from .constraints import validate_strategy
from .domain import Constraints, ModelParameters, Strategy, TyreStint
from .simulation import simulate


@dataclass(frozen=True)
class SearchSettings:
    iterations: int = 1000
    initial_temperature_s: float = 5.0
    cooling_factor: float = 0.995
    minimum_temperature_s: float = 1e-6
    allow_compound_changes: bool = False


def acceptance_probability(delta_s: float, temperature_s: float) -> float:
    if not math.isfinite(delta_s) or not math.isfinite(temperature_s) or temperature_s <= 0:
        raise ValueError('Delta finito y temperatura finita positiva requeridos')
    return 1.0 if delta_s <= 0 else math.exp(-delta_s / temperature_s)


def propose_neighbor(current: Strategy, limits: Constraints, rng: random.Random,
                     allow_compound_changes: bool = False) -> Strategy:
    slot_count = len(current.stops_after_lap)
    if allow_compound_changes:
        slot_count += len(current.stints)
    if slot_count == 0:
        return current
    slot = rng.randrange(slot_count)
    if slot < len(current.stops_after_lap):
        stops = list(current.stops_after_lap)
        stops[slot] += rng.choice((-3, -2, -1, 1, 2, 3))
        return replace(current, stops_after_lap=tuple(stops))
    if any(stint.initial_age != 0 for stint in current.stints):
        raise ValueError('Cambiar compuestos requiere juegos nuevos en esta versión inicial')
    i = slot - len(current.stops_after_lap)
    alternatives = [c for c in limits.allowed_compounds if c != current.stints[i].compound]
    if not alternatives:
        return current
    stints = list(current.stints)
    stints[i] = TyreStint(rng.choice(alternatives), 0)
    return replace(current, stints=tuple(stints))


def optimize(initial: Strategy, params: ModelParameters, limits: Constraints,
             settings: SearchSettings = SearchSettings(), *, seed: int = 0) -> dict:
    if validate_strategy(initial, limits):
        raise ValueError('La estrategia inicial no es factible')
    if type(settings.iterations) is not int or settings.iterations < 1:
        raise ValueError('iterations debe ser entero positivo')
    if not all(math.isfinite(x) for x in [settings.initial_temperature_s,
                                         settings.minimum_temperature_s, settings.cooling_factor]):
        raise ValueError('Configuración de temperatura debe ser finita')
    if not 0 < settings.cooling_factor < 1 or not 0 < settings.minimum_temperature_s <= settings.initial_temperature_s:
        raise ValueError('Se requiere 0 < cooling < 1 y 0 < Tmin <= T0')
    if settings.allow_compound_changes and any(s.initial_age != 0 for s in initial.stints):
        raise ValueError('Cambios de compuesto con neumáticos usados aún no implementados')
    current, best = initial, initial
    current_score = simulate(current, params, limits)['total_time_s']
    best_score = current_score
    rng = random.Random(seed)
    temperature = settings.initial_temperature_s
    evaluations = 1
    history = []
    for iteration in range(1, settings.iterations + 1):
        candidate = propose_neighbor(current, limits, rng, settings.allow_compound_changes)
        violations = validate_strategy(candidate, limits)
        accepted = False
        candidate_score = None
        if not violations:
            candidate_score = simulate(candidate, params, limits)['total_time_s']
            evaluations += 1
            delta = candidate_score - current_score
            accepted = rng.random() < acceptance_probability(delta, temperature)
            if accepted:
                current, current_score = candidate, candidate_score
                if current_score < best_score:
                    best, best_score = current, current_score
        history.append({'iteration': iteration, 'temperature_s': temperature,
                        'candidate_feasible': not violations, 'accepted': accepted,
                        'candidate_s': candidate_score, 'current_s': current_score,
                        'best_s': best_score, 'objective_evaluations': evaluations})
        temperature = max(settings.minimum_temperature_s, temperature * settings.cooling_factor)
    return {'strategy': best, 'best_time_s': best_score, 'initial_time_s':
            simulate(initial, params, limits)['total_time_s'],
            'seed': seed, 'objective_evaluations': evaluations, 'history': history,
            'parameter_provenance': params.provenance,
            'objective_kind': 'DETERMINISTIC_APPROXIMATION_OF_EXPECTED_TIME'}


def enumerate_reference(initial: Strategy, params: ModelParameters, limits: Constraints,
                        *, change_compounds: bool = False, max_candidates: int = 100000) -> dict:
    """Oráculo de pruebas pequeñas, con límites para evitar enumeraciones enormes."""
    n = len(initial.stops_after_lap)
    estimated = math.comb(limits.race_laps - 1, n)
    if change_compounds:
        if any(s.initial_age != 0 for s in initial.stints):
            raise ValueError('Referencia con compuestos variables solo admite juegos nuevos')
        estimated *= len(limits.allowed_compounds) ** len(initial.stints)
    if estimated > max_candidates:
        raise ValueError(f'Caso demasiado grande para referencia exhaustiva: {estimated}')
    best, best_score, feasible_count = None, math.inf, 0
    for stops in itertools.combinations(range(1, limits.race_laps), n):
        sequences = itertools.product(limits.allowed_compounds, repeat=n+1) if change_compounds else [None]
        for compounds in sequences:
            stints = tuple(TyreStint(c) for c in compounds) if compounds else initial.stints
            candidate = Strategy(stops, stints, name='exhaustive_small_reference')
            if validate_strategy(candidate, limits):
                continue
            score = simulate(candidate, params, limits)['total_time_s']
            feasible_count += 1
            if score < best_score:
                best, best_score = candidate, score
    if best is None:
        raise ValueError('No hay estrategias factibles en este espacio enumerado')
    return {'strategy': best, 'best_time_s': best_score, 'feasible_count': feasible_count}
