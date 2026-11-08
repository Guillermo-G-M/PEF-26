# Diseño técnico

## Algoritmo del modo `final`

1. **Escaneo inicial** (`scan_with_stats`): lista ordenada de rutas y un `dict`
   ruta → `stat`. O(n) llamadas a `stat`, sin leer contenido.
2. **Prefiltro por tamaño** (`group_by_size`): `dict` tamaño → rutas. Dos archivos
   de distinto tamaño no pueden ser iguales; los grupos de un solo archivo se
   descartan sin leerlos. O(n).
3. **Cache** (`_partition_by_cache_and_size`): si la clave `(path, size, mtime)`
   coincide, se reutiliza el hash guardado. O(1) por archivo.
4. **Ruteo por tamaño:** los candidatos sin cache de hasta 2 MiB se hashean con
   threads; los mayores, con procesos.
5. **Hash incremental:** SHA-256 leyendo de a 64 KB. Memoria O(1) por archivo.
6. **Agrupación por hash:** `dict` hash → rutas; los grupos de 2 o más son duplicados.

## Estructuras de datos

| Estructura | Uso | Motivo |
|---|---|---|
| `dict[int, list[Path]]` | Agrupar por tamaño | Inserción y búsqueda O(1) promedio |
| `dict[str, list[Path]]` | Agrupar por hash | Ídem; el hash es la clave natural |
| `dict[str, dict]` en JSON | Cache persistente | Búsqueda O(1) por ruta; legible y sin dependencias |
| `queue.Queue` | Cola de trabajos de los threads | Segura entre threads sin locks manuales |
| Generador (`iter_files`) | Recorrer el árbol | No arma en memoria todo el resultado de `os.walk` |

## Complejidad

n = archivos, s̄ = tamaño promedio, N = bytes de los archivos candidatos (los que
comparten tamaño con otro).

| Modo | Tiempo | Memoria adicional |
|---|---|---|
| `baseline` | O(n²·s̄) | O(s̄): dos archivos a la vez |
| `estructura` | O(n + N) | O(n) metadatos + O(1) por hash |
| `cache` (sin cambios) | O(n), solo `stat` | O(n) |
| `final` (frío) | O(n + N), N repartido entre workers | O(n) + O(batch) tareas en vuelo |
| `final` (sin cambios) | O(n) | O(n) |

## Decisiones de implementación

| Decisión | Motivo |
|---|---|
| SHA-256 y no comparación byte a byte | Cada archivo se lee una sola vez; las colisiones son prácticamente imposibles. |
| Chunks de 64 KB | Memoria constante por archivo; `hashlib` libera el GIL en cada `update()` grande y los threads paralelizan. |
| Umbral de 2 MiB | Medido en el Parcial 1: con 1–4 KB ningún pool compensa su overhead; desde ~2 MB sí. |
| Threads para chicos, procesos para grandes | Los procesos pagan arranque e IPC (pickle); solo compensan con mucho cómputo por archivo. |
| Cache por `(path, size, mtime)` | Detecta cambios sin leer el archivo; un `touch` invalida solo esa entrada. |
| Cache junto al directorio, no adentro | El escaneo no se cuenta a sí mismo como archivo. |
| Batching de 5000 | Acota las tareas en vuelo; como la cola lleva rutas (pocos bytes), el impacto medido es bajo, pero evita crecer sin límite. |
