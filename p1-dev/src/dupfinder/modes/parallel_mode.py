"""Modo `paralelo` (Fase 5): mismo pre-filtrado que `estructura`, pero el
hashing de los candidatos se reparte entre `workers` procesos
(`ProcessPoolExecutor`)."""

from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path

from ..concurrency import hash_many_with_processes
from ..report import print_report
from ..scanutil import group_by_size, require_directory, resolve_pool_size, scan_with_stats
from .structural import hash_file


def _hash_one(path: Path) -> tuple[Path, str]:
    return path, hash_file(path)


def find_duplicates(
    root: Path, workers: int, batch_size: int | None = None
) -> tuple[list[list[Path]], int, int]:
    """Mismo pre-filtrado por tamaño que la Fase 2; el hashing de los
    candidatos (CPU-bound) se reparte entre `workers` procesos con
    `ProcessPoolExecutor`, evitando el GIL para el cómputo SHA-256.

    A diferencia de los threads (Fase 4), cada proceso tiene su propia
    memoria: cada archivo y su hash viajan serializados (pickle) por IPC
    entre el proceso principal y los workers. Ese costo de IPC es fijo por
    archivo, independiente de su tamaño, por lo que domina cuando hay muchos
    archivos chicos y se diluye cuando hay pocos archivos grandes.

    Args:
        root: Directorio a escanear.
        workers: Cantidad de procesos del pool.
        batch_size: Ver `concurrency.hash_many_with_processes` (Fase 5 del
            Parcial 2): acota la cantidad de tareas en vuelo a la vez.
    """
    files, stats = scan_with_stats(root)
    n = len(files)

    by_size = group_by_size(stats)
    candidates = [group for group in by_size.values() if len(group) > 1]
    paths = [p for group in candidates for p in group]
    n_hashed = len(paths)

    by_hash: dict[str, list[Path]] = defaultdict(list)
    hash_many_with_processes(
        paths, workers, _hash_one, lambda path, digest: by_hash[digest].append(path), batch_size
    )

    groups = [group for group in by_hash.values() if len(group) > 1]
    return groups, n, n_hashed


def run(
    path: Path,
    workers: int,
    threshold: int,
    cache_file: Path | None = None,
    batch_size: int | None = None,
) -> None:
    """Punto de entrada del modo `paralelo` para la CLI.

    Args:
        path: Directorio a escanear.
        workers: Cantidad de procesos del pool.
        threshold: Ignorado (este modo no rutea por tamaño).
        cache_file: Ignorado (este modo no usa cache).
        batch_size: Tamaño de lote para `hash_many_with_processes` (Fase 5).
    """
    # pylint: disable=unused-argument
    require_directory(path)
    start = time.perf_counter()
    groups, n, n_hashed = find_duplicates(path, workers, batch_size)
    elapsed = time.perf_counter() - start
    print_report(
        "paralelo",
        n,
        groups,
        elapsed,
        extra={"archivos hasheados": f"{n_hashed} de {n}", "workers": resolve_pool_size(workers)},
    )
