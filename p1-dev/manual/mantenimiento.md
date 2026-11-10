# Mantenimiento

## Cómo contribuir

Roles, permisos y flujo para colaboradores externos: [Acceso y colaboración](acceso.md).

1. Crear una rama desde `main`: `git switch -c feature/descripcion-corta`.
2. Hacer el cambio con sus pruebas y, si cambia el comportamiento, su documentación
   en `manual/`.
3. Correr los controles en local (abajo). Lo que pasa en local pasa en el CI.
4. Abrir un pull request hacia `main`. El CI corre solo; el PR no se puede integrar
   hasta que el check **Resultado** esté en verde.
5. Si se agrega una excepción de seguridad, documentarla en
   [Seguridad](seguridad.md#falsos-positivos-y-excepciones) en el mismo PR.

## Ejecutar localmente los mismos controles que el CI

Con el entorno instalado (ver [Instalación](instalacion.md)) y desde `p1-dev/`:

```bash
python scripts/checks.py lint       # Ruff, Pylint, mypy, Radon, Xenon
python scripts/checks.py security   # Bandit, pip-audit, Gitleaks
python scripts/checks.py test       # pytest + cobertura >= 95%
python scripts/checks.py docs       # MkDocs, Sphinx, Lychee
python scripts/checks.py perf       # benchmarks, memoria, profiling
python scripts/checks.py all        # todo, en ese orden
```

Al final de cada etapa se imprime un resumen (`OK`, `FALLA`, `AVISO`, `OMITIDO`) y
los reportes quedan en `reports/`. El script sale con código 1 si algún control
bloqueante falla.

Diferencias con el CI:

- **Gitleaks y Lychee** son binarios externos. Si no están instalados, en local se
  marcan como `OMITIDO`; en el CI su ausencia es un fallo.
- **Comparación de benchmarks:** en el CI se hace automáticamente contra `main`.
  En local, con una copia de `main` en otra carpeta:

    ```bash
    git worktree add ../base main
    python scripts/checks.py perf --base-src ../base/p1-dev/src
    git worktree remove ../base
    ```

## Umbrales

| Umbral | Valor | Motivo |
|---|---|---|
| Cobertura mínima | 95% | Medido: 100%. El margen evita rechazar por una línea defensiva nueva, pero detecta código sin pruebas. |
| Pylint mínimo | 9.5 | Medido: 9.94. Permite advertencias de estilo puntuales, no un deterioro general. |
| Complejidad (Xenon) | Función ≤ B (≤ 10), módulo ≤ B, promedio A | Medido: máximo B (8), promedio A (2.8). Una función C ya es difícil de probar por completo. |
| Regresión de benchmark | Mediana +30% | La variación entre corridas en la misma máquina ronda 5–10%; 30% es una regresión real. |
| Memoria del hash de 32 MB | 1 MiB | Medido: 0.13 MiB. Si el hash dejara de leer por chunks, el pico subiría a ~32 MiB. |
| Memoria del escaneo de 400 archivos | 2 MiB | Medido: 1.2 MiB. Margen para variaciones entre sistemas operativos. |

Para cambiar un umbral: editar la constante al principio de `scripts/checks.py` (o
el límite en `benchmarks/test_memory.py`), justificarlo en esta tabla y abrir un PR.

## Resolver fallos del pipeline

| Job / control que falla | Qué mirar | Cómo resolverlo |
|---|---|---|
| `ruff format` | Archivos sin formato | `python -m ruff format .` |
| `ruff check` | Regla y línea en el log | `python -m ruff check --fix .` o corregir a mano |
| `pylint` | Puntaje y mensajes | Corregir los mensajes nuevos del log |
| `mypy` | Error de tipos y línea | Corregir la anotación o el código; no usar `# type: ignore` sin motivo |
| `xenon` | Función con rango C o mayor (ver `radon-cc.txt`) | Dividir la función |
| `pytest` | Prueba fallida (`junit.xml`) | Reproducir: `python -m pytest tests/<archivo> -q` |
| Cobertura | Líneas sin cubrir (`htmlcov/`) | Agregar pruebas para esas líneas |
| `bandit` | Regla (ej. B602) en `bandit.txt` | Corregir; si es falso positivo, `# nosec Bxxx` + documentarlo |
| `pip-audit` | Paquete e ID en `pip-audit.json` | Subir la versión en `requirements*.in` y recompilar (ver [Instalación](instalacion.md)) |
| `gitleaks` | Archivo y regla en `gitleaks.sarif` | Revocar el secreto; si es falso positivo, agregarlo a `.gitleaks.toml` |
| `mkdocs` / `sphinx` | Advertencia en el log | Corregir el enlace o la referencia indicada |
| `lychee` | URL en `lychee.md` | Corregir o quitar el enlace; si el sitio externo está caído, reintentar el job |
| Benchmark | Benchmark y porcentaje en el log | Reproducir con `--base-src`; perfilar con `profile.prof`; si la regresión es intencional, justificarla en el PR |
| Memoria | Pico impreso en el log | Buscar qué estructura crece (tracemalloc / Scalene) |
| `Resultado` | Qué job falló (está listado en el log) | Ir a ese job |

Un job puede volver a correrse desde la pestaña *Actions* con *Re-run failed
jobs* (útil solo para fallos externos, como un sitio caído en Lychee).

## Actualizar dependencias

Dependabot abre un PR semanal. Resuelve las versiones con Python 3.12, el mismo del
CI, que toma de `.python-version` y de `requires-python = ">=3.12"` en
`pyproject.toml`. Con una versión mínima más vieja no encontraría versiones que solo
existen para Python 3.11 o más (como Sphinx 9) y fallaría.

Si se actualiza a mano:

```bash
# editar requirements.in / requirements-dev.in
python -m uv pip compile requirements.in --universal --python-version 3.12 -o requirements.txt
python -m uv pip compile requirements-dev.in --universal --python-version 3.12 -o requirements-dev.txt
python -m pip install -r requirements-dev.txt
python scripts/checks.py all
```
