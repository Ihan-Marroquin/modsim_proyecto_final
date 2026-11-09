# Lista de cierre contra la rúbrica (LG-06)

Estado al 2026-11-08, rama `luis-gilberto/entrega`. Marcar `[x]` solo con evidencia; cada fila requiere el visto bueno de todo el equipo antes de entregar.

| Criterio | Pts | Evidencia en el repositorio | Estado |
|---|---:|---|---|
| Problema y justificación | 4 | `report/informe.md` §1–2, `docs/datos_openf1.md` | [ ] Falta MA-06 (redacción de Mario) |
| Investigación adicional | 5 | `docs/tecnica_recocido.md`: fundamentos, 3 fuentes, alternativas, límites | [ ] Falta revisión de Jonathan (IH-07) |
| Formulación | 5 | `docs/modelo_simulacion.md`, `docs/calibracion.md`, informe §3–4 | [ ] Falta JO-05 (revisión de Ihan) |
| Simulación funcional | 7 | `src/model.py`, `src/simulation.py`, `python main.py simulate`, pruebas | [x] 103 pruebas OK, también en clon limpio |
| Técnica adicional implementada | 6 | `src/optimization*.py`, `docs/evidence/optimization/`, Figura 5 | [x] 29/30 al óptimo |
| Experimentos y validación | 5 | `src/validation.py`, `src/experiments.py`, `docs/evidence/{validation,experiments}/` | [ ] Falta revisión de Mario a LP-06 |
| Comparación real | 6 | Informe §8, `docs/validacion_experimentos.md` §5.5 | [x] |
| Resultados y conclusiones | 4 | 4 figuras comprometidas + 1 adicional desde CSV (`src/visualization.py`), tablas, informe §9–10 | [x] |
| Presentación y dominio | 8 | `presentation/guion.md`, `presentation/demo.md` | [ ] Faltan diapositivas y ensayo (EQ-04) |

## Entregables finales

- [x] Repositorio con código, configuraciones, semillas y evidencia (`docs/evidence/`).
- [x] Resultados tabulados: `replicas.csv` (120), `diferencias_pareadas.csv`, `sensibilidad.csv`, `resumen.json`, `validacion.json`.
- [x] Figuras: `python main.py figures` → `report/figures/`.
- [x] Informe integrado: `report/informe.md`; Word/PDF con `python report/build_report.py --pdf` (se entregan fuera del repositorio).
- [ ] Portada con el logo de la universidad del Word de avance (el builder genera portada de texto).
- [x] Diapositivas: `presentation/presentacion_proyecto_f1.pdf` (15 páginas, exportadas de la presentación web).
- [x] Prueba de instalación con clon limpio, venv nuevo e instalación desde cero (LG-05, README). [ ] Repetirla en la computadora de otro integrante.
- [ ] Confirmar repositorio accesible para el docente y registrar la evidencia de envío.
- [ ] EQ-01/EQ-02: aprobación del tema y hora de entrega.
- [x] Contribuciones y uso de IA: `docs/CONTRIBUCIONES.md`, informe §13.
