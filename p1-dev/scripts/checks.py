"""Controles de calidad y eficiencia del proyecto.

Es el unico lugar donde estan definidos los comandos: el CI (GitHub Actions)
llama a este script con la misma etapa que se usa localmente, asi lo que pasa
en local es lo mismo que pasa en el pipeline.

Uso (desde p1-dev/):
    python scripts/checks.py lint        # Ruff, Pylint, mypy, Radon, Xenon
    python scripts/checks.py security    # Bandit, pip-audit, Gitleaks
    python scripts/checks.py test        # pytest + cobertura
    python scripts/checks.py docs        # MkDocs, Sphinx, Lychee
    python scripts/checks.py perf        # benchmarks, memoria, profiling
    python scripts/checks.py perf --base-src ../base/p1-dev/src   # + regresion
    python scripts/checks.py all

Los reportes quedan en reports/. Sale con codigo 1 si falla algun control
bloqueante. Gitleaks y Lychee son binarios externos: si no estan instalados se
omiten en local, pero en CI (variable CI=true) su ausencia es un fallo.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
PY = sys.executable
IN_CI = os.environ.get("CI", "").lower() == "true"

# --- Umbrales (politica del equipo; justificados en docs/mantenimiento) -------
PYLINT_MIN = "9.5"  # puntaje actual 9.94/10
COVERAGE_MIN = "95"  # cobertura actual 100%
XENON = ["--max-absolute", "B", "--max-modules", "B", "--max-average", "A"]
BENCH_REGRESSION = "median:30%"  # tolerancia frente a la rama principal

# Vulnerabilidades aceptadas de forma explicita (ID + motivo en docs/seguridad.md).
PIP_AUDIT_IGNORE: list[str] = []


@dataclass
class Step:
    name: str
    cmd: list[str]
    blocking: bool = True
    binary: str | None = None  # binario externo requerido (None = modulo Python)
    env: dict[str, str] = field(default_factory=dict)
    ok_codes: tuple[int, ...] = (0,)


@dataclass
class Result:
    name: str
    status: str  # "OK", "FALLA", "AVISO", "OMITIDO"
    detail: str = ""


def _run(step: Step) -> Result:
    if step.binary and shutil.which(step.binary) is None:
        if IN_CI:
            return Result(step.name, "FALLA", f"{step.binary} no esta instalado")
        return Result(step.name, "OMITIDO", f"{step.binary} no instalado (ver docs)")

    print(f"\n=== {step.name}\n$ {' '.join(step.cmd)}", flush=True)
    env = {**os.environ, **step.env}
    proc = subprocess.run(step.cmd, cwd=ROOT, env=env, check=False)
    if proc.returncode in step.ok_codes:
        return Result(step.name, "OK")
    status = "FALLA" if step.blocking else "AVISO"
    return Result(step.name, status, f"codigo de salida {proc.returncode}")


def _py(*args: str) -> list[str]:
    return [PY, "-m", *args]


# --- Etapas -------------------------------------------------------------------


def lint_steps() -> list[Step]:
    return [
        Step("ruff check", _py("ruff", "check", ".")),
        Step("ruff format", _py("ruff", "format", "--check", ".")),
        Step(
            "pylint",
            _py("pylint", "src/dupfinder", f"--fail-under={PYLINT_MIN}", "--output-format=text"),
        ),
        Step("mypy", _py("mypy", "src")),
        Step(
            "radon (reporte)",
            _py("radon", "cc", "-s", "-a", "src", "-O", str(REPORTS / "radon-cc.txt")),
            blocking=False,
        ),
        Step("xenon (complejidad)", _py("xenon", *XENON, "src")),
    ]


def security_steps() -> list[Step]:
    ignore = [arg for vuln in PIP_AUDIT_IGNORE for arg in ("--ignore-vuln", vuln)]
    return [
        # Reporte legible con todas las severidades (no bloquea).
        Step(
            "bandit (reporte)",
            _py(
                "bandit",
                "-r",
                "src",
                "-c",
                "pyproject.toml",
                "-f",
                "txt",
                "-o",
                str(REPORTS / "bandit.txt"),
            ),
            blocking=False,
        ),
        # Bloquea severidad media o alta con confianza media o alta; SARIF para GitHub.
        Step(
            "bandit (bloqueo)",
            _py(
                "bandit",
                "-r",
                "src",
                "-c",
                "pyproject.toml",
                "--severity-level",
                "medium",
                "--confidence-level",
                "medium",
                "-f",
                "sarif",
                "-o",
                str(REPORTS / "bandit.sarif"),
            ),
        ),
        Step(
            "pip-audit",
            _py(
                "pip_audit",
                "-r",
                "requirements-dev.txt",
                "--no-deps",
                "--disable-pip",
                "--progress-spinner",
                "off",
                "-f",
                "json",
                "-o",
                str(REPORTS / "pip-audit.json"),
                *ignore,
            ),
        ),
        Step(
            "gitleaks",
            [
                "gitleaks",
                "git",
                "..",
                "--log-opts=HEAD",
                "--redact",
                "--no-banner",
                "--config",
                ".gitleaks.toml",
                "--report-format",
                "sarif",
                "--report-path",
                str(REPORTS / "gitleaks.sarif"),
            ],
            binary="gitleaks",
        ),
    ]


def test_steps() -> list[Step]:
    return [
        Step(
            "pytest + cobertura",
            _py(
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                f"--cov-fail-under={COVERAGE_MIN}",
                f"--cov-report=xml:{REPORTS / 'coverage.xml'}",
                f"--cov-report=html:{REPORTS / 'htmlcov'}",
                f"--junitxml={REPORTS / 'junit.xml'}",
            ),
        ),
    ]


def docs_steps() -> list[Step]:
    return [
        # NO_MKDOCS_2_WARNING oculta el aviso de fin de vida de Material (mayo 2027),
        # ya registrado en la documentacion; no afecta la construccion.
        Step(
            "mkdocs build --strict",
            _py("mkdocs", "build", "--strict", "-q", "-d", "site"),
            env={"NO_MKDOCS_2_WARNING": "1"},
        ),
        Step("sphinx -W", _py("sphinx", "-W", "-q", "-b", "html", "docs", "docs/_build/html")),
        Step(
            "lychee (enlaces)",
            [
                "lychee",
                "--no-progress",
                "--config",
                "lychee.toml",
                "--format",
                "markdown",
                "--output",
                str(REPORTS / "lychee.md"),
                "manual",
                "README.md",
            ],
            binary="lychee",
        ),
    ]


def perf_steps(base_src: str | None) -> list[Step]:
    bench = _py(
        "pytest",
        "benchmarks",
        "-q",
        "-p",
        "no:cacheprovider",
        "--no-cov",
        "--benchmark-storage",
        f"file://{REPORTS / 'benchmarks'}",
    )
    steps: list[Step] = []
    if base_src:
        # Linea base: los mismos benchmarks contra el codigo de la rama principal,
        # en la misma maquina. Si la base no se puede medir, no bloquea.
        steps.append(
            Step(
                "benchmark linea base",
                [*bench, "-k", "bench", "--benchmark-save", "base"],
                blocking=False,
                env={"PYTHONPATH": str(Path(base_src).resolve())},
            )
        )
    compare = ["--benchmark-compare", f"--benchmark-compare-fail={BENCH_REGRESSION}"]
    has_base = base_src is not None
    steps.append(
        Step(
            "benchmark + memoria",
            [
                *bench,
                f"--benchmark-json={REPORTS / 'benchmark.json'}",
                *(compare if has_base else []),
            ],
        )
    )
    data = REPORTS / "perf-data"
    steps += [
        Step(
            "dataset de profiling",
            _py(
                "dupfinder.generator",
                "--out",
                str(data),
                "--count",
                "1000",
                "--dup-ratio",
                "0.3",
                "--min-size",
                "1024",
                "--max-size",
                "65536",
                "--seed",
                "7",
            ),
            blocking=False,
        ),
        Step(
            "cProfile (reporte)",
            _py(
                "cProfile",
                "-o",
                str(REPORTS / "profile.prof"),
                "-m",
                "dupfinder.cli",
                "--modo",
                "estructura",
                "--path",
                str(data),
            ),
            blocking=False,
        ),
        Step(
            "cProfile -> texto",
            [
                PY,
                "-c",
                "import pstats,sys; s=pstats.Stats(sys.argv[1], stream=open(sys.argv[2],'w'));"
                " s.sort_stats('cumulative').print_stats(25)",
                str(REPORTS / "profile.prof"),
                str(REPORTS / "profile.txt"),
            ],
            blocking=False,
        ),
    ]
    return steps


def _base_was_measured(results: list[Result]) -> bool:
    return any(r.name == "benchmark linea base" and r.status == "OK" for r in results)


def _pip_audit_summary() -> str:
    path = REPORTS / "pip-audit.json"
    if not path.exists():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))
    vulns = [
        (d["name"], d["version"], v["id"])
        for d in data.get("dependencies", [])
        for v in d.get("vulns", [])
    ]
    if not vulns:
        return "pip-audit: sin vulnerabilidades conocidas"
    return "pip-audit: " + ", ".join(f"{n}=={ver} {vid}" for n, ver, vid in vulns)


def _write_summary(stage: str, results: list[Result]) -> None:
    lines = [f"\n=== Resumen: {stage}"]
    lines += [f"  {r.status:8} {r.name}  {r.detail}" for r in results]
    print("\n".join(lines))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"### Etapa `{stage}`\n\n| Control | Resultado | Detalle |\n|---|---|---|\n")
            f.writelines(f"| {r.name} | {r.status} | {r.detail} |\n" for r in results)
            f.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("stage", choices=["lint", "security", "test", "docs", "perf", "all"])
    parser.add_argument("--base-src", help="src/ de la rama principal para comparar benchmarks")
    args = parser.parse_args(argv)

    REPORTS.mkdir(exist_ok=True)
    stages = {
        "lint": lint_steps,
        "security": security_steps,
        "test": test_steps,
        "docs": docs_steps,
        "perf": lambda: perf_steps(args.base_src),
    }
    selected = list(stages) if args.stage == "all" else [args.stage]

    failed = False
    for stage in selected:
        steps = stages[stage]()
        results: list[Result] = []
        for step in steps:
            if (
                step.name == "benchmark + memoria"
                and args.base_src
                and not _base_was_measured(results)
            ):
                # Sin linea base valida: se mide igual, pero sin comparar.
                step.cmd = [c for c in step.cmd if not c.startswith("--benchmark-compare")]
                step.name += " (sin comparacion)"
            results.append(_run(step))
        if stage == "security":
            print(_pip_audit_summary())
        _write_summary(stage, results)
        failed |= any(r.status == "FALLA" for r in results)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
