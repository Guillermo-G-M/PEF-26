"""Modo `estructura` (Fase 2): pre-filtrado por tamaño (metadata, O(n)) +
hashing incremental SHA-256 solo sobre los candidatos."""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from pathlib import Path

from ..report import print_report
from ..scanutil import group_by_size, require_directory, scan_with_stats

CHUNK_SIZE = 64 * 1024


def hash_file(path: Path, chunk_size: int = CHUNK_SIZE) -> str:
    """Hash SHA-256 de `path`, leído por chunks de `chunk_size` bytes.

    Mantiene la complejidad espacial en O(1) por archivo, sin importar su
    tamaño: nunca se carga el archivo completo en memoria.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicates(root: Path) -> tuple[list[list[Path]], int, int]:
    """2.1: agrupa por tamaño (metadata, O(n)). 2.2: hashea por chunks de
    64KB solo los archivos cuyo tamaño colisiona con otro (candidatos)."""
    files, stats = scan_with_stats(root)
    n = len(files)

    by_size = group_by_size(stats)
    candidates = [group for group in by_size.values() if len(group) > 1]
    n_hashed = sum(len(group) for group in candidates)

    by_hash: dict[str, list[Path]] = defaultdict(list)
    for group in candidates:
        for path in group:
            by_hash[hash_file(path)].append(path)

    groups = [paths for paths in by_hash.values() if len(paths) > 1]
    return groups, n, n_hashed


def run(
    path: Path,
    workers: int,
    threshold: int,
    cache_file: Path | None = None,
    batch_size: int | None = None,
) -> None:
    """Punto de entrada del modo `estructura` para la CLI.

    Args:
        path: Directorio a escanear.
        workers: Ignorado (este modo es secuencial).
        threshold: Ignorado (este modo no rutea por tamaño).
        cache_file: Ignorado (este modo no usa cache).
        batch_size: Ignorado (este modo no usa pools de workers).
    """
    # pylint: disable=unused-argument
    require_directory(path)
    start = time.perf_counter()
    groups, n, n_hashed = find_duplicates(path)
    elapsed = time.perf_counter() - start
    print_report(
        "estructura", n, groups, elapsed, extra={"archivos hasheados": f"{n_hashed} de {n}"}
    )
