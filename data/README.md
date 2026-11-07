# Datos y procedencia

Comando comprobado: `python main.py download`. Descarga historia pública desde https://openf1.org/docs/ para Bahréin 2024, sesión 9472 y piloto VER (número 1). No necesita clave ni cuenta. Los JSON originales de las respuestas se guardan sin editar; las tablas normalizadas son derivados.

`data/raw/`, `data/processed/` y `data/cache/` quedan excluidos de Git. Cada clon debe regenerarlos. La primera adquisición tiene metadatos y huellas en `docs/evidence/openf1_acquisition.json`. El ZIP de relevo tampoco necesita incluir caches ni credenciales.

Resultado inicial: 57 vueltas con tiempos, tres stints SOFT–HARD–SOFT y paradas registradas en 17 y 37. El primer juego SOFT tiene edad inicial de 3 vueltas; los siguientes juegos tienen edad inicial 0. Revisar semántica y fronteras con las fuentes antes de congelar el modelo.

Se observaron 157 registros de clima y 71 mensajes de control de carrera. La suma de vueltas es 5505.217 s y el total FIA citado es 5504.742 s: diferencia +0.475 s. **Conciliada** con `python main.py reconcile` (Jolpica, CC BY-NC-SA 4.0): está toda en la vuelta 1 (OpenF1 97.759 s, convención oficial 97.284 s) y las vueltas 2–57 coinciden al milisegundo. Los datos OpenF1 no se modificaron. Detalle y decisiones en `docs/conciliacion_tiempos.md`.

OpenF1 no proporciona las mismas banderas `IsAccurate`, `Deleted` y `TrackStatus` que FastF1. Se conservan desconocidas. El filtro propio de OpenF1 (`src/openf1_quality.py`, documentado en `docs/filtro_calidad_openf1.md`) usa control de carrera, pits y clima: deja **51 de 57 vueltas elegibles** para el ajuste de vueltas normales y no borra ninguna. Pendiente de revisión de Luis Pedro. **Partición congelada (MA-03):** entrenamiento = stints 1–2 (33 vueltas), validación = stint 3 (18 vueltas); generada con `python main.py partition`, ver `docs/particion_validacion.md`.

`lane_duration` es tiempo dentro del pit lane. `stop_duration` es el tiempo detenido y aparece nulo en estos registros; ninguno se debe inventar ni equiparar automáticamente con la pérdida adicional contra circular por pista.

El adaptador FastF1 3.9.2 está conservado, pero no logró obtener timing en el entorno inicial al solicitar autenticación. No guardar credenciales. No renombrar datos OpenF1 como si vinieran de FastF1.

**Ficha completa de la fuente** (licencia CC BY-NC-SA 4.0, diccionario, unidades, cobertura): `docs/datos_openf1.md`.

**Huellas entre computadoras.** Los JSON crudos se guardan con los saltos de línea del sistema (CRLF en Windows, LF en macOS/Linux), así que `sha256` cambia según la máquina aunque el contenido sea idéntico. Para verificar datos entre integrantes o con el catedrático usar `sha256_portable` del reporte de descarga (`src/data.py::portable_sha256`, convierte CRLF→LF antes de calcular). La evidencia del 2026-11-05 (`docs/evidence/openf1_acquisition.json`) se generó en Windows y solo tiene `sha256`. La del 2026-11-06 (`docs/evidence/openf1_acquisition_mario_2026-11-06.json`) tiene ambas.

**Descarga durante sesiones en vivo.** Mientras hay una sesión de F1 en vivo, OpenF1 responde 401 a todo acceso sin cuenta, incluido el histórico (comprobado el 2026-11-06). Reintentar cuando termine la sesión o usar una caché `data/raw/openf1/` ya descargada: si los URL coinciden, `python main.py download` la reutiliza sin red. No introducir credenciales en el repo.

Separar: observaciones públicas; parámetros estimados a partir del entrenamiento; supuestos de disponibilidad/ruido; datos sintéticos de las demos. Revisar las condiciones de uso del proveedor antes de redistribuir archivos y siempre citar la fuente en el informe.
