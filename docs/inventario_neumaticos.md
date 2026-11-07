# Inventario de neumáticos y espacio de estrategias (MA-05)

**Responsable:** Mario Fernando Rocha. **Coordinar con:** Ihan Marroquin (IH-05) y Jonathan Zacarias (JO-02). **Revisión pendiente:** Luis Pedro Lira.
**Fecha:** 2026-11-06. **Estado: inventario INFERIDO, no certificado.**
**Código:** `src/inventory.py`. **Pruebas:** `tests/test_inventory.py`. **Configuración:** `configs/tyre_inventory_bahrain_2024.json`.
**Comando:** `python main.py inventory` (después de `python main.py download`). **Evidencia:** `docs/evidence/inventario_neumaticos.json`.

## 1. Reglas aplicables (FIA, Reglamento Deportivo 2024, Issue 5, art. 30)

Fuente: https://api.fia.com/sites/default/files/fia_2024_formula_1_sporting_regulations_-_issue_5_-_2024-02-28.pdf (versión del 28-02-2024, anterior al GP del 02-03-2024).

| Artículo | Regla | Uso en el proyecto |
|---|---|---|
| 30.2a)ii y 30.2d)ii | Sin sprint (Bahréin 2024 no tuvo): **13 juegos de seco por piloto: 2 HARD, 3 MEDIUM, 8 SOFT** | Base de la reconstrucción |
| 30.5h)i | Un SOFT (especificación obligatoria de Q3) se reserva para Q3. Quien llega a Q3 devuelve un juego de esa especificación antes de la carrera | Explica por qué se devuelve un SOFT de la clasificación |
| 30.5h)ii | Dos juegos de las especificaciones obligatorias de carrera no se pueden devolver antes de la carrera | Explica los juegos nuevos que llegan a la carrera |
| 30.5h)iii–v | De los otros 10 juegos se devuelven 2 después de cada práctica libre (P1, P2, P3) | Explica por qué no llegan a la carrera los juegos de práctica |
| 30.5j | Pirelli publica la lista de juegos disponibles de cada piloto | **No se obtuvo**: por eso el inventario es inferido |
| 30.5l | En carrera seca: **al menos dos especificaciones distintas**, una de ellas obligatoria (30.2c)ii) | `min_distinct_compounds = 2` |

**Por verificar:** cuáles fueron las especificaciones obligatorias de carrera en Bahréin 2024 (se comunican en las notas del evento, art. 30.2c)ii). Con SOFT y HARD como únicos compuestos permitidos, toda estrategia factible incluye HARD. Hay que confirmar que HARD era obligatoria.

## 2. Reconstrucción del fin de semana de VER (OpenF1)

OpenF1 no identifica juegos físicos, solo stints con compuesto y edad inicial. Los juegos se infieren por **continuidad de edad**: un stint con edad inicial *k* continúa un juego del mismo compuesto que llevaba *k* vueltas.

| Sesión | Stints de VER (compuesto, vueltas, edad inicial) | Juegos nuevos usados |
|---|---|---|
| Práctica 1 | MEDIUM 1–3 (0), MEDIUM 4–6 (3), MEDIUM 7–12 (0), MEDIUM 13–21 (6) | 2 MEDIUM (6 y 15 vueltas) |
| Práctica 2 | SOFT 1–6 (0), SOFT 7–9 (0), SOFT 10–25 (3) | 2 SOFT (6 y 19 vueltas) |
| Práctica 3 | HARD 1–6 (0), SOFT 7–13 (0), SOFT 14–16 (7) | 1 HARD (6), 1 SOFT (10) |
| Clasificación | SOFT ×6 stints: juegos de 6, 5, 3 y 3 vueltas | 4 SOFT |
| **Carrera** | SOFT usado (3) 1–17, HARD nuevo 18–37, SOFT nuevo 38–57 | 1 HARD, 1 SOFT |

**Juegos nuevos sin usar al empezar la carrera** (asignación menos juegos nuevos usados): **1 SOFT, 1 HARD y 1 MEDIUM.** Coinciden con la carrera real, que usó el HARD nuevo y el SOFT nuevo.

**Cuadre con las devoluciones obligatorias** (inferido): 13 juegos − 6 devueltos tras las prácticas − 1 SOFT devuelto tras la clasificación = **6 juegos disponibles para la carrera**: SOFT nuevo, HARD nuevo, MEDIUM nuevo y **3 de los 4 SOFT usados en la clasificación** (6, 5, 3 y 3 vueltas). Hay una ambigüedad en la Práctica 1: no se sabe a cuál de dos MEDIUM de 6 vueltas pertenece el último stint. No afecta los conteos.

## 3. Inventario hipotético común (el mismo para todas las estrategias)

No se sabe cuál de los 4 SOFT de la clasificación se devolvió. VER arrancó la carrera con uno de 3 vueltas, así que al menos uno de esos se conservó.

