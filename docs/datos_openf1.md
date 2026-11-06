# Ficha de la fuente de datos: OpenF1 (MA-01)

**Responsable:** Mario Fernando Rocha. **Revisión pendiente:** Luis Pedro Lira (ver sección 8).
**Fecha de consulta de fuente y descarga:** 2026-11-06 (America/Guatemala).
**Estado:** borrador para revisión. Esta ficha describe y verifica los datos; **no** aplica el filtro de calidad (MA-02) ni congela la partición (MA-03).

## 1. Fuente y condiciones de uso

| Aspecto | Dato verificado | Dónde se verificó |
|---|---|---|
| Proveedor | OpenF1, API pública de datos de F1 en JSON/CSV | https://openf1.org/docs/ |
| Carácter | No oficial: *"OpenF1 is an unofficial project and is not associated in any way with the Formula 1 companies."* | https://openf1.org/docs/ |
| Licencia | **CC BY-NC-SA 4.0** (pie del sitio: *"Licensed under CC BY-NC-SA 4.0"*; archivo `LICENSE` del repo `br-g/openf1`: *Attribution-NonCommercial-ShareAlike 4.0 International*) | https://openf1.org/ y https://github.com/br-g/openf1 |
| Acceso | Datos históricos desde 2023 gratis y sin autenticación | https://openf1.org/docs/ |
| Límite gratuito | *"Up to 3 requests per second and 30 requests per minute"* | https://openf1.org/ |
| Restricción en vivo | **Durante una sesión de F1 en vivo, todo acceso sin cuenta, incluido el histórico, responde 401.** Observado el 2026-11-06: *"Live F1 session in progress. Global API access (including past sessions) is restricted to authenticated users until the session ends."* | Respuesta real de `api.openf1.org` |
| Marcas | Las marcas de F1 pertenecen a Formula One Licensing B.V. | https://openf1.org/docs/ |
| Página de términos de uso | No se encontró una página específica de términos | Revisados openf1.org, /docs y el repo |

**Implicaciones para el proyecto (interpretación del equipo, no asesoría legal):**

- El uso es académico y no comercial, compatible con *NonCommercial*.
- *Attribution*: el informe y el README deben citar OpenF1 como fuente, indicar la licencia y aclarar que no es fuente oficial.
- *ShareAlike*: si se redistribuyen datos o tablas derivadas (por ejemplo, CSV en el repo o en la entrega), van bajo la misma licencia y con atribución. Por eso `data/raw/` y `data/processed/` siguen fuera de Git y cada clon los regenera. La evidencia en `docs/evidence/` solo contiene metadatos, conteos, stints/pits y huellas.
- **Riesgo de reproducibilidad:** si el catedrático o un compañero ejecuta `python main.py download` durante un fin de semana de F1, la descarga puede fallar con 401. Para la demo y la entrega conviene tener la caché `data/raw/openf1/` preparada (la descarga la reutiliza sin red si los URL coinciden) y verificar sus huellas portables (sección 3).

## 2. Caso descargado

| Campo | Valor |
|---|---|
| Evento | Gran Premio de Bahréin 2024, carrera (`session_name = Race`) |
| `session_key` / `meeting_key` | 9472 / 1229 |
| Circuito | Sakhir (`circuit_key = 63`), BRN, `gmt_offset = 03:00:00` |
| Horario programado de la sesión (UTC) | 2024-03-02 15:00 → 17:00 |
| Piloto | Max Verstappen, VER, número 1 |
| Referencia oficial | FIA, 57 vueltas, 1:31:44.742 = 5504.742 s (`configs/case_bahrain_2024.json`) |

## 3. Adquisición reproducible

Comando: `python main.py download` (Python 3.12, solo biblioteca estándar para OpenF1). Solicitudes realizadas:

```text
https://api.openf1.org/v1/sessions?year=2024&country_name=Bahrain&session_name=Race
https://api.openf1.org/v1/laps?session_key=9472&driver_number=1
https://api.openf1.org/v1/stints?session_key=9472&driver_number=1
https://api.openf1.org/v1/pit?session_key=9472&driver_number=1
https://api.openf1.org/v1/weather?session_key=9472
https://api.openf1.org/v1/race_control?session_key=9472
```

