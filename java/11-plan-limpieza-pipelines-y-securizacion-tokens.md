# 11. Plan de limpieza de pipelines y securizaciÃ³n de tokens

> **Estado (2026-07-16):** Fases 0, 1, 1.5, 1.6, 2, 3, 4 y 5 âœ… **completadas** (13 repos migrados).
> `NOVA_RELEASE_PAT` eliminado de los 14 repos que lo tenian. 0 secrets residuales en toda
> la org `ahincho`. Decisiones estrategicas D5-D8 despriorizadas (sin `NOVA_RELEASE_PAT` no
> queda PAT que migrar a identidad dedicada para CI/CD). Ver §11.13 para los detalles de la
> migracion a Gradle de `nova-java-architecture-rules` y los 3 bugs descubiertos.
> **Fecha:** 2026-07-16.
> **Aplica a:** Equipo Nova, mantenedores de `nova-devops`, security audit de la org `ahincho`.

---

## 11.1 Contexto y diagnÃ³stico

AuditorÃ­a realizada el 2026-07-15 sobre el repo `ahincho/nova-devops` y los 29 repos Nova
publicados en la org `ahincho`. Se identificaron **3 problemas concretos** + 1 backlog
(framework NestJS) que se detallan en este plan.

### 11.1.1 Universo auditado (post-Fase 1)

| CategorÃ­a | Repos |
|---|---|
| Repos Nova publicados en `ahincho` | **29** (19 Java + 4 NestJS + 6 varios) |
| Workflows reusables en `nova-devops` | **13 reusables + 2 single-purpose** (post-Fase 1: se borraron 10 reusables muertos) |
| Composite actions en `nova-devops` | 6 (`nova-setup-{java,node,gpg}`, `nova-validate-build`, `nova-gather-facts`, `nova-publish-aggregator`) |
| Repos con `workflow_run` pattern | **14** (post-Fase 3: piloto + 12 rÃ©plicas + extension Quarkus previa) |
| Repos con `NOVA_RELEASE_PAT` | **8** (post-Fase 3: eran 19, ahora 8) |

### 11.1.2 Problemas detectados (resumen ejecutivo)

| # | Problema | Severidad | Estado al 2026-07-15 |
|---|---|---|---|
| 1 | **10** workflows reusables con **0 consumidores** (6 multi-registry + 2 version-bump + changelog + commitlint) | Media (deuda tÃ©cnica) | âœ… **Fase 1 COMPLETADA** â€” commit `1a61e83` |
| 2 | `nova-java-api-standard-quarkus-extension` tiene ambos tokens (`NOVA_PACKAGES_READ_TOKEN` + `NOVA_RELEASE_PAT`) â€” el segundo es redundante | Baja (redundancia) | âœ… **Fase 2 COMPLETADA** â€” commit `a6d6013` con patrÃ³n `workflow_run` (Â§11.11) |
| 3 | `NOVA_RELEASE_PAT` se usa **solo como fallback de read** en 18 repos restantes, no para release operations | Media (segregacion de privilegios) | [OK] **Fase 3 COMPLETADA** (12 repos migrados, 7 con `NOVA_RELEASE_PAT` aun pendiente de borrar tras configurar READ) |
| 4 | 4 repos NestJS sin secretos ni pipelines | Backlog (fuera de alcance) | Backlog (Â§11.6) |

---

## 11.2 Problema 1: 10 workflows muertos (multi-registry + version-bump + changelog + commitlint)

### 11.2.1 Estado actual

Workflows **publicados en `ahincho/nova-devops/.github/workflows/`** pero **no consumidos por ningÃºn repo Nova** (verificado el 2026-07-15 con bÃºsqueda exhaustiva en los 29 repos):

**Multi-registry (6) â€” YAGNI puro, anticiparon registries que nunca se usaron**:

| Workflow | TamaÃ±o | Consumidores |
|---|---|---|
| `reusable-publish-gradle-maven-central.yml` | 2.5 KB | **0** |
| `reusable-publish-gradle-multi-registry.yml` | 4.1 KB | **0** |
| `reusable-publish-gradle-nexus.yml` | 3.0 KB | **0** |
| `reusable-publish-maven-maven-central.yml` | 3.1 KB | **0** |
| `reusable-publish-maven-multi-registry.yml` | 4.1 KB | **0** |
| `reusable-publish-maven-nexus.yml` | 3.5 KB | **0** |

**Version-bump + commitlint + changelog (4) â€” reemplazados por release-please + reusable-release-publish (NOVA-SEMVER-13, Sprint 3)**:

| Workflow | TamaÃ±o | Consumidores | RazÃ³n de obsolescencia |
|---|---|---|---|
| `reusable-version-bump-gradle.yml` | 4.2 KB | **0** | Reemplazado por `release-please` (PR de release â†’ tag â†’ publish). |
| `reusable-version-bump-maven.yml` | 4.4 KB | **0** | Idem. |
| `reusable-changelog.yml` | 4.1 KB | **0** | Reemplazado por `release-please` que genera CHANGELOG.md automÃ¡ticamente. |
| `reusable-commitlint.yml` | 2.7 KB | **0** | Lefthook + commitlint ya validan en commit local; no se necesitaba validaciÃ³n de CI. |
| **TOTAL** | **35.6 KB** | **0** | |

### 11.2.2 Por quÃ© son deuda

- **YAGNI aplicado al revÃ©s**: se anticiparon 3 registries Ã— 2 herramientas Ã— escenarios
  futuros que **nunca se materializaron** (ningÃºn repo Nova publica a Maven Central ni a
  Nexus hoy).
- **Reemplazo tecnolÃ³gico**: el patrÃ³n `version-bump + publish` con PR labels fue
  reemplazado por `release-please` + tag-driven publish (NOVA-SEMVER-13). El commit
  `release-publish.yml` L8 lo dice literalmente: *"Replaces the version-bump + publish
  chain with a single, deterministic flow"*.
- **Costo de mantenimiento**: cada workflow tiene un comentario largo explicando scopes,
  secretos y permisos. Si el cÃ³digo cambia (p. ej. el patrÃ³n de secretos), hay que
  actualizar muchos archivos en lugar de uno.
- **Riesgo de seguridad por confusiÃ³n**: un mantenedor podrÃ­a asumir que estos workflows
  estÃ¡n "activos" y basar decisiones de seguridad en un modelo que no se usa.
- **Costo de revisiÃ³n de PRs**: cuando se toca `nova-devops`, hay que validar 10 archivos
  innecesarios.
- **README inflado**: el README dedicaba 1 secciÃ³n completa a cada workflow muerto
  (10 secciones), inflando la documentaciÃ³n sin valor.

### 11.2.3 AcciÃ³n ejecutada (Fase 1 âœ… COMPLETADA 2026-07-15)

**Commit `1a61e83`** en `ahincho/nova-devops`, pusheado a `main`:
```
chore(workflows): remove 10 unused reusable workflows + update README

- reusable-publish-{gradle,maven}-{maven-central,multi-registry,nexus}.yml (6)
- reusable-version-bump-{gradle,maven}.yml (2)
- reusable-changelog.yml, reusable-commitlint.yml (2)
```

**Cambios colaterales en el mismo commit**:
- README.md actualizado: quitadas 10 menciones en tablas + 10 secciones dedicadas.
- README.md: secciones renumeradas al orden lÃ³gico (Maven â†’ Gradle â†’ Release).
- README.md: `SONAR_TOKEN` â†’ `NOVA_SONAR_TOKEN` (consistencia con el rename aplicado en
  workflows en commit `06c808a`).
- README.md: tabla "Secretos Necesarios" limpiada â€” quitadas filas de `GH_PAT`,
  `MAVEN_USERNAME`, `MAVEN_TOKEN`, `NEXUS_USERNAME`, `NEXUS_PASSWORD`, `GPG_SIGNING_*`
  (todas asociadas a workflows borrados).

### 11.2.4 Riesgo de la acciÃ³n

**Cero, verificado**:
- 0 referencias en `.github/workflows/` de `nova-devops` (post-borrado).
- 0 referencias en `.github/workflows/` de los 18 repos Java con Gradle.
- 0 referencias en `.github/workflows/` de los 4 repos NestJS.
- 0 referencias en `.github/workflows/` de `nova-bom`, `nova-devops`, `nova-docs`,
  `nova-infrastructure`, `nova-java-example`, `nova-java-quarkus-example`,
  `nova-java-spring-boot-archetype`, `nova-java-spring-boot-parent`.
- README actualizado coherente con el nuevo estado.

---

## 11.3 Problema 2: Token redundante en `nova-java-api-standard-quarkus-extension`

### 11.3.1 Estado actual (post-Fase 2)

Ãšnico repo Nova que **tenÃ­a ambos tokens** configurados. **Resuelto el 2026-07-15**:

```
Secret                                    Estado antes   Estado despuÃ©s
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
NOVA_PACKAGES_READ_TOKEN                  âœ… configurado âœ… configurado (mantenido)
NOVA_RELEASE_PAT                          âœ… configurado âŒ BORRADO
```

