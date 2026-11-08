"""Impresión uniforme del resultado de un escaneo, reutilizada por los 6 modos."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path


def print_report(
    modo: str,
    files_scanned: int,
    groups: Sequence[Sequence[Path]],
    elapsed_s: float,
    extra: Mapping[str, object] | None = None,
) -> None:
    """Imprime el resultado de un escaneo de forma uniforme entre modos.

    Args:
        modo: Nombre del modo que generó el reporte (ej. "baseline", "final").
        files_scanned: Cantidad total de archivos recorridos.
        groups: Grupos de archivos duplicados detectados.
        elapsed_s: Tiempo de ejecución, en segundos.
        extra: Líneas adicionales específicas del modo (ej. cache hits/misses),
            impresas antes del resumen de grupos/redundantes/tiempo.
    """
    redundant = sum(len(g) - 1 for g in groups)
    print(f"modo={modo}")
    print(f"archivos escaneados: {files_scanned}")
    if extra:
        for key, value in extra.items():
            print(f"{key}: {value}")
    print(f"grupos de duplicados: {len(groups)}")
    print(f"archivos redundantes: {redundant}")
    print(f"tiempo: {elapsed_s:.4f} s")
    for idx, group in enumerate(groups, 1):
        print(f"  grupo {idx} ({len(group)} archivos):")
        for member in group:
            print(f"    {member}")