Descarga por red el 2026-11-06 a las 13:53–13:54 UTC. El reporte de evidencia (`docs/evidence/openf1_acquisition_mario_2026-11-06.json`) se regeneró con esa misma caché, por eso sus solicitudes aparecen como `cached: true`.

### Huellas portables (SHA-256 con saltos de línea normalizados)

| Archivo crudo | `sha256_portable` |
|---|---|
| `laps.json` | `4c2f8ab9d7dc3a95d92c0840069e81c3622377e5cf553fe254942097464a1a36` |
| `pit.json` | `3bb392bedc3b99b38e8bbc2ed65c2d5dac587b948f6e21c14abde208546ee445` |
| `race_control.json` | `6ef4044aae74d87fb314672cd6eeaaf7c9ef240a71bf686be04101395edc6c55` |
| `sessions.json` | `dd852c09c5f9b1fc933ee80aa281c2ed5a12f6c4ffd1ed1359f3c42d661532e6` |
| `stints.json` | `9e973c322a32aa15690a4a78a0e40daf2116d36272e32dfc18e3f57353d3f24d` |
| `weather.json` | `a41e2ad079ecc3c4d5974b4bc483b0d3cb2ed53575cdb071f3303e32904af9b8` |

**Por qué existe la huella portable.** El código guarda los JSON con `write_text`, que en Windows escribe saltos de línea CRLF y en macOS/Linux LF. El mismo contenido produce entonces bytes y `sha256` distintos según el sistema. La descarga del 2026-11-06 en macOS dio seis huellas distintas a las de la evidencia del 2026-11-05 (Windows). Al convertir LF→CRLF los archivos de macOS, las seis coincidieron exactamente con las de Ihan: **el contenido es idéntico byte a byte salvo los saltos de línea**. `src/data.py::portable_sha256` convierte CRLF→LF antes de calcular y da el mismo valor en cualquier sistema. El reporte de descarga conserva `sha256` (dependiente del sistema, compatible con la evidencia anterior) y añade `sha256_portable`. La evidencia de Ihan (`docs/evidence/openf1_acquisition.json`) no se modificó. Pruebas: `tests/test_portable_hash.py`.

## 4. Diccionario de datos crudos

Definiciones citadas o resumidas de https://openf1.org/docs/. Los rangos y nulos se midieron en los archivos descargados.

### `laps` (57 filas, una por vuelta de VER)

| Campo | Tipo | Unidad | Definición | Nulos | Observado | Uso |
|---|---|---|---|---:|---|---|
| `lap_number` | int | vuelta | Número secuencial de vuelta | 0 | 1–57, sin huecos ni duplicados | Clave |
| `lap_duration` | float | s | Tiempo total de la vuelta | 0 | 92.608 (v39) – 117.854 (v18) | Variable principal |
| `duration_sector_1/2/3` | float | s | Tiempo de cada sector | 0 | S1 29.741–52.815; S2 39.916–42.187; S3 22.951–26.830 | Control de consistencia |
| `date_start` | str ISO 8601 | UTC | Inicio de la vuelta; **la documentación lo declara aproximado** | 0 | 15:03:42.341 (v1) → 16:33:52.694 (v57) | Cruce con control de carrera y clima |
| `is_pit_out_lap` | bool | — | Vuelta de salida de pits | 0 | True en 18 y 38 | Exclusión del ajuste normal |
| `i1_speed`, `i2_speed`, `st_speed` | int | km/h | Velocidad en intermedios y trampa | 23 / 0 / 11 | 230–239 / 242–270 / 212–314 | No se usa |
| `segments_sector_1/2/3` | lista int | código | Minisectores (2048 amarillo, 2049 verde, 2051 morado, 2064 pit lane, 0 no disponible) | 0 | Presentes, aunque la documentación dice que no están disponibles en carreras | No se usa (semántica no confiable en carrera) |
| `driver_number`, `session_key`, `meeting_key` | int | — | Identificadores | 0 | 1 / 9472 / 1229 | Claves |

