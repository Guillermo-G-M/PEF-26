# Detector de archivos duplicados — Parcial 1 (PEF)

Versión: v1 (Fase 6 del roadmap completada).

Aplicación en Python que detecta archivos duplicados en un directorio, usada como caso
de estudio de técnicas de programación eficiente: análisis de complejidad, elección de
estructuras de datos, caching, concurrencia/paralelismo y perfilado.

Diseño detallado en [`doc.md`](doc.md). Plan de trabajo en [`roadmap.md`](roadmap.md).

**Parcial 3:** la documentación funcional, técnica y operativa está en
[`manual/`](manual/index.md) (sitio MkDocs publicado en
[guillermo-g-m.github.io/PEF-26](https://guillermo-g-m.github.io/PEF-26/)). Los controles
de calidad y eficiencia del CI se corren en local con `python scripts/checks.py all`
(ver [`manual/mantenimiento.md`](manual/mantenimiento.md)).

## Requisitos

- Python 3.12 o superior (versión del CI y de las dependencias fijadas en `requirements*.txt`).
- Dependencias de desarrollo: `pip install -r requirements.txt` (`pytest`, `memory_profiler`).
- Paquete instalado en modo editable: `pip install -e .` — necesario para el modo
  `paralelo` (`ProcessPoolExecutor` con `multiprocessing` en modo `spawn`, el único
  disponible en Windows).

## Estructura del proyecto

```
p1-dev/
├── doc.md                     Documento de diseño
├── roadmap.md                 Plan de fases de desarrollo
├── requirements.txt           Dependencias de desarrollo
├── pyproject.toml             Metadata para `pip install -e .` (requerido por el modo `paralelo`)
├── run.py                     Punto de entrada de la CLI
├── src/dupfinder/
│   ├── generator.py           Generador de datasets sintéticos
│   ├── cli.py                 Parseo de argumentos y despacho por modo
│   ├── fsutil.py              Recorrido perezoso de directorios
│   ├── report.py             Impresión del resultado de un escaneo
│   └── modes/                 Una estrategia de detección por archivo
│       ├── baseline.py        Fase 1 — comparación directa (fuerza bruta)
│       ├── structural.py      Fase 2 — pre-filtrado por tamaño + hashing incremental
│       ├── cached.py          Fase 3 — cache de hash por (path, size, mtime)
│       ├── concurrent_mode.py Fase 4 — ThreadPoolExecutor (I/O-bound)
│       ├── parallel_mode.py   Fase 5 — ProcessPoolExecutor (CPU-bound)
│       └── final.py           Fase 6 — todas las optimizaciones + ruteo dinámico
├── tests/
│   ├── test_generator.py
│   ├── test_baseline.py
│   ├── test_structural.py
│   ├── test_cached.py
│   ├── test_concurrent.py
│   ├── test_parallel.py
│   └── test_final.py
├── scripts/
│   └── benchmark_scalability.py  Mide tiempo vs. volumen de archivos por modo
└── data/                      Datasets generados (no versionado)
```

Implementados en v1: el generador de datasets y los 6 modos (`baseline`, `estructura`,
`cache`, `concurrente`, `paralelo`, `final`). No quedan stubs — todas las fases del
roadmap (0 a 6) están implementadas.

El paquete se instala en modo editable (`pip install -e .`, vía `pyproject.toml`) para
que `dupfinder` sea importable por nombre en cualquier proceso — Windows usa `spawn`
(no `fork`) para `multiprocessing`, y `ProcessPoolExecutor` necesita poder reimportar el
módulo de la función (`dupfinder.modes.parallel_mode`) en cada proceso hijo.

## Generador de datasets

Crea un conjunto de archivos sintéticos para las mediciones. El contenido aleatorio se
escribe por bloques de 1 MB para no cargar archivos grandes completos en memoria.

```
python -m dupfinder.generator --out data/set1 --count 1000 --dup-ratio 0.1 --min-size 1024 --max-size 1024 --seed 42
```

Ejecutar desde `src/`, o anteponiendo `src` al `PYTHONPATH`.

| Argumento     | Default | Descripción                                                    |
| ------------- | ------- | -------------------------------------------------------------- |
| `--out`       | —       | Directorio de salida (obligatorio).                            |
| `--count`     | —       | Cantidad total de archivos a generar (obligatorio).            |
| `--dup-ratio` | `0.1`   | Proporción de archivos que son copia de otro, en `[0.0, 1.0)`. |
| `--min-size`  | `1024`  | Tamaño mínimo por archivo, en bytes.                           |
| `--max-size`  | `1024`  | Tamaño máximo por archivo, en bytes.                           |
| `--seed`      | ninguna | Semilla para generación reproducible.                          |

`--min-size` igual a `--max-size` produce archivos de tamaño fijo; distintos, produce
tamaños uniformes en el rango. Este control permite armar los datasets contrastantes
de la Fase 5 (muchos archivos de 1 KB vs. pocos de 50 MB).

## CLI de detección

```
python run.py --modo <modo> --path <directorio> [--workers N] [--threshold BYTES] [--cache-file RUTA] [--batch-size N] [--profile]
```

| Argumento      | Default          | Descripción                                                                   |
| -------------- | ---------------- | ----------------------------------------------------------------------------- |
| `--modo`       | —                | `baseline`, `estructura`, `cache`, `concurrente`, `paralelo`, `final`.        |
| `--path`       | —                | Directorio a escanear.                                                        |
| `--workers`    | `cpu_count()`    | Workers para los modos `concurrente`, `paralelo` y `final`.                   |
| `--threshold`  | `2097152` (2 MiB) | Umbral de tamaño para el ruteo threads/procesos del modo `final` (calibrado en la Fase 5 del Parcial 1). |
| `--cache-file` | inferido         | Ruta del archivo de cache de hashes (modos `cache`/`final`); por defecto `<padre de --path>/.<nombre de --path>.cache.json`, sibling para no ser recorrido por el propio escaneo. |
| `--batch-size` | `5000`           | Archivos en vuelo a la vez en `concurrente`/`paralelo`/`final` (acota la cola/pool por lote; `0` o negativo = un único lote, sin batching). Agregado en el Parcial 2 — medición y análisis en `parcial-2/p2-dev/doc.md` ("Fase 5"). |
| `--profile`    | desactivado      | Ejecuta bajo `cProfile` e imprime las 20 funciones de mayor tiempo acumulado. |

El `--threshold` es configurable a propósito: se calibra con los datos de perfilado de
la Fase 5 y se ajusta en vivo durante la demostración.

## Servicio web (FastAPI, Parcial 2)

API REST sobre la misma lógica del modo `final` — no reimplementa el algoritmo, solo
lo expone como servicio. Justificación de por qué FastAPI en `parcial-2/p2-dev/doc.md`.

```
python -m uvicorn dupfinder.api:app --app-dir src --reload
```

| Endpoint      | Método | Body / respuesta                                                        |
| ------------- | ------ | ------------------------------------------------------------------------ |
| `/health`     | GET    | `{"status": "ok"}`                                                       |
| `/scan`       | POST   | Body: `{"path": "...", "workers": N, "threshold": N, "batch_size": N, "cache_file": "..."}` (todos opcionales salvo `path`). Respuesta: el mismo reporte del modo `final` en JSON (`duplicate_groups`, `cache_hits`/`cache_misses`, `hashed_with_threads`/`hashed_with_processes`, `elapsed_seconds`). |

```
curl -X POST http://127.0.0.1:8000/scan -H "Content-Type: application/json" \
  -d '{"path": "data/set1", "workers": 2, "threshold": 2000}'
```

Tests con `fastapi.testclient.TestClient` en `tests/test_api.py` (sin necesidad de
levantar el servidor).

**Observabilidad (OpenTelemetry, Parcial 2 Fase 8):** cada request queda instrumentado
automáticamente (`FastAPIInstrumentor`) y `/scan` además abre un span propio
(`dupfinder.scan`) con atributos de negocio (archivos escaneados, cache hits/misses,
ruteo threads/procesos, tiempo). Se exporta a **consola** (`ConsoleSpanExporter`,
sin backend externo) — al levantar el servidor, los spans se imprimen como JSON en
la misma terminal. Justificación completa en `parcial-2/p2-dev/doc.md`.

## Tests

```
python -m pytest tests/ -q
```

Corre con cobertura por defecto (`pyproject.toml`, `[tool.pytest.ini_options]`) y un
piso de **95%** (`--cov-fail-under=95`) — la corrida falla si la cobertura cae por
debajo. Al cierre del Parcial 2 (Fase 9): **100%**, 68 tests.

## Documentación (Sphinx)

Referencia de la API generada a partir de los docstrings del código (Parcial 2,
Fase 4). Buildear y abrir:

```
sphinx-build -b html docs docs/_build
```

Abrir `docs/_build/index.html` en el navegador. El source (`docs/*.rst`,
`docs/conf.py`) se versiona; el HTML generado (`docs/_build/`) no.

## Medición

- Tiempo: cada corrida imprime `tiempo: X s`.
- cProfile: `python run.py --modo baseline --path data/set1 --profile`
- Memoria (pico del proceso, sin decoradores):
  `mprof run --python python run.py --modo baseline --path data/set1` y luego `mprof peak`
- CPU + memoria línea por línea (Parcial 2, Fase 6):
  `scalene run -o perfil.json run.py --- --modo final --path data/set1 --workers 4`
  y luego `scalene view --cli -o perfil.json` (o parsear el JSON directamente —
  más confiable que la vista `--cli`, ver `parcial-2/p2-dev/doc.md` "Fase 6").

## Cómo probar la solución

Sección incremental: se completa a medida que avanza cada fase. Todos los comandos se
ejecutan desde `p1-dev/`. Instalar dependencias una vez: `pip install -r requirements.txt`.

### Fase 0 — Estructura, generador y CLI

**Tests automáticos del generador**

```
python -m pytest tests/test_generator.py -q
```

Cubre: cantidad exacta de archivos generados, presencia de duplicados, rechazo de
`--dup-ratio >= 1.0` y de tamaños inválidos (`min > max`).

**Generador manual**

```
python -c "import sys; sys.path.insert(0,'src'); from dupfinder.generator import main; main(['--out','data/set1','--count','100','--dup-ratio','0.2','--min-size','1024','--max-size','1024','--seed','42'])"
```

Verificar:

- `data/set1` contiene 100 archivos `file_000000.bin` … `file_000099.bin`.
- Con el mismo `--seed`, dos corridas producen contenido idéntico byte a byte.
- `--min-size == --max-size` → todos del mismo tamaño; rango distinto → tamaños variados.

**CLI: parseo y despacho**

```
python run.py --help
python run.py --modo xxx --path data/set1            # argparse rechaza, exit 2
```

Verificar: `--help` lista los 6 modos y los flags `--workers`, `--threshold`,
`--cache-file`, `--profile`; los acentos se muestran correctamente (stdout/stderr
forzados a UTF-8). En esta fase (0) los 6 modos todavía eran stubs que lanzaban
`NotImplementedError` indicando su fase — cada uno se implementó y probó en su propia
fase (ver las secciones siguientes); a partir de la Fase 6 no queda ningún stub.

### Fase 1 — Baseline (comparación directa)

**Tests automáticos del baseline**

```
python -m pytest tests/test_baseline.py -q
```

Cubre: detecta todos los archivos redundantes, cada grupo tiene contenido idéntico,
caso sin duplicados devuelve `[]`, directorio vacío devuelve `[]` y `n == 0`.

**Suite completa**

```
python -m pytest tests/ -q          # 7 passed
```

**Corrida real y correctitud**

```
python -c "import sys; sys.path.insert(0,'src'); from dupfinder.generator import main; main(['--out','data/b1','--count','200','--dup-ratio','0.25','--min-size','2048','--max-size','8192','--seed','3'])"
python run.py --modo baseline --path data/b1
```

Verificar: con `--count 200` y `--dup-ratio 0.25`, la línea "archivos redundantes" debe
ser exactamente `int(200 * 0.25) = 50` (invariante independiente del agrupamiento).

**Casos borde**

```
python run.py --modo baseline --path data/no_existe   # "error: ... no es un directorio", exit 1
mkdir data/vacio ; python run.py --modo baseline --path data/vacio   # 0 archivos, 0 grupos
```

**Medición baseline** (línea base para comparar en fases siguientes)

```
python run.py --modo baseline --path data/b1 --profile
mprof run --python python run.py --modo baseline --path data/b1
mprof peak
```

Qué observar:

- **Tiempo**: repetir con `--count` 100 / 200 / 400 (mismo tamaño de archivo). El tiempo
  se multiplica aproximadamente ×4 al duplicar `n` → confirma el crecimiento O(n²·s̄).
- **cProfile**: el mayor tiempo acumulado cae en la lectura de archivos (`_read`), una
  por cada par comparado.
- **mprof peak**: memoria pico baja y ~constante al variar `n` (solo 2 archivos en RAM a
  la vez).

### Fase 2 — Pre-filtrado por tamaño + hashing incremental

**Tests automáticos**

```
python -m pytest tests/test_structural.py -q
```

Cubre: el modo `estructura` da el mismo resultado que `baseline` sobre el mismo dataset
(cruce de validación), el pre-filtrado reduce la cantidad de archivos hasheados,
`hash_file` coincide con `hashlib.sha256` directo (con y sin chunking), caso sin
duplicados y directorio vacío.

**Suite completa**

```
python -m pytest tests/ -q          # 13 passed
```

**Corrida real y comparación contra baseline**

```
python -c "import sys; sys.path.insert(0,'src'); from dupfinder.generator import main; main(['--out','data/b2','--count','400','--dup-ratio','0.2','--min-size','2048','--max-size','8192','--seed','9'])"
python run.py --modo baseline --path data/b2
python run.py --modo estructura --path data/b2
```

Verificar: ambos modos reportan los mismos "grupos de duplicados" y "archivos
redundantes" sobre el mismo dataset; `estructura` además imprime "archivos hasheados: X
de Y", con `X < Y` (el pre-filtrado evitó hashear archivos con tamaño único).

**Medición: comparar contra el baseline**

```
python run.py --modo baseline --path data/b2 --profile
python run.py --modo estructura --path data/b2 --profile
mprof run --python python run.py --modo estructura --path data/b2 ; mprof peak
```

Qué observar:

- **Tiempo**: `estructura` debería ser notoriamente más rápido que `baseline` sobre el
  mismo dataset, y la ventaja crece con `n` (baseline es O(n²·s̄), estructura es ~O(n+N)
  con N = bytes de los candidatos).
- **cProfile**: en `estructura` el tiempo se concentra en `hash_file` (lectura por
  chunks) solo para los archivos candidatos, no para los `n` totales.
- **mprof peak**: memoria similar o menor a la del baseline (un archivo a la vez por
  hash, vs. dos por comparación), y constante respecto de `n`.

### Fase 3 — Caching de hash por (path, size, mtime)

**Tests automáticos**

```
python -m pytest tests/test_cached.py -q
```

Cubre: con cache vacío da el mismo resultado que `estructura` (0 hits); un segundo
escaneo sin cambios reutiliza el 100% de los hashes (0 misses); modificar un archivo y
tocar su `mtime` invalida solo esa entrada (1 miss, el resto hits); `load_cache` sobre
un archivo inexistente devuelve `{}`; round-trip de `save_cache`/`load_cache`; el
archivo de cache por defecto es sibling del directorio escaneado; `run()` persiste el
cache a disco.

**Suite completa**

```
python -m pytest tests/ -q          # 20 passed
```

**Corrida real: escaneo frío vs. escaneo repetido**

```
python -c "import sys; sys.path.insert(0,'src'); from dupfinder.generator import main; main(['--out','data/b3','--count','300','--dup-ratio','0.2','--min-size','4096','--max-size','4096','--seed','21'])"
python run.py --modo cache --path data/b3      # 1er escaneo: cache frío
python run.py --modo cache --path data/b3      # 2do escaneo: directorio sin cambios
```

Verificar: el primer escaneo reporta `cache: 0 hits, 300 misses de 300 candidatos`; el
segundo, sin tocar ningún archivo, reporta `cache: 300 hits, 0 misses de 300
candidatos`, con los mismos "grupos de duplicados" en ambos. El archivo de cache queda
en `data/.b3.cache.json` (no es contado en "archivos escaneados").

**Invalidación**

```
touch data/b3/file_000000.bin          # cambia el mtime sin cambiar contenido
python run.py --modo cache --path data/b3
```

Verificar: ese escaneo reporta exactamente 1 miss (el resto hits) — el cambio de
`mtime` invalida solo la entrada afectada, no todo el cache.

**Medición: comparar contra estructura (sin cache) y entre escaneo frío/caliente**

```
python run.py --modo cache --path data/b3 --profile    # 1er escaneo (frío)
python run.py --modo cache --path data/b3 --profile    # 2do escaneo (caliente)
```

Qué observar:

- **Tiempo**: el escaneo caliente (100% hits) debería ser notoriamente más rápido que el
  frío sobre el mismo dataset, al evitar la lectura y el hasheo de cada candidato.
- **cProfile**: en el escaneo caliente, `hash_file` casi no aparece; el costo se
  concentra en `stat()` (metadata) en vez de lectura de contenido.
- La mejora depende de qué proporción del directorio no cambió entre escaneos: si todos
  los archivos cambiaron, el cache no aporta (todo miss) y el costo iguala al de
  `estructura`.

### Fase 4 — Concurrencia con `Queue` + `ThreadPoolExecutor`

**Tests automáticos**

```
python -m pytest tests/test_concurrent.py -q
```

Cubre: coincide con `estructura` sobre el mismo dataset; 1 worker vs. 8 workers dan el
mismo resultado; con 16 workers sobre 200 archivos no se pierde ningún duplicado (el
`Lock` protege el `dict` compartido); `workers=0` no rompe (se fuerza un mínimo de 1);
sin duplicados y directorio vacío.

**Suite completa**

```
python -m pytest tests/ -q          # 26 passed
```

**Corrida real y correctitud entre cantidades de workers**

```
python -c "import sys; sys.path.insert(0,'src'); from dupfinder.generator import main; main(['--out','data/b4','--count','600','--dup-ratio','0.3','--min-size','4096','--max-size','4096','--seed','13'])"
python run.py --modo estructura  --path data/b4
python run.py --modo concurrente --path data/b4 --workers 1
python run.py --modo concurrente --path data/b4 --workers 8
```

Verificar: los tres reportan los mismos "grupos de duplicados" (151) y "archivos
redundantes" (180) sobre el dataset de ejemplo — ningún duplicado se pierde ni se
duplica por condición de carrera al variar `--workers`.

**Medición: tiempo vs. cantidad de workers — ⚠️ cuidado con el caché de disco**

```
python run.py --modo concurrente --path data/b4 --workers 1
python run.py --modo concurrente --path data/b4 --workers 2
python run.py --modo concurrente --path data/b4 --workers 4
python run.py --modo concurrente --path data/b4 --workers 8
```

**Importante:** la primera lectura de cada archivo después de generarlo es I/O real a
disco (caché de SO frío); las siguientes lecturas del mismo archivo las resuelve el
caché de páginas del SO casi instantáneamente, sin tocar el disco. Esto domina
cualquier comparación entre cantidades de `--workers` si no se controla: corrida de
ejemplo sobre 600 archivos, primera vez con `--workers 1` (frío) dio `tiempo: 3.3 s`;
repitiendo la misma corrida sin cambiar nada (caliente) dio `tiempo: 0.06 s` — una
diferencia de más de 50x que no tiene nada que ver con threads.

Para medir el efecto real de la concurrencia: ejecutar una corrida de descarte primero
(para calentar el caché) y comparar recién a partir de la segunda:

```
python run.py --modo concurrente --path data/b4 --workers 4   # descartar (calienta el caché)
python run.py --modo concurrente --path data/b4 --workers 1   # medir
python run.py --modo concurrente --path data/b4 --workers 2
python run.py --modo concurrente --path data/b4 --workers 4
python run.py --modo concurrente --path data/b4 --workers 8
```

Qué observar (con caché ya caliente):

- Con el dataset de ejemplo (600 archivos de 4 KB) **no se observó mejora al aumentar
  `--workers`** — incluso un leve empeoramiento con 8 (overhead de hilos/`Lock`). A esa
  escala, cada archivo se hashea en una sola llamada a `update()` (4 KB < chunk de
  64 KB), muy por debajo del umbral al que `hashlib` libera el GIL (ver nota de la
  Fase 5) — por eso domina el overhead de scheduling, no el cómputo.
- **Corrección importante (ver Fase 5):** la primera conclusión de esta sección decía
  que "los threads no aceleran cómputo CPU-bound, solo solapan I/O". Eso vale para
  archivos chicos como los de esta prueba, pero **no es cierto en general**: con
  archivos más grandes, `hashlib.sha256().update()` libera el GIL durante el cómputo en
  C, y los threads sí paralelizan el hasheo real. La Fase 5 lo mide y corrige esta
  afirmación con datos.
- **cProfile** (`--profile`): con pocos workers y caché frío, el tiempo se reparte en
  llamadas al sistema de lectura; con caché caliente, se concentra en `hash_file`
  (cómputo SHA-256) independientemente de `--workers`.

### Fase 5 — Paralelismo con `ProcessPoolExecutor`

**Tests automáticos**

```
python -m pytest tests/test_parallel.py -q
```

Cubre: coincide con `estructura` sobre el mismo dataset; 1 worker vs. 4 workers dan el
mismo resultado; con 4 workers sobre 100 archivos no se pierde ningún duplicado;
`workers=0` no rompe; sin duplicados y directorio vacío. Como estos tests sí lanzan
procesos reales (no solo threads), requieren el paquete instalado (`pip install -e .`);
si no, fallan con `ModuleNotFoundError` al reimportar `dupfinder` en el proceso hijo.

**Suite completa**

```
pip install -e .
python -m pytest tests/ -q          # 32 passed
```

**Experimento 1: muchos archivos chicos (IPC domina) — confirma la hipótesis de `doc.md`**

```
python -c "import sys; sys.path.insert(0,'src'); from dupfinder.generator import main; main(['--out','data/many_small','--count','3000','--dup-ratio','0.1','--min-size','1024','--max-size','1024','--seed','31'])"
python run.py --modo estructura --path data/many_small   # descartar (calienta caché), luego medir de nuevo
python run.py --modo paralelo   --path data/many_small --workers 4
```

Resultado medido (3000 archivos de 1 KB, caché caliente): `estructura` (secuencial)
**0.27 s** vs. `paralelo` con 1/2/4/8 workers entre **0.73 s y 1.05 s** — más lento que
el secuencial en todos los casos. El costo fijo de serializar (pickle) cada archivo y
su resultado por IPC, más el arranque del pool de procesos, supera ampliamente el
cómputo real (hashear 1 KB es casi instantáneo). Confirma la hipótesis de `doc.md`:
con datasets de archivos chicos, el paralelismo con procesos pierde frente a lo
secuencial.

**Experimento 2: pocos archivos grandes (el cómputo domina) — aquí si gana el paralelismo**

```
python -c "import sys; sys.path.insert(0,'src'); from dupfinder.generator import main; main(['--out','data/few_large','--count','24','--dup-ratio','0.25','--min-size','20971520','--max-size','20971520','--seed','32'])"
python run.py --modo estructura --path data/few_large    # descartar (calienta caché), luego medir de nuevo
python run.py --modo paralelo   --path data/few_large --workers 4
```

Resultado medido (24 archivos de 20 MB, caché caliente): `estructura` **≈1.1 s**,
`paralelo` con 4 workers **≈0.44–0.53 s** (~2.3× más rápido). Con pocos archivos pero
pesados, el tiempo de cómputo (hashear 20 MB) supera ampliamente el overhead fijo de
IPC por archivo, y el paralelismo gana.

**Hallazgo adicional (corrige una conclusión de la Fase 4): `hashlib` libera el GIL en
archivos grandes, y los threads también paralelizan el hasheo**

Repitiendo el experimento 2 con `concurrente` (threads) en vez de `paralelo`:

```
python run.py --modo concurrente --path data/few_large --workers 4
```

Resultado (mismo dataset, 3 repeticiones): `concurrente` **≈0.33–0.40 s**, más rápido
incluso que `paralelo` (≈0.49–0.53 s) y muy por encima de `estructura` (≈1.1 s).

Esto llevó a verificar con un experimento aislado si `hashlib.sha256().update()`
libera el GIL para buffers grandes:

```python
import time, hashlib, threading

data = b"x" * (50 * 1024 * 1024)


def hash_once():
    h = hashlib.sha256()
    for i in range(0, len(data), 65536):
        h.update(data[i : i + 65536])


t0 = time.perf_counter()
hash_once()
hash_once()
t_seq = time.perf_counter() - t0
t0 = time.perf_counter()
a, b = threading.Thread(target=hash_once), threading.Thread(target=hash_once)
a.start()
b.start()
a.join()
b.join()
t_par = time.perf_counter() - t0
print(t_seq, t_par)  # 0.206s secuencial vs. 0.108s con 2 threads concurrentes
```

Confirmado: **sí libera el GIL** (implementación en C de OpenSSL) para buffers por
encima de un umbral chico, así que dos threads hasheando en simultáneo corren en
paralelo real. Esto corrige la lectura de la Fase 4 ("los threads no aceleran
CPU-bound"): eso solo valía para archivos de 4 KB, donde cada archivo se hashea en una
única llamada `update()` demasiado chica para cruzar ese umbral; con archivos de 2 MB
o más (que generan ~30+ llamadas `update()` de 64 KB cada una), los threads sí
paralelizan el cómputo — y además evitan el costo de IPC/pickling que sí paga
`ProcessPoolExecutor`, por eso ganan en este caso concreto.

**Calibración del umbral de tamaño** (usado por `--threshold` en la Fase 6): con los
datos de arriba, el punto de quiebre está entre 4 KB (ninguna concurrencia ayuda) y
2 MB (ambas ayudan, threads mejor). Se fija el default de `--threshold` en **2 MiB**
(`2 * 1024 * 1024` bytes) como primera calibración razonable — por debajo, ni threads
ni procesos compensan su overhead frente al secuencial/cacheado; por encima, conviene
paralelizar. La Fase 6 puede refinarlo con `Scalene`/más mediciones, y a la luz de este
hallazgo, evaluar directamente threads en vez de procesos para la rama "archivo
grande", ya que evitan el costo de IPC sin perder paralelismo real en este caso.

### Fase 6 — Versión final: cache + ruteo dinámico threads/procesos

**Tests automáticos**

```
python -m pytest tests/test_final.py -q
```

Cubre: coincide con `estructura` en frío; sobre un dataset armado a mano con 2
archivos chicos (100 bytes) y 2 grandes (10000 bytes) y `--threshold 1000`, rutea
exactamente 2 a threads y 2 a procesos, y detecta ambos grupos; un segundo escaneo sin
cambios reutiliza el 100% del cache y no rutea nada (0 threads, 0 procesos); `workers=0`
no rompe; sin duplicados y directorio vacío.

**Suite completa**

```
python -m pytest tests/ -q          # 38 passed
```

**Corrida real con dataset mixto (chicos + grandes) y las dos capas (cache + ruteo)**

```
python -c "
import sys; sys.path.insert(0,'src')
from dupfinder.generator import main
main(['--out','data/mixed/small','--count','200','--dup-ratio','0.2','--min-size','4096','--max-size','4096','--seed','41'])
main(['--out','data/mixed/large','--count','10','--dup-ratio','0.3','--min-size','5242880','--max-size','5242880','--seed','42'])
"
python run.py --modo estructura --path data/mixed   # referencia (recorre subcarpetas igual)
python run.py --modo final      --path data/mixed --workers 4   # 1er escaneo: cache frío
python run.py --modo final      --path data/mixed --workers 4   # 2do escaneo: sin cambios
```

`data/mixed/small` y `data/mixed/large` son subcarpetas del mismo `--path`;
`iter_files` las recorre igual (usa `os.walk`), así que `--path data/mixed` ve los 210
archivos de ambas.

Verificar:

- Los tres comandos reportan los mismos 37 "grupos de duplicados" / 43 "archivos
  redundantes".
- 1er escaneo de `final`: `cache: 0 hits, 210 misses de 210 candidatos` y
  `ruteo (umbral): 200 con threads (<= 2097152 bytes), 10 con procesos (> 2097152 bytes)`
  — los 200 archivos de 4 KB van a threads, los 10 de 5 MB van a procesos.
- 2do escaneo (sin tocar nada): `cache: 210 hits, 0 misses` y
  `ruteo (umbral): 0 con threads (...), 0 con procesos (...)` — con todo en cache no
  hace falta rutear ni hashear nada.

**Medición: tabla comparativa completa (todas las versiones, mismo dataset)**

```
python run.py --modo baseline    --path data/mixed --profile
mprof run --python python run.py --modo baseline --path data/mixed ; mprof peak
# repetir para: estructura, cache, concurrente --workers 4, paralelo --workers 4,
# final --workers 4 (primero borrando data/.mixed.cache.json para medir el 1er escaneo)
```

Resultados medidos (caché de SO caliente salvo que se indique; detalle completo con
observaciones en `doc.md`, sección "Comparación obligatoria"):

| Versión                                   | Tiempo | Memoria pico |
| ------------------------------------------ | ------ | ------------ |
| `baseline` (fuerza bruta)                  | 0.96 s | 36.6 MiB     |
| `estructura` (prefiltro + hashing)          | 0.13 s | 27.3 MiB     |
| `cache` (1er escaneo, frío)                 | 0.16 s | 27.6 MiB     |
| `concurrente` (threads, 4 workers)          | 0.06 s | 27.8 MiB     |
| `paralelo` (procesos, 4 workers)            | 0.26 s | 28.2 MiB     |
| `final` (1er escaneo, frío)                 | 0.28 s | 28.5 MiB     |
| `final` (2do escaneo, sin cambios)          | 0.03 s | 24.2 MiB     |

Qué observar: `final` en frío es más lento que `estructura` sola (overhead de
gestionar cache + dos pools), pero en caliente (segundo escaneo) es el mejor tiempo de
toda la tabla — el valor de integrar todo se ve en el uso repetido, no en un único
escaneo aislado.

**Escalabilidad (tiempo vs. volumen de archivos)**

```
python scripts/benchmark_scalability.py
```

Genera datasets de 50/100/200/400/800 archivos de 64 KiB y mide `baseline`,
`estructura`, `concurrente` y `paralelo` sobre cada uno; guarda `benchmark_results.csv`
en la raíz de `p1-dev/`. Confirma: `baseline` crece cuadrático (×8 entre 100 y 800
archivos), `estructura`/`concurrente` crecen aproximadamente lineal, y `paralelo` no
compensa su overhead fijo en ningún punto del rango con archivos de este tamaño — datos
y análisis completos en `doc.md`.

## Estado por fase

| Fase | Descripción                                   | Estado     |
| ---- | --------------------------------------------- | ---------- |
| 0    | Estructura, generador de datasets y CLI       | Completada |
| 1    | Baseline: comparación directa `O(n²·s̄)`       | Completada |
| 2    | Pre-filtrado por tamaño + hashing incremental | Completada |
| 3    | Caching de hash por `(path, size, mtime)`     | Completada |
| 4    | Concurrencia con `ThreadPoolExecutor`         | Completada |
| 5    | Paralelismo con `ProcessPoolExecutor`         | Completada |
| 6    | Versión final y tabla comparativa             | Completada |
| 7    | Documentación final y presentación            | Pendiente  |
