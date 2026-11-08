# Rendimiento

## Qué se mide en cada ejecución del CI

| Control | Herramienta | Criterio |
|---|---|---|
| Benchmarks | pytest-benchmark (`benchmarks/test_benchmarks.py`) | En un pull request: falla si la **mediana** de algún benchmark empeora más de **30%** frente a `main` |
| Memoria | tracemalloc (`benchmarks/test_memory.py`) | Falla si el pico supera el límite medido |
| Profiling | cProfile sobre un escaneo de 1000 archivos | Solo reporte (`profile.txt`, `profile.prof`); no bloquea |

### Por qué comparar contra `main` en la misma ejecución

Los runners de GitHub no son todos iguales y su velocidad varía entre ejecuciones;
un tiempo absoluto fijo daría falsos rechazos. Por eso, en cada pull request el
pipeline descarga `main`, corre **los mismos benchmarks** contra el código de
`main` y luego contra el del PR, en la misma máquina y uno detrás del otro. Se
compara la mediana (menos sensible a valores atípicos que el promedio) con una
tolerancia del 30%. Se verificó el mecanismo agregando una demora artificial de
20 ms en `group_by_size`: el benchmark empeoró un 93% y el control falló.

Si `main` no puede medirse (por ejemplo, porque el PR agrega un benchmark de una
función nueva), se mide igual pero sin comparar, y queda indicado en el resumen.

### Por qué tracemalloc para el límite de memoria

tracemalloc cuenta solo la memoria que pide Python, no la del proceso completo
(que depende del sistema operativo y de las bibliotecas cargadas). Es estable entre
máquinas y permite un límite fijo.

| Control | Medido | Límite | Qué demuestra |
|---|---|---|---|
| Hash de un archivo de 32 MB | 0.13 MiB | 1 MiB | El hash por chunks no carga el archivo |
| Escaneo `final` de 400 archivos | 1.2 MiB | 2 MiB | La memoria de metadatos es O(n) y chica |

## Benchmarks (referencia local)

Dataset: 400 archivos de 1–64 KB, 30% duplicados, semilla 42. Windows, Python 3.12.

| Benchmark | Mediana |
|---|---|
| Escaneo + agrupación por tamaño | 20 ms |
| Modo `final` con cache completa | 43 ms |
| Modo `estructura` (secuencial) | 50 ms |
| Hash de un archivo de 32 MB | 72 ms |
| Modo `final` sin cache (threads) | 88 ms |

Lectura:

- Con archivos chicos, `final` en frío es más lento que `estructura` secuencial: el
  pool de threads cuesta más de lo que ahorra (coincide con el Parcial 1).
- Con cache completa, `final` no lee ningún archivo, pero tarda el doble que el
  escaneo solo: el costo restante está en armar la clave de cache
  (`path.resolve()` por archivo). Es el próximo punto a optimizar si hiciera falta.

## Profiling

Ejemplo de `profile.txt` (modo `estructura`, 1000 archivos recién generados, Windows):
el 94% del tiempo está en `open()` de archivos nuevos. Es el antivirus revisando cada
archivo la primera vez que se abre; en el runner Linux del CI no aparece. El
hashing en sí (`hash_file` sin contar `open`) es menor al 5%.

## Complejidad y resultados del Parcial 1

Ver [Diseño técnico](diseno.md#complejidad) para la complejidad de cada modo.
Comparación medida sobre el mismo dataset (210 archivos, 200 de 4 KB y 10 de 5 MB):

| Versión | Tiempo | Memoria pico (proceso) |
|---|---|---|
| `baseline` | 0.96 s | 36.6 MiB |
| `estructura` | 0.13 s | 27.3 MiB |
| `cache` (frío) | 0.16 s | 27.6 MiB |
| `concurrente` (4 workers) | 0.06 s | 27.8 MiB |
| `paralelo` (4 workers) | 0.26 s | 28.2 MiB |
| `final` (frío) | 0.28 s | 28.5 MiB |
| `final` (sin cambios) | 0.03 s | 24.2 MiB |

## Ejecutar

```bash
python scripts/checks.py perf                               # benchmarks, memoria, profiling
python scripts/checks.py perf --base-src ../otra-copia/p1-dev/src   # + comparación
```
