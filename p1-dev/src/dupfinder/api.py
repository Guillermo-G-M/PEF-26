"""Servicio FastAPI que expone el detector de duplicados como API REST.

Justificación (Parcial 2, punto 10 — "uso de algún framework"): el material de
la cursada recomienda FastAPI para "APIs REST, microservicios escalables"
(ver `parcial-2/p2-dev/doc.md`, sección de decisiones). Este módulo **no
reimplementa nada del algoritmo**: envuelve tal cual
`dupfinder.modes.final.find_duplicates`, la misma función que usa el modo
`final` de la CLI.
"""

from __future__ import annotations

import multiprocessing
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel, Field

from .cli import DEFAULT_BATCH_SIZE, DEFAULT_THRESHOLD_BYTES
from .modes.cached import default_cache_path, load_cache, save_cache
from .modes.final import find_duplicates
from .observability import tracer

app = FastAPI(
    title="dupfinder",
    description="Detector de archivos duplicados — API REST sobre la misma lógica de la CLI.",
    version="0.1.0",
)
FastAPIInstrumentor.instrument_app(app)

#: Variable de entorno con el directorio raíz que el servicio puede escanear.
SCAN_ROOT_ENV = "DUPFINDER_SCAN_ROOT"


def _scan_root() -> str:
    """Directorio raíz permitido: `DUPFINDER_SCAN_ROOT` o, si no está, el
    directorio de trabajo del proceso. Se lee en cada request para poder
    cambiarlo sin reiniciar (y en las pruebas)."""
    return os.path.realpath(os.environ.get(SCAN_ROOT_ENV) or os.getcwd())


def _inside_root(raw: str, field: str) -> Path:
    """Resuelve `raw` (relativa a la raíz o absoluta) y rechaza con 403 lo que
    quede fuera de la raíz, incluidos `..` y enlaces simbólicos.

    Corrige el hallazgo de CodeQL `py/path-injection`: sin esta validación,
    un cliente HTTP podía recorrer cualquier directorio del servidor y escribir
    el archivo de cache en cualquier ruta.
    """
    root = _scan_root()
    full = os.path.realpath(os.path.join(root, raw))
    if full != root and not full.startswith(root + os.sep):
        raise HTTPException(status_code=403, detail=f"{field} fuera del directorio permitido")
    return Path(full)


class ScanRequest(BaseModel):
    """Parámetros de un escaneo, con los mismos defaults que la CLI (`cli.py`)."""

    path: str = Field(..., description="Directorio a escanear, dentro de DUPFINDER_SCAN_ROOT")
    workers: int = Field(default=multiprocessing.cpu_count(), ge=1)
    threshold: int = Field(
        default=DEFAULT_THRESHOLD_BYTES,
        description="Umbral de tamaño (bytes) para el ruteo threads/procesos",
    )
    batch_size: int | None = Field(default=DEFAULT_BATCH_SIZE)
    cache_file: str | None = Field(
        default=None, description="Ruta del cache, dentro de DUPFINDER_SCAN_ROOT"
    )


class ScanResponse(BaseModel):
    """Mismo contenido que imprime `print_report` para el modo `final`, en JSON."""

    path: str
    files_scanned: int
    duplicate_groups: list[list[str]]
    redundant_files: int
    cache_hits: int
    cache_misses: int
    hashed_with_threads: int
    hashed_with_processes: int
    elapsed_seconds: float


@app.get("/health")
def health() -> dict[str, str]:
    """Chequeo de salud simple, para probes de liveness/readiness."""
    return {"status": "ok"}


@app.post("/scan", response_model=ScanResponse)
def scan(request: ScanRequest) -> ScanResponse:
    """Escanea `request.path` con el modo `final` (Fase 6 del Parcial 1) y
    devuelve el mismo reporte que imprime la CLI, en JSON.

    Además de los spans automáticos que agrega `FastAPIInstrumentor` por
    cada request, abre un span propio (`dupfinder.scan`) con los atributos
    de dominio del escaneo (archivos, cache hits/misses, ruteo, tiempo) —
    son los datos que un APM real (New Relic/Elastic APM) mostraría como
    métricas custom de negocio, no solo latencia HTTP genérica.
    """
    with tracer.start_as_current_span("dupfinder.scan") as span:
        span.set_attribute("dupfinder.path", request.path)
        span.set_attribute("dupfinder.workers", request.workers)
        span.set_attribute("dupfinder.threshold", request.threshold)

        path = _inside_root(request.path, "path")
        if not path.is_dir():
            span.set_attribute("dupfinder.error", "not_a_directory")
            raise HTTPException(status_code=400, detail=f"{request.path} no es un directorio")

        cache_path = (
            _inside_root(request.cache_file, "cache_file")
            if request.cache_file
            else default_cache_path(path)
        )
        cache = load_cache(cache_path)

        start = time.perf_counter()
        groups, n, hits, n_threads, n_processes = find_duplicates(
            path, request.workers, request.threshold, cache, request.batch_size
        )
        elapsed = time.perf_counter() - start

        save_cache(cache_path, cache)

        redundant = sum(len(group) - 1 for group in groups)
        span.set_attribute("dupfinder.files_scanned", n)
        span.set_attribute("dupfinder.duplicate_groups", len(groups))
        span.set_attribute("dupfinder.redundant_files", redundant)
        span.set_attribute("dupfinder.cache_hits", hits)
        span.set_attribute("dupfinder.cache_misses", n_threads + n_processes)
        span.set_attribute("dupfinder.hashed_with_threads", n_threads)
        span.set_attribute("dupfinder.hashed_with_processes", n_processes)
        span.set_attribute("dupfinder.elapsed_seconds", elapsed)

        return ScanResponse(
            path=request.path,
            files_scanned=n,
            duplicate_groups=[[str(member) for member in group] for group in groups],
            redundant_files=redundant,
            cache_hits=hits,
            cache_misses=n_threads + n_processes,
            hashed_with_threads=n_threads,
            hashed_with_processes=n_processes,
            elapsed_seconds=elapsed,
        )
