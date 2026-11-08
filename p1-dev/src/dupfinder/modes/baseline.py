"""Modo `baseline` (Fase 1): comparación directa fuerza bruta, usada como
línea base para medir el resto de las optimizaciones."""

from __future__ import annotations

import time
from pathlib import Path

from ..report import print_report
from ..scanutil import require_directory, sorted_files


def _read(path: Path) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def find_duplicates(root: Path) -> tuple[list[list[Path]], int]:
    """Comparación directa todos-contra-todos leyendo el contenido completo.

    Genera O(n²) pares y cada par paga O(s) de lectura: costo total O(n²·s̄).
    """
    files = sorted_files(root)
    n = len(files)
    assigned = [False] * n
    groups: list[list[Path]] = []
    for i in range(n):
        if assigned[i]:
            continue
        data_i = _read(files[i])
        group = [files[i]]
        for j in range(i + 1, n):
            if assigned[j]:
                continue
            if data_i == _read(files[j]):
                assigned[j] = True
                group.append(files[j])
        if len(group) > 1:
            groups.append(group)
    return groups, n


def run(
    path: Path,
    workers: int,
    threshold: int,
    cache_file: Path | None = None,
    batch_size: int | None = None,
) -> None:
    """Punto de entrada del modo `baseline` para la CLI.

    Args:
        path: Directorio a escanear.
        workers: Ignorado (este modo es secuencial).
        threshold: Ignorado (este modo no rutea por tamaño).
        cache_file: Ignorado (este modo no usa cache). Presente solo para
            que la CLI pueda despachar los 6 modos con la misma firma.
        batch_size: Ignorado (este modo no usa pools de workers).
    """
    # pylint: disable=unused-argument
    require_directory(path)
    start = time.perf_counter()
    groups, n = find_duplicates(path)
    elapsed = time.perf_counter() - start
    print_report("baseline", n, groups, elapsed)
