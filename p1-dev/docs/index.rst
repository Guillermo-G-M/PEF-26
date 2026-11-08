dupfinder
=========

Detector de archivos duplicados en Python — caso de estudio de **Programación
Eficiente** (Parcial 1 y 2): complejidad algorítmica, estructuras de datos,
memoización/caching, concurrencia/paralelismo y perfilado.

Diseño y mediciones completas en ``README.md`` y ``doc.md`` (en la raíz de
``p1-dev/``). Esta documentación cubre la referencia de la API, generada a
partir de los docstrings del código (Fase 2 del Parcial 2).

.. toctree::
   :maxdepth: 1
   :caption: Módulos compartidos

   modules/generator
   modules/cli
   modules/fsutil
   modules/report
   modules/scanutil
   modules/concurrency

.. toctree::
   :maxdepth: 1
   :caption: Modos (una estrategia de detección por archivo)

   modules/modes_baseline
   modules/modes_structural
   modules/modes_cached
   modules/modes_concurrent
   modules/modes_parallel
   modules/modes_final
