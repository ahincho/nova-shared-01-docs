# Evaluacion Comparativa: Quarkus Hexagonal Archetype vs Nova Platform Archetype

## 1. Contexto

Se comparan dos enfoques de scaffolding de proyectos Java:

| | Nova Platform Archetype | Quarkus Hexagonal Archetype |
|---|---|---|
| **Autor** | Equipo propio (meta-framework) | Companero (proyecto independiente) |
| **Framework** | Spring Boot 4.x | Quarkus 3.15.1 |
| **Java** | 25 | 21 (LTS) |
| **Build** | Maven Archetype (`archetype-packaging`) | Bash script (`init.sh`) con copia + sed |
| **Arquitectura** | Flat (single module) | Hexagonal multi-module (shared + bounded context + boot) |
| **Patrones** | Meta-framework starter como base | Hexagonal + CQRS + DDD + Event-Driven |
| **Ubicacion** | `java/nova-spring-boot-archetype/` | `examples/archetypes/java-projects/quarkus-hexagonal-archetype/` |

---

## 2. Que Genera Cada Uno

### Nova Platform Archetype -- Proyecto Generado

```
my-app/
  pom.xml                    <- Hereda de nova-spring-boot-parent:1.0.0
  src/main/java/{package}/
    Application.java          <- @NovaSpringBootApplication + NovaApplication.run()
  src/main/resources/
    application.yaml          <- port: 8080, spring.application.name: ${artifactId}
  src/test/java/{package}/
    ApplicationTest.java      <- @SpringBootTest context loads
```

**Total: 4 archivos.** Un proyecto vacio que compila y arranca.

### Quarkus Hexagonal Archetype -- Proyecto Generado

```
ms-course/
  build.gradle               <- Root con Quarkus BOM, OWASP, PIT
  settings.gradle             <- 3 modulos: shared, product, boot
  gradle.properties           <- Java 21, Quarkus 3.15.1
  Makefile                    <- dev, test, unit, mutation, security, build, native, coverage, clean
  .env.example                <- Variables de entorno (sin defaults inseguros)
  .gitignore
  docker-compose.dev.yml      <- PostgreSQL + Jaeger + Prometheus
  README.md                   <- 637 lineas de documentacion
  config/
    prometheus.yml
    owasp-suppressions.xml
  docs/adr/
    template.md + 8 ADRs
  shared/
    build.gradle              <- JaCoCo 90%, ArchUnit
    src/main/java/
      domain/                 <- AggregateRoot, CQRS buses (interfaces), VOs, exceptions
      infrastructure/         <- CdiCommandBus, CdiQueryBus, EventBus, REST envelope, ProblemDetail
    src/test/java/
      architecture/           <- ArchUnit tests (domain no depende de frameworks)
      aggregate/              <- Tests unitarios
      valueobject/
      exception/
      infrastructure/bus/     <- Tests de buses CDI
  product/
    build.gradle              <- JaCoCo 90/85/60% por capa
    src/main/java/
      domain/                 <- Product aggregate, VOs, events, repository port
      application/            <- 5 use cases CQRS (create, find, list, update, archive)
      infrastructure/         <- Panache adapter, outbox, Kafka publisher, ACL
    src/test/java/
      architecture/           <- ArchUnit tests
      domain/                 <- Tests de agregado y VOs
      application/            <- Tests de cada use case
      infrastructure/         <- Tests de publisher
      mother/                 <- Object Mothers
  boot/
    build.gradle              <- Todas las extensiones Quarkus
    src/main/docker/
      Dockerfile.jvm
      Dockerfile.native
    src/main/resources/
      application.properties  <- 141 lineas de configuracion completa
      db/migration/           <- 5 migraciones Flyway (V1-V5)
    src/main/java/
      resource/               <- ProductResource (JAX-RS, thin controller)
      lifecycle/              <- Graceful shutdown handler
    src/test/java/
      resource/               <- @QuarkusTest integration tests (198 lineas)
```

