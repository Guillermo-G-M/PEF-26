# Pruebas

## Estrategia

| Nivel | Qué se verifica | Herramienta |
|---|---|---|
| Unitarias | Funciones aisladas: `hash_file`, `group_by_size`, `_batches`, cache | pytest |
| Equivalencia entre modos | Todos los modos dan los mismos grupos que `estructura` sobre el mismo dataset | pytest + generador con semilla |
| Integración | CLI completa (`main`) y API (`TestClient` de FastAPI, sin levantar servidor) | pytest, httpx |
| Concurrencia | Mismo resultado con 1, 4, 8 o 16 workers (sin condiciones de carrera) | pytest |
| Rendimiento y memoria | Tiempos y picos de memoria (ver [Rendimiento](rendimiento.md)) | pytest-benchmark, tracemalloc |

Los datasets se generan en directorios temporales (`tmp_path`) con semilla fija:
los resultados son reproducibles y las pruebas no dependen de archivos del repositorio.
El invariante principal es que la cantidad de redundantes es exactamente
`int(count * dup_ratio)`, independiente del modo.

## Casos de prueba

| Archivo | Pruebas | Casos principales |
|---|---|---|
| `test_generator.py` | 7 | Cantidad exacta, duplicados presentes, rechazo de parámetros inválidos, reproducibilidad por semilla |
| `test_baseline.py` | 5 | Detecta todos los redundantes, sin duplicados, directorio vacío |
| `test_structural.py` | 8 | Igual a `baseline`, el prefiltro reduce lo hasheado, `hash_file` igual a `hashlib` con y sin chunks |
| `test_cached.py` | 8 | Segundo escaneo 100% hits, un `touch` invalida solo una entrada, round-trip del JSON |
| `test_concurrent.py` | 8 | Igual a `estructura` con 1/8/16 workers, `workers=0` no rompe |
| `test_parallel.py` | 9 | Ídem con procesos reales |
| `test_final.py` | 8 | Ruteo exacto por umbral, cache caliente no rutea nada, casos borde |
| `test_batching.py` | 5 | Con y sin batching el resultado es el mismo en los tres modos con pool |
| `test_cli.py` | 5 | Defaults, modo inválido, despacho, path inexistente, `--profile` |
| `test_api.py` | 9 | `/health`, `/scan` cumple el invariante, reutiliza cache, ruta relativa a la raíz, 400, 422 y 403 (fuera de la raíz, `..`, `cache_file` externo) |

## Resultados

Último resultado: **72 pruebas aprobadas, cobertura 100%** (umbral bloqueante: 95%).
En cada ejecución del CI se publican como artefactos:

- `junit.xml`: resultado por prueba.
- `coverage.xml` y `htmlcov/`: cobertura por línea.

## Ejecutar

```bash
python scripts/checks.py test     # igual que el CI
python -m pytest tests/test_final.py -q   # un archivo
```
