# Instrucciones de colaboración del proyecto

1. Lee `PLAN_MAESTRO.md` completo antes de continuar: contiene planificación, reparto, estado, contratos y pendientes.
2. El usuario es Ihan Marroquin. Cuando otro integrante use su Codex, trabaja en el rol que indique. Si no indica quién es, confirma su identidad antes de atribuirle una sección; puedes revisar el estado mientras tanto.
3. No reinicies el proyecto ni sustituyas el trabajo de otro integrante por una implementación nueva sin necesidad. Revisa `git status` y diferencias antes de editar.
4. Usa los identificadores de tareas del plan. Marca `[x]` solo con criterio de terminado satisfecho y evidencia en archivos/comandos. Una tarea ejecutada todavía puede tener revisión de compañero pendiente.
5. Mantén separados datos observados, parámetros estimados, supuestos y ejemplos sintéticos. `configs/synthetic_demo.json` y `results/optimizer_demo/` NO validan F1.
6. No ajustes parámetros con el conjunto reservado ni elijas la estrategia por resultados de semillas finales. No inventes datos ni banderas de calidad faltantes.
7. OpenF1 es la vía histórica pública comprobada en esta sesión. FastF1 3.9.2 no pudo descargar timing sin autenticación en este entorno. No solicitar ni guardar credenciales en el repo.
8. Mantén las interfaces de `src/domain.py`; si necesitas cambiarlas, documenta la migración y actualiza usos y pruebas afectadas.
9. Ejecuta `python -m unittest discover -s tests -v` para cambios del núcleo. Añade pruebas sustantivas del comportamiento que cambies. No reportes pruebas que no ejecutaste.
10. Al cerrar un relevo, actualiza estado, tareas marcadas, evidencia, decisiones, problemas y siguiente paso en `PLAN_MAESTRO.md`. Conserva lo que sigue pendiente, aunque exista una demo.
11. Versiona cambios en commits concretos; no incluyas `.env`, caches, entornos virtuales ni datos excluidos. No hagas force push. No borres cambios ajenos para resolver conflictos.
12. El usuario autorizó subir la base a `https://github.com/Ihan-Marroquin/modsim_proyecto_final.git`. Para trabajo posterior, respeta las instrucciones de publicación y ramas de la sesión de ese integrante.
13. Los cinco deben aportar código, redactar su sección y poder explicar el flujo general. Documenta asistencia de IA en `docs/CONTRIBUCIONES.md`.

No es obligatorio delegar ni crear subagentes. Este flujo está diseñado para relevos entre las sesiones de Codex de los integrantes.
