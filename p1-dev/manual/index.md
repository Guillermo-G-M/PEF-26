# dupfinder

Detector de archivos duplicados en Python, desarrollado en Programación Eficiente
(Parcial 1: algoritmo y optimizaciones; Parcial 2: calidad, servicio web y
observabilidad; Parcial 3: documentación externa e integración continua).

Esta documentación vive en el repositorio (`p1-dev/manual/`), se publica con
MkDocs en GitHub Pages y se construye en cada ejecución del CI: si un enlace se
rompe o una página no compila, el pipeline falla.

| Sección | Contenido |
|---|---|
| [Descripción funcional](funcional.md) | Problema, alcance y requisitos |
| [Arquitectura](arquitectura.md) | Módulos, responsabilidades, dependencias y diagrama |
| [Instalación y ejecución](instalacion.md) | Dependencias, configuración y comandos |
| [Diseño técnico](diseno.md) | Estructuras de datos, algoritmos y decisiones |
| [API y contratos](api.md) | CLI, servicio REST, entradas, salidas y errores |
| [Pruebas](pruebas.md) | Estrategia, casos y resultados |
| [Rendimiento](rendimiento.md) | Benchmarks, profiling, complejidad y memoria |
| [Seguridad](seguridad.md) | Riesgos, dependencias, política de bloqueo y excepciones |
| [Integración continua](ci.md) | Pipeline por etapas y matriz de controles |
| [Mantenimiento](mantenimiento.md) | Cómo contribuir, correr los controles en local y resolver fallos |
| [Acceso y colaboración](acceso.md) | Roles, permisos, regla de `main` y flujo de pull requests |

La referencia del código (generada desde los docstrings con Sphinx) se construye
con `python -m sphinx -b html docs docs/_build/html`.

## Por qué MkDocs + GitHub

- **Un solo lugar:** el código, la documentación y el CI están en el mismo
  repositorio. Un cambio de código y su documentación entran en el mismo pull request.
- **Control de acceso y colaboración:** el repositorio es público para leer, pero
  solo los colaboradores autorizados editan; cada cambio pasa por pull request,
  revisión e historial de Git (ver [Acceso y colaboración](acceso.md)).
- **Siempre actualizada:** el CI compila el sitio en modo estricto y valida los
  enlaces; al integrar en `main` se publica automáticamente.
- **Markdown simple:** no requiere herramientas propietarias (a diferencia de
  Confluence o SharePoint) y se lee también directamente en GitHub.
