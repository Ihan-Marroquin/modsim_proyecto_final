# Guion de la exposición (LG-04) — 15 minutos

Reparto del plan (sección 8): Mario 2 min, Jonathan 2 min, Ihan 3 min, Luis Gilberto 3 min (demo), Luis Pedro 3 min, 2 min compartidos. Cada cifra de las diapositivas tiene su fuente al lado; no se agrega ningún número que no esté en `docs/evidence/` o en los documentos técnicos.

| # | Diapositiva | Expone | Tiempo | Contenido | Fuente |
|---|---|---|---:|---|---|
| 1 | Portada | Mario | 0:15 | Título, equipo, caso VER Bahréin 2024 | — |
| 2 | Pregunta y alcance | Mario | 0:45 | ¿Qué paradas y neumáticos minimizan el tiempo esperado? Un piloto, seco, 1–2 paradas; sin tráfico ni Safety Car | Plan §1 |
| 3 | Datos | Mario | 1:00 | OpenF1 (CC BY-NC-SA), 57 vueltas, paradas 17 y 37; FIA 5504.742 s; +0.475 s solo en la vuelta 1; 51/57 elegibles; partición: 33 entrenamiento, 18 validación (stint 3) | `docs/datos_openf1.md`, `docs/conciliacion_tiempos.md`, `docs/particion_validacion.md` |
| 4 | Modelo | Jonathan | 1:00 | `t = b_c + d_c·edad·μ + g·(vuelta−1)` + arranque + pérdida de pits; diagrama de estados | `docs/modelo_simulacion.md` §1–2 |
| 5 | Calibración e identificabilidad | Jonathan | 1:00 | Tabla de parámetros; rango 4 de 5 → tendencia fija −0.0444 s/vuelta (TUM) con sensibilidad 0 y −0.0888 | `docs/calibracion.md` §3, `docs/particion_validacion.md` §3 |
| 6 | Recocido simulado | Ihan | 1:30 | Representación, vecinos, Metropolis, enfriamiento geométrico; 1323 estrategias de 2 paradas, 0 de 1 | `docs/tecnica_recocido.md` |
| 7 | Verificación del recocido | Ihan | 1:30 | Figura 5: 29/30 búsquedas al óptimo de la enumeración; candidata 17/36 SOFT→SOFT→HARD | `docs/evidence/optimization/summary.json` |
| 8 | Demo en vivo | Luis Gilberto | 2:30 | `simulate` → `optimize` → `compare` (×1.00 y ×1.20) → `experiments` | `presentation/demo.md` |
| 9 | Cronograma de stints | Luis Gilberto | 0:30 | Figura 2: dónde gana y pierde la candidata | `vueltas_deterministas.csv` |
| 10 | Validación | Luis Pedro | 1:00 | Figura 1 y tabla: MAE 0.712, sesgo +0.456, acumulado +8.203 s; reconstrucción +9.957 s no es validación | `docs/validacion_experimentos.md` §4 |
| 11 | Experimentos A/B/C/D | Luis Pedro | 1:00 | Figura 3: A−B +0.0750 s, C−D −0.0624 s; por qué la diferencia pareada es constante | §5.2 |
| 12 | Sensibilidad e incertidumbre | Luis Pedro | 1:00 | Figura 4: equilibrio ×1.109; +1.007 / +0.075 / −0.857 s según tendencia; EE 0.128 s | §5.3–5.4 |
| 13 | Conclusión | Todos | 1:00 | No se detectó una mejora robusta; la ventaja es ~110 veces menor que el error de validación | §5.6 |
| 14 | Limitaciones y trabajo futuro | Todos | 0:30 | Ruido i.i.d., tendencia no identificable, validación pequeña, inventario inferido, HARD edad 21 | §6 |
| 15 | Preguntas | Todos | 1:00 | Respuestas cortas en `presentation/demo.md` | — |

**Total:** 15:00.

## Reglas para quien expone

- Decir siempre «simulado» al hablar de la candidata; nunca «habría ganado» ni «la estrategia óptima de la carrera».
- Signos: `mejora_s = base − candidata` (positivo: candidata más rápida) y `error = predicho − observado` (positivo: el modelo es más lento).
- Si preguntan algo fuera del guion, contestar con la fuente (documento y sección) en vez de improvisar cifras.

## Ensayo

- [ ] Martes 10: ensayo completo cronometrado con los cinco integrantes (EQ-04).
- [ ] Grabar la demo como respaldo.
- [ ] Miércoles 11: revisión final de diapositivas contra el informe.
