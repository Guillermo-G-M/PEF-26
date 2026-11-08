"""Mide tiempo vs. volumen de archivos para cada modo (Fase 6, roadmap.md).

Genera datasets frescos de distintos tamaños, llama a `find_duplicates` de
cada modo directamente (sin pasar por la CLI, para no medir el arranque del
intérprete) y escribe los resultados en `benchmark_results.csv`. Pensado
para producir los datos del gráfico de escalabilidad de la presentación
(Fase 7); el gráfico en sí se arma a partir de este CSV.
"""

from __future__ import annotations

import csv
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dupfinder.generator import generate_dataset
from dupfinder.modes import baseline, concurrent_mode, parallel_mode, structural

FILE_COUNTS = [50, 100, 200, 400, 800]
FILE_SIZE = 65536  # 64 KiB: lo bastante chico para correr rápido, lo bastante
# grande para que el hashing no sea instantáneo.
DUP_RATIO = 0.2
WORKERS = 4
WORKDIR = Path(__file__).parent.parent / "data" / "_benchmark_tmp"
OUTPUT_CSV = Path(__file__).parent.parent / "benchmark_results.csv"


def _time_it(fn) -> float:
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


def main() -> None:
    rows = []
    for n in FILE_COUNTS:
        if WORKDIR.exists():
            shutil.rmtree(WORKDIR)
        generate_dataset(
            WORKDIR,
            count=n,
            dup_ratio=DUP_RATIO,
            min_size=FILE_SIZE,
            max_size=FILE_SIZE,
            seed=100 + n,
        )

        # warm-up: calienta el caché de disco del SO para que la comparación
        # entre modos no quede dominada por I/O real (ver hallazgo de la Fase 4).
        structural.find_duplicates(WORKDIR)

        modes = {
            "baseline": lambda: baseline.find_duplicates(WORKDIR),
            "estructura": lambda: structural.find_duplicates(WORKDIR),
            "concurrente": lambda: concurrent_mode.find_duplicates(WORKDIR, WORKERS),
            "paralelo": lambda: parallel_mode.find_duplicates(WORKDIR, WORKERS),
        }
        for modo, fn in modes.items():
            elapsed = _time_it(fn)
            rows.append({"modo": modo, "n": n, "tiempo_s": round(elapsed, 4)})
            print(f"n={n:>4}  modo={modo:<12}  tiempo={elapsed:.4f}s")

    shutil.rmtree(WORKDIR, ignore_errors=True)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["modo", "n", "tiempo_s"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nResultados guardados en {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
