# Instalación y ejecución

Todos los comandos se ejecutan desde `p1-dev/`.

## Requisitos

- Python 3.12 o superior (es la versión del CI y la de las dependencias fijadas).
- Git.
- Opcional, para correr en local los controles de secretos y enlaces:
  [Gitleaks](https://github.com/gitleaks/gitleaks) y
  [Lychee](https://github.com/lycheeverse/lychee). En Windows:
  `winget install Gitleaks.Gitleaks` y `winget install lycheeverse.lychee`.

## Obtener el código

```bash
git clone https://github.com/Guillermo-G-M/PEF-26.git
cd PEF-26/p1-dev
```


## Instalación reproducible

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pip install -e . --no-deps
```

Linux / macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install -e . --no-deps
```

`requirements-dev.txt` fija **todas** las versiones, incluidas las transitivas: dos
instalaciones en días distintos obtienen exactamente lo mismo. Se genera a partir de
`requirements-dev.in` (solo dependencias directas) con:

```bash
python -m uv pip compile requirements.in --universal --python-version 3.12 -o requirements.txt
python -m uv pip compile requirements-dev.in --universal --python-version 3.12 -o requirements-dev.txt
```

`--universal` resuelve para todos los sistemas operativos a la vez (por ejemplo,
`colorama` queda marcado solo para Windows). `pip install -e .` es necesario para el
modo `paralelo`: en Windows los procesos hijos se crean con `spawn` y tienen que poder
importar `dupfinder` por nombre.

## Configuración

Variable de entorno del servicio REST:

| Variable | Default | Uso |
|---|---|---|
| `DUPFINDER_SCAN_ROOT` | directorio de trabajo del proceso | Única carpeta (con sus subcarpetas) que `POST /scan` puede escanear |

Parámetros principales:

| Parámetro | Default | Uso |
|---|---|---|
| `--workers` | cantidad de CPUs | Tamaño de los pools (CLI y `/scan`) |
| `--threshold` | 2 MiB | Umbral de ruteo threads/procesos del modo `final` |
| `--batch-size` | 5000 | Archivos en vuelo por lote |
| `--cache-file` | `<padre>/.<dir>.cache.json` | Ubicación del cache de hashes |

## Ejecución

```bash
# Generar un dataset de prueba
python -m dupfinder.generator --out data/set1 --count 1000 --dup-ratio 0.1 --min-size 1024 --max-size 65536 --seed 42

# Detectar duplicados
python run.py --modo final --path data/set1 --workers 4

# Servicio REST (documentación OpenAPI en http://127.0.0.1:8000/docs)
python -m uvicorn dupfinder.api:app --app-dir src
```

## Documentación

```bash
python -m mkdocs serve                            # este sitio, en http://127.0.0.1:8000
python -m sphinx -b html docs docs/_build/html    # referencia del código
```
