# PLAN MAESTRO — Proyecto F1 y relevo entre integrantes/Codex

**Versión del plan:** 1.0, 5 de noviembre de 2026, America/Guatemala.

**Repo:** https://github.com/Ihan-Marroquin/modsim_proyecto_final . Rama inicial `main`.

**Entrega:** miércoles 11 de noviembre de 2026. **Exposición:** jueves 12. Falta confirmar hora exacta del curso.

**Usuario de la sesión inicial:** Ihan Marroquin. Equipo confirmado: Mario Fernando Rocha, Jonathan Zacarias, Ihan Marroquin, Luis Pedro Lira y Luis Gilberto Marroquin.

Este es el documento central para continuar. Conserva abajo toda la planificación, alcance, fuentes, reparto, calendario, experimentos y rúbrica. Arriba contiene el estado real, casillas y protocolo de relevo. Una copia local del MD puede compartirse; la versión de verdad del proyecto es la que está en el repositorio. **El MD no contiene todos los archivos de código: para ejecutarlos se necesita clonar el repo o recibir el ZIP.**

## A. Estado real de arranque

Ya se hizo, con asistencia de Codex en la sesión de Ihan:

- Base de Python, contratos, comprobación de restricciones y simulador mínimo por eventos.
- Primer módulo de recocido discreto, referencia exhaustiva pequeña y registro de convergencia.
- 18 pruebas de consistencia ejecutadas satisfactoriamente.
- 30 búsquedas del ejemplo SINTÉTICO (semillas 100–129), con diferencia cero contra la referencia exhaustiva de ese caso. No son los experimentos finales.
- Descarga pública OpenF1: 57 vueltas de VER, tres stints, dos paradas, 157 registros de clima y 71 mensajes de control de carrera. Consultar evidencia y fuentes.
- Primera versión de código publicada en GitHub, commit `4524795`. La documentación y ajustes de relevo siguen en commits posteriores; consultar `git log` para el estado más reciente.

**Todavía NO está hecho:** calibración real, validación independiente, aprobación del filtro de calidad y partición, simulación fiel de pérdidas de pits/arranque, inventario histórico completo, comparación final 1/2 paradas, 120 corridas finales, gráficas finales, informe PDF y diapositivas. No marcar el proyecto completo por tener una demo.

### Hallazgos que el próximo Codex debe conocer

1. FastF1 3.9.2 intentó pedir autenticación y no descargó tiempos en este entorno. No introducir credenciales en el repo. `python main.py download` usa OpenF1, que sí funcionó públicamente.
2. No copiar banderas de calidad entre proveedores: OpenF1 no ofrece exactamente `IsAccurate`, `Deleted` y `TrackStatus` de FastF1. Se mantienen desconocidas. El filtro conservador actual deja cero vueltas listas para calibrar, aunque existen 57 observaciones. Mario/Luis Pedro deben implementar revisión documentada con los mensajes de carrera y otras comprobaciones.
3. SOFT inicial tiene edad 3, HARD siguiente edad 0 y SOFT final edad 0. Pits registrados en 17 y 37. No convertir todos los juegos a nuevos.
4. Suma de vueltas OpenF1: 5505.217 s. Referencia FIA: 5504.742 s. Diferencia: +0.475 s. No modificar tiempos para forzar coincidencia ni atribuirla al modelo antes de reconciliar fuentes.
5. `lane_duration` no equivale a pérdida adicional respecto de seguir por pista. `stop_duration` llega nulo en este caso. No inventarlo.
6. El ejemplo en `configs/synthetic_demo.json` tiene 12 vueltas y parámetros inventados. Solo prueba consistencia; no usar sus resultados para conclusiones sobre F1.
7. Un único stint por compuesto en entrenamiento no permite separar libremente desgaste y tendencia de carrera si sus variables quedan colineales. Antes de reservar todo el último stint, Mario debe comprobar rango/identificabilidad o fijar justificadamente algún efecto. No añadir parámetros solo para bajar el error.
8. Límites de edad muy estrechos pueden dejar únicamente la estrategia histórica como factible. Comprobar tamaño del espacio de búsqueda; no ampliar cobertura ni inventario después de ver resultados para fabricar una mejora.

## B. Cómo trabajar, marcar tareas y pasar el relevo

1. Clonar/actualizar el repo. Revisar `git status`, `AGENTS.md`, este MD y últimos commits.
2. Indicar el integrante y escoger sus tareas según las dependencias. Una tarea con bloqueo puede avanzar con fixtures etiquetados, pero no se cierra como integrada al caso real.
3. Usar una rama por cambio/integrante cuando trabajen simultáneamente. Hacer commits pequeños con el ID de tarea. Actualizar desde `main` antes de integrar; nunca reemplazar el plan completo por una copia antigua.
4. Marcar `[x]` únicamente cuando se satisfaga el criterio de terminado y exista evidencia (archivo y comando/resultado). Un `[x]` no sustituye revisión de compañero. Registrar la revisión aparte.
5. Mantener `[ ]` para pendientes y escribir `EN CURSO` o `BLOQUEADA por ...` al lado cuando aplique. No borrar pendientes para aparentar avance.
6. Actualizar la bitácora de relevo y `docs/CONTRIBUCIONES.md`. Todos escriben su sección técnica; Luis Gilberto integra la edición final.
7. Integrar/push según autorización del usuario de esa sesión y permisos del repo. No hacer force push ni borrar código ajeno. Verificar el remoto; un commit local no implica publicación.
8. Compartir el enlace del plan versionado. Si usan ZIP, incluir código y MD; describir qué commit representa. Los datos/caches se regeneran mediante la descarga documentada.

