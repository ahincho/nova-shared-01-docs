# Estrategia de scaffolding Quarkus: archetypes, code.quarkus.io y codestarts

## 1. Contexto

Este documento define como generamos proyectos Quarkus nuevos en Nova Platform:

1. **Archetype Quarkus existente** (codigo de tu compañero en `examples/archetypes/java-projects/quarkus-hexagonal-archetype/`) — ¿como lo absorbemos al meta-framework?
2. **`code.quarkus.io`** — el scaffolder oficial de Quarkus. ¿Lo usamos? ¿Como?
3. **Codestart oficial** — publicacion en Quarkiverse Hub. ¿Vale la pena?

**Audiencia:** desarrollador que va a implementar (o evaluar) la estrategia de scaffolding.

**Prerrequisito:** haber leido los docs 07 (analisis macro) y 08 (DDD + Bus).

---

## 2. Estado actual: que tenemos

### 2.1. `examples/archetypes/java-projects/quarkus-hexagonal-archetype/` (tu compañero)

Verificado al 2026-07-14 leyendo `build.gradle`, `settings.gradle`, `shared/build.gradle`, `product/build.gradle`, `boot/build.gradle`:

| Aspecto | Valor |
|---|---|
| **Java files totales** | ~80 archivos (shared: ~40, product: ~30, boot: ~10) |
| **Total files** | ~115 archivos (incluyendo ADRs, scripts, configs) |
| **Estructura** | Multi-modulo Gradle: `:shared` + `:product` + `:boot` |
| **Build tool** | Gradle Groovy DSL (NO Kotlin DSL) |
| **Quarkus version** | 3.15.1 LTS (configurable via `${quarkusPlatformVersion}` en `gradle.properties`) |
| **Java version** | 21 (LTS) |
| **Plugin** | `id("io.quarkus") 3.15.1` + `org.owasp.dependencycheck 10.0.4` + `info.solidsoft.pitest 1.15.0` |
| **GroupId actual** | `pe.edu.utp.archetype` (de la UTP, no de Nova) |
| **Nombre proyecto** | `quarkus-hexagonal-archetype` |
| **ADRs** | 8 archivos en `docs/adr/` (hexagonal, CDI/CQRS, outbox, soft-delete, OIDC, RFC 7807, idempotency, optimistic-locking) |
| **Docker** | `Dockerfile.jvm` + `Dockerfile.native` (en `boot/`) |
| **docker-compose** | PostgreSQL + Jaeger + Prometheus para dev |
| **Migraciones** | Flyway (`db/migration/V*.sql`) |
| **Makefile** | targets: dev, test, unit, mutation, security, build, native, coverage, clean |
| **Script init** | `scripts/init.sh` (bash scaffolder que copia el archetype a un nuevo path reemplazando placeholders) |
| **CI workflows** | **NINGUNO** — solo Makefile local |
| **Publicacion automatica** | NO — manual (`make build && mvn deploy`) |
| **Versionado automatico** | NO — manual |
| **Consume libs Nova** | NO — esta aislado del meta-framework |
| **Cobertura del codigo generado** | ~80% (DDD kernel + bounded context de ejemplo) |

### 2.2. `examples/code-with-quarkus/` (generado por ti)

| Aspecto | Valor |
|---|---|
| **Java files totales** | 3 (`GreetingResource.java` + `GreetingResourceTest.java` + `GreetingResourceIT.java`) |
| **Total files** | 16 (incluyendo Dockerfiles, wrapper, README) |
| **Estructura** | Single-module Gradle Kotlin DSL |
| **Quarkus version** | 3.37.2 (latest, via `gradle.properties`) |
| **Java version** | 25 |
| **Plugin** | `id("io.quarkus") 3.37.2` |
| **GroupId actual** | `pe.edu.nova` |
| **Dockerfiles** | 4 (`Dockerfile.jvm`, `Dockerfile.native`, `Dockerfile.legacy-jar`, `Dockerfile.native-micro`) |
| **Native test** | `src/native-test/` con `@QuarkusIntegrationTest` |
| **CI workflows** | NINGUNO |
| **Consume libs Nova** | NO |

---

## 3. Decision estrategica: 3 opciones para scaffolding

### Opcion A: Adoptar `quarkus-hexagonal-archetype` (de tu compañero)

**Que es:** tomar el codigo existente y adaptarlo al meta-framework.

**Cambios necesarios:**

