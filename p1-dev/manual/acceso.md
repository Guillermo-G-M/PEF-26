# Acceso y colaboración

La documentación y el código están en un repositorio **público** de GitHub:
cualquiera puede leerlos, pero solo los colaboradores autorizados pueden
modificarlos, y ningún cambio entra a `main` sin pull request y sin el CI en verde.

## Roles

| Rol | Cómo se obtiene | Leer | Proponer cambios | Integrar en `main` |
|---|---|---|---|---|
| Lector | Cualquier persona | Sí | No | No |
| Colaborador externo | Cualquier cuenta de GitHub, sin invitación | Sí | Sí, desde un *fork* con un pull request | No |
| Integrante del equipo | Invitación del dueño con permiso **Write** (Settings → Collaborators) | Sí | Sí, con ramas en el propio repositorio | Sí, con el pull request aprobado y el CI en verde |
| Dueño | Cuenta que creó el repositorio (**Admin**) | Sí | Sí | Sí; además administra permisos y reglas |

Nadie sin permiso **Write** puede hacer `git push` al repositorio: GitHub lo rechaza.

## Regla de protección de `main`

Configurada en Settings → Rules → Rulesets:

| Regla | Efecto |
|---|---|
| *Require a pull request before merging* (1 aprobación) | Nadie sube directo a `main`; otro integrante revisa el cambio |
| *Require status checks to pass*: **Resultado** | Si falla algún control del CI, el botón de integrar queda bloqueado |
| *Require code scanning results*: CodeQL, *High or higher* | Una alerta de seguridad alta bloquea la integración |
| *Block force pushes* y *Restrict deletions* | El historial de `main` no se puede reescribir ni borrar |

El dueño figura en la lista de excepciones (*bypass*) solo para poder integrar sus
propios pull requests sin un segundo revisor, porque el equipo es chico. El CI
corre igual sobre esos pull requests.

## Flujo de un integrante del equipo

1. Acepta la invitación (llega por correo y aparece en github.com/notifications).
2. Clona el repositorio, crea una rama y hace el cambio (código y/o `manual/`).
3. Corre los controles en local ([Mantenimiento](mantenimiento.md#ejecutar-localmente-los-mismos-controles-que-el-ci)).
4. Sube la rama y abre un pull request hacia `main`.
5. El CI corre solo. Otro integrante revisa, comenta o aprueba.
6. Con la aprobación y **Resultado** en verde, se integra. Al integrar, el sitio de
   documentación se vuelve a publicar automáticamente.

## Flujo de un colaborador externo

1. Hace un *fork* (copia en su cuenta) desde el botón **Fork**.
2. Hace el cambio en su copia y abre un pull request hacia `main` del repositorio
   original.
3. Si es su primera contribución, el CI no corre hasta que un integrante lo
   autoriza con **Approve and run workflows** (configuración por defecto de GitHub,
   evita que código ajeno se ejecute sin revisión).
4. Un integrante revisa el cambio. Si se aprueba y el CI está en verde, lo integra;
   si no, pide cambios o cierra el pull request.

En los pull requests desde un *fork*, GitHub entrega al CI un token de solo
lectura: los controles corren igual y bloquean igual, pero los reportes SARIF no se
suben a *Code scanning* (quedan como artefacto del job).

## Por qué la documentación se mantiene actualizada

- Vive en el mismo repositorio que el código: un cambio de comportamiento y su
  documentación entran en el mismo pull request y se revisan juntos.
- El CI compila el sitio con `mkdocs build --strict` y valida los enlaces con
  Lychee: una página rota bloquea la integración.
- Al integrar en `main`, el job `publicar-docs` publica el sitio en GitHub Pages;
  no hay pasos manuales.
- Cada cambio queda en el historial de Git con su autor y su pull request.