| Variante | Supuesto | Juegos para la carrera |
|---|---|---|
| **Principal** | Se devolvió el SOFT más usado (6 vueltas) | SOFT 0, HARD 0, SOFT 3, SOFT 3, SOFT 5 |
| Alternativa (sensibilidad) | Se devolvió uno de los SOFT de 3 vueltas | SOFT 0, HARD 0, SOFT 3, SOFT 5, SOFT 6 |

**MEDIUM queda excluido de la optimización.** VER sí tenía un juego nuevo, pero **ningún piloto usó MEDIUM en la carrera**, así que no hay datos para calibrar su ritmo ni su desgaste. Es una limitación del proyecto, no una regla FIA, y se declara así en el informe.

**No se certifica la viabilidad histórica completa:** el inventario sale de una reconstrucción, no de la lista oficial de Pirelli.

## 4. Límites de edad y tamaño del espacio de búsqueda (hallazgo 8 del plan)

Decidido antes de ver cualquier resultado de optimización.

| Escenario | Edad máxima | Base |
|---|---|---|
| `strict_model_coverage` | SOFT 20, HARD 20 | Máximo observado en las vueltas de VER |
| **`observed_race_feasibility`** (principal) | **SOFT 21, HARD 30** | Stint más largo de **cualquier piloto** en esta carrera (OpenF1, 20 pilotos) |

| Inventario / escenario | Estrategias factibles | 1 parada | 2 paradas | ¿Histórica factible? |
|---|---:|---:|---:|---|
| Principal / estricto | **6** | 0 | 6 | Sí |
| **Principal / observado** | **1323** | **0** | 1323 | Sí |
| Alternativa / estricto | 6 | 0 | 6 | Sí |
| Alternativa / observado | 1746 | 0 | 1746 | Sí |

**Lectura:**
1. **Con cobertura estricta solo cabe la estrategia histórica.** Las 6 estrategias son la misma combinación de 17 + 20 + 20 vueltas en distinto orden. Optimizar ahí no tiene sentido; se reporta como evidencia de que, con lo que corrió VER, la estrategia estaba casi forzada.
2. **Ninguna estrategia de una parada es factible** en ningún escenario respaldado por datos. Requeriría un HARD de al menos 36 vueltas y nadie pasó de 30. La comparación 1 contra 2 paradas del plan queda respondida por factibilidad: **en este caso no hay estrategia de una parada que comparar.** Ampliar el límite para forzarla sería fabricar resultados.
3. **El escenario principal de búsqueda es `observed_race_feasibility`**: 1323 estrategias, suficiente para que el recocido tenga sentido. Cualquier stint de VER con edad mayor a 20 es **extrapolación del modelo**: otro piloto lo corrió, pero el modelo de VER no lo vio. Se marca y se analiza aparte.

## 5. Qué necesitan Ihan y Jonathan

- **Ihan (IH-05):** `Constraints.max_sets_by_compound` solo cuenta stints por compuesto; no distingue juegos con edades distintas. Además, `propose_neighbor` rechaza hoy los juegos usados (`initial_age != 0`). Para buscar en este espacio hace falta un inventario por juego (lista de `{compound, initial_age}`, cada uno usado a lo sumo una vez). `src/inventory.py::enumerate_feasible` ya genera todas las estrategias factibles. Sirve para comprobar el recocido contra la enumeración exhaustiva (1323 casos, tamaño manejable) y como generador de soluciones iniciales factibles.
- **Jonathan (JO-02):** los juegos usados conservan su edad (`TyreStint.initial_age`). El SOFT de salida tiene edad 3, no 0, igual que en los datos.

## 6. Limitaciones

1. La continuidad de edad es una heurística: si dos juegos tienen la misma edad, la asignación es ambigua (pasa una vez en la Práctica 1, sin efecto en los conteos).
2. Qué juegos se devolvieron se infiere de las reglas, no de la lista oficial de Pirelli.
3. Las especificaciones obligatorias de carrera no están verificadas.
4. Los límites de edad del escenario principal vienen de otros pilotos y autos. Indican que el stint es físicamente posible, no cuánto tardaría VER en esas vueltas.

## 7. Revisión

- [ ] Luis Pedro: reproduce `python main.py inventory` y los conteos 6 / 1323 / 1746.
- [ ] Ihan: confirma que puede representar el inventario por juego en IH-05.
- [x] Jonathan: confirma la convención de edad de los juegos usados (edad al terminar la vuelta = initial_age + vuelta_en_stint; SOFT inicial de edad 3 alcanza edad 4 en vuelta 1 y 20 en vuelta 17).
- [x] Observaciones / fecha / commit: 2026-11-06, Jonathan Zacarias implementó la convención en `src/model.py` y `src/simulation.py`.