| Cambio | Esfuerzo | Por que |
|---|---|---|
| Cambiar `pe.edu.utp.archetype` → `pe.edu.nova.java.examples` (package + groupId) | 2 horas | Alinear con la convencion de Nova (`pe.edu.nova.java.*`) |
| Bump Quarkus 3.15.1 → 3.37.2 | 1 hora | Aprovechar la ultima version + Java 25 |
| Bump Java 21 → 25 (toolchain + sourceCompatibility) | 0.5 hora | Coincidir con la build matrix de Nova |
| Agregar workflows de CI (matrix, OWASP, SBOM, release-please, publish-on-tag) | 1 dia | Replicar la infra de los 9 repos Spring Boot |
| Consumir `nova-bom` + `nova-java-ddd-utils` + `nova-java-bus-quarkus` en lugar de duplicar el codigo | 1 dia | Reemplazar las ~25 clases del `shared/` por las de `nova-java-ddd-utils` |
| Adaptar Makefile a ser cross-platform (PowerShell) o usar `gh workflow run` | 0.5 dia | Nova es Windows-friendly |
| Mover de `examples/` a un repo separado `nova-java-quarkus-archetype` o `nova-java-quarkus-template` | 0.5 dia | Es candidato a publicarse como starter/extension |
| **Total** | **~3 dias** | |

**Pros:**
- Es el codigo mas completo que tenemos (8 ADRs, hexagonal + CQRS + DDD + outbox + soft-delete + idempotency).
- Ya esta validado y corriendo.
- Aporta opinionated architecture (vs el `code-with-quarkus` que es plano).

**Contras:**
- Requiere reescribir ~25% del codigo (cambiar package, bump versions, consumir libs Nova).
- El package `pe.edu.utp.archetype` esta repetido en muchos archivos — find/replace masivo.
- No es un "archetype" en el sentido Maven (no usa `maven-archetype-plugin`), es un directorio + `init.sh`.

**Conclusion:** **SI vale la pena adoptarlo**, pero solo despues de tener `nova-java-ddd-utils` y `nova-java-bus-quarkus` listos (Fase 1 del doc 07), sino seguimos duplicando codigo.

### Opcion B: Usar `code.quarkus.io` + post-procesar

**Que es:** generar un proyecto base desde `https://code.quarkus.io/` y agregarle las piezas de Nova.

**Limitaciones conocidas:**

| Limitacion | Impacto | Workaround |
|---|---|---|
| Solo Maven por default (Gradle es beta) | El meta-framework es mixto | Seleccionar `--gradle` si esta disponible; sino generar Maven y portar a Gradle |
| No conoce las libs Nova | Genera proyecto Quarkus vanilla | Post-procesar `build.gradle` para agregar `nova-bom` y deps Nova |
| Genera proyecto flat, no hexagonal | Pierde opinionated architecture | Aceptar — `code.quarkus.io` es opinion-neutral |
| No genera CI workflows | Hay que agregar todo manualmente | Post-procesar con un script que copie los workflows de un repo Spring Boot |
| No configurable via API (generador web) | No se puede invocar desde CI/scripting | Usar el Quarkus CLI (`quarkus create app`) en su lugar |
| No genera tests de arqu. | Hay que agregar ArchUnit | Post-procesar |

**Esfuerzo por opcion:**

| Sub-opcion | Esfuerzo | Resultado |
|---|---|---|
| Generar ZIP, descargar, descomprimir, abrir en IDE | 5 min | Quarkus plano, sin Nova, sin CI |
| Generar ZIP + post-procesar para agregar `nova-bom` + workflows Nova | ~30 min | Quarkus plano con Nova + CI |
| Generar ZIP + post-procesar + agregar libs Nova + patron hexagonal | ~2 horas | Quarkus con arquitectura Nova (similar a Opcion A) |
| Usar Quarkus CLI (`quarkus create app --extension=...`) + post-procesar | ~15 min | Igual a la primera sub-opcion pero CLI-scriptable |

**Pros:**
- Es la fuente oficial — siempre actualizada con las ultimas extensions Quarkus.
- El usuario (developer) elige las extensions que necesita en el momento.
- El ZIP incluye Dockerfiles + native test setup out-of-the-box.

**Contras:**
- Requiere conexion a internet (no funciona offline).
- Genera proyectos opinion-neutral (sin arquitectura) — el developer debe conocer DDD/hexagonal para aprovecharlos.
- No se integra al release-please ni al BOM de Nova sin post-procesamiento.

