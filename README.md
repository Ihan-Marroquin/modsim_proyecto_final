# Estrategia de paradas en F1 — Proyecto de Modelización y Simulación

**Inicio para humanos y Codex: [PLAN_MAESTRO.md](PLAN_MAESTRO.md).** Ahí está el plan completo, el reparto entre los cinco, las tareas marcables y el estado de relevo.

Repositorio: https://github.com/Ihan-Marroquin/modsim_proyecto_final

Entrega: miércoles 11 de noviembre de 2026. Exposición: jueves 12. Horario exacto pendiente de confirmar con el curso.

## Estado real

- Base local con tipos compartidos, restricciones, simulador mínimo de eventos y pruebas de consistencia.
- Parte inicial de Ihan: recocido simulado discreto, historial de convergencia, referencia exhaustiva pequeña y 30 búsquedas sintéticas reproducibles.
- Referente descargado desde OpenF1: 57 vueltas de VER en Bahréin 2024, stints, pits, clima y mensajes de carrera. Los archivos se regeneran; el reporte de procedencia está en `docs/evidence/openf1_acquisition.json`.
- **Pendiente:** depuración documentada de calidad, partición de validación, calibración, inventario real de neumáticos, integración final, experimentos reales, gráficas, informe y presentación.
- La suma observada de vueltas difiere 0.475 s del total FIA. Se conserva la diferencia para investigar el origen temporal o la fuente; no se corrige silenciosamente.

La demo usa parámetros inventados expresamente etiquetados. No representa una mejora demostrada en F1.

## Ejecución rápida sin instalar dependencias

Recomendado Python 3.12. Desde la carpeta del repositorio:

```powershell
python -m unittest discover -s tests -v
python main.py demo --stochastic --seed 42
python main.py optimize-demo --seed 100 --runs 30
python main.py download
```

El núcleo, las pruebas, la demo y la descarga OpenF1 usan la biblioteca estándar. La descarga requiere internet y respeta la limitación del proveedor; después usa sus archivos guardados. No es necesario reproducir el entorno interno del Codex que inició el trabajo.

## Entorno con bibliotecas para continuar

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`requirements.txt` fija FastF1 3.9.2 para el adaptador opcional y las bibliotecas de análisis que trae como dependencias. `requirements-lock.txt` registra el entorno completo probado en Windows/Python 3.12; antes de añadir bibliotecas, actualizar el registro. En macOS/Linux el ejecutable del entorno está en `.venv/bin/python`.

`python main.py download --provider fastf1` conserva el adaptador alternativo. Falló por autenticación en el entorno inicial; no es el camino comprobado para conseguir datos. Preferir OpenF1. No subir archivos de credenciales.

## Archivos y resultados

- `src/domain.py`: contratos de estrategias, neumáticos, límites y parámetros.
- `src/constraints.py`: factibilidad del alcance configurado.
- `src/simulation.py`: motor mínimo, todavía sin calibración real.
- `src/optimization.py`: módulo inicial de Ihan, objetivo determinista.
- `src/openf1_data.py`: descarga histórica comprobada y normalización conservadora.
- `src/data.py`: auditoría y adaptador FastF1 alternativo.
- `tests/`: verificación sintética del núcleo, optimizador y manejo de datos.
- `docs/tecnica_recocido.md`: fundamentos, implementación y pendientes de Ihan.
- `docs/evidence/`: evidencia inicial y metadatos. Distinguirla de resultados finales.
- `data/raw/`, `data/processed/`, `data/cache/`: archivos locales regenerables, excluidos de Git.
- `results/optimizer_demo/`: búsquedas sintéticas, no experimentos finales.

## Flujo para continuar en otro Codex

Clonar el repo, abrirlo en Codex y usar:

> Lee AGENTS.md y PLAN_MAESTRO.md. Soy [nombre]. Continúa mis tareas pendientes en orden de dependencia, conserva el trabajo existente, ejecuta las verificaciones correspondientes y actualiza las casillas y el relevo con evidencia. No presentes la demo sintética como validación real.

Compartir únicamente el MD no transfiere los archivos de código: también se necesita el repo o el ZIP completo. El plan puede leerse de forma independiente para entender el proyecto.

## Fuentes y uso académico

Fuentes técnicas y reglamentarias en el plan y en `docs/tecnica_recocido.md`. OpenF1 es un proveedor independiente que documenta acceso histórico público para proyectos educativos y no comerciales: https://openf1.org/docs/ . Las licencias de las bibliotecas no establecen por sí solas los derechos sobre datos de terceros. Citar fuentes, respetar condiciones y registrar el uso de IA. La licencia del código propio queda por decidir por el equipo.
