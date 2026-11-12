# Lista de cierre contra la rúbrica (LG-06)

Estado al 2026-11-11. Marcar `[x]` solo con evidencia; cada fila requiere el visto bueno de todo el equipo antes de entregar.

| Criterio | Pts | Evidencia en el repositorio | Estado |
|---|---:|---|---|
| Problema y justificación | 4 | `report/informe.md` §1–2, `docs/datos_openf1.md` | [x] MA-06 redactada por Mario el 2026-11-09 (§1 con contexto, justificación y caso; §2 y §4 ampliadas; referencias comprobadas) y revisada por Luis Pedro sin cambios |
| Investigación adicional | 5 | `docs/tecnica_recocido.md`: fundamentos, 3 fuentes, alternativas, límites | [ ] Falta revisión de Jonathan (IH-07) |
| Formulación | 5 | `docs/modelo_simulacion.md`, `docs/calibracion.md`, informe §3–4 | [ ] Falta JO-05 (revisión de Ihan) |
| Simulación funcional | 7 | `src/model.py`, `src/simulation.py`, `python main.py simulate`, pruebas | [x] 103 pruebas OK, también en clon limpio |
| Técnica adicional implementada | 6 | `src/optimization*.py`, `docs/evidence/optimization/`, Figura 5 | [x] 29/30 al óptimo |
| Experimentos y validación | 5 | `src/validation.py`, `src/experiments.py`, `docs/evidence/{validation,experiments}/` | [x] LP-06 revisada y aprobada por Mario el 2026-11-09 (`docs/validacion_experimentos.md` §8) |
| Comparación real | 6 | Informe §8, `docs/validacion_experimentos.md` §5.5 | [x] |
| Resultados y conclusiones | 4 | 4 figuras comprometidas + 1 adicional desde CSV (`src/visualization.py`), tablas, informe §9–10 | [x] |
| Presentación y dominio | 8 | `presentation/presentacion_proyecto_f1.pdf`, demo interactiva con `python main.py replay` (`src/replay.py`, `presentation/replay/`) | [ ] Diapositivas finales listas el 2026-11-11; falta el ensayo (EQ-04) |

## Entregables finales

- [x] Repositorio con código, configuraciones, semillas y evidencia (`docs/evidence/`).
- [x] Resultados tabulados: `replicas.csv` (120), `diferencias_pareadas.csv`, `sensibilidad.csv`, `resumen.json`, `validacion.json`.
- [x] Figuras: `python main.py figures` → `report/figures/`.
- [x] Informe integrado: `report/informe.md` (fuente) y `report/informe_proyecto_f1.pdf` (13 páginas); se regenera con `python report/build_report.py --pdf`.
- [x] Portada con el logo de la UVG (`report/assets/logo_uvg.png`).
- [x] Diapositivas: `presentation/presentacion_proyecto_f1.pdf` (14 diapositivas para 9 minutos más una de respaldo, exportadas de la presentación web). Versión final del 2026-11-11, ajustada a las expectativas del curso: problema, relevancia, objetivo general medible y los cinco objetivos específicos del informe (2), por qué este caso (3), modelo con flujo de eventos, ecuación, supuestos y restricciones (4), ritmo separado de las penalizaciones (4 y 5), por qué y límites del recocido (6), demo en vivo con `optimize`, `compare` con cambio de parámetro y `replay` (8), comparación con la realidad con las 33 vueltas de ajuste 2–16 y 19–36 (9), por qué cambia el signo de la ventaja (11) y conclusiones que cierran los objetivos, con el empate de la histórica limitado al escenario con límite estricto de edad (12).
- [x] Prueba de instalación con clon limpio, venv nuevo e instalación desde cero (LG-05, README). [ ] Repetirla en la computadora de otro integrante.
- [ ] Confirmar repositorio accesible para el docente y registrar la evidencia de envío.
- [ ] EQ-01/EQ-02: aprobación del tema y hora de entrega.
- [x] Contribuciones y uso de IA: `docs/CONTRIBUCIONES.md`, informe §13.