**Conclusion:** util para **POCs rapidas** (developer quiere probar Quarkus en 10 minutos) pero NO para **produccion Nova**. La pieza clave que falta es el post-procesador.

### Opcion C: Publicar un codestart oficial en Quarkiverse Hub

**Que es:** Quarkus tiene un mecanismo de **codestarts** (templates ZIP) que se distribuyen via Quarkiverse Hub y son invocables desde `quarkus create app` o desde `code.quarkus.io`.

**Ejemplo de flujo del usuario final:**
```bash
quarkus create app pe.edu.nova:something --extension=rest,arc
# -> genera proyecto Quarkus con nuestra extension + nova-bom + workflows
```

**Pasos para publicar:**

| Paso | Esfuerzo | Donde |
|---|---|---|
| Empaquetar el archetype Quarkus (Opcion A ya completada) como codestart ZIP | 1 dia | `quarkus-hexagonal-archetype/codestart/` |
| Crear repo en `quarkiverse/quarkus-nova` | 0.5 dia | GitHub |
| Configurar Quarkus Ecosystem CI (acciones automaticas en PR) | 1 dia | Setup automatico |
| Solicitar inclusion en `code.quarkus.io` | 0.5 dia (solicitud, no garantia) | Quarkus team |
| Publicar en `hub.quarkiverse.io` | 0.5 dia | Quarkus team |

**Pros:**
- Descubrible: developer externo puede hacer `quarkus create app pe.edu.nova:something` y obtener un proyecto pre-configurado.
- Co-branding con Quarkus: aparece en el registry oficial.
- Mantenible: Quarkus Ecosystem CI valida que el codestart sigue funcionando con cada release.

**Contras:**
- **Es externo**: Quarkus team controla el registry, no nosotros. Riesgo de que rechacen la solicitud o cambien policies.
- **Overhead de mantenimiento**: cualquier cambio en Quarkus upstream puede romper el codestart y requiere PR de fix.
- **No es necesario** para la adopcion interna de Nova — solo para developer experience externo.

**Conclusion:** **nice-to-have**, no prerequisito. Hacerlo en Fase 2+ (despues de Fase 0 y Fase 1).

---

## 4. Recomendacion: estrategia combinada

### Para Nova Platform (uso interno) — Opcion A modificada

**Paso 1:** Crear `examples/archetypes/java-projects/nova-java-quarkus-template/` (fork del `quarkus-hexagonal-archetype` de tu compañero):
- Bump Quarkus 3.15.1 → 3.37.2.
- Cambiar package `pe.edu.utp.archetype` → `pe.edu.nova.java.examples`.
- Bump Java 21 → 25.
- Agregar workflows de CI copiados de un repo Spring Boot de Nova.
- **NO consumir todavia** las libs Nova (esperar a Fase 1 con ddd-utils/bus disponibles).

**Paso 2:** Una vez `nova-java-ddd-utils` y `nova-java-bus-quarkus` esten publicadas (Fase 1), modificar el template para:
- Eliminar las ~25 clases duplicadas en `shared/`.
- Consumir `pe.edu.nova.java.libs:nova-java-ddd-utils:1.0.0`.
- Consumir `pe.edu.nova.java.starters:nova-java-bus-quarkus:1.0.0`.
- Consumir `pe.edu.nova.java.libs:nova-java-api-standard:1.0.0`.

**Paso 3:** Versionar el template como repo publico:
- `nova-java-quarkus-template` — repo publico con versionado.
- Tagging: no usa `release-please` (no es un artefacto publicable). Se taggea manualmente cuando hay cambios significativos.

### Para developer experience externo — Opcion C (roadmap)

**Cuándo:** despues de Fase 1 (cuando las libs Nova existen y estan publicadas).
**Cómo:** Opcion A ya completa + publicar el codestart en Quarkiverse Hub.

### Para POCs internas rapidas — Opcion B

**Cuándo:** developer quiere probar Quarkus sin esperar a que el template este completo.
**Cómo:** `quarkus create app pe.edu.nova:test --gradle` + post-procesar para agregar `nova-bom` y workflows.

---

## 5. Plan de adopcion por fases

### Fase 0 (esta semana) — Validacion tecnica

**Objetivo:** confirmar que Quarkus funciona end-to-end con la infra de Nova. **Esta fase NO toca el archetype**.

**Output:** `nova-java-api-standard-quarkus-extension` (extension coloquial) + `examples/code-with-quarkus` adaptado para consumir `nova-bom`.

### Fase 0.5 (opcional, paralelizable) — Crear el template Quarkus

