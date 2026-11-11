# Conciliación de la diferencia de +0.475 s (MA-02)

**Responsable:** Mario Fernando Rocha. **Revisado por:** Luis Pedro Lira (2026-11-08).
**Fecha:** 2026-11-06.
**Código:** `src/reconciliation.py`. **Pruebas:** `tests/test_reconciliation.py`.
**Comando:** `python main.py download` y después `python main.py reconcile`.
**Evidencia:** `docs/evidence/conciliacion_tiempos.json`. La tabla por vuelta queda en `data/processed/lap_time_reconciliation.csv`, fuera de Git porque contiene tiempos de las fuentes.

## 1. Problema

La suma de los 57 `lap_duration` de OpenF1 para VER es **5505.217 s**. El tiempo oficial de carrera de la FIA es **1:31:44.742 = 5504.742 s**. La diferencia es de **+0.475 s**. El plan pedía no forzar la coincidencia ni atribuirla al modelo antes de reconciliar las fuentes.

## 2. Método

Se comparó cada vuelta de OpenF1 con una fuente independiente: **Jolpica**, la API pública compatible con Ergast, que publica tiempos por vuelta al milisegundo. Licencia de datos CC BY-NC-SA 4.0, uso no comercial, límite de 4 solicitudes/s y 500/hora (https://github.com/jolpica/jolpica-f1, `TERMS.md` y `docs/rate_limits.md`, consultados el 2026-11-06). Además se contrastaron el total y las paradas con la página de clasificación de la FIA.

Descartado antes de comparar: el redondeo a milisegundos de 57 vueltas puede acumular como máximo 57 × 0.0005 = 0.029 s. No explica 0.475 s.

## 3. Resultado

| Comprobación | Resultado |
|---|---|
| Vueltas comparadas | 57 de 57 |
| Vueltas idénticas al milisegundo | **56** (vueltas 2–57) |
| Única vuelta distinta | **Vuelta 1: OpenF1 97.759 s, Jolpica 97.284 s, diferencia +0.475 s** |
| Suma Jolpica | 5504.742 s = **tiempo oficial FIA exacto** |
| Suma de diferencias por vuelta | 0.475 s = toda la diferencia; residuo 0.000 s |
| Vuelta rápida (FIA, clasificación) | 1:32.608 en la vuelta 39 = OpenF1 vuelta 39 (92.608 s) |

**Conclusión:** la diferencia está **completamente localizada en la vuelta 1**. Las fuentes no discrepan en el ritmo de carrera, sino en **desde qué instante se cronometra la vuelta 1**. El tiempo oficial cuenta desde la señal de salida (apagado de semáforos). La suma de Jolpica coincide con él, así que su vuelta 1 sigue esa convención. La vuelta 1 de OpenF1 empieza 0.475 s antes.

**Inferencia (no confirmada por documentación de OpenF1):** el inicio de la vuelta 2 en OpenF1 es 15:05:20.099 UTC. Restando la vuelta 1 oficial (97.284 s), la señal de salida habría sido hacia las **15:03:42.8 UTC**. Como `date_start` es aproximado (±0.3 s), el margen es amplio. Es coherente con *"SESSION STARTED"* de control de carrera (15:03:42, con resolución de un segundo). OpenF1 no documenta cómo cronometra la vuelta 1, así que la causa exacta queda como **no verificada**.

**Lo que no se hizo:** no se modificó ningún dato de OpenF1, no se ajustó nada para que la suma coincida y no se atribuyó la diferencia al modelo. La coincidencia final resulta de comparar con una fuente independiente, no de corregir números.

## 4. Paradas en pits

| Parada | OpenF1 `lane_duration` | FIA / Jolpica `DURATION` |
|---:|---:|---:|
| Vuelta 17 | 25.0 s | **25.064 s** |
| Vuelta 37 | 24.2 s | **24.209 s** |

OpenF1 publica décimas y la FIA milésimas. La diferencia (≤0.064 s) es de precisión, no de convención.

**Observación para JO-02, no confirmada:** la FIA lista la parada a las 18:31:12 y 19:03:29 hora local (15:31:12 y 16:03:29 UTC, al segundo). OpenF1 da `date` 15:31:37.825 y 16:03:54.529 UTC. La separación es de ~25 s, más o menos la duración en pit lane, lo que sugiere que una marca es la entrada y la otra la salida. Ninguna fuente lo documenta: no usar sin confirmar.

Recordatorio: el tiempo en el pit lane **no** es la pérdida adicional frente a seguir en pista (hallazgo 5 del plan).

## 5. Decisiones para el resto del equipo

1. **Datos OpenF1 intactos.** `data/raw/openf1/` y la tabla normalizada conservan 97.759 s en la vuelta 1.
2. **Ajuste de ritmo normal (MA-04): sin efecto.** La vuelta 1 ya está excluida del ajuste (filtro MA-02) y las vueltas 2–57 son idénticas en ambas fuentes.
3. **Penalización de arranque (JO-02, Jonathan):** usar la vuelta 1 con la convención oficial, **97.284 s** (Jolpica, coherente con el total FIA), tomada de `data/processed/lap_time_reconciliation.csv`. Con el valor de OpenF1 la penalización saldría **0.475 s mayor** de lo real.
4. **Comparación contra el tiempo oficial (LP-03, Luis Pedro):** la referencia observada es **5504.742 s** (FIA). Para comparar sumas por vuelta con ese total, la vuelta 1 debe seguir la convención oficial. Informar que OpenF1 por sí solo suma 5505.217 s y por qué.
5. **Pérdida en pits (JO-02):** si se usa el tiempo en pit lane como insumo, preferir los valores de la FIA (25.064 y 24.209 s) y citar la fuente.

## 6. Limitaciones

- La causa exacta de los 0.475 s en OpenF1 no está documentada por el proveedor. Solo se sabe dónde está la diferencia y qué fuente coincide con el total oficial.
- Jolpica es un proyecto voluntario sin garantía de exactitud (sus términos lo dicen). Su respaldo aquí es que su suma coincide exactamente con el total FIA y su vuelta rápida con la clasificación FIA.
- No se obtuvo el PDF oficial *Race Lap Analysis* de la FIA con la vuelta 1 de VER: la página de clasificación no lo enlaza. Si alguien lo consigue, conviene contrastar la vuelta 1 (esperado: 1:37.284).

## 7. Revisión de Luis Pedro

- [x] Reproduce `python main.py reconcile` y obtiene una sola vuelta distinta (la 1, +0.475 s). 56 de 57 vueltas coinciden, la suma de Jolpica es 5504.742 s y los pits son 25.0/25.064 s y 24.2/24.209 s.
- [x] De acuerdo con las decisiones 3 y 4 para JO-02 y LP-03. `src/validation.py` usa la vuelta 1 de 97.284 s y compara contra 5504.742 s. Además comprueba que las vueltas 2–57 de OpenF1 sean iguales a la referencia; si no lo son, se detiene.
- [x] Observaciones / fecha / commit: 2026-11-08, rama `luis-pedro/validacion`. La diferencia de 0.855 s en pit lane entre ambas paradas según la FIA (25.064 contra 24.209 s) coincide con la diferencia de pérdida que encontró LP-03 en la parada 37–38: la calibrada supera a la implícita en 0.848 s. Ver `docs/validacion_experimentos.md`.
