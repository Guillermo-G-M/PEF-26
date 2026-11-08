# Roadmap de desarrollo – Parcial 1

Basado en `doc.md`. Sistema de detección de duplicados, en Python.

## Fase 0 — Setup

- [ ] Estructura del proyecto (`src/`, `tests/`, `data/` con archivos de prueba generados sintéticamente en distintos volúmenes: ej. 100, 1.000, 10.000 archivos, con % configurable de duplicados **y tamaño de archivo configurable** — este último es necesario para el test de la Fase 5, ej. miles de archivos de 1KB vs. docenas de 50MB).
- [ ] Script generador de dataset de prueba.
- [ ] Implementar la interfaz de línea de comandos (CLI) con `argparse` (ej. `--modo baseline`, `--modo concurrente`) para facilitar las demostraciones en vivo y el perfilado.

## Fase 1 — Implementación inicial (baseline)

- [x] Comparación directa por contenido leyendo el archivo completo, secuencial, todos contra todos (O(n²·s̄)). Implementado en `src/dupfinder/modes/baseline.py`.
- [x] Medición baseline: tiempo (informado por cada corrida) y `--profile` (cProfile); memoria vía `mprof` / `memory_profiler` documentado en `README.md`.

## Fase 2 — Optimización de estructura y algoritmo

- [x] 2.1: Implementar pre-filtrado por tamaño leyendo metadatos (agrupación en `dict` de size → paths en O(n)). Implementado en `group_by_size`.
- [x] 2.2: Implementar hashing (SHA-256) incremental con lectura por chunks (buffers de 64KB) _solo_ sobre los grupos con colisión de tamaño. Guardar en `dict` (hash → lista de paths). Implementado en `hash_file` / `find_duplicates`, `src/dupfinder/modes/structural.py`.
- [x] Medir y comparar contra baseline (tiempo, memoria constante por archivo, escalabilidad con distintos volúmenes). Verificado: mismo resultado que baseline (grupos/redundantes) en dataset cruzado; `archivos hasheados` muestra la reducción del pre-filtrado.

## Fase 3 — Caching inteligente

- [x] Cache de hash por archivo, clave `(path, size, mtime)`. Implementado en `src/dupfinder/modes/cached.py`, persistido en JSON sibling al directorio escaneado (`--cache-file` para elegir otra ruta).
- [x] Invalidación cuando `size`/`mtime` cambian. `hash_with_cache` recalcula y reemplaza la entrada si no coinciden.
- [x] Medir mejora en escaneo repetido (segundo escaneo sobre mismo directorio sin cambios). Verificado: 300 archivos, primer escaneo 0 hits/300 misses, segundo escaneo (sin cambios) 300 hits/0 misses, mismos 53 grupos.

## Fase 4 — Concurrencia (I/O-bound)

- [x] `Queue` de archivos pendientes + `ThreadPoolExecutor` para lectura/hasheo concurrente. Implementado en `src/dupfinder/modes/concurrent_mode.py`.
- [x] Medir tiempo vs. versión secuencial con distinta cantidad de workers.
- [x] Documentar problemas encontrados:
  - **Sincronización:** el `dict` compartido (`by_hash`) se protege con `threading.Lock`, porque `dict[clave].append(valor)` no es atómico aunque el GIL serialice cada bytecode individual.
  - **Caché de disco domina la medición:** en caliente (SO ya cacheó los archivos) no se observó mejora con más workers (e incluso una leve pérdida por overhead de hilos/`Lock`) porque el cuello de botella pasa a ser el hashing CPU-bound, serializado por el GIL. Solo en frío (primera lectura, I/O real a disco) la concurrencia mostró una ganancia drástica. Conclusión: hay que medir con el caché en el mismo estado en ambas corridas para que la comparación sea válida, y el beneficio real de threads está limitado a la espera de I/O, no al cómputo del hash — motivo por el cual la Fase 5 necesita procesos, no más threads, para la parte CPU-bound.

## Fase 5 — Paralelismo (CPU-bound)