### Prompt listo para otro Codex

```text
Este es nuestro proyecto grupal de Modelización y Simulación.
Repo: https://github.com/Ihan-Marroquin/modsim_proyecto_final
Soy [NOMBRE DEL INTEGRANTE].
Lee AGENTS.md y PLAN_MAESTRO.md completos, revisa git status y el historial.
Continúa mis tareas pendientes por orden de dependencia conservando lo existente.
Ejecuta las comprobaciones pertinentes. Marca solo tareas terminadas con evidencia,
actualiza el relevo, contribuciones y commits. No confundas datos sintéticos con
observaciones ni afirmes que el modelo real está validado antes de medir su error.
Si recibiste solo el MD y no hay código, usa el repo o solicita el ZIP; no finjas
que existen archivos o resultados descritos en la planificación.
```

## C. Tablero de tareas con responsables y dependencias

### Arranque compartido — sesión Ihan/Codex

- [x] **BASE-01:** estructura, tipos, CLI y restricciones iniciales. Evidencia: `src/domain.py`, `src/constraints.py`, `main.py`, commit `4524795`.
- [x] **BASE-02:** simulador mínimo con juegos usados, pits adicionales y reloj. Evidencia: `src/simulation.py`, `tests/test_core.py`. Es scaffold, no modelo real terminado.
- [x] **BASE-03:** primera descarga pública y procedencia. Evidencia: `src/openf1_data.py`, `docs/evidence/openf1_acquisition.json`, `data/README.md`.
- [x] **BASE-04:** verificación inicial: 18 pruebas y demos ejecutadas. Evidencia: `docs/evidence/test_report.txt`, `docs/evidence/optimizer_demo_runs.csv`.
- [x] **BASE-05:** primer commit de código publicado en `main` (`4524795`). Las revisiones siguientes se consultan con `git log`.
- [ ] **BASE-06:** revisión de la base por Jonathan y de la procedencia por Mario/Luis Pedro. Cerrar con observaciones y commit de revisión; no está revisada por compañeros todavía.

### Mario Fernando Rocha — datos y calibración

- [ ] **MA-01:** revisar adquisición OpenF1, condiciones de uso, diccionario y cobertura. Depende BASE-03. Terminado: ficha de fuente/fecha/condiciones, columnas/unidades y observaciones verificadas por Luis Pedro.
- [ ] **MA-02:** implementar filtro de calidad propio de OpenF1 y tabla de exclusiones sin eliminar originales; investigar diferencia de 0.475 s. Depende MA-01. Terminado: motivos por vuelta, conteos, tratamiento de flags y convención temporal documentada. No rellenar desconocidos con True.
- [ ] **MA-03:** congelar junto con Luis Pedro entrenamiento/validación por bloques o stint. Depende MA-02. Terminado: manifiesto de partición, cobertura de compuestos/edades y huellas de archivos antes del ajuste.
- [ ] **MA-04:** implementar calibración y entregar parámetros reales con unidades, cobertura e incertidumbre. Depende MA-03 y contrato de Jonathan. Terminado: `src/calibration.py`, configuración real y ajuste reproducible usando solo entrenamiento.
- [ ] **MA-05:** documentar inventario/edades disponibles, o declarar inventario hipotético común. Coordinar con IH-05 y JO-02. Terminado: restricciones trazables; no certificar inventario histórico si se desconoce.
- [ ] **MA-06:** redactar problema, objetivos, datos y calibración; revisar referencias. Terminado: sección entregada a Luis Gilberto y revisada por Luis Pedro.

### Jonathan Zacarias — modelo y simulador

- [ ] **JO-01:** revisar scaffold BASE-02 y definir modelo real con Mario. Terminado: diagrama, estados, variables, ecuaciones, unidades y supuestos; separar desgaste/tendencia sin falsa identificación causal.
- [ ] **JO-02:** modelar arranque, pérdida adicional de pits y edades usadas con convención temporal consistente. Depende MA-02/MA-05. Terminado: desglose no duplica pérdidas y hay comparación documentada con observaciones.
- [ ] **JO-03:** conectar parámetros reales y completar simulador determinista/estocástico. Depende MA-04. Terminado: produce carrera completa y residuos/variabilidad justificados; no basta con la demo.
- [ ] **JO-04:** integrar optimizador, CLI y datos; revisar cambios de Ihan. Depende IH-05. Terminado: una ejecución completa reproduce base/candidata bajo restricciones iguales.
- [ ] **JO-05:** documentar y redactar formulación/simulación. Terminado: sección y diagrama entregados, revisión de Ihan y pruebas correspondientes.

