# Validación, experimentos y comparación con la carrera real (LP-01 a LP-06)

**Responsable:** Luis Pedro Lira. **Revisión pendiente:** Mario Fernando Rocha (LP-06). **Integra en el informe:** Luis Gilberto Marroquin.
**Fecha:** 2026-11-08. **Rama:** `luis-pedro/validacion`, creada desde `7a740c6`.
**Código:** `src/validation.py`, `src/experiments.py`, comandos `validate` y `experiments` en `main.py`.
**Pruebas:** `tests/test_validation.py`, `tests/test_experiments.py`, `tests/test_strategy_conventions.py`.
**Evidencia versionada:** `docs/evidence/validation/` y `docs/evidence/experiments/`, generadas con el código del commit `a4828b5`.

## 1. Reproducción

```bash
python main.py download        # OpenF1; usa la caché si ya existe
python main.py reconcile       # Jolpica/FIA: vuelta 1 con convención oficial
python main.py partition       # comprobar huellas con docs/evidence/particion_manifiesto.json
python main.py validate        # LP-03 → results/validation/
python main.py experiments     # LP-04/LP-05 → results/experiments/ (no necesita descargar datos)
python -m unittest discover -s tests
```

`experiments` funciona sin datos descargados. Solo la propagación de la incertidumbre de parámetros (sección 5.3) necesita las vueltas de entrenamiento regeneradas; sin ellas, el resumen lo indica y omite ese bloque.

Ambos comandos se detienen en tres casos:
- La partición no coincide con su huella congelada.
- `configs/params_bahrain_2024.json` no tiene la misma huella que usó la optimización (`e7343931…`).
- `candidate.json` no coincide con la candidata registrada en `summary.json`.

Si Python no valida el certificado de `api.openf1.org`, ejecutar `download` con `SSL_CERT_FILE` apuntando a `python -c "import certifi; print(certifi.where())"`. Pasó en Windows el 2026-11-08 y no requiere cambiar código.

## 2. Revisión de datos y partición (LP-01)

Las siete huellas de entrada, la huella de la partición, las listas de vueltas, la cobertura y la identificabilidad coinciden con el manifiesto congelado. También se reproducen:
- La calibración, con los mismos parámetros y `validation_laps_read: []`.
- La conciliación: solo difiere la vuelta 1, por +0.475 s.
- La tabla de exclusiones.
- El inventario: 6 / 1323 / 6 / 1746 estrategias.

Detalle en `docs/particion_validacion.md`, sección 5.

## 3. Pruebas del modelo real (LP-02)

Las pruebas nuevas cubren, con parámetros calibrados y casos construidos a mano:

| Propiedad | Prueba |
|---|---|
| El total es igual a la suma de vuelta normal + ruido + arranque + pits; un arranque y dos paradas | `test_total_equals_lap_breakdown_with_and_without_noise` |
| Edades: SOFT 4 en la vuelta 1, 20 en la 17; HARD 1 en la 18; la candidata llega a HARD 21 en la 57 | `test_age_convention_of_observed_and_candidate_strategies` |
| Con la misma semilla, dos estrategias reciben exactamente el mismo ruido | `test_shared_seed_gives_identical_noise_for_different_strategies` |
| Con dos paradas en ambas, la pérdida de pits y el arranque no cambian la diferencia | `test_pit_loss_and_start_penalty_cancel_between_two_stop_strategies` |
| Con base y desgaste fijos, la tendencia se cancela en la diferencia | `test_trend_cancels_when_compound_parameters_are_fixed` |
| La diferencia simulada es igual a la descomposición lineal en 3 tendencias × 3 multiplicadores | `test_difference_matches_linear_decomposition_in_every_scenario` |
| Una parada extra gana exactamente 8·d − pérdida de pits (caso conocido) | `test_extra_stop_gains_only_when_wear_saving_exceeds_pit_loss` |
| La cobertura estricta (edad ≤ 20) rechaza la candidata y admite la histórica | `test_strict_coverage_rejects_candidate_but_keeps_historical` |

Resultado: **92 pruebas aprobadas** (62 previas y 30 nuevas). Las 4 de integración con el caso real se omiten si no se regeneraron los datos.

## 4. Validación del modelo en el stint 3 reservado (LP-03)