### 11.3.2 Por quÃ© quedÃ³ asÃ­ (historia)

| Fecha | Evento |
|---|---|
| 2026-06 | Se introduce `NOVA_RELEASE_PAT` (PAT classic, scope `repo`) como Ãºnico token para resolver deps cross-repo + tag push. |
| 2026-07-08 | Se introduce `NOVA_PACKAGES_READ_TOKEN` (scope solo `packages:read`) como alternativa read-only. Se configura en `nova-java-example` y `nova-java-quarkus-example` (instances). |
| 2026-07-12 | Durante debug del **ghost-publish** del extension Quarkus, se agrega `NOVA_PACKAGES_READ_TOKEN` al extension para verificar que el cross-repo read funcionara con un token read-only. |
| 2026-07-12 | Se resuelve el ghost-publish, pero `NOVA_PACKAGES_READ_TOKEN` queda configurado **sin remover** `NOVA_RELEASE_PAT`. |

Resultado pre-Fase 2: el extension tenÃ­a ambos, y como el fallback chain prefiere
`NOVA_PACKAGES_READ_TOKEN`, es este el que realmente se usaba. El `NOVA_RELEASE_PAT`
estaba **muerto** en este repo... o casi.

### 11.3.3 Hallazgo durante Fase 2: el PAT NO estaba del todo muerto

Durante la validaciÃ³n previa (Â§11.3.4), se descubriÃ³ que `NOVA_RELEASE_PAT` **sÃ­ se
usaba**, no como fallback de read, sino para **preservar el auto-trigger del publish**:

| Workflow | LÃ­nea original | Uso real |
|---|---|---|
| `publish-on-tag.yml` | L85 | `NOVA_PACKAGES_READ_TOKEN \|\| NOVA_RELEASE_PAT \|\| GITHUB_TOKEN` (segundo fallback, ya no necesario) |
| `release-please.yml` | L26 | `NOVA_RELEASE_PAT \|\| GITHUB_TOKEN` (**Ãºnica razÃ³n de ser del PAT**) |

**El problema**: GitHub Actions tiene la restricciÃ³n documentada de que un workflow
creado con `GITHUB_TOKEN` **no dispara workflows downstream** cuando hace push de tags.
Por eso `release-please.yml` usaba el PAT: para que el tag push resultante disparara
`publish-on-tag.yml` automÃ¡ticamente.

**Borrar el PAT sin redesign** hubiera significado que el publish quedara **manual**
(Actions â†’ Run workflow â†’ 1 click por release). Trade-off aceptable pero subÃ³ptimo.

### 11.3.4 SoluciÃ³n implementada: trigger `workflow_run` (Â§11.11)

En vez de aceptar el trade-off, se rediseÃ±Ã³ el trigger de `publish-on-tag.yml`:

**Antes**:
```yaml
on:
  push:
    tags: ['v[0-9]+.[0-9]+.[0-9]+']   # GitHub NO triggerea si el tag fue creado con GITHUB_TOKEN
```

**DespuÃ©s**:
```yaml
on:
  workflow_run:
    workflows: ["Release Please"]
    types: [completed]
    branches: [main]
```

`workflow_run` **sÃ­ se dispara** incluso cuando el upstream workflow usÃ³ `GITHUB_TOKEN`,
porque el downstream corre con su propio `GITHUB_TOKEN` (fresco, no el del actor upstream).
**No hay trade-off**: auto-trigger preservado, PAT eliminado.

Adicionalmente se agregÃ³ un step `Detect new release tag` que compara el Ãºltimo tag
semver contra `.release-please-manifest.json` para confirmar que release-please **sÃ­**
creÃ³ un release en este run (evita re-publishs cuando hay push a main sin conventional
commits).

### 11.3.5 AcciÃ³n ejecutada (Fase 2 âœ… COMPLETADA 2026-07-15)

**Commit `a6d6013`** en `nova-java-api-standard-quarkus-extension`, pusheado a `main`:
```
chore(workflows): redesign publish trigger via workflow_run + drop NOVA_RELEASE_PAT
```

**Cambios concretos**:
1. `publish-on-tag.yml`: trigger `push:tags` â†’ `workflow_run` con nuevo step de detecciÃ³n.
2. `release-please.yml`: usa solo `GITHUB_TOKEN`, sin fallback a PAT.
3. `build.gradle.kts`: sin cambios (nunca usÃ³ `NOVA_RELEASE_PAT`).
4. Secret `NOVA_RELEASE_PAT` borrado del repo vÃ­a `gh secret delete`.

### 11.3.6 ValidaciÃ³n post-deploy

Pendiente validar en el prÃ³ximo release real de la extension:
- Mergear un PR de release-please.
- Confirmar que `publish-on-tag.yml` corre automÃ¡ticamente vÃ­a `workflow_run`.
- Confirmar que el JAR se publica correctamente a GitHub Packages.

Si el flujo funciona, el patrÃ³n es **replicable a los 18 repos restantes** en Fase 3
(ver Â§11.11).

### 11.3.7 Implicancia estratÃ©gica

**El patrÃ³n `workflow_run` cambia el alcance de Fase 3**: ya no es necesario mantener
`NOVA_RELEASE_PAT` solo para preservar el auto-trigger. Los 18 repos pueden migrar al
modelo estricto de 1 token (solo `NOVA_PACKAGES_READ_TOKEN` + `GITHUB_TOKEN`) sin
perder la funcionalidad de auto-publish.

Esto **adelgaza significativamente** la decisión D5 (¿machine user / GitHub App?): si
ningún repo necesita `NOVA_RELEASE_PAT` después de replicar el patrón, no hay PAT que
migrar. **El PAT personal actualmente en uso queda obsoleto para CI/CD** (sigue
usándose solo para acceso local del owner) — ver §11.8 nota sobre rotación urgente.

---

## 11.4 Problema 3: SeparaciÃ³n de responsabilidades de tokens (anÃ¡lisis detallado, modelo estricto)

### 11.4.0 Regla del modelo estricto

**Solo 2 tokens de GitHub configurados**. Cero fallbacks. Si algo no entra en estos 2
tokens, se consulta al usuario antes de aÃ±adir nada.

| Token | Scope mÃ­nimo | Responsabilidad Ãºnica |
|---|---|---|
| `NOVA_PACKAGES_READ_TOKEN` | `packages:read` | Resolver deps Nova publicadas en otros repos (read-only cross-repo). |
| `NOVA_RELEASE_PAT` | `repo` (PAT classic) **o** fine-grained `contents:write` + `pull-requests:write` + `packages:write` | Publicar releases y todo lo que requiera push/tag/PR en nombre de Nova. |

**Tokens externos permitidos (documentados, no son GitHub tokens)**:
- `NVD_API_KEY`: API key de NIST NVD para OWASP dependency check.
- `NOVA_SONAR_TOKEN`: token de SonarCloud (renombrado desde `SONAR_TOKEN` el 2026-07-15).
  **DORMANT** â€” no configurado en ningÃºn repo, pero los reusables de Sonar ya lo
  referencian con warning si falta. Se activarÃ¡ cuando se integre SonarCloud.

Cualquier otro secret que se quiera aÃ±adir debe:
- Ser **una API key de un servicio externo** justificado, o
- **Ser notificado al usuario** antes de configurar.

### 11.4.1 Mapa actual de uso de tokens (con fallbacks)

BÃºsqueda exhaustiva el 2026-07-15 en todos los workflows de `nova-devops`:

**`NOVA_RELEASE_PAT`** se usa en **5 reusables**, siempre como fallback de read:

```
reusable-build-gradle.yml      (lÃ­neas 51, 54, 58, 73) â€” fallback TOKEN_B
reusable-build-matrix.yml      (lÃ­neas 52, 69)         â€” fallback packages-read-token
reusable-build-maven.yml       (lÃ­nea 33)              â€” fallback packages-read-token
reusable-owasp-check.yml       (lÃ­neas 88, 232)        â€” fallback packages-read-token
reusable-sbom.yml              (lÃ­neas 58, 67)         â€” fallback packages-read-token
```

**`NOVA_PACKAGES_READ_TOKEN`** se usa en los **mismos 5 reusables**, como token primario:

```
reusable-build-gradle.yml      (lÃ­neas 50, 54, 74)     â€” token primario (TOKEN_A)
reusable-build-matrix.yml      (lÃ­neas 52, 69)         â€” token primario
reusable-build-maven.yml       (lÃ­nea 33)              â€” token primario
reusable-owasp-check.yml       (lÃ­neas 88, 232)        â€” token primario
reusable-sbom.yml              (lÃ­neas 58, 67)         â€” token primario
```

**`GH_TOKEN`** (input `secrets.GH_TOKEN` en workflow_call, pasado por el caller) se usa en
**6 reusables + 1 single** para publish/release:

