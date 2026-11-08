"""Modo `final` (Fase 6): integra el pre-filtrado por tamaño (Fase 2), el
cache por `(path, size, mtime)` (Fase 3) y, solo para los cache-misses, el
ruteo dinámico entre threads (Fase 4) y procesos (Fase 5) según `--threshold`."""

from __future__ import annotations

import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ..concurrency import hash_many_with_processes, hash_many_with_threads
from ..report import print_report
from ..scanutil import (
    cache_key,
    group_by_size,
    require_directory,
    resolve_pool_size,
    scan_with_stats,
)
from .cached import default_cache_path, load_cache, save_cache
from .parallel_mode import _hash_one
from .structural import hash_file


@dataclass
class _HashContext:
    """Estado compartido entre el reparto de cache-hits/misses y el hashing
    de los misses: qué se sabe de cada archivo (`stats`), el cache a
    actualizar y el acumulador de resultados (`by_hash`). Agrupa en un solo
    parámetro lo que antes viajaba como 3 argumentos sueltos idénticos entre
    `_partition_by_cache_and_size`, `_hash_small_with_threads` y
    `_hash_large_with_processes` (hallazgo de `pylint` R0913/R0917 al agregar
    `batch_size` en la Fase 5 del Parcial 2)."""

    stats: dict[Path, os.stat_result]
    cache: dict[str, dict]
    by_hash: dict[str, list[Path]] = field(default_factory=lambda: defaultdict(list))

    def record(self, path: Path, digest: str) -> None:
        """Guarda el resultado de hashear `path`: lo suma a `by_hash` y
        actualiza su entrada de cache."""
        st = self.stats[path]
        self.by_hash[digest].append(path)
        self.cache[cache_key(path)] = {"size": st.st_size, "mtime": st.st_mtime, "hash": digest}


def _partition_by_cache_and_size(
    candidates: list[list[Path]], ctx: _HashContext, threshold: int
) -> tuple[int, list[Path], list[Path]]:
    """Separa los candidatos en cache-hits (ya resueltos, van directo a
    `ctx.by_hash`) y cache-misses, y a estos últimos los bucketiza por
    tamaño para el ruteo dinámico (umbral = `threshold`).

    Returns:
        `(hits, small_misses, large_misses)`.
    """
    hits = 0
    small_misses: list[Path] = []
    large_misses: list[Path] = []
    for group in candidates:
        for path in group:
            st = ctx.stats[path]
            entry = ctx.cache.get(cache_key(path))
            if (
                entry is not None
                and entry.get("size") == st.st_size
                and entry.get("mtime") == st.st_mtime
            ):
                ctx.by_hash[entry["hash"]].append(path)
                hits += 1
            elif st.st_size > threshold:
                large_misses.append(path)
            else:
                small_misses.append(path)
    return hits, small_misses, large_misses


def _hash_small_with_threads(
    paths: list[Path], ctx: _HashContext, workers: int, batch_size: int | None
) -> None:
    """Candidatos <= threshold: igual que la Fase 4 (`hash_many_with_threads`),
    actualizando el cache de paso (igual que la Fase 3)."""
    hash_many_with_threads(paths, workers, hash_file, ctx.record, batch_size)


def _hash_large_with_processes(
    paths: list[Path], ctx: _HashContext, workers: int, batch_size: int | None
) -> None:
    """Candidatos > threshold: igual que la Fase 5 (`hash_many_with_processes`),
    actualizando el cache con los resultados que vuelven por IPC."""
    hash_many_with_processes(paths, workers, _hash_one, ctx.record, batch_size)


def find_duplicates(
    root: Path,
    workers: int,
    threshold: int,
    cache: dict[str, dict],
    batch_size: int | None = None,
) -> tuple[list[list[Path]], int, int, int, int]:
    """Integra las fases 2 a 5: pre-filtrado por tamaño (2), cache por
    `(path, size, mtime)` (3) y, solo para los cache-misses, ruteo dinámico
    por tamaño de archivo entre threads (<= threshold, Fase 4) y procesos
    (> threshold, Fase 5). `threshold` es la variable configurable (`--threshold`)
    calibrada en la Fase 5. `batch_size` acota la memoria en vuelo por lote
    (Fase 5 del Parcial 2, ver `concurrency.py`).

    Returns:
        `(groups, n, hits, n_threads, n_processes)`.
    """
    files, stats = scan_with_stats(root)
    n = len(files)

    by_size = group_by_size(stats)
    candidates = [group for group in by_size.values() if len(group) > 1]
    ctx = _HashContext(stats=stats, cache=cache)

    hits, small_misses, large_misses = _partition_by_cache_and_size(candidates, ctx, threshold)

    _hash_small_with_threads(small_misses, ctx, workers, batch_size)
    _hash_large_with_processes(large_misses, ctx, workers, batch_size)

    groups = [paths for paths in ctx.by_hash.values() if len(paths) > 1]
    return groups, n, hits, len(small_misses), len(large_misses)


def run(
    path: Path,
    workers: int,
    threshold: int,
    cache_file: Path | None = None,
    batch_size: int | None = None,
) -> None:
    """Punto de entrada del modo `final` para la CLI.

    Args:
        path: Directorio a escanear.
        workers: Cantidad de workers del pool de threads y del de procesos.
        threshold: Umbral de tamaño, en bytes, que decide threads (<=) vs.
            procesos (>) para cada cache-miss.
        cache_file: Ruta del archivo de cache; por defecto, `default_cache_path(path)`.
        batch_size: Tamaño de lote para el hashing de los cache-misses (Fase 5).
    """
    require_directory(path)
    cache_path = cache_file or default_cache_path(path)
    cache = load_cache(cache_path)

    start = time.perf_counter()
    groups, n, hits, n_threads, n_processes = find_duplicates(
        path, workers, threshold, cache, batch_size
    )
    elapsed = time.perf_counter() - start

    save_cache(cache_path, cache)

    misses = n_threads + n_processes
    print_report(
        "final",
        n,
        groups,
        elapsed,
        extra={
            "cache": f"{hits} hits, {misses} misses de {hits + misses} candidatos",
            "ruteo (umbral)": (
                f"{n_threads} con threads (<= {threshold} bytes), "
                f"{n_processes} con procesos (> {threshold} bytes)"
            ),
            "workers": resolve_pool_size(workers),
            "archivo de cache": cache_path,
        },
    )