**Protocolo:**
- Estrategia observada (histórica) en modo determinista, con los parámetros congelados de MA-04. No se reajusta nada.
- `error = predicho − observado` en segundos. Un error positivo significa que el modelo es más lento que la realidad.
- Observación: vueltas 2–57 de OpenF1, iguales a Jolpica al milisegundo, y la vuelta 1 con convención oficial (97.284 s).

### 4.1 Validación reservada: escenario principal preregistrado (`trend_fuel_reference`)

| Conjunto | Vueltas | MAE (s) | Sesgo (s) | Error acumulado (s) |
|---|---:|---:|---:|---:|
| **`validation_all`** (número principal) | 18 | **0.712** | **+0.456** | **+8.203** |
| `validation_covered_ages` (edad 5–19) | 14 | 0.570 | +0.531 | +7.431 |
| `validation_extrapolated_ages` (edad 2–4 y 20) | 4 | 1.206 | +0.193 | +0.772 |

Complementarias, no preregistradas: RMSE de 0.885 s y error absoluto máximo de 2.271 s, en la vuelta 39.

**Lectura:**
- El modelo predice el stint 3 sistemáticamente **más lento** que lo observado: sesgo de +0.46 s por vuelta.
- En las edades cubiertas, el MAE (0.57 s) es **4.8 veces** el MAE de entrenamiento (0.118 s) y **3.5 veces** la dispersión residual (0.163 s).
- En las edades extrapoladas el MAE se duplica, pero el sesgo es menor porque se compensan:
  - la vuelta 39 (+2.27 s), vuelta rápida de la carrera;
  - la vuelta 40 (−1.68 s), de alivio.
- Entre la 42 y la 52 el error es positivo en todas las vueltas. Es lo que se esperaba en `docs/filtro_calidad_openf1.md`, porque los tiempos bajan aunque el desgaste aumente.

### 4.2 Reconstrucción de la carrera completa (no es validación)

| Tramo | Vueltas | Error acumulado (s) |
|---|---|---:|
| Arranque | 1 | 0.000 |
| Stint 1 sin eventos | 2–16 | +0.001 |
| Parada 1 (entrada + salida) | 17–18 | +0.000 |
| Stint 2 sin eventos | 19–36 | −0.003 |
| Parada 2 (entrada + salida) | 37–38 | **+0.848** |
| Stint 3 sin eventos (incluye la 46) | 39–57 | **+9.111** |
| **Total simulado − FIA** | 1–57 | **+9.957** (5514.699 contra 5504.742 s) |

- Los tramos 1–36 casi no tienen error porque los parámetros se ajustaron con esas vueltas. Por eso la reconstrucción **no** sirve como validación.
- La suma de vueltas con convención oficial reproduce exactamente el total de la FIA. OpenF1 sola suma 5505.217 s (+0.475 s en la vuelta 1).
- El error por vuelta en 17/18 y 37/38 refleja la pérdida agrupada en la vuelta de entrada. Solo es comparable el par completo.

### 4.3 Comprobación de la pérdida de pits con la parada 37–38

Esta parada no se usó en la calibración.
- Pérdida implícita: (vuelta 37 + vuelta 38 observadas) − (normales predichas) = 215.679 − 191.005 = **24.674 s**.
- Pérdida calibrada con la parada 17–18: **25.522 s**. Diferencia: **+0.848 s**.
- La FIA registra 25.064 y 24.209 s en pit lane para las dos paradas: una diferencia de **0.855 s**. La discrepancia coincide en magnitud con la variación real entre paradas.
- La vuelta 38 usa SOFT con edad 1, extrapolada, así que la cifra también contiene error de ritmo.
- Ambas estrategias comparadas tienen dos paradas, así que la pérdida de pits **se cancela** en su diferencia (sección 5.4).

### 4.4 Sensibilidad a la tendencia (no se usa para elegir)

| Escenario | Tendencia (s/vuelta) | MAE `validation_all` (s) | Sesgo (s) | Acumulado (s) | Reconstrucción − FIA (s) |
|---|---:|---:|---:|---:|---:|
| `trend_zero` | 0 | 2.232 | +2.232 | +40.171 | +45.477 |
| **`trend_fuel_reference`** | **−0.0444** | **0.712** | **+0.456** | **+8.203** | **+9.957** |
| `trend_double` | −0.0888 | 1.375 | −1.320 | −23.765 | −25.563 |

