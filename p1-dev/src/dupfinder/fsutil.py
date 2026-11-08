"""Recorrido perezoso de directorios, compartido por los 6 modos."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path


def iter_files(root: Path) -> Iterator[Path]:
    """Recorre `root` de forma perezosa y devuelve cada archivo regular."""
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            path = Path(dirpath) / name
            if path.is_file():
                yield path
