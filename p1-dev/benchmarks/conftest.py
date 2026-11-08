"""Datasets compartidos por los benchmarks y los controles de memoria.

No se agrega `src/` a `sys.path` a proposito: el paquete se importa desde donde
indique el entorno (instalado o `PYTHONPATH`). Asi el CI puede medir los mismos
benchmarks contra el codigo de la rama principal y contra el del pull request.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from dupfinder.generator import generate_dataset

# 400 archivos de 1 KB a 64 KB, 30% duplicados: representa el caso tipico (muchos
# archivos chicos) y corre en pocos segundos en un runner de CI.
BENCH_COUNT = 400
BENCH_SEED = 42


@pytest.fixture(scope="session")
def dataset(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("bench_data")
    generate_dataset(
        root, count=BENCH_COUNT, dup_ratio=0.3, min_size=1024, max_size=64 * 1024, seed=BENCH_SEED
    )
    return root


@pytest.fixture(scope="session")
def large_file(tmp_path_factory) -> Path:
    """Archivo de 32 MB para medir el hashing incremental por chunks."""
    path = tmp_path_factory.mktemp("bench_large") / "grande.bin"
    with open(path, "wb") as f:
        for _ in range(32):
            f.write(os.urandom(1024 * 1024))
    return path