**Objetivo:** tener un template Quarkus production-ready para que developers internos arranquen rapido.

| Actividad | Esfuerzo |
|---|---|
| Fork del `quarkus-hexagonal-archetype` en `examples/archetypes/java-projects/nova-java-quarkus-template/` | 0.5 dia |
| Bump versions (Quarkus 3.15.1 → 3.37.2, Java 21 → 25, PIT/OWASP) | 0.5 dia |
| Cambiar package `pe.edu.utp.archetype` → `pe.edu.nova.java.examples` (find/replace masivo) | 0.5 dia |
| Crear workflows de CI (matrix, OWASP, SBOM, release-please — versionando a mano, no via release-please) | 1 dia |
| Escribir README explicando como usar el template + como migrar a Fase 1 | 0.5 dia |
| **Total** | **~3 dias** |

### Fase 1 (siguiente sprint) — Adoptar DDD/Bus (doc 08)

**Output:** `nova-java-ddd-utils` + `nova-java-bus-api` + `nova-java-bus-spring` + `nova-java-bus-quarkus`.

### Fase 1.5 (despues de Fase 1) — Template consume libs Nova

| Actividad | Esfuerzo |
|---|---|
| Eliminar las ~25 clases duplicadas en `nova-java-quarkus-template/shared/` | 0.5 dia |
| Consumir `nova-java-ddd-utils` + `nova-java-bus-quarkus` en `nova-java-quarkus-template/` | 0.5 dia |
| Validar que el template sigue compilando + tests verdes | 0.5 dia |
| **Total** | **~1.5 dias** |

### Fase 2 (opcional, futuro) — Codestart oficial

| Actividad | Esfuerzo |
|---|---|
| Empaquetar `nova-java-quarkus-template/` como codestart ZIP | 1 dia |
| Publicar en Quarkiverse Hub | 1 dia |
| Cross-link desde `code.quarkus.io` | (externo, no garantizado) |
| **Total** | **~2 dias** (sin contar la espera de Quarkus team) |

---

## 6. Detalles tecnicos: como hacer el fork

### 6.1. Cambios al `quarkus-hexagonal-archetype`

```bash
# 1. Crear el nuevo template copiando el archetype
cp -r examples/archetypes/java-projects/quarkus-hexagonal-archetype examples/archetypes/java-projects/nova-java-quarkus-template

# 2. Find/replace del package
# En Linux/Mac:
find examples/archetypes/java-projects/nova-java-quarkus-template -type f \( -name "*.java" -o -name "*.gradle" -o -name "*.properties" -o -name "*.xml" -o -name "*.yml" \) -exec sed -i 's/pe\.edu\.utp\.archetype/pe.edu.nova.java.examples/g' {} +

# En PowerShell:
Get-ChildItem -Path "examples/archetypes/java-projects/nova-java-quarkus-template" -Recurse -Include "*.java","*.gradle","*.properties","*.xml","*.yml" | ForEach-Object { (Get-Content $_.FullName) -replace 'pe\.edu\.utp\.archetype', 'pe.edu.nova.java.examples' | Set-Content $_.FullName }
```

### 6.2. Bumps de versiones

| Archivo | Cambio |
|---|---|
| `gradle.properties` | `quarkusPlatformVersion=3.15.1` → `3.37.2` |
| `build.gradle` (root) | `id 'io.quarkus' version '3.15.1'` → `'3.37.2'`; `id 'org.owasp.dependencycheck' version '10.0.4'` → `'12.2.2'`; `id 'info.solidsoft.pitest' version '1.15.0'` → `'1.19.0-rc.1'` |
| `build.gradle` (subprojects) | `sourceCompatibility = VERSION_21` → `VERSION_25`; `toolchain { languageVersion = 21 }` → `25` |

### 6.3. Workflows de CI a copiar

Copiar desde un repo Spring Boot (e.g., `java/nova-java-api-standard/`):

| Archivo | Origen | Destino |
|---|---|---|
| `.github/workflows/build.yml` | `nova-java-api-standard` | `nova-java-quarkus-template/.github/workflows/build.yml` |
| `.github/workflows/owasp.yml` | `nova-java-api-standard` | `nova-java-quarkus-template/.github/workflows/owasp.yml` |
| `.github/workflows/release-please.yml` | `nova-java-api-standard` | `nova-java-quarkus-template/.github/workflows/release-please.yml` (adaptar, ver abajo) |
| `.github/workflows/publish-on-tag.yml` | `nova-java-api-standard` | `nova-java-quarkus-template/.github/workflows/publish-on-tag.yml` |
| `lefthook.yml` | `nova-java-api-standard` | `nova-java-quarkus-template/lefthook.yml` |
| `commitlint.config.js` | `nova-java-api-standard` | `nova-java-quarkus-template/commitlint.config.js` |
| `package.json` (para commitlint) | `nova-java-api-standard` | `nova-java-quarkus-template/package.json` |