Las tres tendencias producen exactamente el mismo ajuste en entrenamiento (tramos 1–36 idénticos) y solo difieren al extrapolar. Por la regla preregistrada, el escenario principal no se cambia con estos números: los otros dos se reportan como sensibilidad. Con el sesgo positivo de la tendencia principal y el negativo de la doble, la evolución real del ritmo quedaría entre ambas, pero eso no justifica elegir un valor intermedio.

## 5. Experimentos A/B/C/D (LP-04) y análisis (LP-05)

### 5.1 Diseño

| Condición | Estrategia | Degradación | Réplicas | Semillas |
|---|---|---:|---:|---|
| A | Histórica: paradas en 17 y 37; SOFT(3) → HARD(0) → SOFT(0) | ×1.00 | 30 | 3300–3329 |
| B | Candidata congelada (`candidate.json`, búsqueda 2100): paradas en 17 y 36; SOFT(3) → SOFT(0) → HARD(0) | ×1.00 | 30 | 3300–3329 |
| C | Histórica | ×1.20 | 30 | 3300–3329 |
| D | La misma candidata de B | ×1.20 | 30 | 3300–3329 |

- **Parámetros:** `trend_fuel_reference`; las otras dos tendencias se corren igual como sensibilidad.
- **Restricciones:** las mismas para ambas estrategias, `inventory_main / observed_race_feasibility`.
- **Semillas:** las reservadas no se usaron en pilotos (1100–1109) ni en búsqueda (2100–2129).
- **Pares:** A con B y C con D comparten la semilla de cada réplica. Las 30 réplicas de cada condición son independientes entre sí.
- **Ruido:** gaussiano aditivo por vuelta, σ = 0.1631 s.

**Signos:**
- mejora_s = tiempo_base − tiempo_candidata.
- mejora_% = 100 · mejora_s / tiempo_base.
- Un valor positivo significa que la candidata es más rápida.

### 5.2 Resultados (120 réplicas, escenario principal)

| Condición | Determinista (s) | Media de 30 (s) | DE (s) | IC 95 % de la media (s) |
|---|---:|---:|---:|---|
| A | 5514.699 | 5514.810 | 1.303 | 5514.323 – 5515.297 |
| B | 5514.624 | 5514.735 | 1.303 | 5514.248 – 5515.222 |
| C | 5525.419 | 5525.529 | 1.303 | 5525.043 – 5526.016 |
| D | 5525.481 | 5525.592 | 1.303 | 5525.105 – 5526.079 |

Corrección del 2026-11-08 (Luis Gilberto): la DE por condición es 1.30350 s en `resumen.json` y redondea a 1.303 s; antes decía 1.304. `tests/test_report_numbers.py` comprueba esta tabla contra la evidencia.

La DE teórica del total es σ·√57 = 1.231 s. La media supera al valor determinista en 0.11 s por efecto muestral de las 30 semillas, y ese efecto es igual en las cuatro condiciones.

| Par | mejora_s media | DE pareada (s) | mejora_% | Réplicas con candidata más rápida |
|---|---:|---:|---:|---:|
| A − B (×1.00) | **+0.0750** | 1.7 × 10⁻¹² | +0.00136 % | 30 / 30 |
| C − D (×1.20) | **−0.0624** | 1.5 × 10⁻¹² | −0.00113 % | 0 / 30 |

**Por qué la DE pareada es prácticamente cero y qué no significa:**
- Con la misma semilla, la histórica y la candidata reciben las mismas 57 perturbaciones: la suma de ruido es idéntica en cada par (`noise_sum_difference_s = 0`).
- La diferencia pareada es entonces la diferencia determinista más un redondeo de ~10⁻¹² s. Por eso «30 de 30» no es evidencia estadística de superioridad: con este modelo de ruido, todas las réplicas repiten el mismo número.
- La DE pareada **no cuantifica** la incertidumbre de los parámetros, de la tendencia ni de la forma del modelo. Tampoco la variación entre paradas reales.
- Sin emparejar, el IC 95 % de la diferencia de medias sería ±0.67 s: [−0.60, +0.75] s para A − B. Solo indica que el ruido por vuelta oculta una diferencia de 0.075 s si no se comparte semilla, y tampoco es incertidumbre del modelo.

### 5.3 De dónde sale la diferencia y cuánta incertidumbre tiene

Como el modelo es lineal, la diferencia se descompone exactamente. La histórica corre 37 vueltas en SOFT y 20 en HARD; la candidata, 36 y 21.

