# Filtro de calidad propio de OpenF1 (MA-02)

**Responsable:** Mario Fernando Rocha. **Revisión pendiente:** Luis Pedro Lira (LP-01).
**Fecha:** 2026-11-06. **Versión del filtro:** `openf1-v1`.
**Código:** `src/openf1_quality.py`. **Pruebas:** `tests/test_openf1_quality.py`.
**Evidencia:** `docs/evidence/openf1_exclusiones.csv` (motivo por vuelta), `docs/evidence/openf1_filtro_calidad.json` (reglas, conteos, intervalos de banderas, cobertura).
**Regenerar:** `python main.py download` (usa la caché `data/raw/openf1/` si existe) → `data/processed/openf1_target_laps_annotated.csv`, `data/processed/openf1_exclusions.csv`, `results/data_audit/openf1_quality_filter.json`.

## 1. Por qué hacía falta

El filtro inicial exigía las banderas `IsAccurate` y `TrackStatus` de FastF1. OpenF1 no las tiene, así que marcaba las **57 vueltas como no elegibles**. El filtro nuevo no inventa esas banderas (siguen vacías). Las sustituye con evidencia del propio proveedor: mensajes de control de carrera, registro de pits y clima. Deja escrito el motivo de cada decisión.

**Principio:** el filtro **no borra** ninguna vuelta. Solo indica cuáles entran al ajuste de vueltas normales (MA-04). Las 57 siguen disponibles para reconstruir la carrera completa y para la validación.

## 2. Reglas

Decididas antes de calibrar. Ninguna se eligió mirando errores del modelo.

| Código | Efecto | Regla |
|---|---|---|
| `first_lap` | Excluye | Vuelta 1: **cuenta en la carrera y en la reconstrucción**; solo se excluye del ajuste del ritmo normal porque empieza con salida desde parado al apagarse los semáforos. Esa pérdida se modela aparte como penalización de arranque (JO-02). La vuelta de formación no forma parte de los datos. Evidencia: `date_start` de la vuelta 1 (15:03:42.341 UTC) coincide con *"SESSION STARTED"* de control de carrera (15:03:42). |
| `pit_in_lap` | Excluye | Vuelta registrada en `pit`. |
| `pit_out_lap` | Excluye | `is_pit_out_lap = True`. |
| `time_deleted_race_control` | Excluye | Mensaje de control de carrera `CAR <n> (...) TIME ... DELETED ... LAP <k>` para el piloto objetivo. Es el equivalente reconstruido de `Deleted` de FastF1. `(NEXT LAP)` se resuelve como la vuelta siguiente al último borrado del mismo auto. |
| `track_neutralization` | Excluye | La vuelta coincide con Safety Car/VSC (`category = SafetyCar` con `DEPLOYED`), bandera roja o amarilla de pista completa. Se cierra solo con `GREEN`/`CHEQUERED` de pista; `GREEN LIGHT - PIT EXIT OPEN` **no** la cierra, porque solo abre la salida de pits. Si nunca se cierra, se extiende hasta el final (conservador). |
| `rainfall` | Excluye | Muestra de clima con `rainfall > 0` durante la vuelta o en los 60 s previos (el clima se muestrea cada ~1 min). |
| `missing_or_invalid_*`, `unsupported_or_unknown_compound`, `missing_lap_window` | Excluye | Faltan datos necesarios. Nunca se imputan. |
| `local_yellow_overlap` | Advierte | Amarilla de un solo sector activa durante la vuelta. No excluye: es local, puede no coincidir con el paso del piloto y no hubo pérdida medible (sección 4). |
| `unpaired_clear_in_lap` | Advierte | `CLEAR` de sector sin amarilla previa registrada: posible amarilla no publicada en el feed. |
| `deleted_time_mismatch` | Advierte | El tiempo citado en el mensaje de borrado no coincide con `lap_duration`. |

**Margen temporal:** `date_start` de OpenF1 es aproximado (±0.3 s observado, ficha MA-01). Cada vuelta se amplía ±1.0 s al cruzarla con eventos.

