# Descripción funcional

## Problema

Encontrar archivos con contenido idéntico dentro de un directorio (y sus
subdirectorios) para liberar espacio. Compararlos todos contra todos es
cuadrático en cantidad de archivos y lee cada archivo muchas veces; con miles de
archivos o archivos grandes deja de ser viable.

## Alcance

Incluido:

- Recorrido recursivo de un directorio local.
- Detección de duplicados por contenido (SHA-256), no por nombre ni fecha.
- Seis modos que muestran la evolución de las optimizaciones (`baseline`,
  `estructura`, `cache`, `concurrente`, `paralelo`, `final`).
- Cache persistente de hashes para acelerar escaneos repetidos.
- CLI, servicio REST (FastAPI) y trazas (OpenTelemetry a consola).
- Generador de datasets sintéticos reproducibles para medir.

Fuera de alcance:

- Borrar o mover duplicados (solo se informan).
- Detección de archivos *parecidos* (imágenes similares, texto casi igual).
- Directorios remotos o almacenamiento en la nube.

## Requisitos

| Tipo | Requisito |
|---|---|
| Funcional | Informar cada grupo de archivos idénticos y la cantidad de redundantes. |
| Funcional | Dar el mismo resultado en todos los modos para un mismo directorio. |
| Funcional | Reutilizar el hash de un archivo si no cambió su tamaño ni su fecha de modificación. |
| No funcional | Memoria acotada: hashear por chunks de 64 KB, sin cargar archivos completos. |
| No funcional | Escalar aproximadamente lineal en cantidad de archivos (modo `final`). |
| No funcional | Funcionar en Windows y Linux con Python 3.12. |
| Calidad | Cobertura de pruebas ≥ 95%, sin errores de Ruff/mypy, Pylint ≥ 9.5. |