### Ihan Marroquin — técnica adicional y optimización

- [x] **IH-01:** borrador de fundamentos, representación, procedimiento, parámetros provisionales, alternativas y limitaciones. Evidencia: `docs/tecnica_recocido.md`. Falta lectura y revisión final del autor en IH-07.
- [x] **IH-02:** implementar recocido discreto inicial con objetivo determinista y trazas. Evidencia: `src/optimization.py`. Número de paradas fijo por búsqueda; no atribuir capacidades aún no implementadas.
- [x] **IH-03:** probar restricciones, reproducibilidad y referencia exhaustiva pequeña. Evidencia: `tests/test_optimization.py`, `docs/evidence/test_report.txt`.
- [x] **IH-04:** 30 búsquedas sintéticas con semillas registradas. Evidencia: `docs/evidence/optimizer_demo_runs.csv`, semillas 100–129. No cuenta como experimento final de F1.
- [ ] **IH-05:** integración real: inicializadores factibles para 1/2 paradas, compuestos y juegos realmente modelados. Depende MA-04/MA-05 y JO-03. Terminado: busca en el espacio declarado y conserva edades/inventario; solución comprobada por código.
- [ ] **IH-06:** justificar parámetros con pilotos y ejecutar 30 búsquedas reales; congelar candidata según criterio de entrenamiento. Depende IH-05. Terminado: configuraciones, semillas de búsqueda, presupuestos y logs; sin usar semillas finales para escoger.
- [ ] **IH-07:** leer/verificar las tres fuentes y redacción final; comparar alternativas y explicar dos limitaciones. Depende IH-06 para resultados. Terminado: revisión de Jonathan y dominio de todos los pasos del método.

### Luis Pedro Lira — verificación y experimentos

- [ ] **LP-01:** revisar datos con Mario y aprobar partición/métricas antes de calibrar. Depende MA-02. Terminado: manifiesto explícito y revisión registrada.
- [ ] **LP-02:** completar pruebas sustantivas del modelo real y de estrategias. Depende JO-02/JO-03. Terminado: pruebas y casos conocidos cubren convenciones, límites y efectos de pits/desgaste.
- [ ] **LP-03:** validar contra datos reservados y separar ese error de reconstrucción. Depende MA-04/JO-03. Terminado: `src/validation.py`, métricas por vuelta/acumulado y explicación de correspondencia.
- [ ] **LP-04:** ejecutar A/B/C/D, 30 corridas por condición, con semillas finales distintas de búsqueda. Depende IH-06/LP-03. Terminado: `src/experiments.py`, 120 resultados y configuración completa.
- [ ] **LP-05:** analizar diferencias pareadas, dispersión, sensibilidad, incertidumbre y límites. Depende LP-04. Terminado: tablas comparables real/base/mejora y análisis sin seleccionar solo corridas favorables.
- [ ] **LP-06:** redactar experimentación, validación, comparación real y limitaciones. Terminado: revisión por Mario y entrega a Luis Gilberto.

### Luis Gilberto Marroquin — visualización y entrega

- [ ] **LG-01:** implementar gráficas desde CSV: validación, estrategias, distribución y sensibilidad. Puede iniciar con fixtures etiquetados. Terminado: `src/visualization.py`, ejes/unidades y valores consistentes con tablas reales finales.
- [ ] **LG-02:** ampliar CLI/demo para carga, simulación, optimización y comparación del caso real. Depende JO-04. Terminado: demo local completa y resultados precalculados de respaldo.
- [ ] **LG-03:** ensamblar informe PDF con las secciones de todos y revisar formato. Depende redacciones y LP-05. Terminado: PDF legible, citas, limitaciones, conclusiones, contribuciones y revisión de autores.
- [ ] **LG-04:** preparar diapositivas y guion de 15 minutos incluyendo preguntas. Depende resultados. Terminado: todos participan y ensayo cronometrado; respaldo visual de demo.
- [ ] **LG-05:** actualizar README/dependencias y probar en otra computadora. Depende versión integrada. Terminado: instalación/ejecución reproducible por otro integrante, no únicamente en la máquina inicial.
- [ ] **LG-06:** cierre de entrega: repo accesible, PDF, tablas, semillas, figuras, diapositivas, contribuciones y evidencia de envío. Terminado: lista final de rúbrica cotejada por todos.

### Coordinación del equipo

- [ ] **EQ-01:** confirmar aprobación del tema y técnica adicional con el docente; no consta todavía.
- [ ] **EQ-02:** confirmar hora/medio de entrega y regla exacta de extras. El PDF no confirma bonificación.
- [ ] **EQ-03:** acordar estilo del informe. El proyecto anterior es referencia conocida; nuevas guías/ejemplos pueden incorporarse antes de LG-03, sin bloquear código.
- [ ] **EQ-04:** ensayo completo el martes 10 y revisión final el miércoles 11.
- [ ] **EQ-05:** registrar aportes, usos de IA y revisiones efectivamente realizadas.

## D. Arranque y comandos comprobados