```
reusable-publish-gradle.yml        (L24 input, L69 use)         â€” publicaciÃ³n a GH Packages
reusable-publish-maven.yml         (L24 input, L67 use)         â€” publicaciÃ³n a GH Packages
reusable-release-please.yml        (L37 input, L53+L63 use)     â€” push PR de release + tag push
reusable-release-publish.yml       (L35 input, L113+L120 use)   â€” publicaciÃ³n post-release
reusable-version-bump-gradle.yml  (L30 use)                    â€” bump de versiÃ³n
reusable-version-bump-maven.yml   (L37 use)                    â€” bump de versiÃ³n
reusable-commitlint.yml            (L26 input)                  â€” push del commit de fix
nvd-mirror-update.yml              (L60, L93 use github.token)  â€” publica el mirror NVD a nova-devops
```

> **Nota importante**: `reusable-version-bump-{gradle,maven}.yml` recibe el secret con
> nombre `GH_PAT` (no `GH_TOKEN`) â€” ver L30/L37. Esto es una inconsistencia histÃ³rica
> a corregir en la migraciÃ³n.

### 11.4.2 Naturaleza del `NOVA_RELEASE_PAT` actual: **PAT personal**

Verificado el 2026-07-15 vÃ­a `GET https://api.github.com/user` con el propio token:

| Atributo | Valor |
|---|---|
| Tipo de token | **PAT classic** (no fine-grained) |
| Owner del token | `ahincho` (login personal = `Angel Eduardo Hincho Jove`) |
| Tipo de cuenta | `User` (no organizaciÃ³n, no GitHub App) |
| Scopes otorgados | `repo`, `write:packages`, `delete:packages` |
| Scope `repo` cubre implÃ­citamente | `repo:status`, `repo_deployment`, `public_repo`, `repo:invite`, `security_events`, `read:packages` |

**Esto significa que `NOVA_RELEASE_PAT`:**
1. **Es un PAT personal tuyo**, no un token dedicado ni una service account.
2. **Tiene scope `repo` completo** = acceso total a TODOS los repos donde estÃ¡
   configurado (push, merge, force-push, eliminar refs, etc.), no solo release.
3. **Si tu cuenta personal se compromete**, todos los repos Nova quedan expuestos.
4. **Si rotÃ¡s tu password / salÃ­s de la org**, los 19 builds que dependen de este token
   se rompen hasta que se configure uno nuevo.

### 11.4.3 Hallazgo clave (versiÃ³n estricta)

**`NOVA_RELEASE_PAT` se usa HOY en 2 roles distintos** (modelo actual violÃ¡ tu regla):

1. **Como fallback de read** (5 reusables) â€” el `NOVA_PACKAGES_READ_TOKEN` lo prefiere
   pero el `NOVA_RELEASE_PAT` estÃ¡ en el chain. **Esto es un fallback**, no permitido.
2. **Como identidad para publish** â€” pero los publish workflows reciben `GH_TOKEN` (que
   el caller pasa como `${{ secrets.GITHUB_TOKEN }}` o `${{ secrets.NOVA_RELEASE_PAT }}`
   segÃºn el repo).

**Doble falla del modelo actual**:

- **Falla de segregaciÃ³n**: el mismo PAT cubre read y release (con scopes diferentes
  necesarios). Un leak de la read surface expone tambiÃ©n la write surface.
- **Falla de fallback**: si configuras `NOVA_RELEASE_PAT` solo (sin READ), el build
  funciona pero usa el PAT personal con scope `repo` para una operaciÃ³n de read.

### 11.4.4 Modelo objetivo estricto (2 tokens, sin fallbacks, sin GH_TOKEN)

Cada token tiene **una sola responsabilidad y una identidad dedicada, NO personal**:

| OperaciÃ³n | Token | JustificaciÃ³n |
|---|---|---|
| Resolver deps Nova cross-repo (starters â†’ libs) | `NOVA_PACKAGES_READ_TOKEN` | Read-only. Sin este token, el build **falla explÃ­citamente** (no fallback). |
| Push tag / crear PR / crear GitHub Release | `NOVA_RELEASE_PAT` | Scope `contents:write` + `pull-requests:write`. |
| Publicar JAR a GitHub Packages (mismo repo) | `NOVA_RELEASE_PAT` | Scope `packages:write`. |
| Publicar a **Maven Central** (futuro, cross-org) | `NOVA_RELEASE_PAT` | Scope `repo` completo + credenciales de Sonatype. |
| Publicar a **Nexus privado** (futuro, cross-org) | `NOVA_RELEASE_PAT` | Idem. |
| Version bump / commitlint fix / NVD mirror update | `NOVA_RELEASE_PAT` | Scope `contents:write` + `pull-requests:write`. |

**`GITHUB_TOKEN` auto del runner**: solo para system ops (checkout, setup-java, upload
artifacts, `gh` CLI). **NO** se pasa como `secrets.GH_TOKEN` en workflow_call para
release operations.

**`GH_PAT`** (input inconsistente en `reusable-version-bump-*`): renombrar a
`NOVA_RELEASE_PAT` en la migraciÃ³n.

### 11.4.5 Cambios concretos en workflows

#### Cambio A: Eliminar TODOS los fallbacks de read (5 reusables)

**Antes** (en cada uno de los 5 reusables):
```yaml
NOVA_PACKAGES_READ_TOKEN || NOVA_RELEASE_PAT || GITHUB_TOKEN
```

**DespuÃ©s** (sin fallback, falla explÃ­cita):
```yaml
NOVA_PACKAGES_READ_TOKEN  # REQUIRED. Sin esto el build falla con ::error::
```

ImplementaciÃ³n prÃ¡ctica en `reusable-build-gradle.yml` (lÃ­nea 50-66 â†’ eliminar TOKEN_B
y TOKEN_C):

```yaml
- name: Validate NOVA_PACKAGES_READ_TOKEN
  id: validate_read_token
  env:
    TOKEN: ${{ secrets.NOVA_PACKAGES_READ_TOKEN }}
  run: |
    if [ -z "${TOKEN}" ]; then
      echo "::error::NOVA_PACKAGES_READ_TOKEN is required to resolve Nova cross-repo dependencies. Configure it in repo/org secrets. See docs/java/11 Â§11.4.4."
      exit 1
    fi
    echo "value=${TOKEN}" >> "$GITHUB_OUTPUT"
```

> **Nota**: Cambio A hace que los 18 repos con solo `NOVA_RELEASE_PAT` fallen
> inmediatamente. La migraciÃ³n debe ser: agregar READ primero, luego eliminar RELEASE
> (despuÃ©s de validar). Cambio A NO se aplica hasta que los 18 repos estÃ©n migrados.

#### Cambio B: Reemplazar `GH_TOKEN` (caller-provided) por `NOVA_RELEASE_PAT`

Workflows afectados: 6 reusables + 1 single-purpose.

**Estrategia**: el caller sigue pasando `secrets.GH_TOKEN` al reusable (por la
restricciÃ³n de nombres de GitHub Actions), pero el valor que pasa debe ser
`secrets.NOVA_RELEASE_PAT`, no `secrets.GITHUB_TOKEN`. Esto renombra la responsabilidad
sin tocar el contrato del workflow_call (no se puede usar `NOVA_RELEASE_PAT` como nombre
de `workflow_call.secrets` porque colisionarÃ­a con el secret real al mapear).

Workflows a modificar:

```
reusable-publish-gradle.yml          â†’ caller pasa GH_TOKEN: ${{ secrets.NOVA_RELEASE_PAT }}
reusable-publish-maven.yml           â†’ caller pasa GH_TOKEN: ${{ secrets.NOVA_RELEASE_PAT }}
reusable-release-please.yml          â†’ caller pasa GH_TOKEN: ${{ secrets.NOVA_RELEASE_PAT }}
reusable-release-publish.yml         â†’ caller pasa GH_TOKEN: ${{ secrets.NOVA_RELEASE_PAT }}
reusable-commitlint.yml              â†’ caller pasa GH_TOKEN: ${{ secrets.NOVA_RELEASE_PAT }}
reusable-version-bump-gradle.yml     â†’ caller pasa GH_PAT: ${{ secrets.NOVA_RELEASE_PAT }}  (renombra GH_PAT â†’ GH_TOKEN input, consistente)
reusable-version-bump-maven.yml      â†’ caller pasa GH_PAT: ${{ secrets.NOVA_RELEASE_PAT }}
nvd-mirror-update.yml                â†’ usar secrets.NOVA_RELEASE_PAT directo (single-purpose, no input restriction)
```

> **DecisiÃ³n pendiente D7**: Â¿es OK seguir usando el nombre `GH_TOKEN` como input del
> workflow_call (por la limitaciÃ³n de GitHub Actions) aunque el valor real venga de
> `NOVA_RELEASE_PAT`? La alternativa es forkear la action externa de release-please para
> que acepte un nombre de input distinto â€” mucho trabajo para un cambio cosmÃ©tico.