**Total: ~113 archivos.** Un microservicio completo con bounded context funcional, 90+ tests pasando desde el dia uno.

---

## 3. Comparativa Detallada

### 3.1. Mecanismo de Generacion

| Aspecto | Nova Platform | Quarkus Hexagonal |
|---------|:-:|:-:|
| **Tipo** | Maven Archetype Plugin | Bash script (`init.sh`) |
| **Invocacion** | `mvn archetype:generate -DarchetypeGroupId=...` | `make init` (interactivo) |
| **Parametros** | groupId, artifactId, version, package | projectName, microserviceName, outputDir |
| **Validacion de input** | Maven lo valida | Regex explícita + existencia de directorio |
| **Sustitucion de variables** | Velocity templates (`${groupId}`, `${package}`) | `sed` con regex sobre archivos |
| **Renombramiento de paquetes** | Automatico por Maven (filtered+packaged) | `mv` manual de directorios |
| **Git init** | No | Si (commit inicial automatico) |
| **Soporte Windows** | Si (Maven es cross-platform) | No (requiere bash, sed, find) |
| **Publicable a Maven repo** | Si (`mvn deploy`) | No (requiere clonar el repo) |

**Analisis:** El mecanismo de Maven Archetype es mas robusto para distribucion y cross-platform. El script bash es mas flexible para copiar estructuras complejas multi-modulo pero no funciona en Windows sin WSL/Git Bash y no es publicable como artefacto.

---

### 3.2. Arquitectura del Proyecto Generado

| Aspecto | Nova Platform | Quarkus Hexagonal |
|---------|:-:|:-:|
| Modulos | 1 (flat) | 3 (shared + product + boot) |
| Patron arquitectonico | Ninguno impuesto | Hexagonal + CQRS + DDD |
| Capas | Ninguna definida | domain / application / infrastructure |
| CQRS | No | Si (CommandBus + QueryBus con CDI) |
| DDD | No | Si (AggregateRoot, VOs, Domain Events, Repository port) |
| Event-Driven | No | Si (DomainEvent + Outbox + Kafka opcional) |
| Enforcement de reglas | Ninguno | ArchUnit en cada `./gradlew test` |
| Bounded Context ejemplo | No | Si (Product con CRUD completo) |

---

### 3.3. Testing

| Aspecto | Nova Platform | Quarkus Hexagonal |
|---------|:-:|:-:|
| Tests generados | 1 (context loads) | ~30 archivos, ~90 tests |
| Tests unitarios de dominio | No | Si (Product, VOs, excepciones) |
| Tests de aplicacion | No | Si (cada use case con Mockito) |
| Tests de integracion | No | Si (@QuarkusTest + Testcontainers) |
| Tests de arquitectura | No | Si (ArchUnit: domain no importa frameworks) |
| Object Mothers | No | Si (ProductMother, etc.) |
| Mutation testing | No | Si (PIT, 75% kill rate) |
| Coverage enforcement | No | Si (JaCoCo: domain 90%, app 85%, infra 60%) |
| OWASP dependency scan | No | Si (fail on CVSS >= 7) |

---

### 3.4. Infraestructura y DevEx

| Aspecto | Nova Platform | Quarkus Hexagonal |
|---------|:-:|:-:|
| Makefile | No | Si (10 targets) |
| Docker Compose | No | Si (PostgreSQL + Jaeger + Prometheus) |
| Dockerfile | No | Si (JVM + Native) |
| .env management | No | Si (.env.example, sin defaults inseguros) |
| Hot-reload | Via Spring Boot DevTools (manual) | `make dev` (Quarkus dev mode) |
| Database migrations | No | Si (Flyway, 5 migraciones) |
| OpenAPI / Swagger | No | Si (SmallRye OpenAPI) |
| Health checks | Via Actuator (transitivo del starter) | Si (SmallRye Health) |

---

### 3.5. Seguridad