Desde la raíz del repo, Python 3.12 recomendado:

```powershell
python -m unittest discover -s tests -v
python main.py demo --stochastic --seed 42
python main.py optimize-demo --seed 100 --runs 30
python main.py download
```

El núcleo y OpenF1 usan biblioteca estándar. Para las bibliotecas opcionales de análisis:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Las rutas de otra máquina o del entorno interno de Codex no se deben copiar como comandos del proyecto. En macOS/Linux usar el ejecutable apropiado del entorno.

**Interfaces existentes:**

- `validate_strategy(strategy, limits) -> list[str]`: lista vacía significa factible dentro del alcance configurado.
- `simulate(strategy, params, limits, *, seed=0, stochastic=False, degradation_multiplier=1.0) -> dict`: resumen, vueltas y eventos.
- `optimize(initial, params, limits, settings, *, seed=0) -> dict`: candidata, objetivo, evaluaciones e historial.
- Tipos: `Strategy`, `TyreStint`, `Constraints`, `ModelParameters`, `CompoundParameters` en `src/domain.py`.
- No existen aún `src/calibration.py`, `src/validation.py`, `src/experiments.py` ni `src/visualization.py`. Están asignados, no terminados.

## E. Relevo actual — continuar desde aquí

**Sesión:** 2026-11-05, Ihan con asistencia de Codex.

**Trabajo realizado:** BASE-01 a BASE-05 e IH-01 a IH-04; quedan pendientes revisiones de compañeros. No se calibró el modelo ni se ejecutaron experimentos finales.

**Verificación:** 18 pruebas aprobadas; demo estocástica reproducible; 30 búsquedas sintéticas alcanzan 1120.0 s, referencia exacta de ese caso; descarga OpenF1 realizada. Evidencia en `docs/evidence/`.

**Siguiente por integrante:**

- Mario: MA-01/MA-02, revisar las observaciones y diseñar filtro propio de OpenF1; investigar +0.475 s.
- Jonathan: JO-01, revisar el motor y acordar modelo real con Mario; después JO-02.
- Ihan: revisar personalmente `docs/tecnica_recocido.md`; preparar inicializadores de IH-05 con fixtures sin declarar integración real hasta recibir parámetros/inventario.
- Luis Pedro: LP-01, acordar partición y métricas con Mario; puede extender pruebas de casos conocidos.
- Luis Gilberto: LG-01 y EQ-03, preparar visualización y reunir ejemplos del informe; usar fixtures etiquetados hasta recibir resultados reales.

**Dependencia principal:** la interpretación de la optimización está a la espera de MA-02/MA-03/MA-04 y JO-02/JO-03. No sustituir ese trabajo con los parámetros sintéticos.

**Plantilla para el siguiente relevo (añadir debajo, sin borrar el historial):**

```text
Fecha / integrante / rama:
Tareas iniciadas y completadas (IDs):
Archivos modificados:
Comandos ejecutados y resultados:
Datos observados / estimaciones / supuestos usados:
Decisiones y limitaciones nuevas:
Revisiones pendientes:
Siguiente tarea y dependencias:
Commits creados / publicación remota verificada:
```

---

# Planificación completa y requisitos

Entrega: miércoles 11 de noviembre de 2026. Exposición: jueves 12 de noviembre de 2026.

Asignación propuesta usando los cinco integrantes del informe anterior. Los roles se pueden intercambiar antes de empezar; cada entregable conserva un responsable y un revisor. Este plan cubre los requisitos documentados, pero la calificación depende de la evidencia efectivamente entregada y defendida.

## 1. Propuesta y alcance

**Título:** Simulación y optimización de estrategias de paradas en boxes mediante recocido simulado.

**Pregunta:** ¿Qué vueltas de parada y secuencia de neumáticos minimizan el tiempo esperado de carrera de un piloto bajo las restricciones y supuestos estudiados?

**Caso candidato con datos adquiridos:** Max Verstappen, GP de Bahréin 2024, carrera principal. La FIA documenta 57 vueltas y 1:31:44.742. Se descargaron 57 vueltas con tiempos desde OpenF1, tres stints SOFT–HARD–SOFT y paradas en 17 y 37. Falta revisar calidad y calibrar. La suma de vueltas OpenF1 es 5505.217 s, 0.475 s mayor que la referencia FIA; investigar convención temporal/fuente antes de interpretar error de reconstrucción. Fuentes y evidencia: `data/README.md` y `docs/evidence/openf1_acquisition.json`.

**Unidad principal:** segundos de carrera, minimizar. Métricas secundarias: MAE de tiempos por vuelta, error del tiempo acumulado, desviación estándar del tiempo simulado, mejora absoluta y porcentual y porcentaje de estrategias factibles.

**Versión comprometida:** un evento, un piloto objetivo, condiciones secas, estrategias de una o dos paradas, compuestos con datos suficientes, pérdida de tiempo en pits, evolución del ritmo y desgaste, incertidumbre explícita. Una estrategia puede resultar inviable por cobertura de neumáticos o restricciones. Las limitaciones del modelo no se deben presentar como reglas oficiales.

