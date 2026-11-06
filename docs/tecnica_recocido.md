# Técnica adicional: recocido simulado discreto

Responsable: Ihan Marroquin. Estado: entrega inicial realizada y verificada con asistencia de Codex. Incluye implementación y pruebas sintéticas. La conexión con parámetros reales y la revisión de integración se harán al disponer de los datos calibrados; no se presentan como completadas.

## Problema y representación

Una estrategia tiene vueltas enteras de parada y una secuencia de stints. Cada stint tiene un compuesto y la edad inicial del juego. La función objetivo devuelve segundos simulados de carrera y se minimiza, comprobando previamente restricciones.

El número de paradas permanece fijo durante cada búsqueda. La comparación 1/2 paradas se realizará con ejecuciones separadas bajo protocolo común, aún pendiente de integrar. El programa acepta una estrategia inicial válida; no inventa juegos de neumáticos disponibles.

## Fundamento

Recocido simulado explora vecinos y permite aceptar empeoramientos para escapar de soluciones locales. Para diferencia `delta = f(vecino) - f(actual)`, aceptar siempre si `delta <= 0`; en otro caso, aceptar con probabilidad `exp(-delta / temperatura)`. Una temperatura alta facilita explorar y una menor favorece aceptar principalmente mejoras. Se conserva por separado la mejor solución factible visitada.

Nuestra variante usa enfriamiento geométrico `T <- max(Tmin, alpha * T)` y presupuesto finito. No afirmamos convergencia global: los resultados teóricos de esquemas de enfriamiento tienen condiciones que esta implementación práctica no demuestra.

## Procedimiento implementado

1. Comprobar la estrategia inicial y parámetros de búsqueda.
2. Evaluar la estrategia inicial con el simulador determinista.
3. Proponer mover una parada ±1, ±2 o ±3 vueltas; opcionalmente cambiar un compuesto si todos los juegos son nuevos.
4. Si el vecino viola restricciones, registrar el rechazo y seguir; no ordenar ni redondear silenciosamente una solución inválida.
5. Evaluar el vecino válido, aplicar aceptación y conservar el mejor resultado.
6. Registrar temperatura, factibilidad, aceptación, objetivo actual/mejor y número de evaluaciones.
7. Enfriar y terminar al completar el presupuesto.

La propuesta cambia compuestos solo bajo supuesto de juegos nuevos. Para un inicio con neumáticos usados se conserva el compuesto y la edad de cada slot. Falta desarrollar la selección por identidad de juegos reales si el modelo final la requiere. Las edades no se borran para mejorar artificialmente una estrategia.

## Parámetros iniciales de la demo

| Parámetro | Valor | Interpretación |
|---|---:|---|
| Iteraciones | 1000 | Presupuesto de propuestas por búsqueda, no necesariamente 1000 evaluaciones válidas. |
| Temperatura inicial | 5 s | Escala del empeoramiento aceptable; provisional y solo para demo. |
| Factor de enfriamiento | 0.995 | Reducción geométrica, provisional. |
| Temperatura mínima | 0.000001 s | Evitar división por cero. |
| Semillas del ensayo | 100–129 | 30 búsquedas independientes sintéticas. |

Estos valores permiten verificar funcionamiento. Deben calibrarse mediante pilotos separados de la evaluación final; no están justificados como los mejores para Bahréin.

## Justificación y alternativas

- Frente a Hill Climbing, permite aceptar temporalmente soluciones peores. Hill Climbing ya aparece en el curso.
- Frente a un genético, el estado y los operadores iniciales son sencillos y el algoritmo básico genético ya fue trabajado en clase. No se afirma superioridad general del recocido.
- La búsqueda exhaustiva es excelente para verificar un espacio pequeño; podría incluso ser suficiente para el alcance final. Si el espacio resulta pequeño, explicar con honestidad que el recocido se estudia como técnica y comparar calidad/costo, sin exagerar necesidad o complejidad.

## Verificaciones realizadas y límites

Pruebas: aceptación, reproducibilidad, factibilidad, mejor valor no creciente, caso pequeño contra enumeración, dos paradas con compuestos variables bajo supuesto de juegos nuevos y rechazo de cambios de compuesto con juegos usados.

En la demo de 12 vueltas, las 30 semillas 100–129 alcanzaron el valor de la referencia exhaustiva para esa secuencia fija. Esto no demuestra optimalidad en la carrera real, ni buena calibración del modelo, ni mejor estrategia histórica.

Limitaciones: dependencia de temperatura y vecindario; posible atrapamiento en búsqueda finita; objetivo que puede explotar sesgos del modelo; incertidumbre de parámetros no modelada todavía; inventario simplificado; resultados con ruido no equivalente al objetivo determinista. Usar semillas nuevas para evaluar una estrategia congelada y mantener separadas variabilidad del optimizador y variabilidad de carrera.

## Tres fuentes técnicas para investigar y citar

1. Kirkpatrick, S.; Gelatt, C. D.; Vecchi, M. P. (1983). *Optimization by Simulated Annealing*. Science 220(4598), 671–680. https://doi.org/10.1126/science.220.4598.671 . Fundamento del método; copia académica consultable: https://www2.stat.duke.edu/~scs/Courses/Stat376/Papers/TemperAnneal/KirkpatrickAnnealScience1983.pdf
2. Hajek, B. (1988). *Cooling Schedules for Optimal Annealing*. Mathematics of Operations Research 13(2), 311–329. https://doi.org/10.1287/moor.13.2.311 . Condiciones de enfriamiento y límites de afirmaciones de convergencia; copia académica: https://web.mit.edu/6.435/www/Hajek88.pdf
3. SciPy. *scipy.optimize.dual_annealing*, documentación técnica. https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.dual_annealing.html . Variante de annealing con otros mecanismos; se usa como comparación documental, no como descripción del código propio ni biblioteca llamada por este módulo.

Referencia adicional de aplicación: TUMFTM, *race-simulation*, https://github.com/TUMFTM/race-simulation . Estudiar cómo se separan ritmo, neumáticos y pérdidas. No se ha copiado ni ejecutado ese simulador como entrega propia.

Antes del informe final, Ihan debe leer las secciones relevantes, comprobar el respaldo de cada afirmación, ajustar parámetros reales y poder explicar cada decisión sin depender de este borrador.
