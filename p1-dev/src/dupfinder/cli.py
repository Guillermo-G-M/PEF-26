"""CLI del detector de duplicados: parsea argumentos y despacha al modo
elegido (`baseline`, `estructura`, `cache`, `concurrente`, `paralelo` o
`final`)."""

from __future__ import annotations

import argparse
import cProfile
import io
import multiprocessing
import pstats
import sys
from pathlib import Path

# isinstance (no hasattr) para que mypy sepa que el stream admite reconfigure().
if isinstance(sys.stdout, io.TextIOWrapper) and isinstance(sys.stderr, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from .modes import baseline, cached, concurrent_mode, final, parallel_mode, structural

MODES = {
    "baseline": baseline.run,
    "estructura": structural.run,
    "cache": cached.run,
    "concurrente": concurrent_mode.run,
    "paralelo": parallel_mode.run,
    "final": final.run,
}

# Calibrado empíricamente en la Fase 5: con 1 KB (3000 archivos) el paralelismo con
# procesos pierde contra lo secuencial (overhead de IPC); con 2-20 MB gana. Ver
# README.md "Fase 5" para las mediciones.
DEFAULT_THRESHOLD_BYTES = 2 * 1024 * 1024

# Calibrado en la Fase 5 del Parcial 2 (batching): ver README.md "Fase 5 (Parcial 2)".
DEFAULT_BATCH_SIZE = 5000


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Detector de archivos duplicados.")
    parser.add_argument(
        "--modo",
        choices=sorted(MODES),
        required=True,
        help="Estrategia de procesamiento a ejecutar",
    )
    parser.add_argument("--path", required=True, help="Directorio a escanear")
    parser.add_argument(
        "--workers",
        type=int,
        default=multiprocessing.cpu_count(),
        help="Cantidad de workers para los modos concurrente/paralelo/final",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_THRESHOLD_BYTES,
        help="Umbral de tamaño en bytes para el ruteo dinámico threads/procesos en modo 'final'",
    )
    parser.add_argument(
        "--cache-file",
        default=None,
        help=(
            "Ruta del archivo de cache de hashes (modos 'cache'/'final'); "
            "por defecto se infiere junto a --path"
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=(
            "Cantidad máxima de archivos en vuelo a la vez en los modos "
            "concurrente/paralelo/final (acota la memoria de la cola/pool; "
            "0 o negativo = sin batching, un único lote)"
        ),
    )
    parser.add_argument(
        "--profile", action="store_true", help="Ejecutar bajo cProfile e imprimir estadísticas"
    )
    return parser.parse_args(argv)


def _run(args) -> None:
    handler = MODES[args.modo]
    cache_file = Path(args.cache_file) if args.cache_file else None
    handler(
        path=Path(args.path),
        workers=args.workers,
        threshold=args.threshold,
        cache_file=cache_file,
        batch_size=args.batch_size,
    )


def main(argv=None) -> None:
    """Punto de entrada de la CLI: parsea `argv`, ejecuta el modo elegido y,
    si `--profile` está activo, lo envuelve con `cProfile`."""
    args = _parse_args(argv)
    if args.profile:
        profiler = cProfile.Profile()
        profiler.enable()
        _run(args)
        profiler.disable()
        pstats.Stats(profiler).sort_stats("cumulative").print_stats(20)
    else:
        _run(args)


if __name__ == "__main__":
    main()