**Supuestos iniciales:** sin interacción dinámica entre 20 autos, decisiones de rivales, adelantamientos, lluvia o decisiones de safety car. Se inspeccionarán las condiciones reales: no se eliminarán vueltas conflictivas para luego afirmar que se reprodujo una carrera completa sin ellas. Si hay neutralizaciones relevantes, se cambiará el caso o se limitará explícitamente la comparación a ventanas compatibles. Las vueltas de salida, entrada a pits y arranque requieren tratamiento separado.

**Relación con clases:** simulación de eventos discretos con reloj, estados y eventos de fin de vuelta/cambio de neumáticos; variables aleatorias, semillas, promedios y dispersión. La técnica adicional propuesta es recocido simulado discreto. El genético básico y A* ya aparecen en el material del curso. Presentar la propuesta y confirmar la aprobación del tema y del aporte adicional con el docente.

## 2. Datos y modelo

### Datos

Usar OpenF1 como vía histórica pública comprobada; conservar FastF1 como adaptador alternativo que no obtuvo timing sin autenticación en la sesión inicial. Obtener tiempos de vuelta, número de vuelta, piloto, stint, compuesto, edad inicial del neumático, condición de nuevo/usado cuando exista, marcas de entrada/salida a pits, estado de pista, banderas de calidad y datos meteorológicos disponibles. Conservar los registros originales; documentar las exclusiones en otra tabla. Registrar fuente, fecha de descarga, evento/sesión, versiones, filas originales, filas usadas y motivos de exclusión. Si no procede redistribuir datos, incluir instrucciones de obtención y respetar las condiciones de la fuente.

Separar un conjunto de calibración y un bloque o stint reservado para validación antes del ajuste. La partición debe preservar cobertura de compuestos y edades; usar separación temporal o por stint y documentar extrapolaciones. La reconstrucción de toda la carrera con parámetros ajustados a esa carrera no es validación independiente. No ajustar parámetros contra el bloque reservado.

### Modelo inicial interpretable

Tiempo de una vuelta normal, en segundos:

`t_vuelta = b_compuesto + d_compuesto * edad_neumatico + g(vuelta_carrera) + ruido`

Es un modelo propuesto, no una ley física. `b` representa ritmo de referencia, `d` degradación estimada y `g` una tendencia de carrera simplificada. La tendencia temporal, combustible, pista, ritmo administrado y desgaste se pueden confundir: revisar identificabilidad y no atribuir automáticamente toda la pendiente al neumático. Justificar los parámetros y simplificar si los datos no permiten estimarlos. No introducir términos de combustible y tendencia equivalentes a la vez sin respaldo.

Añadir por separado la penalización de arranque y la pérdida adicional de cada parada, con una convención temporal consistente. No sumar dos veces los efectos de pits. El tiempo entre entrar y salir del pit lane no es automáticamente la pérdida adicional frente a seguir por pista. Estimar y documentar esa diferencia con datos de entrenamiento o una referencia técnica. La suma de vueltas y el tiempo oficial deben reconciliar su origen temporal y cobertura antes de compararse.

El ruido puede estimarse mediante residuos del ajuste, con una distribución o remuestreo justificado. Examinar su dispersión y dependencia temporal; cualquier independencia asumida debe declararse. La versión sin ruido sirve para depurar y evaluar rápidamente el valor esperado aproximado; no debe ocultar incertidumbre de parámetros.

### Restricciones

- Vueltas de parada enteras, ordenadas, dentro de la carrera y con stints no vacíos.
- Una o dos paradas como límite del proyecto.
- Secuencia e inventario de neumáticos factibles dentro del alcance declarado.
- En una carrera seca de 2024, revisar las exigencias aplicables sobre compuestos en el reglamento de esa temporada y las notas del evento. No usar por defecto reglas de 2026 para reproducir 2024.
- Conservar la edad inicial real de juegos usados; cambiar de juego no siempre significa edad cero.
- Limitar la optimización a compuestos y rangos de edad respaldados por datos, o declarar expresamente las extrapolaciones y analizarlas por separado.
- Si no se conoce el inventario real disponible, definir un inventario hipotético común a todas las estrategias y reconocer que no se certifica viabilidad histórica completa.

La función de validación de estrategias devuelve errores explicativos; una solución inválida nunca se reporta como candidata aceptada.

## 3. Optimización adicional

La primera implementación del recocido discreto usa la biblioteca estándar de Python; NumPy puede incorporarse si existe una necesidad documentada. Una solución contiene el número de paradas, las vueltas y los compuestos de cada stint. Un vecino desplaza una parada o cambia un compuesto; el cambio entre una y dos paradas puede hacerse con movimientos factibles o ejecutando búsquedas separadas para cada número y comparándolas con el mismo protocolo.

Objetivo: minimizar el tiempo esperado aproximado del simulador bajo las restricciones. Aceptar mejoras y, según temperatura, algunas soluciones peores; enfriar y guardar la mejor solución factible visitada. Documentar temperatura inicial, enfriamiento, vecindario, presupuesto de evaluaciones, semilla y terminación. Elegir parámetros con pruebas piloto separadas de la evaluación final.

