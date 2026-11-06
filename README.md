# Simulación y optimización de paradas en F1

Proyecto de Modelización y Simulación. Repositorio de trabajo técnico:
https://github.com/Ihan-Marroquin/modsim_proyecto_final

## Entrega inicial de Ihan realizada

Ihan Marroquin, con asistencia de Codex, completó la implementación inicial del recocido simulado discreto, las restricciones, el historial de convergencia, la referencia exhaustiva pequeña y 30 búsquedas sintéticas reproducibles. La base incluye contratos compartidos, un simulador mínimo por eventos y una descarga pública del caso candidato.

Verificación de arranque: **18 pruebas aprobadas**. Las semillas 100–129 alcanzaron el resultado exacto del caso sintético de referencia. Evidencia en `docs/evidence/` y explicación del método en `docs/tecnica_recocido.md`.

Esto documenta la parte inicial realizada. El modelo todavía necesita parámetros calibrados, revisión de datos e integración antes de ejecutar los experimentos finales sobre el caso real. Las demos no demuestran una mejora histórica de F1.

## Ejecución

Python 3.12 recomendado. Desde la raíz del repositorio:

```powershell
python -m unittest discover -s tests -v
python main.py demo --stochastic --seed 42
python main.py optimize-demo --seed 100 --runs 30
python main.py download
```

El núcleo, las pruebas, las demos y la descarga histórica OpenF1 usan la biblioteca estándar. La descarga requiere internet; conserva respuestas para reutilizarlas sin repetir solicitudes innecesarias.

Para bibliotecas opcionales de análisis:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

En macOS/Linux, el ejecutable del entorno está en `.venv/bin/python`. `requirements-lock.txt` registra el entorno inicial probado en Windows/Python 3.12.

## Componentes técnicos

- `src/domain.py`: estrategias, juegos de neumáticos, límites y parámetros.
- `src/constraints.py`: comprobación de factibilidad dentro del alcance configurado.
- `src/simulation.py`: motor mínimo, todavía sin calibración empírica.
- `src/optimization.py`: implementación inicial del recocido discreto de Ihan.
- `src/openf1_data.py`: adquisición histórica pública comprobada.
- `src/data.py`: auditoría y adaptador alternativo FastF1.
- `tests/`: consistencia del motor, optimizador y manejo de datos.
- `docs/tecnica_recocido.md`: fundamentos, decisiones y límites.
- `docs/CONTRIBUCIONES.md`: trabajo efectivamente realizado y asistencia de IA.

## Caso candidato y datos

Se descargaron 57 vueltas de VER en Bahréin 2024, stints, pits, clima y control de carrera. La suma de vueltas es 5505.217 s frente a 5504.742 s de la referencia FIA: diferencia de 0.475 s pendiente de reconciliar. Ver `data/README.md` y `docs/evidence/openf1_acquisition.json`.

Los datos regenerables y caches quedan excluidos de Git. OpenF1 no ofrece las mismas banderas de calidad de FastF1; no se rellenan desconocidos como si fueran observados. La descarga FastF1 3.9.2 no obtuvo timing sin autenticación en la sesión inicial; OpenF1 es la vía comprobada. No guardar credenciales.

La planificación del equipo y las instrucciones de relevo se comparten por fuera del repositorio. Este repo conserva la entrega técnica y su evidencia.
