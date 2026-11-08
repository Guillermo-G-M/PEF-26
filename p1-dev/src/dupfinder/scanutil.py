"""Utilidades de escaneo compartidas por los 6 modos: recorrido de archivos,
agrupación por tamaño (Fase 2), clave de cache (Fase 3) y tamaño de pool
(Fases 4 a 6). Extraído en la Fase 1 del Parcial 2 para eliminar código
duplicado entre modos (hallazgo de `pylint` R0801 en la línea base de
calidad)."""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

from .fsutil import iter_files


def require_directory(path: Path) -> None:
    """Corta la ejecución si `path` no es un directorio existente.

    Repetido antes al principio del `run()` de los 6 modos; factorizado acá
    (hallazgo de `pylint` R0801 en la línea base de calidad del Parcial 2).
    """
    if not path.is_dir():
        sys.exit(f"error: {path} no es un directorio")


def sorted_files(root: Path) -> list[Path]:
    """Lista de archivos de `root`, en un orden estable (determinismo para
    los reportes y los tests)."""
    return sorted(iter_files(root))


def scan_with_stats(root: Path) -> tuple[list[Path], dict[Path, os.stat_result]]:
    """Archivos de `root` + su `stat()`, una sola vez por archivo (tamaño y
    `mtime` salen del mismo `stat()`, no hace falta llamarlo dos veces)."""
    files = sorted_files(root)
    stats = {path: path.stat() for path in files}
    return files, stats


def group_by_size(stats: dict[Path, os.stat_result]) -> dict[int, list[Path]]:
    """Agrupa archivos por tamaño en bytes — el pre-filtro de la Fase 2
    (metadata, O(n), sin leer contenido)."""
    groups: dict[int, list[Path]] = defaultdict(list)
    for path, st in stats.items():
        groups[st.st_size].append(path)
    return groups


def cache_key(path: Path) -> str:
    """Clave de cache estable para un archivo: su path absoluto resuelto."""
    return str(path.resolve())


def resolve_pool_size(workers: int) -> int:
    """`workers` puede venir en 0 o negativo desde la CLI; nunca se arranca
    un pool con menos de 1 worker."""
    return max(1, workers)
