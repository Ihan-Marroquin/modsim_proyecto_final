# Simulación y optimización de paradas en F1

Proyecto de Modelización y Simulación. Repositorio de trabajo técnico:
https://github.com/Ihan-Marroquin/modsim_proyecto_final

## Estado del caso de Bahréin 2024

El simulador y el recocido discreto usan parámetros calibrados con 33 vueltas de entrenamiento de Verstappen. El inventario inferido admite 1323 estrategias de dos paradas y ninguna de una. El recocido igualó el mejor valor de la enumeración en 29 de 30 búsquedas.

La candidata congelada para en las vueltas **17 y 36**. La ventaja determinista estimada sobre la estrategia histórica simulada es de **0.075 s**. Ver [método y límites](docs/tecnica_recocido.md) y [resumen reproducible](docs/evidence/optimization/summary.json).

**Validación en el stint 3 reservado** (18 vueltas, sin reajuste): MAE de 0.712 s, sesgo de +0.456 s por vuelta (el modelo es más lento) y error acumulado de +8.203 s. La reconstrucción de las 57 vueltas, que no es validación, da +9.957 s frente a la FIA.

**Experimentos A/B/C/D** (30 semillas reservadas, 3300–3329):
- La mejora de la candidata es de +0.075 s con degradación ×1.00 y de −0.062 s con ×1.20.
- Cambia de signo según la tendencia de carrera.
- Su error estándar por parámetros es de 0.128 s.

No se detectó una mejora robusta. Ver [validación y experimentos](docs/validacion_experimentos.md).

## Ejecución

Python 3.12 recomendado. Desde la raíz del repositorio:

```powershell
python -m unittest discover -s tests -v
python main.py optimize
python main.py simulate --strategy docs/evidence/optimization/candidate.json
python main.py experiments
python main.py validate          # requiere download, reconcile y partition
python main.py demo --stochastic --seed 42
python main.py optimize-demo --seed 100 --runs 30
python main.py download
```

La optimización y la simulación se ejecutan sin internet con los parámetros versionados. `optimize` genera el resumen, la candidata, los pilotos y las trazas en `results/optimization/`. La descarga OpenF1 sí requiere internet y conserva las respuestas para reutilizarlas.

Para bibliotecas opcionales de análisis:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

En macOS/Linux, el ejecutable del entorno está en `.venv/bin/python`. `requirements-lock.txt` registra el entorno inicial probado en Windows/Python 3.12.

## Componentes técnicos

- `src/domain.py`: estrategias, juegos de neumáticos, límites y parámetros.
- `src/constraints.py`: comprobación de factibilidad dentro del alcance configurado.
- `src/model.py` y `src/simulation.py`: carga de parámetros y motor de carrera calibrado.
- `src/optimization.py` y `src/optimization_case.py`: recocido discreto y protocolo para Bahréin.
- `src/validation.py`: validación en el stint 3 reservado y reconstrucción completa, por separado.
- `src/experiments.py`: experimentos A/B/C/D, diferencias pareadas, incertidumbre y sensibilidad.
- `src/openf1_data.py`: adquisición histórica pública comprobada.
- `src/data.py`: auditoría y adaptador alternativo FastF1.
- `tests/`: consistencia del motor, optimizador y manejo de datos.
- `docs/tecnica_recocido.md`: fundamentos, decisiones y límites.
- `docs/CONTRIBUCIONES.md`: trabajo efectivamente realizado y asistencia de IA.

## Caso candidato y datos

Se descargaron 57 vueltas de VER, stints, pits, clima y control de carrera. La conciliación con Jolpica y FIA ubicó la diferencia de 0.475 s en la convención de la primera vuelta. Ver [conciliación](docs/conciliacion_tiempos.md) y [partición para validación](docs/particion_validacion.md).

Los datos regenerables y caches quedan excluidos de Git. OpenF1 no ofrece las mismas banderas de calidad de FastF1; no se rellenan desconocidos como si fueran observados. La descarga FastF1 3.9.2 no obtuvo timing sin autenticación en la sesión inicial; OpenF1 es la vía comprobada. No guardar credenciales.

La planificación del equipo y las instrucciones de relevo se comparten por fuera del repositorio. Este repo conserva la entrega técnica y su evidencia.
