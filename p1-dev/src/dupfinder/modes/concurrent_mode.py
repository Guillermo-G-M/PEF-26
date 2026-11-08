"""Modo `concurrente` (Fase 4): mismo pre-filtrado que `estructura`, pero el
hashing de los candidatos se reparte entre `workers` threads
(`ThreadPoolExecutor` + `Queue`)."""

from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path

from ..concurrency import hash_many_with_threads
from ..report import print_report
from ..scanutil import group_by_size, require_directory, resolve_pool_size, scan_with_stats
from .structural import hash_file


def find_duplicates(
    root: Path, workers: int, batch_size: int | None = None
) -> tuple[list[list[Path]], int, int]:
    """Mismo pre-filtrado por tamaño que la Fase 2; el hashing de los
    candidatos (I/O-bound) se reparte entre `workers` threads que consumen
    una `Queue` de trabajos pendientes (`hash_many_with_threads`). El GIL se
    libera durante la lectura de archivo, por lo que los threads sí aportan
    paralelismo real en I/O.

    El `dict` compartido (`by_hash`) se protege con un `Lock` dentro de
    `hash_many_with_threads`: aunque el GIL hace atómica cada operación de
    bytecode, `dict[k].append(v)` no es una sola operación, y dos threads
    podrían pisarse un `setdefault` sobre la misma clave si no se serializa
    el acceso.

    Args:
        root: Directorio a escanear.
        workers: Cantidad de threads del pool.
        batch_size: Ver `concurrency.hash_many_with_threads` (Fase 5 del
            Parcial 2): acota la memoria de la cola de trabajo por lote.
    """
    files, stats = scan_with_stats(root)
    n = len(files)

    by_size = group_by_size(stats)
    candidates = [group for group in by_size.values() if len(group) > 1]
    paths = [p for group in candidates for p in group]
    n_hashed = len(paths)

    by_hash: dict[str, list[Path]] = defaultdict(list)
    hash_many_with_threads(
        paths, workers, hash_file, lambda path, digest: by_hash[digest].append(path), batch_size
    )

    groups = [paths for paths in by_hash.values() if len(paths) > 1]
    return groups, n, n_hashed


def run(
    path: Path,
    workers: int,
    threshold: int,
    cache_file: Path | None = None,
    batch_size: int | None = None,
) -> None:
    """Punto de entrada del modo `concurrente` para la CLI.

    Args:
        path: Directorio a escanear.
        workers: Cantidad de threads del pool.
        threshold: Ignorado (este modo no rutea por tamaño).
        cache_file: Ignorado (este modo no usa cache).
        batch_size: Tamaño de lote para `hash_many_with_threads` (Fase 5).
    """
    # pylint: disable=unused-argument
    require_directory(path)
    start = time.perf_counter()
    groups, n, n_hashed = find_duplicates(path, workers, batch_size)
    elapsed = time.perf_counter() - start
    print_report(
        "concurrente",
        n,
        groups,
        elapsed,
        extra={"archivos hasheados": f"{n_hashed} de {n}", "workers": resolve_pool_size(workers)},
    )