| Aspecto | Nova Platform | Quarkus Hexagonal |
|---------|:-:|:-:|
| Autenticacion | No | OIDC/JWT (off en dev, required en prod) |
| Autorizacion | No | @RolesAllowed por endpoint |
| Security headers | No | Si (X-Content-Type-Options, X-Frame-Options, etc.) |
| CORS | No | Si (configurado) |
| Rate limiting | No | Si (@RateLimit en endpoints de escritura) |
| Secrets management | No | Si (sin defaults, falla si no hay .env) |
| HSTS | No | Si (en perfil prod) |

---

### 3.6. Observabilidad

| Aspecto | Nova Platform | Quarkus Hexagonal |
|---------|:-:|:-:|
| Distributed tracing | Via observability-starter (transitivo) | OpenTelemetry nativo Quarkus |
| Metricas | Via observability-starter (Golden Signals) | Micrometer + Prometheus + metricas custom |
| Logging estructurado | No configurado | JSON en prod, human-readable en dev |
| Correlation ID propagation | No | Si (X-Transaction-Id -> MDC -> HTTP clients) |
| Infrastructure para visualizar | No incluida en archetype | docker-compose con Jaeger + Prometheus |

---

### 3.7. Documentacion

| Aspecto | Nova Platform | Quarkus Hexagonal |
|---------|:-:|:-:|
| README | No generado | 637 lineas (quickstart, arquitectura, guias) |
| ADRs | No | 8 Architecture Decision Records |
| Guia de onboarding | No | Si (seccion 4: reglas por capa con ejemplos) |
| Naming conventions | No | Si (tabla de 14 patrones) |
| Guia "How to add..." | No | Si (nuevo bounded context, nuevo use case) |
| Documentacion de planning | No | Si (openspec: explore, proposal, design, spec, tasks) |

---

### 3.8. Patrones Avanzados

| Patron | Nova Platform | Quarkus Hexagonal |
|--------|:-:|:-:|
| Outbox Pattern | No | Si (domain_events_outbox table + scheduler) |
| Optimistic Locking | No | Si (@Version, transparente) |
| Idempotency | No | Si (InMemoryIdempotencyStore, migration para DB store) |
| Soft Delete | No | Si (status = DELETED, queries filtradas) |
| Anti-Corruption Layer | No | Si (ExternalUserServiceAdapter + UserSnapshot) |
| Graceful Shutdown | No | Si (30s timeout) |
| Audit metadata | No | Si (createdBy, updatedBy, createdAt, updatedAt) |

---

## 4. Puntos Fuertes del Quarkus Hexagonal Archetype

### 4.1. Proyecto funcional desde el dia uno

El aspecto mas valioso es que el proyecto generado **no es un esqueleto vacio**. Incluye un bounded context completo (`product`) que demuestra end-to-end:
- Aggregate con invariantes de dominio
- Value Objects como records con validacion en constructor
- CQRS con CommandBus/QueryBus via CDI
- Repositorio port/adapter con Panache
- Outbox pattern para eventos
- REST resource thin controller
- ~90 tests pasando

Esto funciona como **documentacion ejecutable**: el desarrollador copia el patron de `product/` para crear su propio bounded context.

### 4.2. ArchUnit como guardian de arquitectura

Los tests de ArchUnit (`SharedArchitectureTest`, `ProductArchitectureTest`) verifican en cada build que:
- El dominio **no importa** `jakarta.enterprise`, `jakarta.persistence`, `io.quarkus`, `org.springframework`
- La aplicacion **no importa** infraestructura ni JAX-RS
- La infraestructura **no tiene** logica de negocio

Esto convierte reglas arquitectonicas de "documentacion que nadie lee" a **tests que fallan si se violan**.

### 4.3. Proceso de diseno documentado (openspec)