Usar el simulador determinista o un lote fijo de semillas de entrenamiento durante la búsqueda. Congelar la estrategia antes de probarla con semillas nuevas. Ejecutar 30 búsquedas con semillas independientes para medir estabilidad del algoritmo; elegir la candidata con el criterio fijado de entrenamiento, no por su desempeño en las semillas finales.

En un caso reducido, enumerar estrategias factibles para conocer el óptimo y comprobar la implementación del recocido. Esa enumeración es una verificación interna, no validación real ni prueba de optimalidad global para cualquier caso. SciPy dual_annealing es una variante distinta; no atribuir su procedimiento a una implementación discreta propia.

## 4. Reparto entre cinco integrantes

### Mario Fernando Rocha: datos y calibración

- Preparar la propuesta de una página y la ficha del caso; coordinar la consulta de aprobación.
- Implementar descarga, caché, exportación y limpieza reproducible.
- Entregar diccionario de columnas/unidades y tabla de exclusiones.
- Fijar la partición de datos con Luis Pedro antes de calibrar.
- Estimar parámetros, documentar incertidumbre y cobertura por compuesto/edad.
- Entregar parámetros configurables y una gráfica exploratoria real.
- Escribir problema, objetivos, fuentes, procedencia de parámetros y calibración.

**Archivos propios:** `src/data.py`, `src/calibration.py`, `configs/`, `data/README.md`.

**Aceptación:** otro integrante reproduce la obtención y el ajuste desde instrucciones; no se usan datos reservados para calibrar. **Revisa:** Luis Pedro.

### Jonathan Zacarias: modelo, simulación e integración

- Definir con Mario estados, variables, unidades y ecuaciones.
- Implementar avance por vuelta, neumáticos usados/nuevos, paradas y acumulación temporal.
- Implementar modo determinista y estocástico, sin acceso a internet dentro del simulador.
- Definir interfaces compartidas y el formato de resultados desde el primer día.
- Integrar módulos y conservar una ejecución completa operativa.
- Escribir formulación, supuestos y funcionamiento del simulador.

**Archivos propios:** `src/model.py`, `src/simulation.py`, `src/domain.py`.

**Aceptación:** una estrategia manual termina la carrera, produce desglose por vuelta y respeta estados/unidades; misma configuración y semilla repiten resultados. **Revisa:** Ihan.

### Ihan Marroquin: investigación e implementación del optimizador

- Investigar recocido simulado con al menos tres fuentes técnicas; incluir artículo o libro especializado.
- Justificarlo frente a búsqueda exhaustiva, Hill Climbing y genético; explicar al menos dos limitaciones.
- Definir representación, vecinos, aceptación, enfriamiento y terminación.
- Implementar búsqueda y verificación explícita de restricciones.
- Guardar historial de convergencia y resultados de 30 búsquedas independientes.
- Verificar un caso pequeño contra enumeración.
- Escribir técnica adicional e integración.

**Archivos propios:** `src/optimization.py`, `src/constraints.py`, `configs/optimizer.json`.

**Aceptación:** entrega candidata factible, objetivo y trazas reproducibles dentro de un presupuesto documentado. No prometer superioridad ni ocultar casos sin mejora. **Revisa:** Jonathan.

### Luis Pedro Lira: verificación, validación y experimentos

- Especificar con Mario el conjunto reservado, métricas y condiciones antes de los resultados.
- Implementar pruebas de consistencia y casos pequeños conocidos.
- Comparar la base histórica simulada con el referente observado bajo el mismo período/unidad.
- Ejecutar experimentos y conservar cada repetición, parámetros y semillas.
- Calcular media, desviación estándar, diferencias pareadas e incertidumbre de la diferencia.
- Analizar sensibilidad y señalar si la magnitud del supuesto beneficio es menor que el error de validación.
- Escribir diseño experimental, validación, comparación real y limitaciones experimentales.

**Archivos propios:** `src/validation.py`, `src/experiments.py`, `tests/`.

**Aceptación:** al menos 30 repeticiones independientes por condición aleatoria, separación búsqueda/evaluación y comparación cuantitativa real. **Revisa:** Mario.

### Luis Gilberto Marroquin: visualización, ejecución y entrega

- Implementar gráficas desde CSV, sin números escritos manualmente.
- Crear la entrada del programa y una demo local: cargar caso, mostrar base, optimizar y comparar.
- Integrar README, dependencias, comandos y registro de contribuciones.
- Armar el informe con los textos entregados por todos; cada autor revisa su sección.
- Preparar diapositivas, resultados precalculados y respaldo de la demostración.
- Comprobar junto con otra persona la instalación y ejecución en una máquina limpia.

**Archivos propios:** `src/visualization.py`, `main.py`, `README.md`, `requirements.txt`, `report/`, `presentation/`.

**Aceptación:** las figuras coinciden con resultados tabulados, la demo funciona con datos preparados y todos los entregables son accesibles. **Revisa:** Jonathan para ejecución; todos para informe y diapositivas.

