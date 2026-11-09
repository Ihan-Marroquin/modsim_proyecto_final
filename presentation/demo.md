# Demo en vivo (LG-02) — 3 minutos, Luis Gilberto

Todo corre sin internet en menos de 2 s por comando (medido el 2026-11-08 en Windows, Python 3.14, `.venv` con `requirements.txt`). Las cifras esperadas salen de esas ejecuciones y coinciden con `docs/evidence/`.

## Antes de exponer

```bash
python -m unittest discover -s tests          # esperado: OK
python main.py download                       # solo si hay internet; deja la caché lista
python main.py reconcile
python main.py partition
python main.py validate
python main.py figures                        # report/figures/fig1..fig5
```

Si OpenF1 responde 401 (pasa durante sesiones de F1 en vivo) o no hay red, la demo sigue igual: solo la Figura 1 necesita la descarga, y su imagen ya queda generada en `report/figures/` y en el informe PDF.

## Guion de la demo

| Paso | Comando | Qué decir | Qué debe aparecer |
|---|---|---|---|
| 1. Cargar el caso y simular la base | `python main.py simulate` | El simulador corre las 57 vueltas de VER con los parámetros calibrados solo con entrenamiento. | `total_simulated_time_s: 5514.6992`, `official_reference_time_s: 5504.742`, diferencia +9.9572 s |
| 2. Optimizar | `python main.py optimize` | Pilotos, enumeración de 1323 estrategias y 30 búsquedas del recocido. | `feasible_by_stops: {"1": 0, "2": 1323}`, `search_runs_at_reference: 29`, candidata `[17, 36]` |
| 3. Comparar | `python main.py compare` | Histórica contra candidata congelada, mismo modelo y restricciones. | `mejora_s: 0.075` |
| 4. Robustez | `python main.py compare --degradation-multiplier 1.2` | Con 20 % más degradación la ventaja se invierte. | `mejora_s: -0.0624` |
| 5. Experimentos | `python main.py experiments` | 30 réplicas por condición con semillas reservadas 3300–3329. | medias A 5514.81, B 5514.735, C 5525.5294, D 5525.5919; A−B 0.075, C−D −0.0624 |
| 6. Cerrar con figuras | abrir `report/figures/fig4_sensibilidad.png` | El signo depende de la tendencia y la degradación: no hay mejora robusta. | Cruce en ×1.109 y tres líneas de tendencia |

## Respaldo si algo falla

- Resultados precalculados versionados: `docs/evidence/optimization/` (candidata, búsquedas, traza) y `docs/evidence/experiments/` (120 réplicas, pares, sensibilidad, resumen).
- `optimize` y `experiments` regeneran archivos idénticos a esos (salvo fin de línea), así que mostrar el CSV versionado es equivalente.
- Figuras ya generadas en `report/figures/` y en el PDF del informe.
- Captura de pantalla o grabación corta de los pasos 1–5 (hacerla el martes 10 durante el ensayo).

## Preguntas probables y respuesta corta

| Pregunta | Respuesta (fuente) |
|---|---|
| ¿Por qué 30 de 30 réplicas favorecen a B si la ventaja es tan pequeña? | Porque comparten semilla y el ruido se cancela; la diferencia es determinista. No es evidencia estadística (`docs/validacion_experimentos.md` §5.2). |
| ¿Validaron con datos que el modelo no vio? | Sí: stint 3 reservado antes de calibrar. MAE 0.712 s, sesgo +0.456 s, acumulado +8.203 s (§4.1). |
| ¿Por qué no estimaron la tendencia? | No es identificable con un stint por compuesto (rango 4 de 5); se fijó con TUM y se hizo sensibilidad (`docs/particion_validacion.md` §3). |
| ¿Para qué el recocido si la enumeración cabe? | Aquí la enumeración sirve para verificarlo (29/30 al óptimo); el recocido escala cuando el espacio crece (`docs/tecnica_recocido.md`). |
| ¿Habría ganado más rápido Verstappen? | No se puede afirmar: la ventaja (0.075 s) es menor que su EE (0.128 s) y unas 110 veces menor que el error de validación. |
