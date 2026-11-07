# Partición entrenamiento/validación (MA-03)

**Responsable:** Mario Fernando Rocha. **Revisión pendiente:** Luis Pedro Lira (LP-01).
**Fecha de decisión:** 2026-11-06. Luis Pedro Lira y Jonathan Zacarias delegaron la decisión en Mario.
**Código:** `src/partition.py`. **Pruebas:** `tests/test_partition.py`. **Comando:** `python main.py partition` (después de `python main.py download`).
**Evidencia congelada:** `docs/evidence/particion_manifiesto.json` (manifiesto con huellas y commit) y `docs/evidence/particion_entrenamiento_validacion.csv` (rol de cada vuelta; sin tiempos).

## 1. Decisión: reservar completo el stint 3 (opción A)

| Conjunto | Vueltas | Compuesto | Edades |
|---|---|---|---|
| **Entrenamiento** (33) | 2–16 (stint 1) y 19–36 (stint 2) | SOFT usado (15) y HARD nuevo (18) | SOFT 5–19, HARD 2–19 |
| **Validación** (18) | 39–57, sin la 46 (stint 3) | SOFT nuevo | 2–20 |
| **Fuera del ajuste** (6) | 1, 17, 18, 37, 38, 46 | — | Motivos en `docs/filtro_calidad_openf1.md` |

Las 57 vueltas siguen disponibles para la reconstrucción de la carrera completa, que se reporta aparte.

**Por qué A:**
- Es una validación temporal: el modelo predice un tramo posterior de la carrera que no vio, igual que tendría que hacerlo con una estrategia nueva.
- La alternativa, reservar las últimas vueltas de cada stint, solo prueba neumáticos algo más viejos. Además, las vueltas consecutivas se parecen mucho entre sí, así que ese examen parece mejor de lo que es.

**Costo aceptado y declarado:**
1. El entrenamiento solo cubre SOFT con edades 5–19. Las edades 2–4 y 20 de la validación son **extrapolación**.
2. La tendencia de carrera se entrena con las vueltas 2–36 y se aplica a la 39–57.
3. El stint 3 incluye comportamiento que un modelo lineal no reproduce: la vuelta rápida en la 39, el alivio en la 40 y la mejora entre la 41 y la 46 (hipótesis en `docs/filtro_calidad_openf1.md`). Se espera error de validación alto en esas vueltas. **No se quitan para mejorar la métrica.**

## 2. Métricas registradas antes de calibrar

`error_i = tiempo_predicho_i − tiempo_observado_i` (s). Para cada conjunto se reportan **MAE** (media de |error|), **sesgo** (media del error) y **error acumulado** (suma del error).

| Conjunto | Vueltas | Para qué |
|---|---|---|
| `validation_all` | 18: 39–45, 47–57 | **Número principal.** No se esconde ninguna vuelta |
| `validation_covered_ages` | 14: 42–45, 47–56 (edad 5–19) | Cuánto falla el modelo dentro de lo que conoce |
| `validation_extrapolated_ages` | 4: 39, 40, 41 (edad 2–4) y 57 (edad 20) | Cuánto falla fuera de lo que conoce |

**Aparte, no es validación:** `reconstruction_full_race`, las 57 vueltas con arranque y pits modelados. La vuelta 1 va con la convención oficial (97.284 s, `docs/conciliacion_tiempos.md`) y se compara con el total FIA de 5504.742 s.

**Reglas:**
1. Calibrar solo con las 33 vueltas de entrenamiento.
2. Congelar los parámetros antes de calcular cualquier métrica de validación.
3. Si el modelo cambia después de ver la validación, se crea una versión nueva, se reportan ambas y se repiten los experimentos afectados.
4. Se reportan los tres conjuntos aunque algún resultado sea desfavorable.

## 3. Identificabilidad (hallazgo 7 del plan): resultado y consecuencia

