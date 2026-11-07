# Calibración de parámetros reales (MA-04)

**Responsable:** Mario Fernando Rocha. **Revisión pendiente:** Luis Pedro Lira y Jonathan Zacarias (modelo, JO-01/JO-02).
**Fecha:** 2026-11-06. Jonathan aprobó en llamada fijar la tendencia con referencia externa y hacer sensibilidad.
**Código:** `src/calibration.py`. **Pruebas:** `tests/test_calibration.py`.
**Comandos:** `python main.py download`, `python main.py reconcile` y después `python main.py calibrate`. La partición no se regenera: se verifica contra la congelada.
**Salidas:** `configs/params_bahrain_2024.json` (parámetros para el simulador) y `docs/evidence/calibracion.json` (detalle, incertidumbre y auditoría de datos).

## 1. Modelo y protocolo

```
vuelta_normal = base_c + desgaste_c · edad + tendencia · (vuelta − 1)
vuelta 1      = vuelta_normal + penalización_arranque
pits          = una pérdida adicional por parada, sumada tras la vuelta de entrada
```

Las convenciones son idénticas a `src/simulation.py`:
- `edad` = vueltas del juego al terminar la vuelta.
- La pérdida de pits cubre el exceso de la vuelta de entrada **y** de la de salida sobre sus vueltas normales.

Una prueba (`test_losses_follow_simulator_convention_without_double_counting`) verifica que el simulador reproduce la suma observada sin contar dos veces la pérdida.

**Por qué la tendencia es fija:** con la partición congelada (un solo stint por compuesto) el modelo completo no es identificable (`docs/particion_validacion.md`, sección 3). Se estiman **base y desgaste por compuesto** (4 parámetros) con mínimos cuadrados ordinarios sobre `tiempo − tendencia·(vuelta − 1)`.

**Protocolo cumplido** (auditoría en `docs/evidence/calibracion.json`, sección `data_audit`):
- **Huella de la partición:** antes de leer datos se comprueba que `partition_split.csv` coincide con la huella congelada (`6dcb304d…`, commit `e989cf7`). Si no coincide, la calibración se detiene.
- **Tiempos leídos:** solo los de las 33 vueltas de entrenamiento, más la 1, la 17 y la 18 para el arranque y la primera parada. **Vueltas de validación leídas: ninguna.**
- **Validación:** no se calcula ninguna métrica. Le corresponde a LP-03, con estos parámetros ya congelados.

## 2. Tendencia de carrera: referencia y escenarios

| Escenario | Tendencia (s/vuelta) | Rol |
|---|---:|---|
| `trend_zero` | 0 | Sensibilidad: todo el cambio de ritmo se atribuye al neumático |
| **`trend_fuel_reference`** | **−0.0444** | **Principal**, preregistrado |
| `trend_double` | −0.0888 | Sensibilidad: combustible más evolución de pista de magnitud similar |

**Referencia:** −(0.023 s/kg × 1.93 kg/vuelta) = −0.0444 s/vuelta. Son los parámetros de Bahréin 2019 (también de 57 vueltas) del simulador de TUM: `racesim/input/parameters/pars_Sakhir_2019.ini`, campos `t_lap_sens_mass` y `b_fuel_perlap`, https://github.com/TUMFTM/race-simulation (LGPL-3.0). Descrito en Heilmeier, Graf y Lienkamp (2018), *A Race Simulation for Strategy Decisions in Circuit Motorsports*, IEEE ITSC, https://doi.org/10.1109/itsc.2018.8570012. Solo se toman dos números, no se reutiliza código.

**Limitaciones de la referencia:**
- Son autos de 2019, no de 2024.
- Solo representa el combustible: no incluye la evolución de la pista (goma acumulada; la pista se enfría de 23.8 a 21.9 °C).
- Antes de citarla en el informe hay que confirmar en el artículo la definición de ambos campos.

## 3. Resultados

### Escenario principal (`trend_fuel_reference`)

| Parámetro | Estimación | Error estándar | IC 95 % | Datos |
|---|---:|---:|---|---|
| SOFT base (s) | 96.414 | 0.153 | 96.084 – 96.744 | 15 vueltas (2–16), edades 5–19 |
| SOFT desgaste (s/vuelta) | 0.0761 | 0.0120 | 0.050 – 0.102 | |
| HARD base (s) | 95.652 | 0.067 | 95.511 – 95.793 | 18 vueltas (19–36), edades 2–19 |
| HARD desgaste (s/vuelta) | 0.1052 | 0.0057 | 0.093 – 0.117 | |
| Dispersión residual (s) | 0.163 | | | 33 vueltas, 29 grados de libertad |
| Penalización de arranque (s) | 0.566 | ≥ 0.16 (ruido de una vuelta) | | 1 observación |
| Pérdida adicional por parada (s) | 25.522 | ≥ 0.23 (ruido de dos vueltas) | | 1 observación (parada de la vuelta 17) |

`base` es el tiempo de un juego con edad 0 en la vuelta 1. Los intervalos usan t de Student con *n* − 2 grados de libertad por compuesto.

**Arranque:**
- Vuelta 1 con la convención oficial: 97.284 s (`docs/conciliacion_tiempos.md`).
- Vuelta normal predicha para SOFT con edad 4: 96.718 s. Diferencia: 0.566 s.
- La edad 4 está una vuelta por debajo del rango de entrenamiento (extrapolación mínima).
- Comparación: TUM 2019 usa 2.4 s (`t_loss_firstlap`). VER salió desde la pole y sin incidentes, y la definición de TUM puede no ser equivalente. No se ajusta para acercarse.

