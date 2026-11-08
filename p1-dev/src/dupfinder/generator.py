"""Generador de datasets sintéticos para probar el detector de duplicados.

Cantidad de archivos, tamaño (fijo o en rango) y proporción de duplicados son
configurables. El contenido aleatorio se escribe por chunks de 1 MB para no
cargar archivos grandes completos en memoria.
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

CHUNK_SIZE = 1024 * 1024


def _write_random_file(path: Path, size: int, rng: random.Random) -> None:
    with open(path, "wb") as f:
        remaining = size
        while remaining > 0:
            chunk = min(CHUNK_SIZE, remaining)
            f.write(rng.randbytes(chunk))
            remaining -= chunk


def generate_dataset(
    out_dir: Path,
    count: int,
    dup_ratio: float,
    min_size: int,
    max_size: int,
    seed: int | None = None,
) -> None:
    """Genera `count` archivos sintéticos en `out_dir`.

    Crea `count - int(count * dup_ratio)` archivos con contenido aleatorio
    distinto y copia algunos de ellos para completar la proporción de
    duplicados pedida.

    Args:
        out_dir: Directorio de salida (se crea si no existe).
        count: Cantidad total de archivos a generar.
        dup_ratio: Proporción de archivos que son copia de otro, en [0.0, 1.0).
        min_size: Tamaño mínimo por archivo, en bytes.
        max_size: Tamaño máximo por archivo, en bytes.
        seed: Semilla para generación reproducible.

    Raises:
        ValueError: si `count`, `dup_ratio` o el rango de tamaños son inválidos.
    """
    # pylint: disable=too-many-arguments, too-many-positional-arguments
    # Los 6 parámetros son independientes y cada uno es necesario para
    # describir el dataset a generar; envolverlos en un objeto de
    # configuración solo movería la misma cantidad de datos a otro lugar,
    # sin ganar claridad en esta función pequeña y de uso frecuente en tests.
    if count < 1:
        raise ValueError("count debe ser >= 1")
    if not 0.0 <= dup_ratio < 1.0:
        raise ValueError("dup_ratio debe estar en [0.0, 1.0)")
    if min_size < 1 or max_size < min_size:
        raise ValueError("tamaños inválidos: min_size >= 1 y max_size >= min_size")

    rng = random.Random(seed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    n_dup = int(count * dup_ratio)
    n_unique = count - n_dup

    unique_paths = _generate_unique_files(out_dir, n_unique, min_size, max_size, rng)
    _generate_duplicate_files(out_dir, n_dup, n_unique, unique_paths, rng)


def _generate_unique_files(
    out_dir: Path, n_unique: int, min_size: int, max_size: int, rng: random.Random
) -> list[Path]:
    """Crea `n_unique` archivos con contenido aleatorio distinto."""
    unique_paths = []
    for i in range(n_unique):
        path = out_dir / f"file_{i:06d}.bin"
        size = rng.randint(min_size, max_size)
        _write_random_file(path, size, rng)
        unique_paths.append(path)
    return unique_paths


def _generate_duplicate_files(
    out_dir: Path, n_dup: int, n_unique: int, unique_paths: list[Path], rng: random.Random
) -> None:
    """Copia archivos de `unique_paths` al azar para completar `n_dup` duplicados."""
    for j in range(n_dup):
        source = rng.choice(unique_paths)
        dest = out_dir / f"file_{n_unique + j:06d}.bin"
        shutil.copyfile(source, dest)


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generador de datasets sintéticos para el detector de duplicados."
    )
    parser.add_argument("--out", required=True, help="Directorio de salida")
    parser.add_argument(
        "--count", type=int, required=True, help="Cantidad total de archivos a generar"
    )
    parser.add_argument(
        "--dup-ratio", type=float, default=0.1, help="Proporción de archivos duplicados (0.0-1.0)"
    )
    parser.add_argument(
        "--min-size", type=int, default=1024, help="Tamaño mínimo por archivo, en bytes"
    )
    parser.add_argument(
        "--max-size", type=int, default=1024, help="Tamaño máximo por archivo, en bytes"
    )
    parser.add_argument("--seed", type=int, default=None, help="Semilla para reproducibilidad")
    return parser.parse_args(argv)


def main(argv=None) -> None:
    """Punto de entrada de línea de comandos: parsea `argv` y genera el dataset."""
    args = _parse_args(argv)
    generate_dataset(
        out_dir=Path(args.out),
        count=args.count,
        dup_ratio=args.dup_ratio,
        min_size=args.min_size,
        max_size=args.max_size,
        seed=args.seed,
    )
    print(f"Generados {args.count} archivos en {args.out} (dup_ratio={args.dup_ratio})")


if __name__ == "__main__":
    main()
