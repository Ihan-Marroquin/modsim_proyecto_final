# Datos y procedencia

Comando comprobado: `python main.py download`. Descarga historia pública desde https://openf1.org/docs/ para Bahréin 2024, sesión 9472 y piloto VER (número 1). No necesita clave ni cuenta. Los JSON originales de las respuestas se guardan sin editar; las tablas normalizadas son derivados.

`data/raw/`, `data/processed/` y `data/cache/` quedan excluidos de Git. Cada clon debe regenerarlos. La primera adquisición tiene metadatos y huellas en `docs/evidence/openf1_acquisition.json`. El ZIP de relevo tampoco necesita incluir caches ni credenciales.

Resultado inicial: 57 vueltas con tiempos, tres stints SOFT–HARD–SOFT y paradas registradas en 17 y 37. El primer juego SOFT tiene edad inicial de 3 vueltas; los siguientes juegos tienen edad inicial 0. Revisar semántica y fronteras con las fuentes antes de congelar el modelo.

Se observaron 157 registros de clima y 71 mensajes de control de carrera. La suma de vueltas es 5505.217 s y el total FIA citado es 5504.742 s: diferencia +0.475 s pendiente de reconciliar. No ajustar los datos para que coincidan automáticamente.

OpenF1 no proporciona las mismas banderas `IsAccurate`, `Deleted` y `TrackStatus` que FastF1. Se conservan desconocidas. El filtro conservador marca provisionalmente cero vueltas elegibles para calibración hasta revisar control de carrera/calidad. Esto NO significa que falten las 57 observaciones. Mario y Luis Pedro deben definir el filtro correspondiente al proveedor y congelar la partición antes de ajustar.

`lane_duration` es tiempo dentro del pit lane. `stop_duration` es el tiempo detenido y aparece nulo en estos registros; ninguno se debe inventar ni equiparar automáticamente con la pérdida adicional contra circular por pista.

El adaptador FastF1 3.9.2 está conservado, pero no logró obtener timing en el entorno inicial al solicitar autenticación. No guardar credenciales. No renombrar datos OpenF1 como si vinieran de FastF1.

Separar: observaciones públicas; parámetros estimados a partir del entrenamiento; supuestos de disponibilidad/ruido; datos sintéticos de las demos. Revisar las condiciones de uso del proveedor antes de redistribuir archivos y siempre citar la fuente en el informe.