**Pits** (parada de la vuelta 17):
- Entrada: 99.896 s observados contra 97.226 s normales (SOFT edad 20).
- Salida: 117.854 s observados contra 95.002 s normales (HARD edad 1).
- Pérdida: 25.522 s.
- Comparaciones:
  - Tiempo en el pit lane según la FIA: 25.064 s. No es la misma magnitud (hallazgo 5 del plan).
  - Referencia de TUM 2019: ~22.9 s (`t_pitdrive_inlap` 3.359 + `t_pitdrive_outlap` 17.173 + detención mínima 1.9 + adicional del equipo ~0.4).
- La pérdida incluye la vuelta de salida con el HARD frío, porque el modelo no tiene un término de calentamiento.
- La segunda parada (37–38) se dejó **sin usar** para que LP-03 la use como comprobación independiente.

### Sensibilidad a la tendencia

| Escenario | SOFT base | SOFT desgaste | HARD base | HARD desgaste | Dispersión residual | Arranque | Pits |
|---|---:|---:|---:|---:|---:|---:|---:|
| `trend_zero` | 96.592 | 0.0317 | 94.941 | 0.0608 | 0.163 | 0.566 | 25.522 |
| **`trend_fuel_reference`** | **96.414** | **0.0761** | **95.652** | **0.1052** | 0.163 | 0.566 | 25.522 |
| `trend_double` | 96.236 | 0.1205 | 96.362 | 0.1496 | 0.163 | 0.566 | 25.522 |

**Lectura clave:**
- La dispersión residual, el arranque y la pérdida de pits son **idénticos** en los tres escenarios. Es la falta de identificabilidad funcionando: dentro de los stints de entrenamiento, cualquier tendencia predice exactamente lo mismo (prueba `test_trend_choice_does_not_change_training_predictions`). **Los datos de entrenamiento no pueden decidir cuál tendencia es la correcta.**
- La tendencia solo cambia cómo se reparte la pendiente entre desgaste y avance de carrera, y por eso **cambia las predicciones de estrategias distintas a la histórica y del stint 3**. La incertidumbre por la tendencia hay que medirla en los resultados de estrategia (LP-05), no en la calidad del ajuste.
- El R² por compuesto cambia entre escenarios solo porque cambia la variable ajustada. No sirve para comparar escenarios.
- **Prohibido por las reglas preregistradas:** elegir la tendencia según el error de validación.

## 4. Diagnóstico de residuos

| Compuesto | Dispersión (s) | Autocorrelación de orden 1 |
|---|---:|---:|
| SOFT | 0.200 | 0.21 |
| HARD | 0.125 | 0.00 |

El ruido del modo estocástico (`residual_sd_s` = 0.163 s) supone vueltas independientes y normales. En HARD es razonable. En SOFT hay una dependencia leve (0.21), así que los errores estándar del SOFT son algo optimistas. Se declara y no se modela.

## 5. Resultados contraintuitivos (no se corrigen)

1. **HARD con base más rápida que SOFT** en los escenarios cero y de referencia (95.65 contra 96.41). Solo con la tendencia doble se invierte (96.36 contra 96.24).
2. **HARD con más desgaste que SOFT** en los tres escenarios.

Causas posibles, sin verificar:
- La tendencia de referencia solo incluye combustible y no la evolución de la pista, que el stint 1 (más temprano) sufre más.
- VER administró el ritmo en el stint 1, con tráfico inicial y ventaja que cuidar.
- El SOFT del stint 1 era un juego usado de la clasificación.

**Consecuencia para la optimización:** con el escenario principal, el modelo puede favorecer estrategias con mucho SOFT. Hay que repetir la optimización con los tres escenarios. Cualquier conclusión que cambie entre escenarios no es robusta y debe reportarse así.

**Transparencia:** durante la revisión de datos (MA-02) el equipo vio todos los tiempos, incluido el stint 3, antes de congelar la partición. El valor de la tendencia **no** se eligió con esos tiempos: viene de una referencia externa y se fijó antes de calibrar.

## 6. Cómo usar los parámetros

```python
import json
from src.domain import parameters_from_dict
cfg = json.load(open('configs/params_bahrain_2024.json', encoding='utf-8'))
params = parameters_from_dict(cfg['parameters'])                                 # principal
sens = {k: parameters_from_dict(v) for k, v in cfg['sensitivity_parameters'].items()}
```

- **Jonathan (JO-02/JO-03):** pérdida de pits y arranque con la misma convención que `simulate`. Si cambias la convención (por ejemplo, separar entrada y salida), hay que recalcular ambas con `event_losses`.
- **Ihan (IH-05/IH-06):** el espacio de búsqueda principal está en `configs/tyre_inventory_bahrain_2024.json`. Las edades mayores a 20 son extrapolación del modelo.
- **Luis Pedro (LP-03/LP-05):**
  - Validación con los tres conjuntos preregistrados.
  - Comprobación de la pérdida de pits con la parada 37–38.
  - Reconstrucción completa aparte.
  - Experimentos A/B/C/D también con los parámetros de sensibilidad.

## 7. Revisión (pendiente)

- [ ] Luis Pedro: reproduce `python main.py calibrate`, obtiene los mismos parámetros y `validation_laps_read: []`.
- [ ] Jonathan: confirma convención de pits y arranque y el escenario principal de tendencia.
- [ ] Verificar en Heilmeier et al. (2018) la definición de `t_lap_sens_mass` y `b_fuel_perlap`.
- [ ] Observaciones / fecha / commit: ______