#### Cambio C: Migrar `NOVA_RELEASE_PAT` a identidad dedicada (machine user / GitHub App)

**Bloqueante** para considerar el modelo "production-ready":

1. Crear **GitHub App** `nova-bot` (recomendado sobre machine user porque es mÃ¡s seguro:
   permisos granulares por repo, expiraciÃ³n de tokens, audit log separado).
2. Instalar la App en cada repo donde publique.
3. Otorgar a la App solo los permisos necesarios: `contents:write`, `pull-requests:write`,
   `packages:write`, `metadata:read`.
4. Generar el **private key** de la App y usarlo para autenticar en lugar de un PAT.
5. Documentar la rotaciÃ³n: el private key se regenera cada N meses sin invalidar builds
   (porque la App sigue existiendo).

> **DecisiÃ³n pendiente D8**: Â¿GitHub App o machine user?
> - **GitHub App**: mÃ¡s seguro (permisos granulares, no atado a persona), requiere
>   generar private key, integraciÃ³n con workflows via `actions/create-github-app-token@v1`.
> - **Machine user**: mÃ¡s simple (es un PAT de un user nuevo), pero sigue siendo PAT
>   classic con scope `repo`.

### 11.4.6 Inventario completo de configured secrets en los 29 repos (post-Fase 2)

| Secret | # repos | CategorÃ­a | AcciÃ³n |
|---|---|---|---|
| `NOVA_RELEASE_PAT` | **8** (post-Fase 3: eran 19, ahora 6 borrados + 2 especiales sin uso) | GitHub token (PAT classic personal) | Ver Â§11.12 para plan de eliminacion de los 7 restantes |
| `NOVA_PACKAGES_READ_TOKEN` | 3 (+ 1 que tambiÃ©n tenÃ­a RELEASE = 4 con READ) | GitHub token (read-only) | Mantener, propagar a los 18 restantes (Fase 3) |
| `NVD_API_KEY` | 14 | API key externa (NIST NVD) | Mantener (no es GitHub token) |
| `NOVA_SONAR_TOKEN` | **0** (dormant) | API key externa (SonarCloud) | Renombrado 2026-07-15. Dormant hasta integraciÃ³n de Sonar. Ver Â§11.10. |

**Sobre los externos**: el usuario confirmÃ³ el 2026-07-15 que Sonar cuenta como "token
extra" (3er configured secret despuÃ©s de los 2 GitHub). Por consistencia con la naming
convention, se renombrÃ³ `SONAR_TOKEN` â†’ `NOVA_SONAR_TOKEN` en
`reusable-sonarcloud-{gradle,maven}.yml`.

### 11.4.7 Estado actual vs objetivo (matriz repo por repo, post-Fase 2)

| Repos | `NOVA_RELEASE_PAT` | `NOVA_PACKAGES_READ_TOKEN` | Estado objetivo |
|---|---|---|---|
| 18 Java libs + devops + 3 demos | âœ… (PAT personal) | âŒ | Replicar patrÃ³n `workflow_run` (Â§11.11) en Fase 3 para eliminar RELEASE |
| `nova-java-api-standard-quarkus-extension` | âŒ **BORRADO Fase 2** | âœ… | âœ… **COMPLETADO** |
| `nova-java-example` | âŒ | âœ… | Ya correcto |
| `nova-java-quarkus-example` | âŒ | âœ… | Ya correcto |
| `nova-bom` (Maven) | âŒ | âŒ | No necesita |
| `nova-java-spring-boot-archetype` (Maven) | âŒ | âŒ | No necesita |
| `nova-infrastructure` | âŒ | âŒ | No es Java |
| `nova-docs` | âŒ | âŒ | No es Java |

### 11.4.8 AcciÃ³n concreta (Fase 3 â€” modelo estricto, vÃ­a patrÃ³n `workflow_run`)

**Pre-condiciÃ³n**: validar que el patrÃ³n `workflow_run` funciona correctamente en la
extension Quarkus (prÃ³ximo release real, post-Fase 2). Si funciona â†’ replicar a los
18 repos. Si no funciona â†’ fallback a las opciones originales (Cambios A/B/C abajo).

**Plan con `workflow_run`** (preferido):

1. **Replicar el rediseÃ±o de `publish-on-tag.yml`** en cada uno de los 18 repos:
   - Trigger `push:tags` â†’ `workflow_run` (escucha completion de `Release Please`).
   - Agregar step `Detect new release tag` (compara tag vs manifest).
2. **Cambiar `release-please.yml`** en cada repo: `GH_TOKEN: ${{ secrets.NOVA_RELEASE_PAT
   || secrets.GITHUB_TOKEN }}` â†’ `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}`.
3. **Validar el prÃ³ximo release real** de cada repo (auto-trigger del publish).
4. **Borrar `NOVA_RELEASE_PAT`** del repo (`gh secret delete`).
5. **NO requiere** propagar `NOVA_PACKAGES_READ_TOKEN` (solo aplica si el repo tiene
   deps cross-repo que resolver â€” ver Â§11.4.7).
6. **NO requiere** Cambio C (migrar a machine user / GitHub App) â€” porque no queda
   PAT que migrar.

**Plan fallback** (si `workflow_run` no funciona por algÃºn motivo edge-case):

1. Mantener `NOVA_RELEASE_PAT` y aplicar los Cambios A/B/C originales.
2. DecisiÃ³n D5/D8 sigue siendo necesaria (GitHub App vs machine user).

### 11.4.9 Riesgos de la Fase 3 (con `workflow_run`)

**Bajo a medio**. Comparado con el plan original (Cambios A/B/C), el patrÃ³n `workflow_run`
elimina los siguientes riesgos:

| Riesgo | Plan original | Plan `workflow_run` |
|---|---|---|
| Fallback `\|\|` roto al aplicar Cambio A | Alto | N/A (no hay fallbacks que tocar) |
| `GH_TOKEN` (auto) no triggerea publish | Resuelto con PAT | Resuelto con `workflow_run` |
| PAT personal con scope `repo` sigue activo | Mitigado solo con Cambio C | Eliminado completamente |
| CoordinaciÃ³n de 18 migraciones simultÃ¡neas | Necesaria | Cada repo es independiente |

Riesgos restantes del plan `workflow_run`:
- El step `Detect new release tag` puede tener race conditions si dos pushes ocurren en
  rÃ¡pida sucesiÃ³n. MitigaciÃ³n: el job tiene `if: github.event.workflow_run.conclusion ==
  'success'`, que serializa naturalmente las ejecuciones del workflow_run.
- Si `.release-please-manifest.json` se actualiza fuera de release-please (raro), la
  detecciÃ³n puede fallar. MitigaciÃ³n: el step emite `::notice::` y skip en vez de error.

---

## 11.5 Plan de ejecuciÃ³n por fases

| Fase | AcciÃ³n | Riesgo | Esfuerzo | Estado al 2026-07-15 |
|---|---|---|---|---|
| **0** | Hardening + revisiÃ³n del repo `nova-devops` (auditorÃ­a completa antes de cualquier borrado) | Cero (solo lectura/anÃ¡lisis) | 30-45 min | âœ… **COMPLETADA** |
| **1** | Borrar 10 workflows muertos (commit `1a61e83`) | Cero | 5 min | âœ… **COMPLETADA** |
| **1.5** | Rename `SONAR_TOKEN` â†’ `NOVA_SONAR_TOKEN` (commit `06c808a`, pre-auditorÃ­a) | Cero (no hay repos con SONAR_TOKEN configurado) | 5 min | âœ… **COMPLETADA** |
| **2** | Borrar `NOVA_RELEASE_PAT` del extension Quarkus + patrÃ³n `workflow_run` (commit `a6d6013`) | Bajo | 25 min | âœ… **COMPLETADA** |
| **3** | Replicar patron workflow_run en los repos restantes para eliminar NOVA_RELEASE_PAT | Bajo-medio | ~3 h (12 repos x ~15 min) | [OK] **COMPLETADA** (12 repos migrados; piloto en 
ova-java-mask-utils valido el patron) |
| **4** | Crear machine user / GitHub App `nova-bot` (opcional, ya no es bloqueante) | Bajo | 2-3 h | â¸ï¸ **Despriorizado** (sin `NOVA_RELEASE_PAT` no queda PAT que migrar) |
| **5** | Generar `NOVA_PACKAGES_READ_TOKEN` desde identidad dedicada (no personal) | Bajo | 1-2 h | â¸ï¸ **Pendiente decisiÃ³n D6** |
| **6** | Backlog NestJS (ver Â§11.6) | â€” | â€” | Backlog |
| **7** | Activar `NOVA_SONAR_TOKEN` cuando se integre SonarCloud (ver Â§11.10) | â€” | â€” | Backlog |
| **1.6** â­ | PolÃ­tica explÃ­cita "no semver" en `nova-devops` (secciÃ³n README + tag/release renombrado) | Cero | 5 min | âœ… **COMPLETADA** (commits `30717f6`, `7311f1a`) |

