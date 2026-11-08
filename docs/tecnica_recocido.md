# Técnica adicional de Ihan — recocido simulado discreto

## Representación y objetivo

Cada estado representa vueltas de parada y una secuencia de juegos identificados por compuesto y edad inicial. El catálogo toma juegos distintos del inventario inferido por Mario, admite cada juego como máximo una vez y agrupa las asignaciones que tienen la misma secuencia de compuestos y edades. Así respeta que hay un solo SOFT nuevo, un HARD nuevo y varios SOFT usados. Las edades de estos últimos se conservan al permutar la secuencia.

El objetivo minimiza el tiempo total determinista del simulador de Jonathan con la calibración de entrenamiento y degradación ×1.00. Se usa el mismo modelo para la candidata y la estrategia histórica. El alcance principal admite SOFT hasta edad 21 y HARD hasta 30. Una sola parada podría cubrir a lo sumo 51 vueltas aun con ambos juegos nuevos, frente a las 57 requeridas. El catálogo contiene 0 estrategias de una parada y 1323 de dos paradas.

## Algoritmo

1. Elegir una estrategia inicial uniformemente del catálogo para el número de paradas, con una semilla por búsqueda.
2. En el 95 % de las propuestas, elegir entre desplazar una parada ±1, ±2 o ±3 vueltas y proponer una secuencia completa de juegos tomada del grupo. El 5 % restante propone una estrategia uniforme del grupo completo y da acceso a todos los estados factibles. Las combinaciones ausentes del catálogo se rechazan sin simular.
3. Calcular la diferencia de tiempo Δ entre propuesta y estado actual. Si Δ ≤ 0, aceptar. Si Δ > 0, aceptar con probabilidad exp(−Δ/T). El valor T se expresa en segundos.
4. Conservar el menor tiempo visitado y reducir T con un factor geométrico hasta un piso de 0.000001 s. Terminar al agotar las propuestas. Registrar temperatura, factibilidad, aceptación, valor actual, mejor valor y llamadas al simulador.

## Pilotos, referencia y resultados

Se enumeró el tiempo determinista de las 1323 estrategias para medir la distancia al mínimo del catálogo. Cada perfil se probó con las mismas diez semillas piloto (1100–1109) para que la comparación tuviera los mismos arranques. El protocolo escoge el perfil con menos llamadas medias al simulador entre los que alcanzan la referencia en al menos 9 de 10 pilotos, con tolerancia de 10⁻⁸ s. Si ninguno alcanza ese umbral, prioriza la proporción de aciertos y después la brecha media.

| Perfil | Propuestas | T inicial (s) | Factor | Pilotos en el mínimo | Simulaciones medias |
|---|---:|---:|---:|---:|---:|
| Compacto | 120 | 1 | 0.970 | 10/10 | 63.4 |
| Medio | 300 | 1 | 0.980 | 10/10 | 158.9 |
| Amplio | 600 | 3 | 0.990 | 10/10 | 314.7 |
| Demo | 1000 | 5 | 0.995 | 10/10 | 551.0 |

Con el perfil compacto se ejecutaron 30 búsquedas con semillas 2100–2129. En 29 se alcanzó el mínimo de referencia. La mayor brecha fue 0.1522 s y el promedio fue de 66.8 evaluaciones por búsqueda. El conteo incluye el inicio y cada propuesta factible evaluada, incluso si repite un estado. La enumeración de referencia y los pilotos tienen un costo aparte. Las 30 búsquedas suman 2004 simulaciones y sirven para medir estabilidad. La enumeración de 1323 simulaciones por sí sola es una alternativa exacta y práctica para este caso.

| Estrategia | Paradas al final de vuelta | Juegos en orden (edad inicial) | Tiempo determinista (s) |
|---|---|---|---:|
| Histórica | 17, 37 | SOFT (3), HARD (0), SOFT (0) | 5514.6992 |
| Candidata congelada | 17, 36 | SOFT (3), SOFT (0), HARD (0) | 5514.6242 |