### `stints` (3 filas)

| `stint_number` | `compound` | `lap_start` | `lap_end` | `tyre_age_at_start` |
|---:|---|---:|---:|---:|
| 1 | SOFT | 1 | 17 | 3 |
| 2 | HARD | 18 | 37 | 0 |
| 3 | SOFT | 38 | 57 | 0 |

`tyre_age_at_start`: *"The age of the tyres at the start of the stint, in laps completed."* `lap_end`: *"Number of the last completed lap in this stint."*

### `pit` (2 filas)

| `lap_number` | `date` (UTC) | `lane_duration` (s) | `pit_duration` (s) | `stop_duration` (s) |
|---:|---|---:|---:|---|
| 17 | 2024-03-02 15:31:37.825 | 25.0 | 25.0 | nulo |
| 37 | 2024-03-02 16:03:54.529 | 24.2 | 24.2 | nulo |

- `lane_duration`: tiempo dentro del pit lane. **No es la pérdida adicional respecto de seguir en pista** (eso se estima aparte, JO-02).
- `stop_duration`: tiempo detenido. Viene nulo en ambas paradas y no se imputa.
- `pit_duration`: según la documentación es igual a `lane_duration` y se eliminará al final de la temporada 2026. Usar `lane_duration`.

### `weather` (157 filas, ~1 por minuto)

| Campo | Unidad | Observado (toda la ventana) |
|---|---|---|
| `air_temperature` | °C | 17.6–18.9 |
| `track_temperature` | °C | 21.9–26.5 |
| `humidity` | % | 45–51 |
| `pressure` | mbar | 1016.9–1017.5 |
| `rainfall` | indicador | **0 en las 157 muestras** |
| `wind_speed` | m/s | 0.0–2.1 |
| `wind_direction` | ° | 0–356 |

Ventana: 14:03:56 → 16:39:56 UTC. 90 muestras caen entre el inicio de la vuelta 1 y el de la vuelta 57.

### `race_control` (71 filas, toda la sesión)

Campos: `date` (UTC), `lap_number`, `category`, `flag`, `scope` (`Track`/`Sector`/`Driver`), `sector` (minisector), `driver_number`, `message`. Ventana 14:06:41 → 16:38:38 UTC.

| Categoría | Filas | | Bandera | Filas |
|---|---:|---|---|---:|
| Flag | 37 | | BLUE | 26 |
| Other | 28 | | CLEAR | 4 |
| Drs | 2 | | GREEN | 2 |
| SessionStatus | 2 | | DOUBLE YELLOW | 2 |
| CarEvent | 2 | | YELLOW | 1 |
| SafetyCar | **0** | | CHEQUERED / BLACK AND WHITE | 1 / 1 |

No aparece ningún mensaje en la categoría `SafetyCar`. Las amarillas (3) y su efecto sobre vueltas de VER se analizan en MA-02; no se concluye nada aquí.

## 5. Tabla normalizada derivada

`data/raw/openf1_target_laps.csv` (57 filas), generada por `src/openf1_data.py::normalize_laps`. Columnas con contenido:

| Columna | Origen | Unidad / convención |
|---|---|---|
| `lap_number`, `driver`, `driver_number` | `laps` + configuración | — |
| `lap_time_s` | `laps.lap_duration` | s |
| `stint`, `compound` | `stints` (vuelta dentro de `lap_start..lap_end`) | — |
| `tyre_life_laps` | `tyre_age_at_start + lap_number − lap_start + 1` | **vueltas acumuladas por el juego al terminar esa vuelta** (v1 = 4, v18 = 1, v38 = 1) |
| `fresh_tyre` | `tyre_age_at_start == 0` | stint 1 False, stints 2–3 True |
| `is_pit_in_lap` | `lap_number` presente en `pit` | True en 17 y 37 |
| `is_pit_out_lap` | `laps.is_pit_out_lap` | True en 18 y 38 |
| `date_start_utc` | `laps.date_start` | UTC, aproximado |

