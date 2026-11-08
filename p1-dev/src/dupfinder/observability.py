"""Observabilidad tipo APM con OpenTelemetry sobre el servicio FastAPI.

Justificación (Parcial 2, punto 3 — "herramientas generales" tipo YourKit/New
Relic/Elastic APM): esas tres requieren infraestructura externa (agente +
backend, o licencia). Acá se exporta a **consola** con
`ConsoleSpanExporter`, sin depender de ningún servicio aparte — ver la
justificación completa en `parcial-2/p2-dev/doc.md`.

Se usa `SimpleSpanProcessor` (no `BatchSpanProcessor`) a propósito: imprime
cada span apenas termina, para que se vea en una demo en vivo sin esperar a
que se llene un buffer. En producción real, con un volumen alto de requests,
convendría `BatchSpanProcessor` para no pagar el costo de exportar span por
span — acá se prioriza la demostrabilidad sobre el rendimiento.
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

_provider = TracerProvider(resource=Resource.create({"service.name": "dupfinder-api"}))
_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(_provider)

tracer = trace.get_tracer("dupfinder")