La candidata procede de la semilla 2100. Entre resultados dentro de 10⁻⁸ s del menor valor de las 30 búsquedas, se priorizan menos paradas y luego la menor semilla. Distintas combinaciones de cortes y juegos pueden empatar en tiempo dentro de esa tolerancia. Las semillas 3300–3329 se reservaron para evaluar las estrategias después de congelar la candidata.

## Interpretación y alternativas

- La diferencia de 0.075 s es una estimación del modelo. La candidata llega a edad 21 en HARD en la vuelta 57, por encima del máximo de 20 observado para Verstappen y del máximo de entrenamiento de 19. Las edades tempranas de SOFT y HARD también pueden quedar fuera del intervalo de entrenamiento. Con el límite de edad 20 en ambos compuestos quedan seis órdenes equivalentes en el modelo y la diferencia estimada desaparece.
- El inventario es inferido y el modelo usa pérdida fija de pits, desgaste lineal y ritmo sin tráfico ni reacción de rivales. La búsqueda puede favorecer casos donde estos supuestos son débiles. La comparación con el tercer stint reservado y la sensibilidad de degradación quedan para Luis Pedro.
- El enfriamiento finito no garantiza llegar al óptimo. Hill Climbing aceptaría mejoras sin explorar ascensos y un algoritmo genético necesitaría operadores y restricciones para una población. La comparación cuantitativa hecha aquí es con enumeración. La tabla separa estabilidad del método y rendimiento de la estrategia.
- El ruido actual del simulador es aditivo, con la misma desviación para todos los compuestos. Con semilla compartida, una histórica y una candidata de 57 vueltas reciben la misma secuencia de perturbaciones y el ruido se cancela en su diferencia, salvo redondeo. Las 30 réplicas de A/B/C/D describirán dispersión de tiempos totales dentro del modelo. La dispersión pareada resultante no cuantifica incertidumbre de parámetros ni del modelo.

## Fuentes verificadas para la redacción

1. Kirkpatrick, Gelatt y Vecchi (1983), *Optimization by Simulated Annealing*, Science 220, pp. 671–680. En p. 672 se describe la aceptación probabilística de ascensos con el criterio de Metropolis. [Artículo](https://www2.stat.duke.edu/~scs/Courses/Stat376/Papers/TemperAnneal/KirkpatrickAnnealScience1983.pdf).
2. Hajek (1988), *Cooling Schedules for Optimal Annealing*, Mathematics of Operations Research 13, pp. 311–329. La introducción y el teorema relacionan el enfriamiento logarítmico y la profundidad de los mínimos bajo hipótesis específicas. El programa usa enfriamiento geométrico con presupuesto finito. [Artículo](https://web.mit.edu/6.435/www/Hajek88.pdf).
3. SciPy, documentación de `dual_annealing`, sección *Notes*. Describe otra variante, con distribución de visita generalizada y búsqueda local opcional. El recocido discreto del proyecto usa la biblioteca estándar. [Documentación](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.dual_annealing.html).

## Reproducción y relevo técnico

```bash
python -m unittest discover -q
python main.py optimize
python main.py simulate --strategy docs/evidence/optimization/candidate.json
```

La optimización escribe el resumen, los pilotos, el CSV de 30 búsquedas y las 30 trazas en `results/optimization/`. La carpeta versionada `docs/evidence/optimization/` contiene el resumen con huellas de entrada, ambos CSV, la traza ganadora y el JSON de la candidata congelada. La demo sintética previa sigue disponible con `python main.py optimize-demo --seed 100 --runs 30`.

Para evaluar, cargar `candidate.json` con `src.domain.strategy_from_dict` y usar `src.model.get_historical_strategy()` para la base. Usar el mismo `ModelParameters` calibrado y las mismas restricciones del escenario principal para ambas. Congelar esta candidata para B y D. Emparejar A/B y C/D con las semillas reservadas, y aplicar degradación ×1.20 solo en C/D. La validación del modelo debe usar primero los grupos registrados en [partición](particion_validacion.md), sin volver a ajustar el modelo.

Revisión de la integración por Jonathan y revisión personal de Ihan para la defensa pendientes.