El directorio `openspec/` contiene el proceso completo que llevo al diseno:
1. `explore.md` - Analisis de 3 proyectos fuente (2 Spring Boot + 1 NestJS)
2. `proposal.md` - Propuesta con scope, decisiones, riesgos
3. `design.md` - Diseno tecnico detallado
4. `spec.md` - Especificacion delta
5. `tasks.md` - 30 tareas organizadas en 5 PRs

Esto demuestra un enfoque de ingenieria riguroso: no se empezo a codificar sin planificar primero.

### 4.4. Makefile como interfaz unificada

```
make dev        -> PostgreSQL + Quarkus dev mode
make test       -> Suite completa + coverage enforcement
make unit       -> Solo unit tests (sin Docker)
make mutation   -> PIT mutation testing
make security   -> OWASP CVE scan
make build      -> JAR
make native     -> GraalVM native executable
```

Un desarrollador nuevo puede ser productivo en minutos sin conocer los comandos de Gradle.

### 4.5. Seguridad por defecto

- OIDC deshabilitado en dev (no necesita Keycloak local) pero **obligatorio en produccion**.
- Sin passwords por defecto: la app **se niega a arrancar** sin `.env`.
- Security headers (HSTS, XSS protection, frame options) preconfigurados.
- OWASP dependency check falla el build con CVSS >= 7.

---

## 5. Puntos Debiles del Quarkus Hexagonal Archetype

### 5.1. No es un archetype real

Usa `init.sh` (bash + sed + mv) en lugar de Maven Archetype Plugin o un mecanismo estandar. Esto tiene consecuencias:

- **No funciona en Windows nativo** (necesita WSL, Git Bash, o similar).
- **No es publicable como artefacto Maven/Gradle** -- requiere clonar el repo.
- **Sustitucion fragil**: `sed` puede romper contenido si los patrones aparecen en lugares inesperados.
- **No es composable**: no se puede combinar con otros archetypes o features.

### 5.2. Solo Quarkus

El archetype esta 100% acoplado a Quarkus:
- CDI (`@ApplicationScoped`, `Instance<>`)
- Panache (`PanacheRepositoryBase`, `PanacheEntity`)
- JAX-RS (`@Path`, `@GET`, `@POST`)
- SmallRye (Health, OpenAPI, Fault Tolerance, Reactive Messaging)
- Quarkus profiles (`%dev`, `%test`, `%prod`)

No hay una capa de abstraccion que permita reutilizar el shared kernel con Spring Boot o Micronaut. Si la organizacion usa multiples frameworks, se necesitarian archetypes completamente separados.

### 5.3. No integra con el meta-framework

El archetype del companero es un proyecto aislado. No consume:
- Las librerias de Nova Platform (mask-utils, date-utils, mapper-utils, api-standard)
- Los starters del meta-framework
- El BOM de versiones
- Los workflows de CI/CD reutilizables

Esto significa que un proyecto generado con este archetype no obtiene las capacidades del meta-framework y viceversa.

### 5.4. Complejidad para proyectos simples

La estructura hexagonal + CQRS con CommandBus/QueryBus es overhead para:
- APIs CRUD simples
- BFFs (Backend for Frontend) que solo orquestan llamadas
- Microservicios de lectura sin logica de dominio

No hay un modo "simple" o "light" que genere un proyecto mas plano.

### 5.5. Quarkus 3.15.1 fijo

La version de Quarkus esta hardcodeada en `gradle.properties`. No hay un mecanismo tipo BOM para actualizar coordinadamente.

---

## 6. Puntos Fuertes del Nova Platform Archetype

### 6.1. Maven Archetype real

Es un archetype Maven estandar publicable en cualquier repositorio Maven:
```bash
mvn archetype:generate \
  -DarchetypeGroupId=pe.edu.nova.java \
  -DarchetypeArtifactId=nova-spring-boot-archetype \
  -DarchetypeVersion=1.0.0
```
- Cross-platform (funciona en Windows, Linux, macOS).
- Publicable en GitHub Packages, Nexus, Artifactory.
- Integracion con IDEs (IntelliJ, Eclipse soportan archetypes Maven).

