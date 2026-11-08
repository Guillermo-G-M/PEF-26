"""Benchmarks de operaciones representativas (pytest-benchmark).

En CI se comparan contra la rama principal medida en la misma maquina; ver
`scripts/checks.py perf` y la seccion Rendimiento de la documentacion.
"""

from __future__ import annotations

from dupfinder.modes import final, structural
from dupfinder.modes.structural import hash_file
from dupfinder.scanutil import group_by_size, scan_with_stats

THRESHOLD = 2 * 1024 * 1024  # mismo umbral por defecto que la CLI


def test_bench_scan_y_agrupacion(benchmark, dataset):
    """Escaneo inicial + agrupacion por tamano: O(n), sin leer contenido."""

    def run():
        _, stats = scan_with_stats(dataset)
        return group_by_size(stats)

    benchmark(run)


def test_bench_estructura(benchmark, dataset):
    """Pipeline secuencial: prefiltro por tamano + SHA-256 por chunks."""
    groups, _, _ = benchmark(structural.find_duplicates, dataset)
    assert groups


def test_bench_final_sin_cache(benchmark, dataset):
    """Modo final en frio: todos los candidatos se hashean con threads."""
    result = benchmark(lambda: final.find_duplicates(dataset, 4, THRESHOLD, cache={}))
    assert result[0]


def test_bench_final_con_cache(benchmark, dataset):
    """Modo final con la cache completa: ningun archivo se vuelve a leer."""
    cache: dict[str, dict] = {}
    final.find_duplicates(dataset, 4, THRESHOLD, cache=cache)
    result = benchmark(lambda: final.find_duplicates(dataset, 4, THRESHOLD, cache=cache))
    assert result[2] > 0  # hubo hits de cache


def test_bench_hash_archivo_grande(benchmark, large_file):
    """SHA-256 incremental de un archivo de 32 MB."""
    benchmark(hash_file, large_file)