```
mejora_s = (b_SOFT − b_HARD) + μ · (20 · d_SOFT − 21 · d_HARD)
         = 0.7622 + μ · (1.5220 − 2.2092) = 0.7622 − 0.6872 · μ
```

- La tendencia y la pérdida de pits se cancelan: ambas estrategias tienen 57 vueltas y dos paradas. Lo comprueban las pruebas de la sección 3 y `pit_loss_invariance` en `resumen.json`.
- La candidata gana porque cambia una vuelta de SOFT por una de HARD, que tiene una base 0.76 s más rápida. Pierde 0.69 s por el mayor desgaste del HARD que corre al final.
- **Equilibrio:** μ = 0.7622 / 0.6872 = **×1.109**. Con más de un 11 % de degradación adicional, la histórica es mejor.

**Propagación del error estándar de la calibración** (`parameter_uncertainty` en `resumen.json`):
- Toma los ajustes MCO de MA-04 por compuesto (independientes) con la covarianza exacta entre base y desgaste.
- Solo lee las 33 vueltas de entrenamiento.

| Multiplicador | mejora_s | EE por parámetros (s) | IC 95 % aproximado (s) |
|---|---:|---:|---|
| ×1.00 | +0.075 | 0.128 | −0.175 – +0.325 |
| ×1.20 | −0.062 | 0.176 | −0.408 – +0.283 |

Este intervalo es **condicional**: tendencia fija, modelo lineal correcto y residuos independientes. El SOFT tiene autocorrelación 0.21, así que el EE es optimista. Aun así, ambos intervalos contienen el cero.

### 5.4 Sensibilidad

**Degradación y tendencia** (deterministas, `sensibilidad.csv`; mejora_s en segundos):

| Tendencia | ×0.80 | ×1.00 | ×1.10 | ×1.15 | ×1.20 | ×1.30 |
|---|---:|---:|---:|---:|---:|---:|
| `trend_zero` | +1.136 | +1.007 | +0.943 | +0.911 | +0.879 | +0.815 |
| **`trend_fuel_reference`** | +0.212 | **+0.075** | +0.006 | −0.028 | **−0.062** | −0.131 |
| `trend_double` | −0.711 | −0.857 | −0.931 | −0.967 | −1.004 | −1.077 |

Las 120 réplicas A/B/C/D se repitieron con las otras dos tendencias: `replicas_sensibilidad_tendencia.csv` y `diferencias_pareadas_sensibilidad_tendencia.csv`. Dan las mismas diferencias deterministas.

**Otras sensibilidades:**
- **Pérdida de pits** (0, 25.5 y 51.0 s): la diferencia no cambia (dispersión 0.000 s), porque ambas estrategias tienen dos paradas.
- **Cobertura estricta** (edad ≤ 20): la candidata es **infactible** (`Edad fuera de la cobertura configurada: HARD`). Con ese límite, los seis órdenes factibles empatan con la histórica: mejora de 0 s.

### 5.5 Comparación con la carrera real

| Métrica, 57 vueltas (s) | Observado (FIA) | Histórica simulada (A) | Candidata simulada (B) |
|---|---:|---:|---:|
| Tiempo total, determinista | 5504.742 | 5514.699 | 5514.624 |
| Tiempo total, media de 30 réplicas | — | 5514.810 | 5514.735 |
| Simulado − observado | — | +9.957 | No comparable: estrategia no observada |
| Error en el stint 3 reservado (acumulado, 18 vueltas) | — | +8.203 | — |

La columna observada solo contiene mediciones. La candidata nunca se corrió en la realidad, así que su tiempo es una predicción del modelo.

**La ventaja estimada frente al error del modelo:**
- La ventaja de **0.075 s** es el 0.0014 % del tiempo de carrera.
- Es **6 veces menor** que el sesgo de **una sola vuelta** en validación (0.456 s).
- Es unas **110 veces menor** que el error acumulado del stint reservado (8.2 s).
- Es **11 veces menor** que la discrepancia de la segunda parada (0.85 s).
- Es menor que su propio error estándar por parámetros (0.128 s).

**Lectura ilustrativa, no reajuste:** si el sesgo de +0.46 s/vuelta del stint 3 fuera un error de nivel del SOFT, la ventaja pasaría a ≈ 0.075 − 0.456 = −0.38 s, porque la histórica tiene una vuelta más de SOFT. Si fuera un error de la tendencia común, no cambiaría, porque la tendencia se cancela. Los datos no permiten distinguir ambos casos (identificabilidad, `docs/particion_validacion.md`, sección 3).

