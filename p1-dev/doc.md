# Parcial 1 – Programación Eficiente

## Aplicación elegida

Sistema de detección de archivos duplicados a gran escala.

## Lenguaje

Python.

**Justificación:** el problema es principalmente I/O-bound (lectura de miles de archivos), con un componente CPU-bound en el cálculo de hashes. Python permite contrastar directamente `threading`/`asyncio` (I/O-bound) contra `multiprocessing` (CPU-bound) y justificar la elección en base al GIL, que es uno de los puntos de análisis pedidos. Además, el ecosistema de profiling (`cProfile`, `memory_profiler`, `py-spy`, `Scalene`) es simple de integrar, y la librería estándar (`hashlib`, `pathlib`, `functools.lru_cache`, `concurrent.futures`) cubre todo lo necesario sin boilerplate.

## Descripción del problema

Dado un directorio con un volumen importante de archivos (o imágenes), detectar cuáles son duplicados entre sí.

## Estrategias de comparación (análisis de complejidad)

1. **Comparación directa (fuerza bruta):** comparar cada archivo contra todos los demás (byte a byte o por contenido completo). Se generan O(n²) pares de comparación y cada comparación cuesta además O(s) por la lectura del contenido (s = tamaño del archivo). Costo total en el peor caso: O(n²·s̄), con n = cantidad de archivos y s̄ = tamaño promedio de archivo.
2. **Pre-filtrado por tamaño:** agrupar los archivos por su tamaño en bytes leyendo la metadata del sistema (sin tocar el contenido). Complejidad O(n). Dos archivos de distinto tamaño no pueden ser duplicados, lo que reduce drásticamente los candidatos a procesar antes de pagar el costo de I/O.
3. **Hashing incremental + indexado:** calcular un hash (ej. SHA-256) solo para los archivos que coincidan en tamaño. La lectura se hace por chunks (buffers de 64KB) utilizando `hashlib.sha256().update(chunk)`, lo que mantiene la complejidad espacial en O(1) por archivo sin importar su tamaño. Cada archivo candidato se lee una única vez, por lo que el costo total es O(N), con N = suma de bytes de todos los archivos candidatos — muy inferior al O(n²·s̄) de la fuerza bruta. La inserción y detección de duplicados en el `dict` es O(1) promedio por archivo.

Se implementará primero la versión de fuerza bruta como baseline, y luego la versión con pre-filtrado y hashing como optimización algorítmica, midiendo y comparando ambas.

## Estructuras de datos a utilizar

- **`dict` (HashMap):** agrupaciones intermedias (size → lista de paths) y final (hash de contenido → lista de paths), para indexar y detectar duplicados consultando sus claves en O(1) promedio.
- **`Queue`:** cola de archivos pendientes de procesar por los workers concurrentes.

## Memoización / Caching

- **Qué se almacena:** el hash calculado de cada archivo, junto a su `path`, `size` y `mtime` (fecha de modificación).
- **Por qué:** calcular el hash de un archivo grande es costoso; si el archivo no cambió desde el último escaneo, no tiene sentido volver a leerlo y hashearlo.
- **Cuándo se reutiliza:** en cada nuevo escaneo, si `size` y `mtime` de un archivo coinciden con lo cacheado, se reutiliza el hash almacenado en lugar de recalcularlo.
- **Invalidación:** si `size` o `mtime` difieren del valor cacheado, el cache para ese archivo se considera obsoleto y se recalcula el hash.
- **Mejora esperada:** en escaneos repetidos sobre un directorio mayormente sin cambios, el tiempo de procesamiento baja drásticamente al evitar I/O y cómputo de hash innecesarios.

## Concurrencia / Paralelismo

- **Tareas simultáneas:** lectura y hasheo de múltiples archivos en paralelo.
- **Por qué son independientes:** el procesamiento de un archivo no depende del resultado de procesar otro; solo se sincroniza al insertar el hash resultante en la estructura compartida (dict).
- **Mecanismo:**
  - `concurrent.futures.ThreadPoolExecutor` para la parte I/O-bound (lectura de archivos), aprovechando que el GIL se libera durante I/O.
  - `multiprocessing` (o `ProcessPoolExecutor`) para la parte CPU-bound (cálculo de hash sobre archivos grandes), evitando el cuello de botella del GIL.
- **Hipótesis y trade-offs (Problemas potenciales):** Se espera un fuerte overhead por IPC (comunicación entre procesos) y serialización de datos (pickling) al usar `multiprocessing`. Si el set de datos contiene miles de archivos muy pequeños (ej. 1KB), la versión paralela perderá en rendimiento frente a la secuencial o concurrente. Esta hipótesis se demostrará en el perfilado.
- **Hallazgo verificado en la Fase 5 (matiza el punto anterior):** `hashlib.sha256().update()` libera el GIL para buffers grandes (confirmado con un experimento aislado: 2 threads hasheando en simultáneo tardan ~la mitad que hacerlo secuencialmente). Esto significa que, para archivos por encima de cierto tamaño, `ThreadPoolExecutor` también paraleliza el cómputo del hash — y en las mediciones de la Fase 5 (24 archivos de 20MB) fue incluso más rápido que `ProcessPoolExecutor`, porque evita el costo de IPC/pickling. El "CPU-bound ⇒ necesariamente procesos" no es universal: depende de si la operación es una extensión en C que libera el GIL. Se mantiene `ProcessPoolExecutor` en la implementación porque el enunciado lo pide explícitamente, pero esta observación es material relevante para la sección de conclusiones/trade-offs de la presentación.
- **Umbral de ruteo dinámico:** el tamaño de archivo que decide entre `ThreadPoolExecutor` (archivos chicos) y `ProcessPoolExecutor` (archivos grandes) se implementa como una **variable/parámetro configurable** (no hardcodeado), calibrada empíricamente con los resultados de Scalene/cProfile de la Fase 5, y expuesta también por CLI para poder recalibrarla en la demo en vivo.

