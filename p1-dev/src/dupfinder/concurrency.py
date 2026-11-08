"""Patrones de pool (threads y procesos) sobre una cola de trabajos, con
batching opcional, compartidos por los modos `concurrente` (Fase 4),
`paralelo` (Fase 5) y `final` (Fase 6).

Factorizado en la Fase 3 del Parcial 2: antes `concurrent_mode._worker` y el
worker interno de `final._hash_small_with_threads` repetían el mismo loop
`while True: ... except queue.Empty: ...` (hallazgo de `pylint` R0801).

El batching (`batch_size`) se agregó en la Fase 5 del Parcial 2: sin él, los
tres modos armaban una `Queue` (threads) o enviaban todas las tareas a la vez
a `executor.map` (procesos) con **todos** los candidatos de la colección —
con millones de archivos, esa cola o esa tanda de futuros vive entera en
memoria de una sola vez. Con `batch_size`, se procesa de a lotes acotados,
cerrando y reabriendo el pool entre lotes, así la cantidad de tareas "en
vuelo" nunca supera `batch_size`.
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

from .scanutil import resolve_pool_size


def _batches(paths: list[Path], batch_size: int | None) -> Iterator[list[Path]]:
    """Parte `paths` en listas de a lo sumo `batch_size` elementos.

    Sin `batch_size` (o si es >= `len(paths)`), es un único lote con todo
    `paths` — el comportamiento previo a la Fase 5 del Parcial 2.
    """
    size = batch_size if batch_size and batch_size > 0 else len(paths)
    for i in range(0, len(paths), size):
        yield paths[i : i + size]


def hash_many_with_threads(
    paths: list[Path],
    workers: int,
    hash_fn: Callable[[Path], str],
    on_result: Callable[[Path, str], None],
    batch_size: int | None = None,
) -> None:
    """Hashea `paths` repartiéndolos entre `workers` threads, de a lotes.

    Cada lote vive en su propia `Queue`; cada thread saca un archivo
    pendiente, lo hashea con `hash_fn` y llama a `on_result(path, hash)` bajo
    un `Lock` compartido (protege el estado mutable que `on_result`
    actualice, ej. un `dict` de resultados o una entrada de cache). El pool
    de threads se recrea en cada lote, así la memoria en vuelo (cola +
    futuros) queda acotada por `batch_size`, no por `len(paths)`.

    Args:
        paths: Archivos a hashear. Si está vacío, no hace nada.
        workers: Cantidad de threads del pool (mínimo 1, ver `resolve_pool_size`).
        hash_fn: Función que calcula el hash de un archivo (ej. `hash_file`).
        on_result: Callback `(path, hash) -> None`, invocado bajo el `Lock`.
        batch_size: Tamaño máximo de cada lote. `None` (default) procesa todo
            `paths` en un único lote.
    """
    if not paths:
        return
    for batch in _batches(paths, batch_size):
        _hash_batch_with_threads(batch, workers, hash_fn, on_result)


def _hash_batch_with_threads(
    paths: list[Path],
    workers: int,
    hash_fn: Callable[[Path], str],
    on_result: Callable[[Path, str], None],
) -> None:
    work_queue: queue.Queue[Path] = queue.Queue()
    for path in paths:
        work_queue.put(path)
    lock = threading.Lock()

    def worker() -> None:
        while True:
            try:
                path = work_queue.get_nowait()
            except queue.Empty:
                return
            try:
                digest = hash_fn(path)
                with lock:
                    on_result(path, digest)
            finally:
                work_queue.task_done()

    pool_size = resolve_pool_size(workers)
    with ThreadPoolExecutor(max_workers=pool_size) as executor:
        futures = [executor.submit(worker) for _ in range(pool_size)]
        for future in futures:
            future.result()


def hash_many_with_processes(
    paths: list[Path],
    workers: int,
    hash_one_fn: Callable[[Path], tuple[Path, str]],
    on_result: Callable[[Path, str], None],
    batch_size: int | None = None,
) -> None:
    """Hashea `paths` repartiéndolos entre `workers` procesos, de a lotes.

    Args:
        paths: Archivos a hashear. Si está vacío, no hace nada.
        workers: Cantidad de procesos del pool.
        hash_one_fn: Función module-level **picklable** que recibe un `Path`
            y devuelve `(path, hash)` (ej. `parallel_mode._hash_one`) — no
            puede ser una lambda ni una función anidada, porque viaja por
            IPC a cada proceso worker.
        on_result: Callback `(path, hash) -> None`, invocado en el proceso
            principal por cada resultado (no necesita ser picklable).
        batch_size: Tamaño máximo de cada lote. `None` (default) procesa todo
            `paths` en un único lote (un solo `ProcessPoolExecutor`).
    """
    if not paths:
        return
    pool_size = resolve_pool_size(workers)
    for batch in _batches(paths, batch_size):
        with ProcessPoolExecutor(max_workers=pool_size) as executor:
            for path, digest in executor.map(hash_one_fn, batch):
                on_result(path, digest)
