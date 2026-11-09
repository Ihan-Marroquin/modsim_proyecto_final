# Partición entrenamiento/validación (MA-03)

**Responsable:** Mario Fernando Rocha. **Revisión:** Luis Pedro Lira (LP-01), cerrada el 2026-11-08 (sección 5).
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

## 5. Revisión de Luis Pedro (LP-01, cerrada el 2026-11-08)

- [x] De acuerdo con la opción A y sus costos declarados.
- [x] De acuerdo con las métricas y los tres conjuntos de validación, fijados antes de calibrar.
- [x] Reproduce las huellas del manifiesto.
- [x] Revisa la consecuencia de identificabilidad para MA-04. Jonathan ya la había confirmado en `docs/calibracion.md`.
- [x] Observaciones / fecha / commit: abajo. Rama `luis-pedro/validacion`, creada desde `7a740c6`.

**Reproducción.** Clon en Windows con Python 3.12.10. Se ejecutaron `python main.py download`, `python main.py reconcile` y `python main.py partition` el 2026-11-08 y se compararon con este manifiesto:

| Huella portable | Congelada | Regenerada |
|---|---|---|
| `data/raw/openf1/laps.json` | `4c2f8ab9…` | Igual |
| `data/raw/openf1/pit.json` | `3bb392be…` | Igual |
| `data/raw/openf1/race_control.json` | `6ef4044a…` | Igual |
| `data/raw/openf1/sessions.json` | `dd852c09…` | Igual |
| `data/raw/openf1/stints.json` | `9e973c32…` | Igual |
| `data/raw/openf1/weather.json` | `a41e2ad0…` | Igual |
| `data/processed/openf1_target_laps_annotated.csv` | `a073c360…` | Igual |
| `sha256_portable_split` (`partition_split.csv`) | `6dcb304d…` | Igual |

También coinciden las listas de vueltas de entrenamiento, validación, excluidas, cubiertas y extrapoladas; los rangos de edad; la cobertura y los rangos de identificabilidad (4 de 5, 3 de 4 y 4 de 4). `python main.py calibrate` reproduce los parámetros versionados con `validation_laps_read: []`. Por eso `configs/params_bahrain_2024.json` se restauró sin cambios: solo diferían los saltos de línea.

**Observaciones.**
1. El campo `status` del manifiesto sigue en `FROZEN_PENDING_REVIEW_LUIS_PEDRO`. No se edita, para no alterar la evidencia congelada. La revisión queda registrada aquí.
2. La revisión se registra en la misma sesión que LP-03, después de calibrar. La partición no cambió (huellas idénticas) y la validación usa los conjuntos tal como se preregistraron.
3. En este entorno Python no validó el certificado de `api.openf1.org` (`CERTIFICATE_VERIFY_FAILED`), aunque `curl` sí. Se resolvió solo en la sesión con `SSL_CERT_FILE` apuntando a `certifi`, sin cambiar código ni datos.
4. La identificabilidad pesa sobre todo en la comparación de estrategias. Las tres tendencias producen el mismo ajuste de entrenamiento, pero la ventaja de la candidata vale +1.007, +0.075 y −0.857 s. Ver `docs/validacion_experimentos.md`.
