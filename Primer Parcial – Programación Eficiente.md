# Primer Parcial – Programación Eficiente

## Objetivo general

Desarrollar una aplicación que permita analizar y demostrar la aplicación de técnicas
de **programación eficiente**.

El trabajo deberá implementarse en **Python, Java o Go** , a elección.

La evaluación se centrará no solamente en que la aplicación funcione correctamente,
sino fundamentalmente en la capacidad de los estudiantes para:

- Analizar la **complejidad algorítmica**.
- Seleccionar el **algoritmo más adecuado**.
- Elegir estructuras de datos eficientes.
- Aplicar **memoización y/o caching inteligente**.
- Incorporar **concurrencia y/o paralelismo** cuando resulte apropiado.
- Realizar **perfilado del código**.
- Medir, comparar y justificar las optimizaciones realizadas.

# Aplicacion a desarrollar – Sistema

# inteligente de procesamiento de

# imágenes o archivos

Desarrollar una aplicación que procese un conjunto importante de archivos o
imágenes.

Las operaciones podrían incluir:

- Lectura de archivos.
- Cálculo de estadísticas.
- Búsqueda de duplicados.
- Generación de hashes.
- Compresión simulada.

- Transformaciones sobre datos.

No es necesario desarrollar algoritmos complejos de procesamiento de imágenes; el
foco debe estar en la **eficiencia del procesamiento**.

### Conceptos de Programación Eficiente

**Complejidad**

- Analizar el coste de cada estrategia de procesamiento.

**Algoritmos**
Por ejemplo, comparar:

- Comparación directa de archivos.
- Uso de hashes para detectar duplicados.

**Estructuras de datos**

- HashMap para indexar hashes.
- Sets para detección rápida.
- Queues para gestionar trabajos pendientes.

**Caching**

- Evitar procesar nuevamente archivos que no hayan cambiado.

**Memoización**

- Reutilizar resultados de transformaciones o cálculos repetitivos.

**Concurrencia**

- Procesar varios archivos simultáneamente.

**Paralelismo**

- Utilizar múltiples núcleos para operaciones CPU-intensive.

**Perfilado**

- Determinar si la mejora depende del tipo de tarea: CPU-bound o I/O-bound.

### Desafío

Comparar el procesamiento secuencial, concurrente y paralelo.

# Requisitos

## 1. Implementación inicial

Presentar una primera implementación funcional.

Esta versión servirá como **línea base o baseline** para las mediciones.

## 2. Análisis de complejidad

Deberá identificar al menos **dos algoritmos u operaciones relevantes** y analizar su
complejidad temporal.

Por ejemplo:

Búsqueda secuencial: O(n)
Búsqueda con HashMap: O(1) promedio
Ordenamiento: O(n log n)
Comparación de todos contra todos: O(n²)

No alcanza con indicar la notación: deberán explicar **cómo se obtiene y por qué
resulta relevante para el problema**.

## 3. Elección de algoritmo

Deberán justificar al menos una decisión de diseño relacionada con la selección de un
algoritmo.

Por ejemplo:

Se reemplazó un algoritmo de búsqueda/comparación por otra estrategia porque, para
el volumen esperado de datos, presenta una mejor escalabilidad.

## 4. Estructuras de datos

Deberán utilizar y justificar al menos **dos estructuras de datos**.

Por ejemplo:

- Lista.
- HashMap / Dictionary / Map.
- Set.
- Queue.
- Stack.
- Heap / Priority Queue.
- Grafo.

Se deberá explicar por qué esa estructura resulta adecuada considerando las
operaciones principales.

## 5. Memoización o caching inteligente

El grupo deberá implementar al menos una estrategia de reutilización de resultados.

Deberá explicar:

- Qué se almacena.
- Por qué es conveniente almacenarlo.
- Cuándo se reutiliza.
- Cómo se evita devolver información obsoleta, si corresponde.
- Qué mejora se obtiene.

Es importante diferenciar:

**Memoización:** almacenar resultados de cálculos para reutilizarlos.

**Caching:** almacenar información o resultados de acceso frecuente, definiendo una
estrategia de reutilización e invalidación.

## 6. Concurrencia o paralelismo

Deberán identificar una parte del problema que pueda beneficiarse de procesamiento
concurrente o paralelo.

Se deberá justificar:

- Qué tareas se ejecutan simultáneamente.
- Por qué son independientes.
- Qué mecanismo utiliza el lenguaje.
- Qué problemas pueden aparecer.

Por ejemplo:

**Java**

- ExecutorService.
- CompletableFuture.
- Parallel Streams.

**Python**

- threading.
- multiprocessing.
- concurrent.futures.
- asyncio, cuando sea apropiado.

**Go**

- Goroutines.
- Channels.
- Worker Pools.

No se valorará simplemente "usar threads". Deberán demostrar que existe una
**justificación técnica**.

## 7. Perfilado y medición

El proyecto deberá incluir mediciones antes y después de las optimizaciones.

Cada grupo deberá utilizar herramientas compatibles con el lenguaje seleccionado.

### Python

- cProfile.
- line_profiler.
- memory_profiler.
- Scalene.
- py-spy.

### Java

- Java Flight Recorder.
- Java Mission Control.
- VisualVM.

### Go

- pprof.
- go tool trace.
- Benchmarks integrados con testing.

Las mediciones deberán responder preguntas como:

- ¿Dónde está el principal cuello de botella?
- ¿Qué optimización se realizó?
- ¿Qué impacto tuvo?
- ¿La mejora se mantiene al aumentar el volumen de datos?
- ¿Qué trade-off se produjo?

# Comparación obligatoria

```
Versión Tiempo Memoria Observación
Implementación inicial X ms X MB Baseline
Estructura optimizada X ms X MB Mejora de búsqueda
Algoritmo optimizado X ms X MB Mejor escalabilidad
Concurrencia/paralelismo X ms X MB Evaluar overhead
Versión final X ms X MB Resultado final
```

# Propuesta para la presentación oral

Se dispone de aproximadamente **10 a 15 minutos**.

## Estructura sugerida del PowerPoint

### 1. El problema

- ¿Qué problema resolvieron?
- ¿Por qué resulta interesante desde el punto de vista del rendimiento?

### 2. Diseño inicial

- Arquitectura general.
- Primera solución implementada.

### 3. Complejidad algorítmica

- Operaciones críticas.
- Complejidad temporal.
- Posibles problemas de escalabilidad.

### 4. Algoritmos y estructuras de datos

- Alternativas consideradas.
- Decisiones tomadas.
- Justificación.

### 5. Memoización y caching

- Qué se almacenó.
- Estrategia utilizada.
- Impacto.

### 6. Concurrencia y paralelismo

- Qué parte se paralelizó.
- Implementación.
- Problemas y trade-offs.

### 7. Perfilado

- Herramientas utilizadas.
- Resultados obtenidos.
- Cuellos de botella detectados.

### 8. Comparación de resultados

- Antes y después.
- Gráficos y tablas.
- Escalabilidad.

### 9. Demostración del código

El grupo deberá mostrar las partes más relevantes del código y ejecutar o demostrar al
menos una funcionalidad.

### 10. Conclusiones

- Qué optimización produjo mayor impacto.
- Qué decisión no produjo la mejora esperada.
- Qué harían diferente en una nueva versión.