## Perfilado y medición

- **Herramientas:** `cProfile` (cuellos de botella por función), `memory_profiler` (uso de RAM), `py-spy` (perfilado en vivo sin modificar código).
- **Comparaciones a realizar:**
  1. Implementación inicial (fuerza bruta, secuencial) — baseline.
  2. Estructura optimizada (Pre-filtrado por tamaño + Hashing incremental, secuencial).
  3. Algoritmo optimizado / con cache (evitar rehash de archivos sin cambios).
  4. Versión concurrente (threads para I/O).
  5. Versión paralela (procesos para hashing CPU-bound).
- Se medirá tiempo de ejecución y memoria en cada versión, variando el volumen y el peso de los archivos, para evaluar escalabilidad y aislar el overhead de concurrencia/paralelismo.

## Comparación obligatoria

Dataset de medición: `data/mixed` — 210 archivos (200 de 4 KB + 10 de 5 MB, mezcla
I/O-bound / CPU-bound), 37 grupos de duplicados esperados (43 archivos redundantes).
Caché de disco del SO ya caliente (corrida de descarte previa) en todas las filas,
salvo donde se indica "frío". Memoria = pico del proceso (`mprof peak`).

| Versión                                                                             | Tiempo  | Memoria pico | Observación                                                                                                                     |
| ------------------------------------------------------------------------------------ | ------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| Implementación inicial (`baseline`, fuerza bruta)                                   | 0.96 s  | 36.6 MiB     | O(n²·s̄); los 10 archivos de 5 MB son los que más castigan cada comparación de par.                                              |
| Estructura optimizada (prefiltro por tamaño) + Algoritmo optimizado (hashing SHA-256) | 0.13 s  | 27.3 MiB     | ~7.2× más rápido que baseline. En este dataset el prefiltro no descarta candidatos (cada subgrupo comparte tamaño exacto); su beneficio con tamaños heterogéneos ya se midió en la Fase 2 (160 de 400 archivos hasheados, ver `README.md`). |
| Memoización/Caching (`cache`, 1er escaneo, frío)                                     | 0.16 s  | 27.6 MiB     | Mismo algoritmo que la fila anterior + registro en cache; el costo extra de persistir es marginal.                               |
| Concurrencia (`concurrente`, `ThreadPoolExecutor`, 4 workers)                        | 0.06 s  | 27.8 MiB     | Más rápido que la versión secuencial: `hashlib` libera el GIL en los archivos de 5 MB (ver hallazgo de la Fase 5).               |
| Paralelismo (`paralelo`, `ProcessPoolExecutor`, 4 workers)                           | 0.26 s  | 28.2 MiB     | Más lento que la versión con threads: el costo de IPC/pickling por archivo supera el beneficio, incluso con archivos de 5 MB.     |
| Versión final (`final`, 1er escaneo, frío; cache + ruteo dinámico)                   | 0.28 s  | 28.5 MiB     | Integra todo; rutea 200 archivos a threads y 10 a procesos según `--threshold` (2 MiB).                                          |
| Versión final (`final`, 2do escaneo, sin cambios)                                    | 0.03 s  | 24.2 MiB     | Cache 100% hit: ~9.3× más rápido que el primer escaneo de la versión final, y el mejor tiempo de toda la tabla.                  |

**Escalabilidad (tiempo vs. volumen de archivos):** medida por separado con
`scripts/benchmark_scalability.py` sobre archivos de 64 KiB fijos, de 50 a 800
archivos, para `baseline`, `estructura`, `concurrente` y `paralelo` (datos crudos en
`benchmark_results.csv`, que genera el script y no se versiona):

| n   | baseline  | estructura | concurrente | paralelo |
| --- | --------- | ---------- | ----------- | -------- |
| 50  | 0.053 s   | 0.012 s    | 0.009 s     | 0.165 s  |
| 100 | 0.207 s   | 0.024 s    | 0.013 s     | 0.157 s  |
| 200 | 1.670 s   | 0.090 s    | 0.043 s     | 0.194 s  |
| 400 | 5.684 s   | 0.103 s    | 0.053 s     | 0.249 s  |
| 800 | 15.435 s  | 0.213 s    | 0.117 s     | 0.376 s  |

- `baseline` crece claramente de forma cuadrática (×8 al pasar de 100 a 800 archivos,
  cerca del ×16 teórico de O(n²), con algo de ruido de medición).
- `estructura` y `concurrente` crecen de forma aproximadamente lineal, como predice
  O(n) + O(N) (N = bytes totales de los candidatos).
- `paralelo` queda dominado por el overhead fijo de `ProcessPoolExecutor` (arranque del
  pool + IPC por archivo) en todo el rango medido: con archivos de 64 KiB, ni a 800
  archivos compensa frente a `estructura` o `concurrente`. Coincide con el hallazgo de
  la Fase 5: el paralelismo con procesos solo se justifica con archivos bastante más
  grandes (en los experimentos de la Fase 5, a partir de ~2-20 MB), y aun así los
  threads suelen rendir igual o mejor para esta operación puntual (hashing con
  `hashlib`, que libera el GIL).
- El gráfico de estos datos para la presentación se arma en la Fase 7.
