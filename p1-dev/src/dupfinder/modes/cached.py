"""Modo `cache` (Fase 3): memoización de hashes por `(path, size, mtime)`,
persistida en JSON, para evitar recalcular archivos que no cambiaron entre
escaneos."""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path

from ..report import print_report
from ..scanutil import cache_key, group_by_size, require_directory, scan_with_stats
from .structural import hash_file


def default_cache_path(path: Path) -> Path:
    """Archivo sibling (no `--path`) para no ser recorrido por `iter_files`."""
    resolved = path.resolve()
    return resolved.parent / f".{resolved.name}.cache.json"


def load_cache(cache_path: Path) -> dict[str, dict]:
    """Carga el cache desde `cache_path`; devuelve `{}` si no existe o está
    corrupto (nunca propaga la excepción de parseo)."""
    if not cache_path.exists():
        return {}
    try:
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_cache(cache_path: Path, cache: dict[str, dict]) -> None:
    """Persiste `cache` en `cache_path`, creando el directorio si hace falta."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f)


def hash_with_cache(path: Path, st: os.stat_result, cache: dict[str, dict]) -> tuple[str, bool]:
    """Reutiliza el hash cacheado si `size`/`mtime` coinciden; si no, lo
    recalcula y reemplaza la entrada (invalidación)."""
    key = cache_key(path)
    entry = cache.get(key)
    if entry is not None and entry.get("size") == st.st_size and entry.get("mtime") == st.st_mtime:
        return entry["hash"], True
    digest = hash_file(path)
    cache[key] = {"size": st.st_size, "mtime": st.st_mtime, "hash": digest}
    return digest, False


def find_duplicates(root: Path, cache: dict[str, dict]) -> tuple[list[list[Path]], int, int, int]:
    """Como `structural.find_duplicates`, pero reutilizando hashes cacheados.

    Args:
        root: Directorio a escanear.
        cache: Cache mutable, clave `cache_key(path)` → `{size, mtime, hash}`.
            Se actualiza in-place con los cache-misses recalculados.

    Returns:
        `(groups, n, hits, misses)`.
    """
    files, stats = scan_with_stats(root)
    n = len(files)

    by_size = group_by_size(stats)
    candidates = [group for group in by_size.values() if len(group) > 1]

    by_hash: dict[str, list[Path]] = defaultdict(list)
    hits = 0
    misses = 0
    for group in candidates:
        for path in group:
            digest, hit = hash_with_cache(path, stats[path], cache)
            by_hash[digest].append(path)
            hits += int(hit)
            misses += int(not hit)

    groups = [paths for paths in by_hash.values() if len(paths) > 1]
    return groups, n, hits, misses


def run(
    path: Path,
    workers: int,
    threshold: int,
    cache_file: Path | None = None,
    batch_size: int | None = None,
) -> None:
    """Punto de entrada del modo `cache` para la CLI.

    Args:
        path: Directorio a escanear.
        workers: Ignorado (este modo es secuencial).
        threshold: Ignorado (este modo no rutea por tamaño).
        cache_file: Ruta del archivo de cache; por defecto, `default_cache_path(path)`.
        batch_size: Ignorado (este modo no usa pools de workers).
    """
    # pylint: disable=unused-argument
    require_directory(path)
    cache_path = cache_file or default_cache_path(path)
    cache = load_cache(cache_path)

    start = time.perf_counter()
    groups, n, hits, misses = find_duplicates(path, cache)
    elapsed = time.perf_counter() - start

    save_cache(cache_path, cache)

    print_report(
        "cache",
        n,
        groups,
        elapsed,
        extra={
            "cache": f"{hits} hits, {misses} misses de {hits + misses} candidatos",
            "archivo de cache": cache_path,
        },
    )