- [x] `ProcessPoolExecutor`/`multiprocessing` para hashing de archivos grandes. Implementado en `src/dupfinder/modes/parallel_mode.py` (mismo prefiltro por tamaño que la Fase 2; hashing de candidatos repartido entre procesos). Requirió empaquetar el proyecto (`pyproject.toml` + `pip install -e .`) para que `dupfinder` sea reimportable por los procesos hijo de `spawn` en Windows.
- [x] Testear con datasets de distintos pesos (3000 archivos de 1KB vs. 24 archivos de 20MB) para aislar y demostrar el overhead del paralelismo (IPC y pickling). Confirmado: con 1KB, procesos pierden contra secuencial (0.7-1.05s vs. 0.27s); con 20MB, procesos ganan (~0.44-0.53s vs. ~1.1s secuencial).
- [x] Medir tiempo vs. versión con threads. **Hallazgo que corrige una conclusión de la Fase 4:** con archivos de 20MB, `concurrente` (threads) fue más rápido que `paralelo` (procesos) — ~0.33-0.40s vs. ~0.49-0.53s, repetido 3 veces. Se verificó con un experimento aislado que `hashlib.sha256().update()` libera el GIL para buffers grandes (confirmado: 2 threads concurrentes hashean en ~0.108s vs. 0.206s secuencial para el mismo trabajo). Es decir: el hasheo SÍ es paralelizable con threads cuando el archivo es lo bastante grande como para generar varias llamadas `update()` de 64KB; con archivos de 4KB (una sola llamada `update()` chica) no hay beneficio, que es lo que se había observado en la Fase 4.
- [x] A partir de estas mediciones, calibrar el "umbral de tamaño" que decide threads vs. procesos. `DEFAULT_THRESHOLD_BYTES` fijado en 2 MiB en `cli.py` (antes 5 MB, sin base empírica). Nota para la Fase 6: dado el hallazgo de que `hashlib` libera el GIL, conviene evaluar usar threads (no procesos) también para la rama de archivos "grandes" en la versión final, ya que evitan el costo de IPC sin perder paralelismo real en este caso concreto.

## Fase 6 — Comparación final y tabla de resultados

- [x] Integrar en una "versión final" todas las optimizaciones anteriores: pre-filtrado por tamaño + hashing incremental + cache + selección dinámica entre `ThreadPoolExecutor` y `ProcessPoolExecutor` según el peso de los archivos del dataset (en base a la hipótesis validada en la Fase 5). El umbral de decisión es una **variable configurable** (`--threshold`, default 2 MiB calibrado en la Fase 5), no un valor fijo en el código. Implementado en `src/dupfinder/modes/final.py`: solo los cache-misses se rutean por tamaño (los cache-hits no necesitan hashear nada).
- [x] Completar tabla obligatoria (Baseline / Estructura optimizada / Algoritmo optimizado / Concurrencia-Paralelismo / Versión final) con tiempo, memoria y observaciones. Tabla completa en `doc.md` (sección "Comparación obligatoria"), medida sobre `data/mixed` (210 archivos: 200×4KB + 10×5MB).
- [x] Gráficos de escalabilidad (tiempo vs. volumen de archivos) para cada versión. Datos recolectados con `scripts/benchmark_scalability.py` → `benchmark_results.csv` (50 a 800 archivos, baseline/estructura/concurrente/paralelo); confirma O(n²) en baseline, ~O(n) en estructura/concurrente, y que `paralelo` no compensa su overhead fijo en todo ese rango con archivos de 64KiB. El gráfico en sí (imagen para las slides) se arma en la Fase 7.

## Fase 7 — Documentación y presentación

- [ ] Completar justificaciones de complejidad, estructuras, caching y concurrencia (ya en `doc.md`, ampliar con resultados obtenidos).
- [ ] Armar PowerPoint según estructura sugerida del enunciado (10 secciones).
- [ ] Preparar demo en vivo usando los flags de `argparse`.

## Orden de trabajo

Fase 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7, midiendo al cierre de cada fase antes de pasar a la siguiente.