Se calculó el rango exacto de la matriz de diseño de cada modelo con las 33 vueltas de entrenamiento. Solo se usan edad, vuelta y compuesto, **no tiempos**, así que la comprobación no filtra información de la validación.

| Modelo | Parámetros | Rango | ¿Identificable? |
|---|---:|---:|---|
| `base_c + desgaste_c·edad + tendencia·vuelta` (modelo del plan) | 5 | 4 | **No** |
| `base_c + desgaste_común·edad + tendencia·vuelta` | 4 | 3 | **No** |
| `base_c + desgaste_c·edad`, tendencia fijada con referencia externa | 4 | 4 | **Sí** |

**Por qué:** dentro de un stint, edad − vuelta es constante (stint 1: edad = vuelta + 3; stint 2: edad = vuelta − 17). Esa constante la absorbe la base de cada compuesto, así que con **un solo stint por compuesto** los datos no pueden repartir la pendiente entre desgaste y tendencia: infinitas combinaciones dan el mismo ajuste. Como contraste, la matriz con los tres stints sí tiene rango completo (el SOFT aparece en dos stints con desfases distintos). La limitación la causa la partición elegida, no los datos. Las pruebas `test_one_stint_per_compound_cannot_separate_wear_from_trend` y `test_two_stints_of_one_compound_make_the_plan_model_identifiable` lo comprueban.

**Consecuencia para MA-04, a confirmar con Jonathan (JO-01):** con la opción A, la calibración debe **fijar la tendencia de carrera con una referencia externa** y estimar solo base y desgaste por compuesto. Propuesta:

- **Valor:** efecto del combustible = −(sensibilidad del tiempo al peso × consumo por vuelta) = −(0.023 s/kg × 1.93 kg/vuelta) ≈ **−0.044 s/vuelta**. Fuente: parámetros de Bahréin 2019 del simulador de TUM (`racesim/input/parameters/pars_Sakhir_2019.ini`, campos `t_lap_sens_mass` y `b_fuel_perlap`, repositorio https://github.com/TUMFTM/race-simulation, LGPL-3.0), descrito en Heilmeier, Graf y Lienkamp (2018), *A Race Simulation for Strategy Decisions in Circuit Motorsports*, IEEE ITSC, https://doi.org/10.1109/itsc.2018.8570012.
- **Limitaciones del valor:**
  - Es de 2019, no de 2024.
  - Solo representa combustible: la evolución de la pista (que se enfría de 23.8 a 21.9 °C) no está incluida.
  - Hay que verificar en el artículo y el repositorio que el valor se interpreta así antes de citarlo en el informe.
- **Sensibilidad obligatoria:** repetir la calibración con tendencia 0, −0.044 y −0.089 s/vuelta, y reportar cómo cambian el desgaste estimado y el error de validación. Esa tabla es parte de la incertidumbre del modelo (LP-05).
- **Lo que no se hará:** estimar la tendencia con los datos de entrenamiento (no es identificable) ni elegir su valor según el error de validación.

## 4. Congelación

El manifiesto registra:
- La fecha.
- El commit del código y si había cambios sin commit.
- Que `src/calibration.py` aún no existía (`frozen_before_calibration`).
- Que la partición no leyó tiempos de vuelta (`reads_lap_times: false`).
- Las huellas portables de los seis JSON crudos de OpenF1, de la tabla anotada y del propio CSV de partición.

Para verificar: `python main.py download` y `python main.py partition`, y comparar `sha256_portable_inputs` y `sha256_portable_split` con `docs/evidence/particion_manifiesto.json`.

## 5. Revisión de Luis Pedro (LP-01, pendiente)

- [ ] De acuerdo con la opción A y sus costos declarados.
- [ ] De acuerdo con las métricas y los tres conjuntos de validación, fijados antes de calibrar.
- [ ] Reproduce las huellas del manifiesto.
- [ ] Revisa la consecuencia de identificabilidad para MA-04 (junto con Jonathan).
- [ ] Observaciones / fecha / commit de revisión: ______