**Nota sobre `release-please.yml`:** el template NO se publica a GitHub Packages como artefacto (es solo estructura de archivos para que developers lo copien). Por lo tanto, `release-please.yml` puede omitirse o configurarse para no hacer nada. Alternativamente, se puede usar `release-please` solo para generar changelogs + tags (sin publish).

---

## 7. Documentacion que debe acompanar al template

| Archivo | Contenido | Esfuerzo |
|---|---|---|
| `README.md` | Que es, como usarlo (`cp -r nova-java-quarkus-template mi-app && cd mi-app && ./init.sh`), prerequisitos, ejemplos | 0.5 dia |
| `docs/adr/` (heredado del archetype) | Mantener los 8 ADRs del archetype (son buena documentacion) | 0 dia (heredado) |
| `docs/migration-to-nova.md` | Guia para migrar apps que usen el template standalone a consumir `nova-bom` y las libs Nova compartidas | 0.5 dia |

---

## 8. Riesgos especificos del scaffolding

| Riesgo | Probabilidad | Impacto | Mitigacion |
|---|---|---|---|
| El archetype `quarkus-hexagonal-archetype` tiene muchos archivos hardcoded con `pe.edu.utp.archetype` — find/replace puede romper algunos | Media | Bajo | Hacer find/replace, luego `grep -r "pe.edu.utp"` para verificar que no quede nada |
| Bump de Quarkus 3.15.1 → 3.37.2 puede romper APIs internas (e.g., Panache) | Baja | Medio | Revisar CHANGELOG.md de Quarkus entre 3.15 y 3.37; iterar fixes |
| El script `init.sh` (bash) no funciona en Windows sin WSL | Alta | Medio | Reescribir como PowerShell script + bash (cross-platform); o usar `gh workflow run` en su lugar |
| El template tiene Dockerfiles + docker-compose.dev.yml con versiones hardcoded | Baja | Bajo | Externalizar a `.env` (el `.env.example` ya existe) |
| El template no tiene tests de arqu. con ArchUnit | Baja | Bajo | Agregar ArchUnit en Fase 1.5 (cuando consuma `nova-java-ddd-utils`) |
| Si publicamos codestart en Quarkiverse Hub, Quarkus team puede rechazar la solicitud | Media | Bajo | No es bloqueante — usamos el codestart internamente aunque no este en Hub |

---

## 9. Conclusion

**Recomendacion principal:**

1. **Fase 0** (esta semana): crear `nova-java-api-standard-quarkus-extension` + adaptar `examples/code-with-quarkus`. **NO tocar el archetype todavia**.
2. **Fase 0.5** (paralela si hay tiempo): fork del archetype a `nova-java-quarkus-template`, con bumps + workflows + cambio de package. **3 dias**.
3. **Fase 1** (siguiente sprint): DDD + Bus (doc 08).
4. **Fase 1.5** (despues de Fase 1): template consume libs Nova. **1.5 dias**.
5. **Fase 2** (futuro): codestart oficial en Quarkiverse Hub. **Opcional**.

`code.quarkus.io` se usa solo para POCs rapidas que no necesitan opinionated architecture.

---

## 10. Preguntas abiertas

1. **Naming del template:** `nova-java-quarkus-template` (fork del archetype) o `nova-java-quarkus-archetype` (alineado con el nombre del original)? Mi sugerencia: `template` porque NO es un archetype Maven (no usa `maven-archetype-plugin`), es un directorio + scripts de init. Confirmar.
2. **`init.sh` cross-platform:** ¿reescribir a PowerShell + bash, o reemplazar por `gh workflow run` (GitHub CLI)? Mi sugerencia: ambos (PowerShell + bash) porque algunos developers usan Windows sin WSL.
3. **Publicacion del codestart:** ¿es requisito para la primera POC o nice-to-have? Mi sugerencia: nice-to-have, no bloqueante.
4. **Repositorio del template:** ¿publico o privado? Mi sugerencia: publico (es reference implementation, otros pueden contribuir).