### 6.2. Integrado con el meta-framework

El proyecto generado hereda del Parent POM y obtiene automaticamente:
- Todas las dependencias del meta-framework (mask-utils, observability, api-standard).
- Configuracion de plugins de build.
- Versiones coordinadas via BOM.

### 6.3. Simplicidad

Un proyecto generado tiene 4 archivos y compila. No impone ninguna arquitectura ni patron. El desarrollador decide como estructurar su codigo.

---

## 7. Puntos Debiles del Nova Platform Archetype

### 7.1. Demasiado minimo

4 archivos no es suficiente para ser util. El desarrollador tiene que:
- Crear la estructura de paquetes manualmente.
- Configurar Docker/docker-compose.
- Crear `.gitignore`.
- Configurar CI/CD.
- Escribir su primer controller.
- Decidir una arquitectura.

Esto anula el proposito de un archetype: **eliminar la friccion inicial**.

### 7.2. Sin guia arquitectonica

No hay opiniones sobre como organizar el codigo. Cada equipo creara su propia estructura, lo que lleva a inconsistencia entre microservicios -- exactamente lo que un meta-framework deberia prevenir.

### 7.3. Sin tests significativos

El unico test generado es `@SpringBootTest` context loads, que verifica que Spring arranca pero no prueba ningun comportamiento.

### 7.4. Sin infraestructura de desarrollo

No hay Docker Compose, no hay Makefile, no hay `.env`, no hay Dockerfile. El desarrollador empieza desde cero con la infraestructura.

---

## 8. Que Puede Aprender Cada Proyecto del Otro

### Nova Platform puede adoptar del Quarkus Hexagonal:

| Que | Como | Prioridad |
|-----|------|-----------|
| Proyecto generado mas completo | Incluir controller de ejemplo, .gitignore, Dockerfile, docker-compose, application.yaml con profiles | ALTA |
| Tests de arquitectura con ArchUnit | Generar SharedArchitectureTest que verifique que el dominio no importa Spring | ALTA |
| Makefile o scripts de DX | Generar un Makefile con `make dev`, `make test`, `make build` | MEDIA |
| ADRs como practica | Incluir directorio `docs/adr/` con template | MEDIA |
| Guia "How to add..." en README | Generar README con instrucciones de como agregar controllers, services, etc. | MEDIA |
| Coverage enforcement | Configurar JaCoCo con minimos reales en el Parent POM | ALTA |
| Security headers | Configurar en `application.yaml` generado | MEDIA |
| Object Mother pattern en test template | Generar una clase Mother de ejemplo | BAJA |

### Quarkus Hexagonal puede adoptar de Nova Platform:

| Que | Como | Prioridad |
|-----|------|-----------|
| Mecanismo de generacion estandar | Migrar de bash script a Maven Archetype o Quarkus CLI extension | ALTA |
| Soporte Windows | Consecuencia del punto anterior | ALTA |
| Integracion con meta-framework | Consumir librerias compartidas (mask-utils, api-standard) via BOM | MEDIA |
| CI/CD reusable workflows | Integrar con los GitHub Actions workflows de nova-devops | MEDIA |
| Observabilidad estandarizada | Usar el stack de observabilidad de nova-infrastructure | MEDIA |
| Publicacion como artefacto | Publicar en GitHub Packages para consumo sin clonar | MEDIA |

---

## 9. Oportunidad de Convergencia

El escenario ideal es que ambos enfoques se complementen dentro del meta-framework:

