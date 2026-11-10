# API y contratos

## CLI

```text
python run.py --modo {baseline,estructura,cache,concurrente,paralelo,final} --path DIR
              [--workers N] [--threshold BYTES] [--cache-file RUTA] [--batch-size N] [--profile]
```

| Situación | Salida | Código |
|---|---|---|
| Escaneo correcto | Grupos, redundantes, tiempo (y cache/ruteo según el modo) | 0 |
| `--path` no es un directorio | `error: ... no es un directorio` en stderr | 1 |
| Modo o argumento inválido | Mensaje de `argparse` | 2 |

## Servicio REST

Con el servidor levantado, la documentación interactiva (OpenAPI) está en
`http://127.0.0.1:8000/docs`.

### `GET /health`

```json
{"status": "ok"}
```

### `POST /scan`

Entrada (`ScanRequest`; solo `path` es obligatorio):

| Campo | Tipo | Default | Validación |
|---|---|---|---|
| `path` | string | — | Directorio existente dentro de `DUPFINDER_SCAN_ROOT` (relativo a esa raíz o absoluto) |
| `workers` | int | cantidad de CPUs | Mayor o igual a 1 |
| `threshold` | int | 2097152 | Bytes |
| `batch_size` | int o null | 5000 | `null` o ≤ 0 = un solo lote |
| `cache_file` | string o null | junto al directorio | Ruta del cache, dentro de `DUPFINDER_SCAN_ROOT` |

Salida (`ScanResponse`):

```json
{
  "path": "data/demo",
  "files_scanned": 210,
  "duplicate_groups": [["data/demo/a.bin", "data/demo/b.bin"]],
  "redundant_files": 43,
  "cache_hits": 0,
  "cache_misses": 210,
  "hashed_with_threads": 200,
  "hashed_with_processes": 10,
  "elapsed_seconds": 0.28
}
```

Errores:

| Código | Causa |
|---|---|
| 400 | `path` no es un directorio |
| 403 | `path` o `cache_file` fuera de `DUPFINDER_SCAN_ROOT` (incluye `..` y enlaces simbólicos) |
| 422 | Cuerpo inválido (falta `path`, `workers` < 1, tipos incorrectos) |

Ejemplo:

```bash
curl -X POST http://127.0.0.1:8000/scan -H "Content-Type: application/json" \
  -d '{"path": "data/set1", "workers": 2}'
```

## Uso como biblioteca

```python
from pathlib import Path
from dupfinder.modes import final

groups, n, hits, n_threads, n_processes = final.find_duplicates(
    Path("data/set1"), workers=4, threshold=2 * 1024 * 1024, cache={}
)
```

| Función | Devuelve | Excepciones |
|---|---|---|
| `structural.hash_file(path)` | SHA-256 en hexadecimal | `OSError` si no se puede leer |
| `structural.find_duplicates(root)` | `(grupos, n, hasheados)` | — |
| `final.find_duplicates(root, workers, threshold, cache, batch_size=None)` | `(grupos, n, hits, threads, procesos)` | — |
| `generator.generate_dataset(...)` | `None` | `ValueError` si `count < 1`, `dup_ratio` fuera de [0, 1) o tamaños inválidos |
| `scanutil.require_directory(path)` | `None` | `SystemExit(1)` si no es un directorio |

La referencia completa, generada desde los docstrings, es la de Sphinx.
