"""Controles de memoria con tracemalloc.

tracemalloc cuenta solo la memoria que pide Python (no la del proceso entero),
por eso el pico es estable entre maquinas y sirve como limite en CI. Los limites
salen de medir y dejar margen; ver la seccion Rendimiento de la documentacion.
"""

from __future__ import annotations

import tracemalloc

from dupfinder.modes import final
from dupfinder.modes.structural import hash_file

MiB = 1024 * 1024

# Hashear 32 MB por chunks de 64 KB no debe acercarse al tamano del archivo.
# Medido: ~0.13 MiB. Limite: 1 MiB.
LIMITE_HASH_GRANDE = 1 * MiB

# Escaneo completo (modo final, 400 archivos). Medido: ~1.2 MiB. Limite: 2 MiB
# (crece con la cantidad de archivos: lista, dict de stat y grupos por tamano).
LIMITE_SCAN = 2 * MiB


def _peak(func, *args, **kwargs) -> int:
    tracemalloc.start()
    try:
        func(*args, **kwargs)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return peak


def test_memoria_hash_archivo_grande(large_file):
    peak = _peak(hash_file, large_file)
    print(f"pico hash 32 MB: {peak / MiB:.3f} MiB")
    assert peak < LIMITE_HASH_GRANDE


def test_memoria_scan_final(dataset):
    peak = _peak(final.find_duplicates, dataset, 4, 2 * MiB, cache={})
    print(f"pico scan final: {peak / MiB:.3f} MiB")
    assert peak < LIMITE_SCAN
