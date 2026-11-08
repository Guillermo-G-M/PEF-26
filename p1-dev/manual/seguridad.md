# Seguridad

## Controles

| Qué se analiza | Herramienta | Reporte | Cuándo |
|---|---|---|---|
| Código fuente (patrones inseguros de Python) | Bandit | `bandit.txt` (legible) y `bandit.sarif` | Cada push y PR |
| Código fuente (análisis semántico) | CodeQL | Pestaña *Security* de GitHub | Cada push y PR, y semanal |
| Dependencias con vulnerabilidades conocidas | pip-audit | `pip-audit.json` | Cada push y PR |
| Actualización de dependencias | Dependabot | Alertas y pull requests automáticos | Semanal |
| Secretos en el historial de Git | Gitleaks | `gitleaks.sarif` | Cada push y PR (historial completo) |

Los SARIF de Bandit y Gitleaks se suben a *Security → Code scanning*, junto con los
de CodeQL, para ver todas las alertas en un mismo lugar.

## Política de bloqueo

| Hallazgo | Acción |
|---|---|
| Bandit: severidad media o alta con confianza media o alta | **Bloquea** |
| Bandit: severidad baja | Se reporta; se revisa antes de integrar |
| pip-audit: cualquier vulnerabilidad conocida en una dependencia fijada | **Bloquea**, salvo excepción documentada abajo |
| Gitleaks: cualquier secreto detectado | **Bloquea** |
| CodeQL: alerta de severidad alta o crítica | **Bloquea** (regla de protección de `main`) |
| CodeQL: media o baja | Se revisa antes de integrar |
| Dependabot | No bloquea; abre un PR que pasa por el mismo CI |

pip-audit bloquea todo porque las dependencias están fijadas: corregir suele ser
subir una versión en `requirements-dev.in` y recompilar.

## Riesgos identificados

| Riesgo | Impacto | Medida |
|---|---|---|
| `/scan` acepta cualquier ruta del servidor | Un cliente puede listar y leer metadatos de cualquier directorio accesible | El servicio se levanta solo en `127.0.0.1` (uso local); para exponerlo habría que limitar `path` a un directorio raíz y agregar autenticación |
| `/scan` sobre un árbol enorme | Consumo alto de CPU y disco (denegación de servicio) | Batching acota la memoria; para exponerlo, limitar workers y tiempo por request |
| Cache JSON modificado a mano | Un hash falso haría reportar duplicados inexistentes | El cache se guarda junto al directorio del usuario; es un riesgo local y aceptado |
| Dependencias de terceros | Vulnerabilidades heredadas | pip-audit en cada ejecución + Dependabot + versiones fijadas |
| Secretos subidos por error | Filtración de credenciales | Gitleaks sobre todo el historial; el proyecto no usa credenciales |

## Falsos positivos y excepciones

| Herramienta | Hallazgo | Decisión | Justificación |
|---|---|---|---|
| Bandit B311 | `random.Random(seed)` en `generator.py` | Excepción con `# nosec B311` | El azar solo genera datos de prueba; se necesita una semilla reproducible y no protege claves ni tokens |
| Bandit (configuración) | `assert` y archivos temporales en `tests/` y `benchmarks/` | Carpetas excluidas en `pyproject.toml` | Es el uso normal de pytest; no es código de producción |

Toda excepción nueva se agrega en esta tabla en el mismo pull request que la
introduce (`# nosec` con código de regla, `PIP_AUDIT_IGNORE` en
`scripts/checks.py` o `.gitleaks.toml`).

## Medidas correctivas

- **Vulnerabilidad en una dependencia:** subir la versión en `requirements*.in`,
  recompilar los `.txt`, correr `python scripts/checks.py all`. Si no hay versión
  corregida, agregar el ID a `PIP_AUDIT_IGNORE` con fecha y motivo en esta página.
- **Secreto detectado:** revocar la credencial en el servicio que la emitió (borrarla
  del código no alcanza, sigue en el historial) y luego limpiar el historial.
- **Hallazgo de Bandit o CodeQL:** corregir el código; si es falso positivo,
  documentarlo en la tabla de arriba.
