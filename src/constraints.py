"""Factibilidad del alcance del proyecto; no certifica legalidad histórica FIA."""
from collections import Counter
from .domain import Constraints, Strategy


def validate_strategy(strategy: Strategy, limits: Constraints) -> list[str]:
    violations = []
    if type(limits.race_laps) is not int or limits.race_laps < 1:
        return ['race_laps debe ser un entero positivo']
    if not (0 <= limits.min_stops <= limits.max_stops):
        return ['Intervalo de paradas inválido']
    stops = strategy.stops_after_lap
    if not limits.min_stops <= len(stops) <= limits.max_stops:
        violations.append('Cantidad de paradas fuera del alcance')
    if len(strategy.stints) != len(stops) + 1:
        violations.append('Debe haber un stint más que paradas')
    if any(type(lap) is not int for lap in stops):
        violations.append('Las vueltas de parada deben ser enteras')
        return violations
    if any(lap <= 0 or lap >= limits.race_laps for lap in stops):
        violations.append('Parada fuera de las vueltas permitidas')
    if any(a >= b for a, b in zip(stops, stops[1:])):
        violations.append('Las paradas deben estar estrictamente ordenadas')
    for stint in strategy.stints:
        if stint.compound not in limits.allowed_compounds:
            violations.append(f'Compuesto no permitido: {stint.compound}')
        if type(stint.initial_age) is not int or stint.initial_age < 0:
            violations.append('La edad inicial debe ser un entero no negativo')
    counts = Counter(stint.compound for stint in strategy.stints)
    if len(counts) < limits.min_distinct_compounds:
        violations.append('No se cumple la diversidad mínima de compuestos')
    for compound, count in counts.items():
        if compound in limits.max_sets_by_compound and count > limits.max_sets_by_compound[compound]:
            violations.append(f'Inventario insuficiente de {compound}')
    if violations:
        return violations
    boundaries = (0,) + stops + (limits.race_laps,)
    for stint, begin, end in zip(strategy.stints, boundaries, boundaries[1:]):
        max_age = limits.max_age_by_compound.get(stint.compound)
        if max_age is not None and stint.initial_age + end - begin > max_age:
            violations.append(f'Edad fuera de la cobertura configurada: {stint.compound}')
    return violations