Cada integrante programa, redacta y expone. Nadie queda únicamente a cargo de la portada o de copiar textos. Todos deben poder explicar el flujo completo.

## 5. Contratos de integración

Contratos conceptuales de destino. La implementación inicial existe para `simulate`, `optimize` y `validate_strategy`; sus firmas reales están en el código y se resumen en el relevo. El resto sigue pendiente:

- `load_case(config) -> observed_data, metadata`
- `fit_parameters(training_data, config) -> model_parameters`
- `validate_strategy(strategy, constraints) -> feasible, violations`
- `simulate(strategy, model_parameters, scenario, seed) -> lap_results, summary`
- `optimize(model_parameters, constraints, search_config, seed) -> strategy, search_log`
- `run_experiments(experiment_config) -> results_table`
- `make_figures(results_table, observed_data) -> image_files`

Campos mínimos por repetición: caso, piloto, escenario, estrategia, parámetros/versiones, semilla de búsqueda si aplica, semilla de evaluación, tiempo total en segundos, paradas, factibilidad. Desglose: vuelta, compuesto, edad del neumático, tiempo normal, penalización por parada y acumulado.

## 6. Experimentos comprometidos

| Condición | Estrategia | Entorno | Repeticiones |
|---|---|---|---:|
| A | Estrategia histórica, sin optimizador | Parámetros base | 30 |
| B | Candidata optimizada y congelada | Mismos parámetros base | 30 |
| C | Estrategia histórica | Degradación multiplicada por 1.20 | 30 |
| D | Misma candidata optimizada de B | Degradación multiplicada por 1.20 | 30 |

El +20 % es un escenario hipotético de sensibilidad, no un dato observado. Congelar B permite medir robustez; reoptimizar para sensibilidad sería una ampliación aparte. Mantener todas las demás restricciones iguales. Cada condición usa semillas independientes entre sus repeticiones; compartir la semilla de entorno entre A y B, y entre C y D, permite comparaciones pareadas sin que las repeticiones dentro de una condición dejen de ser independientes. Usar semillas finales distintas de las de búsqueda.

Tabla de comparación: referencia observada, base simulada y candidata simulada, mismas métricas, unidades y ventana. Las columnas observadas solo contienen mediciones; las predicciones de la candidata se identifican como simuladas. Informar por separado error en datos reservados y error de reconstrucción completa.

Calcular `mejora_segundos = tiempo_base - tiempo_candidata` y `mejora_porcentaje = 100 * mejora_segundos / tiempo_base`. Una mejora negativa o incierta también es un resultado; no seleccionar solo repeticiones favorables. No afirmar que se habría ganado la carrera ni superado la estrategia del equipo en todas sus condiciones reales.

Pruebas mínimas: tiempo total coincide con su desglose; vueltas de parada válidas; factibilidad de neumáticos; misma semilla reproduce la corrida; en un caso artificial sin degradación ni diferencias de ritmo entre compuestos, una parada extra con penalización positiva no genera una ganancia artificial; comparación del optimizador con enumeración en caso pequeño.

Gráficas comprometidas: (1) vueltas observadas y predichas en validación; (2) cronograma de stints de base y candidata; (3) distribución de tiempos o diferencias pareadas; (4) sensibilidad. Convergencia del optimizador como figura adicional.

## 7. Calendario y dependencias

| Fecha | Resultado de cierre | Trabajo del equipo |
|---|---|---|
| Jueves 5 | Caso viable, alcance y contratos acordados | Mario obtiene muestra y fuentes; Jonathan fija interfaces y caso manual; Ihan investiga método y prototipo con objetivo de juguete; Luis Pedro fija métricas/pruebas; Luis Gilberto crea estructura de entrega y prototipo de gráficas. |
| Viernes 6 | Datos depurados y simulador determinista conectado | Mario entrega parámetros iniciales y partición; Jonathan ejecuta una carrera manual; Ihan conecta su optimizador; Luis Pedro ejecuta consistencia; Luis Gilberto muestra datos reales y estrategia manual. |
| Sábado 7 | Reconstrucción y validación inicial del modelo base | Mario/Jonathan corrigen modelo con entrenamiento; Luis Pedro evalúa reservado sin reajustar a él; Ihan verifica factibilidad/enumeración; Luis Gilberto integra figuras y borrador de secciones. |
| Domingo 8 | Optimización integrada y versión estocástica | Ihan congela el protocolo; Jonathan/Mario documentan ruido y límites; Luis Pedro ejecuta pilotos; Luis Gilberto prepara demo completa. Cerrar añadidos funcionales. |
| Lunes 9 | Experimentos finales y tablas | Ejecutar 30 búsquedas y las 120 evaluaciones finales, revisar errores, interpretar resultados; todos redactan sus secciones. Si cambia el modelo, versionar y repetir los experimentos afectados. |
| Martes 10 | Informe, repositorio y presentación candidatos finales | Luis Gilberto compone artefactos; todos revisan; Mario/Luis Pedro verifican datos/métricas; Jonathan/Ihan verifican ejecución; prueba de instalación por otro integrante y ensayo completo. |
| Miércoles 11 | Entrega verificada y respaldo | Revisar rúbrica punto por punto, permisos del repo, archivos y registro de entrega. Ensayo final. Ajustar la hora interna al horario oficial del curso. |
| Jueves 12 | Exposición y defensa | Usar la versión entregada, demo preparada y respaldos; todos participan. |