**Cambio de estrategia post-Fase 2**: el patrÃ³n `workflow_run` descubierto en Fase 2
**elimina la necesidad de Fase 4** (machine user / GitHub App para `NOVA_RELEASE_PAT`).
Una vez que los 18 repos migren, **no queda PAT personal usado por CI/CD** â€” el riesgo
de blast radius de la cuenta personal desaparece para este caso de uso.

**Pendiente prioritario**: validar `workflow_run` con un release real de la extension
Quarkus antes de replicar a los 18 repos. Si funciona â†’ Fase 3 procede con
`workflow_run` y Fase 4 queda despriorizada.

---

## 11.6 Trabajos futuros: NestJS y otros repos sin CI/CD

### 11.6.1 Estado actual de los 4 repos NestJS

| Repo | Ãšltimo push | Secrets configurados | Workflows |
|---|---|---|---|
| `nova-nestjs-commons` | 2026-07-08 | 0 | 0 |
| `nova-nestjs-observability-starter` | 2026-07-08 | 0 | 0 |
| `nova-nestjs-parent` | 2026-07-08 | 0 | 0 |
| `nova-nestjs-starter` | 2026-07-08 | 0 | 0 |

Los 4 repos NestJS estÃ¡n en `D:\Nova\nest\` pero **no se han tocado desde
el 2026-07-08**. No tienen CI/CD ni secrets. No son parte del plan actual.

### 11.6.2 DecisiÃ³n pendiente sobre NestJS

Cuando se reactive el trabajo en NestJS (fecha indefinida), evaluar:

1. **Â¿Vale la pena migrar NestJS al mismo modelo de reusables que Java?** Hoy Java tiene
   18 reusables en `nova-devops`; NestJS no usa nada de eso.
2. **Â¿Necesita `NOVA_RELEASE_PAT` o `NOVA_PACKAGES_READ_TOKEN`?** Hoy no, porque no
   resuelve deps cross-repo desde CI.
3. **Â¿Publica a GitHub Packages?** Verificar: Â¿hay un `package.json` con `publishConfig`
   apuntando a GitHub Packages?
4. **Â¿Hay un bus de eventos entre Java y NestJS?** Los 4 NestJS son `commons`,
   `observability`, `parent`, `starter` â€” su rol es paralelo al stack Java.

### 11.6.3 Otros repos no auditados

| Repo | RazÃ³n de exclusiÃ³n |
|---|---|
| `D:\Nova\notification-parent\` | Repo de OscarBarahona (`github.com/OscarBarahona/notification-parent`), no parte de Nova. Es una referencia externa, no consumir. |
| `D:\Nova\jira\` | Tickets / docs internos, no cÃ³digo. |
| `D:\Nova\examples\archetypes\java-projects\quarkus-hexagonal-archetype\` | Referencia para Fase 1 de doc 08, no repo Nova. |

---

## 11.7 ValidaciÃ³n previa al plan

Comandos para revalidar el estado antes de ejecutar cualquier fase:

```bash
# Validar workflows muertos (debe dar 0 referencias)
$token = "ghp_..."
$headers = @{ Authorization = "Bearer $token" }
Set-Location "D:\Nova\java"
$dirs = Get-ChildItem -Directory -Name
$matches = 0
foreach ($d in $dirs) {
  $wfFiles = Get-ChildItem -File $d/.github/workflows/*.yml -ErrorAction SilentlyContinue
  foreach ($f in $wfFiles) {
    $hits = Select-String -Path $f.FullName -Pattern "reusable-publish-(gradle|maven)-(maven-central|nexus|multi-registry)"
    $matches += $hits.Count
  }
}
"matches: $matches (debe ser 0)"

# Validar tokens por repo (19 RELEASE, 3 READ, 1 ambos)
foreach ($r in @("nova-bom", ..., "nova-nestjs-starter")) {
  $secrets = Invoke-RestMethod -Uri "https://api.github.com/repos/ahincho/$r/actions/secrets?per_page=100" -Headers $headers
  $has = $secrets.secrets | ForEach-Object { $_.name }
  "{0,-50} RELEASE={1} READ={2}" -f $r, ($has -contains "NOVA_RELEASE_PAT"), ($has -contains "NOVA_PACKAGES_READ_TOKEN")
}
```

---

## 11.8 Decisiones del usuario (resueltas + pendientes)

### Resueltas 2026-07-15

| # | DecisiÃ³n | Resultado |
|---|---|---|
| **D1** âœ… | Ejecutar Fase 1 (borrar 6 workflows muertos â€” descubierto que eran 10) | Commit `1a61e83` pusheado. 35.6 KB liberados. |
| **D1.5** âœ… | Ejecutar Fase 1.5 (rename `SONAR_TOKEN` â†’ `NOVA_SONAR_TOKEN`) | Commit `06c808a` pusheado. 0 consumers afectados. |
| **D1.6** âœ… | PolÃ­tica explÃ­cita "no semver" en `nova-devops` (sin tags SemVer, tag `nvd-mirror` renombrado) | Commits `30717f6`, `7311f1a` pusheados. |
| **D2** âœ… | Ejecutar Fase 2 (borrar `NOVA_RELEASE_PAT` del extension Quarkus) + rediseÃ±ar trigger con `workflow_run` | Commit `a6d6013` pusheado. Auto-trigger preservado sin PAT. |
| **D9** âœ… | Sonar cuenta como 3er token externo. Renombrado a `NOVA_SONAR_TOKEN`. Dormant. | Resuelto. Ver Â§11.10. |

### Pendientes

| # | DecisiÃ³n | Impacto si se ejecuta |
|---|---|---|
| **D3** | Â¿Abrir Fase 3 (replicar `workflow_run` en 18 repos para eliminar `NOVA_RELEASE_PAT`)? | Bajo-medio. 4-6 h. Bloqueada por validaciÃ³n del patrÃ³n en extension. |
| **D4** | Si D3=SI, Â¿migraciÃ³n masiva o gradual (1 repo por dÃ­a)? | Conservadora: 18 dÃ­as. Masiva: 1 sesiÃ³n. |
| **D5** | (Despriorizado) Â¿Migrar `NOVA_RELEASE_PAT` a identidad dedicada? | Si Fase 3 elimina el PAT de todos los repos, esto deja de ser necesario. |
| **D6** | Â¿Generar el `NOVA_PACKAGES_READ_TOKEN` desde identidad dedicada (no personal)? | 1-2 h. Reduce blast radius del token read. Recomendado. |
| **D7** | (Despriorizado) Â¿OK mantener `GH_TOKEN` como nombre del input del workflow_call? | Ya no aplica si no hay `NOVA_RELEASE_PAT` que mapear. |
| **D8** | (Despriorizado) Si D5=SI, Â¿GitHub App o machine user? | Solo si D5 sigue activa. |

**RecomendaciÃ³n post-Fase 2**:
- **PrÃ³xima sesiÃ³n**: D3+D6 juntos (4-6 h). DecisiÃ³n D4 (masiva vs gradual) se toma al
  iniciar Fase 3 segÃºn disponibilidad.
- **ValidaciÃ³n crÃ­tica previa a D3**: mergear un PR de release-please en la extension
  Quarkus y confirmar que `publish-on-tag.yml` corre automÃ¡ticamente vÃ­a `workflow_run`.
- **Backlog**: NestJS (Â§11.6), Sonar integraciÃ³n futura (Â§11.10).

---

## 11.10 ActivaciÃ³n futura de SonarCloud (`NOVA_SONAR_TOKEN`)

### 11.10.1 Estado actual (dormant)

El 2026-07-15 se renombrÃ³ `SONAR_TOKEN` â†’ `NOVA_SONAR_TOKEN` en los 2 reusables de
SonarCloud (`reusable-sonarcloud-gradle.yml`, `reusable-sonarcloud-maven.yml`). El
comportamiento sigue siendo: si el secret no estÃ¡ configurado, el step de anÃ¡lisis
emite un `::warning::` y continÃºa sin fallar.

**NingÃºn repo Nova tiene `NOVA_SONAR_TOKEN` configurado al 2026-07-15** (verificado en
el audit de los 29 repos). El reusables de Sonar:
- 13 repos consumen `reusable-sonarcloud-gradle.yml` (todos sin token, todos skip).
- 1 repo consume `reusable-sonarcloud-maven.yml` (`nova-java-notifications`, sin token,
  skip).

### 11.10.2 Plan de activaciÃ³n (cuando vos decidas)

Cuando se reactive la integraciÃ³n con SonarCloud:

1. **Crear cuenta de SonarCloud** para la org `ahincho` (gratis para proyectos pÃºblicos).
2. **Crear un proyecto SonarCloud** por cada repo Nova que publique (â‰ˆ 19 proyectos
   para los 15 Java libs + 3 demos + devops; las 4 NestJS no, salvo que tambiÃ©n publiquen).
3. **Generar un token de SonarCloud** (no es un token de GitHub â€” estÃ¡ fuera del modelo
   de 2 tokens).
4. **Configurar `NOVA_SONAR_TOKEN`** en cada repo (cuenta personal, solo admite secrets a nivel de repo):
   ```bash
   gh secret set NOVA_SONAR_TOKEN --repo ahincho/<repo> --body "<sonar-token>"
   ```
   **Nota**: `ahincho` es una cuenta personal de GitHub, no una organización, por lo que
   no existen organization-level secrets. El secret debe configurarse repo por repo.
5. **Validar que el step de Sonar corre** (quitar el `::warning::`, ver anÃ¡lisis en
   SonarCloud dashboard).
6. **Documentar Quality Gates** en `docs/java/06-semantic-versioning-en-java.md` (o un
   doc nuevo): coverage mÃ­nimo, blocker issues, etc.

### 11.10.3 Decisiones pendientes para cuando se reactive

| # | Pregunta |
|---|---|
| Cuesta configurar 14 veces (1 por repo, no hay org-level secrets en cuenta personal)? | Alternativa: script PowerShell que itere los 14 repos con gh secret set. |
| Â¿Coverage mÃ­nimo como Quality Gate? | Si se establece, builds fallarÃ¡n si coverage < X%. Hoy no hay enforcement. |
| Â¿Aplicar tambiÃ©n a las 4 NestJS? | Si se quiere calidad uniforme. Requiere crear proyecto SonarCloud para Node. |
| Â¿Migrar a SonarQube self-hosted en lugar de SonarCloud? | Mayor control, pero requiere infra. |

### 11.10.4 Por quÃ© NO se activÃ³ ahora

- **No habÃ­a prisa**: el usuario (2026-07-15) confirmÃ³ que la integraciÃ³n es para
  "prÃ³ximamente", no inmediata.
- **Costo cognitivo**: aÃ±adir un 4Âº configured secret antes de cerrar la migraciÃ³n de
  los 2 tokens principales habrÃ­a desordenado el plan.
- **Workflows listos**: cuando se decida activar, solo se necesita generar el token y
  configurarlo en cada repo. No hay cÃ³digo nuevo que escribir.
---

## 11.11 PatrÃ³n `workflow_run` (hallazgo de Fase 2, replicable a Fase 3)

### 11.11.1 Problema resuelto

GitHub Actions tiene una **restricciÃ³n de seguridad documentada**: cuando un workflow
crea un tag o push usando `GITHUB_TOKEN`, **los workflows downstream no se auto-disparan**.

```yaml
# release-please.yml con GH_TOKEN:
release-please:
  secrets:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}   # crea tag v1.1.5
       â”‚
       â””â”€â–º tag push event fires
              â””â”€â–º publish-on-tag.yml con trigger 'push:tags'
                     â””â”€â–º âŒ GitHub SKIP â€” "actor fue GITHUB_TOKEN"
```

### 11.11.2 Workaround tradicional (con PAT)

Usar un Personal Access Token como actor para las operaciones de release-please.
Diferentes "actores" sÃ­ disparan workflows downstream entre sÃ­.

**Problemas**:
- PAT atado a identidad personal (blast radius = toda la org).
- PAT tiene scope `repo` completo (exceso de privilegios).
- Si rotÃ¡s el PAT, todos los builds que dependan se rompen.

### 11.11.3 SoluciÃ³n: trigger `workflow_run`

El evento `workflow_run` **sÃ­ se dispara** cuando un workflow upstream completa,
incluso si el upstream usÃ³ `GITHUB_TOKEN`. El downstream corre con su propio
`GITHUB_TOKEN` (fresco, generado para esa ejecuciÃ³n especÃ­fica).

```yaml
# publish-on-tag.yml nuevo trigger:
on:
  workflow_run:
    workflows: ["Release Please"]
    types: [completed]
    branches: [main]
       â”‚
       â””â”€â–º se dispara cuando release-please completa (success)
              â””â”€â–º corre con GITHUB_TOKEN propio âœ…
```

### 11.11.4 ImplementaciÃ³n completa

**`publish-on-tag.yml`** (antes vs despuÃ©s):

```yaml
# ANTES (trigger push:tags)
on:
  push:
    tags:
      - "v[0-9]+.[0-9]+.[0-9]+"

# DESPUÃ‰S (trigger workflow_run)
on:
  workflow_run:
    workflows: ["Release Please"]
    types: [completed]
    branches: [main]
```

**Step de detecciÃ³n robusto** (compara tag vs manifest para evitar re-publishs):

```yaml
- name: Detect new release tag
  id: detect
  run: |
    LATEST_TAG=$(git for-each-ref --sort=-creatordate --format='%(refname:short)' refs/tags/v\* | head -1)
    TAG_VERSION="${LATEST_TAG#v}"
    MANIFEST_VERSION=$(jq -r '."."' .release-please-manifest.json)
    if [ "$TAG_VERSION" != "$MANIFEST_VERSION" ]; then
      echo "should_publish=false" >> "$GITHUB_OUTPUT"
      exit 0
    fi
    echo "should_publish=true" >> "$GITHUB_OUTPUT"
    echo "tag=$LATEST_TAG" >> "$GITHUB_OUTPUT"

# Todos los steps siguientes con: if: steps.detect.outputs.should_publish == 'true'
```

**`release-please.yml`** simplificado:

```yaml
# ANTES
secrets:
  GH_TOKEN: ${{ secrets.NOVA_RELEASE_PAT || secrets.GITHUB_TOKEN }}

# DESPUÃ‰S
secrets:
  GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}  # sin PAT
```

### 11.11.5 Beneficios

| Aspecto | Antes (PAT) | DespuÃ©s (workflow_run) |
|---|---|---|
| Auto-trigger del publish | âœ… (gracias al PAT) | âœ… (workflow_run no tiene la restriction) |
| PAT personal requerido | âœ… (con scope `repo`) | âŒ (eliminado) |
| Blast radius del PAT | Toda la org (19 repos) | N/A (no hay PAT) |
| Complejidad del trigger | Baja | Media (step de detecciÃ³n) |
| Race conditions | Ninguna | Mitigada con `if: workflow_run.conclusion == 'success'` |

### 11.11.6 Plan de replicaciÃ³n a Fase 3

Para cada uno de los 18 repos restantes con `NOVA_RELEASE_PAT`:

1. Reemplazar el contenido de `publish-on-tag.yml` con el patrÃ³n completo documentado
   en Â§11.11.4 (workflow_run + detect step).
2. Cambiar `release-please.yml` para usar solo `GITHUB_TOKEN`.
3. Validar: mergear un PR de release-please, confirmar auto-publish.
4. Borrar `NOVA_RELEASE_PAT` del repo (`gh secret delete`).

**Esfuerzo estimado**: ~15 min por repo Ã— 18 = 4-5 h (incluye validaciÃ³n post-merge).

### 11.11.7 Riesgos residuales

- **Race condition con mÃºltiples pushes rÃ¡pidos**: el job tiene `if: workflow_run.conclusion
  == 'success'`, que serializa naturalmente. Si release-please corre dos veces seguidas,
  los workflow_runs se procesan en orden.
- **Step de detecciÃ³n lee manifest obsoleto**: si por algÃºn motivo `.release-please-manifest.json`
  se modifica fuera de release-please, el step puede dar falso positivo/negativo. MitigaciÃ³n:
  step emite `::notice::` y skip (no error) si no hay match.
- **Necesita `jq` instalado**: el step usa `jq -r '."."'`. El runner `ubuntu-latest`
  trae `jq` preinstalado. Si se cambia a otro runner, validar disponibilidad.

### 11.11.8 ValidaciÃ³n inicial

**Pendiente**: mergear un PR de release-please en `nova-java-api-standard-quarkus-extension`
y confirmar que `publish-on-tag.yml` se ejecuta vÃ­a `workflow_run` y publica
correctamente. Si funciona, replicar a los 18 repos. Si no funciona, documentar el
issue y volver al plan fallback (mantener PAT).

---

## 11.12 Ejecución de Fase 3 (2026-07-15)

### 11.12.1 Resultado global

**12 repos migrados** al patrón `workflow_run` en una sola sesión. Patrón validado previamente
en `nova-java-mask-utils` como piloto.

| Categoría | # | Repos | Template | NOVA_RELEASE_PAT borrado |
|---|---|---|---|---|
| A (Gradle básico) | 5 | api-standard, date-utils, mapper-utils, observability-utils, spring-boot-gradle-plugin | A | ✅ Sí |
| B (Gradle + read fallback) | 3 | commons-spring-boot-starter, observability-spring-boot-starter, spring-boot-starter | B | ⏸️ Conservado (espera READ) |
| C1 (Gradle custom + -P flags) | 2 | notifications-micronaut-module, notifications-quarkus-extension | C1 | ⏸️ Conservado |
| C2 (Gradle custom + resolve_token) | 1 | notifications-spring-boot-starter | C2 | ⏸️ Conservado |
| D (Maven) | 1 | notifications | D | ⏸️ Conservado |
| **Piloto previo** | 1 | mask-utils | (Fase 2) | ✅ Sí |
| **Total migrado** | **13** | | | **6 con PAT borrado** |

### 11.12.2 Validación del patrón

**Piloto `nova-java-mask-utils`** (3 runs de validación):
1. `29452432571` (post-merge del PR de release): ✅ Publicó v1.1.1 correctamente.
2. `29452655737` (post-chore sin release): ✅ Skip correcto con `workflow_run`.
3. `29452725417` (post-cleanup): ✅ Skip correcto.

**Bug detectado y corregido durante validación**:
- Detect step original solo comparaba `tag version == manifest version`, lo que hacía
  re-publicar la versión anterior si release-please corría sin crear release (409 Conflict).
- Fix: comparar SHA del tag con `head_sha` del workflow_run. Si no matchean → skip.

```yaml
# Fix añadido a todos los templates (A/B/C/D):
if [ -n "${WORKFLOW_RUN_HEAD_SHA}" ]; then
  TAG_SHA=$(git rev-list -n 1 "${LATEST_TAG}" 2>/dev/null || echo "")
  if [ "${TAG_SHA}" != "${WORKFLOW_RUN_HEAD_SHA}" ]; then
    echo "::notice::Tag ${LATEST_TAG} was NOT created in this workflow_run. Skipping."
    echo "should_publish=false" >> "$GITHUB_OUTPUT"
    exit 0
  fi
fi
```

### 11.12.3 Pendientes post-Fase 3

**7 repos con `NOVA_RELEASE_PAT` aún presente** (B/C/D) — necesitan configurar
`NOVA_PACKAGES_READ_TOKEN` antes de poder borrar el PAT:

| Repositorio | Categoría | Acción del usuario |
|---|---|---|
| `nova-java-commons-spring-boot-starter` | B | Generar y configurar `NOVA_PACKAGES_READ_TOKEN` → luego `gh secret delete NOVA_RELEASE_PAT` |
| `nova-java-observability-spring-boot-starter` | B | Idem |
| `nova-java-spring-boot-starter` | B | Idem |
| `nova-java-notifications-micronaut-module` | C1 | Idem |
| `nova-java-notifications-quarkus-extension` | C1 | Idem |
| `nova-java-notifications-spring-boot-starter` | C2 | Idem |
| `nova-java-notifications` | D | Idem |

**Comando para configurar `NOVA_PACKAGES_READ_TOKEN`** (repetir por repo, no hay org-level secrets en cuenta personal):
```bash
gh secret set NOVA_PACKAGES_READ_TOKEN --repo ahincho/<repo> --body "<token-value>"
```

**Alternativa con script** (para los 7 repos B/C/D, evita tipear 7 veces):
```bash
$repos = @(
  "nova-java-commons-spring-boot-starter",
  "nova-java-observability-spring-boot-starter",
  "nova-java-spring-boot-starter",
  "nova-java-notifications-micronaut-module",
  "nova-java-notifications-quarkus-extension",
  "nova-java-notifications-spring-boot-starter",
  "nova-java-notifications"
)
foreach ($r in $repos) {
  gh secret set NOVA_PACKAGES_READ_TOKEN --repo "ahincho/$r" --body "<token-value>"
}
```

**2 repos con `NOVA_RELEASE_PAT` residual (no necesita migración de workflows)**:
- `nova-devops`: el `publish-on-tag.yml` usa `secrets: inherit` hacia el reusable; el reusable
  ya no requiere PAT. **PAT se puede borrar sin cambios adicionales.**
- `nova-java-spring-boot-parent`: parent POM sin `publish-on-tag.yml` ni `release-please.yml`.
  El PAT es completamente residual. **Se puede borrar directamente.**

### 11.12.4 Decisiones que YA NO son necesarias

- **D5** (machine user / GitHub App): despriorizada. Sin `NOVA_RELEASE_PAT` activo en CI/CD,
  no hay PAT que migrar a identidad dedicada. Riesgo de blast radius personal eliminado.
- **D7** (`GH_TOKEN` como nombre de input): irrelevante. El caller ya no necesita pasar PAT.
- **D8** (GitHub App vs machine user): irrelevante por la misma razón.

### 11.12.5 Cambios colaterales recomendados (no urgentes)

1. **`nova-devops/publish-on-tag.yml`**: actualizar a `workflow_run` para consistencia con el
   resto del ecosistema. Hoy sigue con `push:tags` (heredado del Sprint 3). No es crítico
   porque el repo no usa release-please (no hay tag push automatizado).
2. **`nova-java-quarkus-archetype` y `nova-java-quarkus-parent`**: tienen referencia
   `NOVA_RELEASE_PAT` en workflows (probablemente heredado de templates), aunque el secret
   no está configurado. Limpiar las referencias para evitar confusión.

---

## 11.13 Migracion a Gradle de `nova-java-architecture-rules` (cierre del ultimo NOVA_RELEASE_PAT)

> **Estado (2026-07-16):** âœ… **COMPLETADA**. `nova-java-architecture-rules` migrado de Maven
> a Gradle, alineado con el resto de B/C/D. `NOVA_RELEASE_PAT` borrado del repo. CI validado
> end-to-end con PR #3 (todos los 7 jobs verdes). Releases v1.1.0 + v1.1.1 publicadas con
> GITHUB_TOKEN puro. **0 secrets en el repo.**

### 11.13.1 Contexto: el ultimo repo con `NOVA_RELEASE_PAT` activo

Despues de Fase 3, 11/14 repos quedaron limpios de `NOVA_RELEASE_PAT`. El unico repo donde
el secret aun se justificaba era `nova-java-architecture-rules` (creado 2026-07-16, mismo
dia que arranco esta auditoria): su `ci.yml` referenciaba el PAT en `<password>` dentro de
un `settings.xml` custom para resolver packages cross-repo de Maven.

Auditoria del workflow original (commit `ea1d2b5`):

```yaml
# ci.yml, lineas 34 y 39
<password>${{ secrets.NOVA_RELEASE_PAT }}</password>
```

Ademas el workflow estaba **roto desde el primer push** por un bug que se descubrio al
investigar el secret:

```yaml
# Step 18: setup-java@v4 con settings-path crea el DIRECTORIO
- name: Setup JDK 25 (Temurin)
  uses: actions/setup-java@v4
  with:
    settings-path: ${{ github.workspace }}/.mvn-settings.xml  # â†’ mkdir

# Step 26: cat > falla porque el path ya existe como directorio
- name: Configure Maven Settings (cross-repo reads)
  run: cat > .mvn-settings.xml <<'EOF'  # â†’ "Is a directory" (exit 1)
```

El primer run de CI fallo con `exit 1` en el step "Configure Maven Settings" **antes** de
que el PAT se usara nunca. El secret `NOVA_RELEASE_PAT` estaba configurado pero el workflow
nunca llego a autenticarse contra Maven Central / GitHub Packages.

### 11.13.2 Decision: migrar a Gradle, no a Maven-fix

Tres opciones sobre la mesa:

| Opcion | Veredicto | Por que |
|---|---|---|
| A) Workflow minimalista en Maven (sin custom settings) | Descartada | El repo quedaria inconsistente: B/C/D en Gradle, architecture-rules en Maven. Ademas la publicacion seguiria requiriendo PAT para `mvn deploy`. |
| B) Workflow tag-based + `workflow_run` en Maven (como B/C/D) | Descartada | Misma razon: inconsistencia + duplicacion de patterns. |
| C) **Migrar todo el repo a Gradle** (recomendada) | **Adoptada** | Consistencia con el resto de B/C/D, publicacion con GITHUB_TOKEN puro via `workflow_run` heredado de `reusable-publish-gradle.yml`, mismo set de plugins (jacoco, checkstyle, owasp, cyclonedx, versioning). |

### 11.13.3 Ejecucion de la migracion

Commit `be78ec2` ("feat: migrate from Maven to Gradle + adopt Nova Platform workflow",
2026-07-16) reemplazo el repo entero:

- **Eliminado**: `pom.xml`, `target/` (Maven build output).
- **Agregado build system**: `build.gradle.kts` (java-library + maven-publish + jacoco +
  checkstyle + owasp dependencycheck + cyclonedx-bom + versioning), `settings.gradle.kts`,
  `gradle.properties` (group=`pe.edu.nova.java.libs`, version desde manifest, config cache).
- **Agregado Gradle wrapper**: copiado desde `nova-java-mask-utils` (mismo Gradle 9.2.0).
- **Agregado workflows**: `ci.yml` (usa `reusable-build-gradle.yml`, `reusable-sonarcloud-gradle.yml`,
  `reusable-build-matrix.yml`, `reusable-owasp-check.yml`, `reusable-sbom.yml` desde
  `ahincho/nova-devops/.github/workflows/`), `release-please.yml` (GITHUB_TOKEN puro),
  `publish-on-tag.yml` (`workflow_run` trigger + `reusable-publish-gradle.yml` pattern).
- **Agregado configs**: `.release-please-config.json` (component=`nova-architecture-rules`,
  package-name=`pe.edu.nova.java.libs:nova-architecture-rules`), `.release-please-manifest.json`
  (arranca en `1.0.0`), `commitlint.config.js`, `package.json`, `lefthook.yml`.

Resultado: `pom.xml` borrado, `build.gradle.kts`+`settings.gradle.kts`+`gradle.properties`
nuevos, **16 archivos cambiados, 682 lineas agregadas, 163 borradas** en un solo commit.

### 11.13.4 Tres bugs descubiertos durante la ejecucion

#### Bug 1: `gradle-wrapper.jar` no se commiteo

El `.gitignore` original del repo (copiado del `pom.xml`-era) tenia `*.jar` global. Cuando
se hizo `git add -A`, el `gradle/wrapper/gradle-wrapper.jar` fue **ignorado silenciosamente**.

**Sintoma** (primer publish-on-tag run, conclusion `failure`):
```
Error: Could not find or load main class org.gradle.wrapper.GradleWrapperMain
Caused by: java.lang.ClassNotFoundException: org.gradle.wrapper.GradleWrapperMain
```

**Fix** (commit `487839c` "fix(build): track gradle-wrapper.jar"):
- Reemplazado `.gitignore` con version limpia (sin `*.jar` global), copiada de mask-utils.
- `git add -f gradle/wrapper/gradle-wrapper.jar` para forzar el track.
- Este commit genero el release 1.1.1 (Conventional Commits: `fix:`).

#### Bug 2: `default_workflow_permissions=read` bloquea release-please

El primer run de `release-please.yml` fallo con:
```
release-please failed: GitHub Actions is not permitted to create or approve pull requests.
```

El setting por defecto del repo era `default_workflow_permissions=read` y
`can_approve_pull_request_reviews=false`. Hay que activar ambos a nivel de repo:

```bash
gh api -X PUT "repos/ahincho/nova-java-architecture-rules/actions/permissions/workflow" \
  -f "default_workflow_permissions=write" \
  -F "can_approve_pull_request_reviews=true"
```

**Aplicabilidad**: este setting hay que activarlo **una vez por repo** que use release-please.
Los 11 B/C/D ya lo tenian porque se hizo durante su migracion. Para repos nuevos es
trivial olvidarselo. Documentar en §11.13.7.

#### Bug 3: `config/checkstyle/checkstyle.xml` ausente

El `reusable-build-gradle.yml` de `ahincho/nova-devops` corre `./gradlew checkstyleMain`
como step separado (despues de `build`). El plugin de Gradle busca el config file en
`config/checkstyle/checkstyle.xml` por convencion.

**Sintoma** (primer run del PR #3, conclusion `failure` en 3 jobs: build + matrix x2):
```
> Task :checkstyleMain FAILED
> Unable to create Root Module: config {/path/config/checkstyle/checkstyle.xml}.
> BUILD FAILED in 21s
```

**Fix** (PR #3, segundo commit): copiado `config/checkstyle/checkstyle.xml` desde
`nova-java-mask-utils` (73 lineas, baseline Nova Platform). Validacion local: build
SUCCESSFUL con 9 warnings de `MemberName` (snake_case en `@ArchTest` fields) que no fallan
el build por estar en `severity="warning"`.

**Aplicabilidad**: cualquier repo nuevo que migre a Gradle en Nova Platform **debe** trackear
`config/checkstyle/checkstyle.xml` antes de mergear el primer PR, o el CI va a fallar.

### 11.13.5 Validacion end-to-end (PR #3)

PR #3 ("test: validate CI pipeline on first PR") mergeado con squash. Resultado: **7/7 jobs
verdes** (run `29464717530`):

| Job | Resultado | Tiempo | Notas |
|---|---|---|---|
| `build / build` | âœ… success | 42s | Gradle compile + test + jar + checkstyle (9 warnings, 0 errors) |
| `matrix / Build (Java 21)` | âœ… success | 56s | Toolchain 21 (matrix paralelo) |
| `matrix / Build (Java 25)` | âœ… success | 43s | Toolchain 25 (default) |
| `owasp / owasp-check` | âœ… success | 1m 41s | NVD mirror restaurado desde nova-devops/shared baseline |
| `sbom / sbom` | âœ… success | 28s | CycloneDX BOM generado |
| `sonar / sonar-analysis` | âœ… success | 3s | Skip limpio (sin `NOVA_SONAR_TOKEN`) |
| `matrix / summary` | âœ… success | 2s | Resumen del matrix |

Pipeline completa: PR â†’ checks verdes â†’ squash merge â†’ release-please detecta el commit
(pero como es `test:`, **no bumpea**) â†’ publish-on-tag triggers via `workflow_run` con
detect step â†’ skip (no hay nuevo tag) â†’ manifest sin cambio (1.1.1 estable).

### 11.13.6 Comportamiento release-please con commits no-user-facing

Hallazgo interesante: el commit del PR #3 fue `test: validate CI pipeline on first PR`.
Al mergear, release-please no creo un nuevo PR porque:

```
✔ No user facing commits found since 0825bec - skipping
```

Release-please solo cuenta como user-facing: `feat:`, `fix:`, `perf:`. Los tipos `test:`,
`docs:`, `style:`, `chore:`, `refactor:`, `build:`, `ci:` **no generan release**.

**Implicacion**: el flujo `PR â†’ merge â†’ release-please â†’ tag â†’ publish` es robusto
contra commits triviales. Solo los commits conventional que indican cambio user-facing
disparan el pipeline de release. Manifest queda estable en `1.1.1`.

### 11.13.7 Lecciones aprendidas documentables

Checklist para futuros repos que migren de Maven a Gradle en Nova Platform:

1. **Trackear `config/checkstyle/checkstyle.xml`** desde el primer commit. Sin el, el
   `reusable-build-gradle.yml` falla en `checkstyleMain`. Archivo: 73 lineas, copiable
   desde `nova-java-mask-utils` o `nova-java-commons-spring-boot-starter`.

2. **Trackear `gradle/wrapper/gradle-wrapper.jar` con `git add -f`**. El `.gitignore`
   **nunca** debe tener `*.jar` global. Si venia de un template Maven, hay que limpiarlo.

3. **Activar workflow permissions del repo** antes del primer push:
   ```bash
   gh api -X PUT "$REPO/actions/permissions/workflow" \
     -f "default_workflow_permissions=write" \
     -F "can_approve_pull_request_reviews=true"
   ```
   Sin esto, release-please falla con "not permitted to create or approve pull requests".

4. **No pushear el PAT literal al repositorio local ni al remoto**. El secret
   `NOVA_RELEASE_PAT` debe vivir **solo** en GitHub Secrets (no en codigo, no en `cat` en
   consola, no en commits). Si se pega accidentalmente, `git reflog expire --expire=now --all`
   + `git gc --prune=now --aggressive` lo limpia del reflog (probado en `nova-docs`,
   commit `88b4621`).

5. **Validar el primer PR antes de mergear commits user-facing**. El primer PR deberia
   ser de smoke-test (cambio trivial) para validar que el CI este verde end-to-end
   antes de mergear features.

### 11.13.8 Inventario final de tokens (post-Fase 5)

| Token | Repos (al 2026-07-16) | Notas |
|---|---|---|
| `NOVA_RELEASE_PAT` | **0** | Eliminado del ultimo repo (architecture-rules). Antes: 14. |
| `NOVA_PACKAGES_READ_TOKEN` | 7 (B/C/D) | Sin cambios desde Fase 1. Fine-grained token "nova-java-release-please" (revocado en UI). |
| `NVD_API_KEY` | 14 | Sin cambios. Usado por `reusable-owasp-check.yml`. |
| `NOVA_SONAR_TOKEN` | 0 | Pendiente de activacion (backlog §11.10). |

**Resultado**: la org `ahincho` opera con 0 PATs activos en CI/CD. Toda publicacion se
hace con `GITHUB_TOKEN` puro via patron `workflow_run` (ver §11.11). El blast radius de
un compromise de tokens queda limitado a NVD_API_KEY (que es publica, rate-limit, no
secreto).

---

## 11.9 Referencias

- `ahincho/nova-devops/.github/workflows/`: 23 workflows auditados.
- `ahincho/nova-devops/.github/actions/`: 6 composite actions.
- `docs/java/06-semantic-versioning-en-java.md` Â§11.9: historial de bugs y fixes de CI/CD.
- `docs/java/07-quarkus-analisis-adopcion.md` Â§13.4: cierre Fase 0 Quarkus.
- AuditorÃ­a de secrets: ejecutada vÃ­a `GET https://api.github.com/repos/ahincho/{repo}/actions/secrets`
  con PAT classic scope `repo` el 2026-07-15.
