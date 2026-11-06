# Registro de contribuciones y asistencia de IA

Este registro describe trabajo verificable, no atribuye a compañeros tareas que todavía no han ejecutado.

| Fecha local | Integrante/sesión | Trabajo | Evidencia | Revisión |
|---|---|---|---|---|
| 2026-11-05 | Ihan Marroquin, con asistencia de Codex | Arranque del repo, contratos, motor mínimo, restricciones, pruebas y CLI sintética | `src/`, `tests/`, primer commit del historial | Pendiente de Jonathan |
| 2026-11-05 | Ihan Marroquin, con asistencia de Codex | Recocido discreto y verificación en ejemplo sintético, 30 búsquedas | `src/optimization.py`, `docs/tecnica_recocido.md`, `docs/evidence/optimizer_demo_runs.csv` | Pendiente de Jonathan e Ihan |
| 2026-11-05 | Ihan Marroquin, con asistencia de Codex | Descarga pública OpenF1 y auditoría inicial; FastF1 no logró timing sin autenticación | `src/openf1_data.py`, `docs/evidence/openf1_acquisition.json` | Revisada la procedencia por Mario el 2026-11-06 (ver `docs/datos_openf1.md`); pendiente Luis Pedro |
| 2026-11-06 | Mario Fernando Rocha, con asistencia de Claude Code | MA-01: ficha de la fuente (licencia, diccionario, unidades, cobertura, consistencia); huella SHA-256 portable entre Windows y macOS; mensaje claro ante el bloqueo 401 de OpenF1 durante sesiones en vivo | `docs/datos_openf1.md`, `src/data.py`, `src/openf1_data.py`, `tests/test_portable_hash.py`, `tests/test_openf1_data.py`, `docs/evidence/openf1_acquisition_mario_2026-11-06.json`; 22 pruebas aprobadas | Pendiente de Luis Pedro |

Uso de IA: Codex ayudó a estructurar el plan, investigar fuentes y generar el código inicial y documentación. Se ejecutaron las pruebas y demos indicadas. El equipo debe revisar la implementación, verificar las fuentes y poder defender decisiones. Todavía no hay conclusiones experimentales reales.

Para cada contribución nueva añadir fecha, responsable, tareas del plan, archivos/commit y verificación. No incluir datos personales innecesarios ni credenciales.