```
Meta-Framework Nova Platform
  |
  +-- Librerias Puras (Nivel 1) -------- Reutilizables por ambos
  |     mask-utils, date-utils, etc.
  |
  +-- Starters (Nivel 2)
  |     +-- Spring Boot starters --------- Ya existen
  |     +-- Quarkus extensions ----------- Pueden basarse en los patrones del archetype
  |
  +-- Archetypes (Nivel 5)
  |     +-- nova-spring-boot-archetype (flat, para microservicios simples)
  |     +-- nova-spring-boot-hexagonal-archetype (multi-module DDD)
  |     +-- nova-quarkus-hexagonal-archetype (multi-module DDD)
  |
  +-- Shared Kernel
        +-- CQRS buses (framework-agnostico en dominio)
        +-- AggregateRoot, VOs, DomainEvent
        +-- Implementaciones CDI (Quarkus) y Spring (Spring Boot)
```

**Acciones concretas:**

1. **Extraer el shared kernel del archetype Quarkus como libreria pura (Nivel 1):**
   - `AggregateRoot`, `Command`, `Query`, `DomainEvent`, `CommandBus`, `QueryBus`, `EventBus` (interfaces)
   - Esto pertenece al mismo nivel que `mask-utils` o `api-standard`
   - Las implementaciones CDI y Spring van en starters separados

2. **Crear dos variantes de archetype:**
   - **Simple** (actual Nova Platform): para APIs CRUD, BFFs, microservicios sin logica compleja
   - **Hexagonal** (basado en el del companero): para microservicios con logica de dominio rica

3. **Migrar el script bash a Maven Archetype o Quarkus CLI:**
   - Permite publicacion y distribucion estandar
   - Cross-platform sin dependencia de bash

4. **Unificar la observabilidad:**
   - El archetype Quarkus usa Jaeger directamente; Nova Platform usa OTel Collector + Grafana stack
   - Estandarizar en OTel Collector (mas flexible) y reutilizar `nova-infrastructure`

---

## 10. Resumen de Calificaciones

| Criterio | Nova Platform Archetype | Quarkus Hexagonal Archetype |
|----------|:-:|:-:|
| Mecanismo de generacion | **7** (Maven estandar, cross-platform) | **4** (bash script, no-Windows, no-publicable) |
| Completitud del proyecto generado | **2** (4 archivos vacios) | **9** (~113 archivos, bounded context completo) |
| Arquitectura impuesta | **2** (ninguna) | **9** (Hexagonal + CQRS + DDD, enforced con ArchUnit) |
| Testing generado | **1** (1 test trivial) | **9** (~90 tests, unit + integration + architecture + mutation) |
| Documentacion generada | **1** (ninguna) | **9** (README 637 lineas + 8 ADRs + naming conventions) |
| Infraestructura de desarrollo | **1** (ninguna) | **8** (Docker Compose + Makefile + .env + Dockerfiles) |
| Seguridad | **1** (ninguna) | **8** (OIDC, security headers, OWASP scan, rate limiting) |
| Integracion con meta-framework | **8** (hereda Parent, usa starters) | **1** (proyecto aislado) |
| Soporte multi-framework | **3** (solo Spring Boot pero meta-framework lo contempla) | **1** (solo Quarkus) |
| Simplicidad / Low barrier | **8** (genera proyecto minimo sin opiniones) | **4** (complejidad alta para novatos) |
| Produccion-readiness | **2** | **8** |
| **PROMEDIO** | **3.3** | **6.4** |

---

## 11. Conclusion

Los dos proyectos estan en extremos opuestos del espectro:

- **Nova Platform Archetype**: mecanismo de distribucion correcto (Maven Archetype), integrado con el meta-framework, pero genera un proyecto tan minimo que no aporta valor practico al desarrollador.

- **Quarkus Hexagonal Archetype**: genera un proyecto production-ready con patrones avanzados, testing exhaustivo, documentacion rica, y infraestructura completa, pero usa un mecanismo de generacion fragil y no se integra con el ecosistema del meta-framework.

**La estrategia optima es combinar ambos:** usar el mecanismo de distribucion del Nova Platform Archetype con la riqueza de contenido del Quarkus Hexagonal Archetype, y extraer el shared kernel de DDD como libreria pura del Nivel 1 del meta-framework para que sea reutilizable por ambos frameworks.