Reunión diaria breve: cada persona muestra un archivo o ejecución verificable, un bloqueo y el siguiente entregable. Trabajar en ramas pequeñas, integrar diariamente y registrar aportes. Los datos preparados y las interfaces desbloquean el modelo; el modelo validado desbloquea la interpretación de la optimización. El optimizador puede empezar desde el primer día con una función de juguete.

## 8. Cobertura de la rúbrica y cierre

| Criterio | Puntos | Responsable principal | Evidencia |
|---|---:|---|---|
| Problema y justificación | 4 | Mario | Propuesta, pregunta, unidades, alcance y fuente verificable. |
| Investigación adicional | 5 | Ihan | Fundamentos, tres fuentes técnicas, alternativas y dos limitaciones. |
| Formulación | 5 | Jonathan + Mario | Diagrama, estados, ecuaciones, procedencia/unidades, restricciones. |
| Simulación funcional | 7 | Jonathan | Ejecución parametrizable, módulos e instrucciones reproducibles. |
| Técnica adicional implementada | 6 | Ihan | Búsqueda operativa, integración, restricciones comprobadas y trazas. |
| Experimentos y validación | 5 | Luis Pedro | Condiciones, repeticiones, semillas, consistencia, error e incertidumbre. |
| Comparación real | 6 | Luis Pedro + Mario | Referencia documentada, tabla comparable, diferencias y límites. |
| Resultados y conclusiones | 4 | Luis Gilberto + todos | Al menos tres gráficas pertinentes, tablas y conclusiones sustentadas. |
| Presentación y dominio | 8 | Todos | Demo verificable, respuestas, participación y máximo 15 minutos. |

Entregables finales: informe técnico PDF, repositorio GitHub accesible, resultados experimentales tabulados y configuraciones, gráficas, diapositivas/demo y contribuciones. Documentar herramientas, bibliotecas y uso de IA. Cada responsable entrega su sección al editor; la edición no sustituye la autoría ni revisión técnica.

Guion de 15 minutos: Mario 2 min (problema/datos), Jonathan 2 min (modelo), Ihan 3 min (método), Luis Gilberto 3 min (demo), Luis Pedro 3 min (resultados/validación), 2 min compartidos para conclusiones y preguntas. Disponer de resultados locales y un respaldo visual de la ejecución.

Una conclusión válida puede indicar que no se detectó mejora robusta. El programa y la evidencia deben permitir evaluar lo ocurrido sin presentar como observados los resultados de estrategias hipotéticas.

## 9. Ampliaciones, solo después de cerrar lo obligatorio

Prioridad: comparar recocido con búsqueda aleatoria usando el mismo presupuesto de evaluaciones; incorporar incertidumbre de parámetros; añadir un segundo piloto como caso de validación con su parametrización justificada. No comprometer estas ampliaciones antes de tener datos, base, validación y experimentos. No hay bonificación confirmada por hacerlas.

## 10. Fuentes para empezar

- Enunciado del curso: `Proyecto_2_Modelizacion_y_Simulacion_UVG_2026.pdf`, partes 1–7 y rúbrica. Este MD conserva los requisitos operativos y su tabla de cobertura; el PDF original no está incluido en el repo. Si se necesita revisar un detalle literal, pedir al equipo el PDF, sin suponer que existe en una ruta de otra computadora.
- OpenF1, proveedor histórico público comprobado: https://openf1.org/docs/
- FastF1, proyecto y condiciones: https://github.com/theOehrly/Fast-F1
- FastF1, columnas de tiempos y banderas de calidad: https://github.com/theOehrly/Fast-F1/blob/main/docs/api_reference/timing_data.rst
- FIA, clasificación Bahréin 2024: https://www.fia.com/events/fia-formula-one-world-championship/season-2024/bahrain-grand-prix/race-classification
- FIA, reglamento deportivo 2024, edición del 28 de febrero anterior al evento: https://api.fia.com/sites/default/files/fia_2024_formula_1_sporting_regulations_-_issue_5_-_2024-02-28.pdf . Comprobar además las notas y prescripciones específicas del evento.
- Kirkpatrick, Gelatt y Vecchi (1983), Optimization by Simulated Annealing: https://doi.org/10.1126/science.220.4598.671
- SciPy, referencia de una variante de annealing, para comparación y bibliografía: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.dual_annealing.html
- TUM, referencia técnica de simulación y estrategia de carreras, para estudiar componentes y citar cualquier reutilización: https://github.com/TUMFTM/race-simulation . La versión propuesta es propia y acotada; no basta con ejecutar este repositorio ajeno.

Estas fuentes inician la investigación; leer y verificar las partes utilizadas antes de citarlas como respaldo de una decisión concreta.