Las columnas `pit_in_time_s`, `pit_out_time_s`, `session_time_s`, `lap_start_time_s`, `track_status`, `deleted`, `is_accurate` y `fastf1_generated` existen por compatibilidad con FastF1, pero **OpenF1 no las provee y quedan vacías**. No se rellenan.

**Convención de edad (para JO-01/JO-02):** `tyre_life_laps` cuenta la vuelta en curso como completada. `TyreStint.initial_age` en `src/domain.py` se define como "vueltas completadas antes del stint", igual que `tyre_age_at_start`. El simulador aplica la misma regla: suma 1 antes de calcular el tiempo de cada vuelta (`src/simulation.py`, línea 42: *"Edad al terminar la vuelta, coherente con TyreLife"*). Jonathan debe mantenerla si cambia el modelo.

## 6. Cobertura y comprobaciones de consistencia

Ejecutadas el 2026-11-06 sobre los archivos de la sección 3:

| Comprobación | Resultado |
|---|---|
| Vueltas presentes | 57 de 57, numeradas 1–57, sin duplicados |
| Tiempos de vuelta faltantes | 0 |
| Suma de sectores vs `lap_duration` | Diferencia máxima 0.000 s en las 57 vueltas |
| Cobertura de stints | 17 + 20 + 20 = 57 vueltas, sin solapes ni huecos |
| Paradas | Entradas en 17 y 37; salidas marcadas en 18 y 38, consistentes |
| Vueltas más lentas | 18 (117.854, salida de pits), 38 (116.445, salida), 17 (99.896, entrada), 37 (99.234, entrada), 1 (97.759, arranque), 9 (97.229, **sin motivo evidente aún: revisar en MA-02**) |
| Vuelta más rápida | 39, 92.608 s (SOFT nuevo, edad 2) |
| `date_start[n+1] − date_start[n] − lap_duration[n]` | Entre −0.228 y +0.325 s. Coherente con que `date_start` es aproximado: **no sirve para conciliar diferencias por debajo de ~0.5 s** |
| Lluvia | 0 en toda la ventana: carrera seca |
| Safety Car / VSC | Sin mensajes de categoría `SafetyCar` |
| Suma de `lap_duration` | 5505.217 s; FIA 5504.742 s; diferencia **+0.475 s pendiente (MA-02)** |
| Igualdad con la descarga del 2026-11-05 | Mismos conteos, suma y contenido (ver sección 3) |

Cobertura por compuesto para el modelo: SOFT con edades 4–20 (stint 1, juego usado) y 1–20 (stint 3, juego nuevo); HARD con edades 1–20 (stint 2). Un solo stint de HARD; ver hallazgo 7 del plan sobre identificabilidad antes de MA-03.

## 7. Limitaciones conocidas de la fuente

1. OpenF1 no da banderas de calidad por vuelta equivalentes a `IsAccurate`, `Deleted` o `TrackStatus` de FastF1. El filtro propio se construye en MA-02 con `race_control`, `pit` y comprobaciones internas.
2. `date_start` es aproximado (±0.3 s observado). Los cruces con `race_control` deben tolerar ese margen.
3. `stop_duration` no está disponible para este caso.
4. No hay datos de combustible, modos de motor ni inventario de neumáticos por piloto. El inventario se trata en MA-05.
5. La fuente no es oficial. Las comparaciones contra el total FIA deben reconciliar convenciones antes de interpretarse.
6. La disponibilidad depende de que no haya una sesión en vivo (sección 1).

## 8. Revisión de Luis Pedro (pendiente)

- [ ] Reproduce `python main.py download` (o usa la caché compartida) y obtiene las mismas `sha256_portable`.
- [ ] Confirma diccionario, unidades y convención de `tyre_life_laps`.
- [ ] Revisa la interpretación de licencia y la nota sobre redistribución.
- [ ] Observaciones / fecha / commit de revisión: ______