**No se usa:**
- **Atípicos estadísticos.** No se excluyen. Las vueltas 39–40 son comportamiento real (sección 4), y fijar un umbral después de ver los datos no es defendible.
- **Banderas azules.** Ninguna fue para VER (#1). Las que muestran a otros pilotos no permiten saber de forma verificable si VER perdió tiempo al doblar.

## 3. Resultado en Bahréin 2024, VER

**51 de 57 vueltas elegibles** (el filtro anterior daba 0).

| Vuelta | Decisión | Motivo | Evidencia |
|---:|---|---|---|
| 1 | Excluida solo del ajuste (cuenta en la carrera) | `first_lap` | Salida desde parado; 97.759 s frente a 96.296 s de la vuelta 2. También doble amarilla sector 2, 15:03:59–15:04:03 y 15:04:29–15:04:36 UTC |
| 2 | Elegible, advertencia | `unpaired_clear_in_lap` | `CLEAR IN TRACK SECTOR 4` a las 15:05:55 sin amarilla previa; coincide con el trompo de STR (#18) en T1 y "superficie resbaladiza en sector 4" |
| 10, 11 | Elegibles, advertencia | `local_yellow_overlap` | `YELLOW IN TRACK SECTOR 4`, 15:19:07–15:19:58 UTC |
| 17, 37 | Excluidas | `pit_in_lap` | Registro `pit` |
| 18, 38 | Excluidas | `pit_out_lap` | `is_pit_out_lap` |
| 46 | Excluida | `time_deleted_race_control` | *"CAR 1 (VER) TIME 1:34.193 DELETED - TRACK LIMITS AT TURN 4 LAP 46"*. El tiempo citado (94.193 s) coincide exactamente con `lap_duration` de la vuelta 46: **OpenF1 y control de carrera numeran las vueltas igual** |

Sin Safety Car, VSC, bandera roja ni lluvia en esta carrera. Las reglas quedan implementadas y probadas con casos construidos (`tests/test_openf1_quality.py`).

**Cobertura elegible** (base para MA-03):

| Stint | Compuesto | Vueltas elegibles | Rango de vueltas | Edad del neumático |
|---:|---|---:|---|---|
| 1 | SOFT (usado) | 15 | 2–16 | 5–19 |
| 2 | HARD (nuevo) | 18 | 19–36 | 2–19 |
| 3 | SOFT (nuevo) | 18 | 39–57, sin 46 | 2–20 |

**Nota sobre la vuelta 46:** el borrado afecta récords de vuelta, no el tiempo de carrera. La vuelta **sí** cuenta para la suma total y la reconstrucción. Solo se excluye del ajuste porque cortar en T4 la hace no representativa del ritmo normal.

## 4. Observaciones e hipótesis (no comprobadas)

- **Vuelta 9 (97.229 s):** en la ficha MA-01 se señaló como "sin motivo evidente". Revisada: está 0.20 s sobre la mediana de las vueltas 2–16 (+0.12 S1, +0.11 S2, +0.03 S3), dentro de la variación normal del stint (las vueltas 5 y 16 son similares). **No es una anomalía.**
- **Vueltas 10–11 con amarilla:** 96.960 y 97.085 s, normales. La amarilla se retiró justo cuando VER cruzaba meta. No hubo pérdida medible.
- **Vuelta 39 (92.608 s, vuelta rápida de la carrera) y 40 (96.589 s):** comportamiento normal de carrera. Con SOFT nuevo el agarre máximo está en la primera vuelta lanzada; VER empujó (la vuelta rápida daba un punto en 2024) y después aflojó. No es error de datos y no se excluye.
- **Vueltas 41–46, tiempos que bajan (95.29 → 94.19 s):** contrario a lo que haría solo el desgaste. **Hipótesis**, que con estos datos no se pueden separar (OpenF1 no trae temperatura de neumáticos ni combustible):
  1. Gestión del piloto, que recupera ritmo tras enfriar los neumáticos en la vuelta 40.
  2. Menos combustible. Orden de magnitud por verificar y citar si se usa: ~0.03 s/kg y ~1.6 kg/vuelta, unos 0.3 s en seis vueltas.
  3. Asentamiento del neumático (*graining* inicial que se limpia).
  4. Pista más fría: 22.4 → 22.1 °C en ese tramo, en una carrera al atardecer.
  5. Tráfico: **descartado** como explicación principal, porque hay pocas banderas azules entre 41 y 46 y ninguna es para VER.
- **Ritmo administrado:** VER lideró con amplia ventaja. Sus tiempos no representan necesariamente el ritmo máximo. Debe declararse como limitación del modelo.
- **Tendencia de pista:** la temperatura de pista baja de 23.8 a 21.9 °C durante la carrera. Se confunde con el combustible en la "tendencia de carrera" (hallazgo 7 del plan; ver MA-03).

## 5. Revisión de Luis Pedro (pendiente)

- [ ] Las reglas de la sección 2 son aceptables y se fijaron antes de calibrar.
- [ ] La tabla `docs/evidence/openf1_exclusiones.csv` coincide con lo que obtiene al regenerar.
- [ ] De acuerdo con no excluir atípicos ni amarillas locales.
- [ ] Observaciones / fecha / commit de revisión: ______