**Extrapolación del HARD.**
- Edades de la candidata fuera del entrenamiento de HARD (2–19): edad 1 en la vuelta 37, y 20–21 en las vueltas 56–57.
- La edad 21 supera también el máximo de 20 vueltas observado en VER.
- El tramo HARD de la candidata cae en las vueltas 37–57, una fase de carrera que el HARD nunca corrió con VER. Ahí el modelo falló para el SOFT.
- La ventaja depende justamente del desgaste del HARD en ese tramo: cada 0.01 s/vuelta de error en d_HARD mueve la diferencia 0.21 s.

### 5.6 Conclusión

**No se detectó una mejora robusta.** La candidata del recocido supera a la histórica por 0.075 s solo bajo:
- la tendencia principal,
- la degradación nominal,
- el límite de edad amplio.

La ventaja:
- se invierte con +20 % de degradación (−0.062 s; equilibrio en ×1.109);
- cambia de signo según la tendencia no identificable (+1.007 / +0.075 / −0.857 s);
- desaparece con la cobertura estricta;
- es mucho menor que el error de validación y que su error estándar por parámetros.

El resultado es compatible con que la estrategia histórica ya estaba en el grupo de estrategias equivalentes del modelo. No permite afirmar que la candidata habría sido más rápida en la carrera real.

## 6. Limitaciones experimentales

1. **Ruido:** aditivo, gaussiano, independiente por vuelta e igual para ambos compuestos. Con semillas compartidas se cancela. La DE dentro de cada condición (1.30 s) solo describe ruido entre vueltas, no incertidumbre del modelo.
2. **Incertidumbre de parámetros:** el EE de la sección 5.3 supone tendencia fija, normalidad e independencia, y no incluye el error de especificación que revela la validación. Una ampliación sería remuestrear residuos por bloques o parámetros completos.
3. **Tendencia no identificable** con un stint por compuesto. El signo de la ventaja depende de ella.
4. **Validación pequeña:** 18 vueltas consecutivas (correlacionadas) de un piloto en una carrera, con ritmo administrado por VER en el stint 3 y una vuelta rápida deliberada en la 39.
5. **Pérdida de pits fija:** la variación real entre paradas (~0.85 s) no se modela. No afecta esta comparación (mismas paradas), pero sí afectaría estrategias con distinto número de paradas.
6. **Inventario inferido**, desgaste lineal sin *cliff* y sin tráfico, rivales ni Safety Car. El multiplicador ×1.20 es un escenario hipotético, no un dato.
7. **Transparencia:** el equipo vio los tiempos del stint 3 durante MA-02, antes de congelar la partición. Los parámetros y la tendencia se fijaron sin ellos y nada se reajustó después de esta validación.

## 7. Archivos para gráficas e informe (Luis Gilberto)

| Figura comprometida | Fuente | Columnas |
|---|---|---|
| 1. Vueltas observadas y predichas en validación | `results/validation/validacion_vueltas.csv` (regenerar con `validate`; no se versiona por la licencia CC BY-NC-SA de las fuentes) | `lap`, `observed_official_s`, `predicted_<escenario>_s`, `error_<escenario>_s`, `cumulative_error_<escenario>_s`, `in_validation_*`, `age_coverage` |
| 2. Cronograma de stints, base y candidata | `docs/evidence/experiments/vueltas_deterministas.csv` | `condition`, `lap`, `compound`, `tyre_age_end_laps`, `cumulative_s` |
| 3. Distribución de tiempos o diferencias pareadas | `docs/evidence/experiments/replicas.csv` y `diferencias_pareadas.csv` | `condition`, `total_time_s`; `pair`, `mejora_s`. Indicar en la figura que la diferencia pareada es constante por construcción |
| 4. Sensibilidad | `docs/evidence/experiments/sensibilidad.csv`, `parameter_uncertainty` en `resumen.json` | `trend_scenario`, `degradation_multiplier`, `mejora_s` |
| Tablas de validación | `docs/evidence/validation/validacion.json`, `sensibilidad_tendencia_validacion.csv` | Métricas agregadas por conjunto y escenario |

Los demás archivos de `results/experiments/` se regeneran con `python main.py experiments`. `vueltas_replicas.csv` (6840 filas, desglose por vuelta de las 120 réplicas) no se versiona por tamaño.
