# Libreria pura DDD + implementaciones del Bus por framework

## 1. Contexto

Este documento describe las piezas compartidas que necesitamos para que Quarkus sea un ciudadano de primera clase en Nova Platform (paralelo a Spring Boot):

1. **Una libreria pura de DDD** (Nivel 1, framework-agnostic) que aporte los building blocks del Domain-Driven Design que ya estan bien resueltos en el `quarkus-hexagonal-archetype` de tu compañero.
2. **Una libreria de abstraccion del Bus** (Nivel 1, framework-agnostic) con solo interfaces (`CommandBus`, `QueryBus`, `EventBus`).
3. **Dos implementaciones del Bus** (Nivel 2, una por framework):
   - `nova-java-bus-spring` — para Spring Boot.
   - `nova-java-bus-quarkus` — para Quarkus.

**Audiencia:** desarrollador que va a implementar (o evaluar) las piezas compartidas entre Spring Boot y Quarkus.

**Prerrequisito:** haber leido el doc 07 (analisis macro de adopcion Quarkus).

---

## 2. Por que se necesitan estas piezas

### 2.1. Estado actual

`nova-java-api-standard` es la unica libreria framework-agnostic de Nova que aporta valor funcional (modelos de request/response, error handling, paginacion). El resto del meta-framework es Spring Boot-centric o es una libreria individual sin cohesion arquitectonica.

### 2.2. Lo que el `quarkus-hexagonal-archetype` ya resuelve (y que Nova deberia absorber)

El `quarkus-hexagonal-archetype` (codigo de tu compañero en `examples/archetypes/java-projects/quarkus-hexagonal-archetype/`) implementa los siguientes patrones DDD/CQRS en el modulo `shared/`:

| Patron | Implementacion actual | Donde |
|---|---|---|
| Aggregate root | `AggregateRoot<I>` clase base abstracta | `shared/src/main/java/.../shared/domain/AggregateRoot.java` |
| Entity | `Entity<I>` clase base abstracta | `shared/src/main/java/.../shared/domain/Entity.java` |
| Value Object | `ValueObject` clase base abstracta | `shared/src/main/java/.../shared/domain/ValueObject.java` |
| Identifier | Interface `Identifier` + varias implementaciones (UUID, Long, String) | `shared/src/main/java/.../shared/domain/Identifier.java` |
| Domain Event | `DomainEvent` interface + `BaseDomainEvent` | `shared/src/main/java/.../shared/domain/DomainEvent.java` |
| Repository (interface) | `Repository<A, I>` interface | `shared/src/main/java/.../shared/domain/Repository.java` |
| Domain Service | Patron convencional (no hay clase base) | (no aplica) |
| Application Service | Patron convencional (no hay clase base) | (no aplica) |
| Command (CQRS) | `Command` interface + `CommandHandler<C>` | `shared/src/main/java/.../shared/application/Command.java` |
| Query (CQRS) | `Query<R>` interface + `QueryHandler<Q, R>` | `shared/src/main/java/.../shared/application/Query.java` |
| CommandBus | `CommandBus` interface + implementacion | `shared/src/main/java/.../shared/application/CommandBus.java` |
| QueryBus | `QueryBus<R>` interface + implementacion | `shared/src/main/java/.../shared/application/QueryBus.java` |
| EventBus | `EventBus` interface + implementacion | `shared/src/main/java/.../shared/application/EventBus.java` |
| Specification | `Specification<T>` interface | `shared/src/main/java/.../shared/domain/Specification.java` |
| Domain Exception | `DomainException` clase base | `shared/src/main/java/.../shared/domain/DomainException.java` |
| Use Case (generic) | `UseCase<I, O>` interface | `shared/src/main/java/.../shared/application/UseCase.java` |

(Conteo: ~25 archivos Java en `shared/src/main/java/.../shared/domain/` + `application/`. Verificar conteo exacto en Fase 0 leyendo el codigo.)

### 2.3. Lo que Nova tiene hoy vs lo que necesita

| Pieza | Nova tiene? | Donde |
|---|---|---|
| Aggregate root, Entity, Value Object base | ❌ No | (se implementa en `nova-java-ddd-utils`) |
| Identifier generico | ❌ No | (se implementa en `nova-java-ddd-utils`) |
| Domain Event + BaseDomainEvent | ❌ No | (se implementa en `nova-java-ddd-utils`) |
| Repository interface | ❌ No | (se implementa en `nova-java-ddd-utils`) |
| Specification | ❌ No | (se implementa en `nova-java-ddd-utils`) |
| Domain Exception | ❌ No | (se implementa en `nova-java-ddd-utils`) |
| Command, Query interfaces | ❌ No | (se implementa en `nova-java-bus-api`) |
| CommandHandler, QueryHandler interfaces | ❌ No | (se implementa en `nova-java-bus-api`) |
| CommandBus, QueryBus, EventBus interfaces | ❌ No | (se implementa en `nova-java-bus-api`) |
| Spring CommandBus impl | ❌ No | (se implementa en `nova-java-bus-spring`) |
| Quarkus CommandBus impl | ❌ No | (se implementa en `nova-java-bus-quarkus`) |

---

## 3. Arquitectura propuesta: 4 piezas

```
nova-java-ddd-utils               <- Nivel 1: Aggregate, Entity, VO, ID, Event, Repo, Spec, DomainException
        |
        v (depende de)
nova-java-bus-api                 <- Nivel 1: Command, Query, Bus interfaces (NO implementaciones)
        |
        +---------------+---------------+
        v                               v
nova-java-bus-spring          nova-java-bus-quarkus
(Nivel 2: Spring impl)        (Nivel 2: Quarkus impl)
```

### 3.1. Pieza 1: `nova-java-ddd-utils` (Nivel 1, framework-agnostic)

**Proposito:** aportar los building blocks DDD base. Es **puro Java**, sin dependencias de framework.

**Origen del codigo:** copia + adaptacion del modulo `shared/` del `quarkus-hexagonal-archetype` (eliminando las dependencias de Quarkus como `@Configurable` annotations, etc.).

**Contenido propuesto** (~25 clases en `pe.edu.nova.java.libs.ddd.*`):

```
pe.edu.nova.java.libs.ddd
├── domain
│   ├── AggregateRoot<I>          // abstract class, hereda de Entity<I>
│   ├── Entity<I>                 // abstract class
│   ├── ValueObject                // abstract class (equals/hashCode por campos)
│   ├── Identifier                 // interface marker
│   ├── UuidIdentifier            // record
│   ├── LongIdentifier             // record
│   ├── StringIdentifier           // record
│   ├── DomainEvent                // interface (extends Serializable, tiene occurredOn)
│   ├── BaseDomainEvent            // abstract class
│   ├── Repository<A, I>          // interface (save, findById, delete, etc.)
│   ├── Specification<T>          // interface (isSatisfiedBy, and, or, not)
│   └── DomainException            // abstract class (extends RuntimeException)
└── (sin sub-package "application" — eso va en bus-api)
```

**Stack tecnologico:**
- Java 25 (LTS)
- Gradle Kotlin DSL (`id("java-library")` + `id("maven-publish")`)
- Sin frameworks: sin Spring, sin Quarkus, sin Hibernate, sin Jackson.
- Tests: JUnit 6 + jqwik (mismo patron que `nova-java-api-standard`).
- Cobertura: JaCoCo + PIT mutation testing.

**Naming en GitHub Packages:**
- `groupId`: `pe.edu.nova.java.libs`
- `artifactId`: `nova-java-ddd-utils`
- `version`: `1.0.0`

### 3.2. Pieza 2: `nova-java-bus-api` (Nivel 1, framework-agnostic)

**Proposito:** aportar los contratos abstractos del Bus (CQRS pattern). Es **puro Java**, sin dependencias de framework.

**Contenido propuesto** (~12 clases en `pe.edu.nova.java.libs.bus.*`):

```
pe.edu.nova.java.libs.bus
├── command
│   ├── Command                   // interface marker (extends Serializable)
│   ├── CommandHandler<C, R>     // interface funcional: handle(C) -> R
│   ├── CommandBus                // interface: dispatch(C) -> R
│   └── CommandHandlerNotFoundException
├── query
│   ├── Query<R>                  // interface marker (extends Serializable, tiene tipo de retorno)
│   ├── QueryHandler<Q, R>       // interface funcional: handle(Q) -> R
│   ├── QueryBus                  // interface: ask(Q) -> R
│   └── QueryHandlerNotFoundException
└── event
    ├── DomainEvent (extiende ddd.DomainEvent, ya existe)
    ├── EventHandler<E>            // interface funcional: handle(E)
    ├── EventBus                   // interface: publish(E)
    └── EventHandlerNotFoundException
```

**Decisiones de diseno:**

1. **`Command` vs `Query`:** ambos son interfaces marker (sin metodos). El proposito es dar identidad al objeto para que el Bus sepa que handler dispatchear.

2. **`CommandHandler`:** interface funcional con un unico metodo `R handle(C command)`. Esto permite implementarlos como lambdas o como clases anotadas.

3. **¿Por que separar `CommandBus` de `QueryBus` de `EventBus`?** Por claridad semantica. En CQRS, comandos modifican estado, queries leen, eventos son broadcast. Mezclarlos en un unico `MessageBus` complica el type-safety.

4. **Errores especificos:** `CommandHandlerNotFoundException` permite al caller saber que falto registrar un handler, en vez de recibir un `ClassCastException` o `NullPointerException` generico.

**Stack tecnologico:** identico a `nova-java-ddd-utils`.

**Naming en GitHub Packages:**
- `groupId`: `pe.edu.nova.java.libs`
- `artifactId`: `nova-java-bus-api`
- `version`: `1.0.0`

**Dependencias:** depende de `pe.edu.nova.java.libs:nova-java-ddd-utils:1.0.0` (porque `DomainEvent` esta en ddd-utils, no en bus-api).

### 3.3. Pieza 3: `nova-java-bus-spring` (Nivel 2, Spring Boot)

**Proposito:** implementar `CommandBus`, `QueryBus`, `EventBus` usando Spring como contenedor de DI.

**Patron de implementacion:**

```java
// CommandBusImpl
@ApplicationScoped  // o @Service — evaluar cual encaja mejor
public class SpringCommandBus implements CommandBus {
    private final ApplicationContext context;

    public SpringCommandBus(ApplicationContext context) {
        this.context = context;
    }

    @Override
    public <C extends Command, R> R dispatch(C command) {
        // Buscar todos los beans que sean CommandHandler<C, R>
        Map<String, CommandHandler> handlers = context.getBeansOfType(CommandHandler.class);
        return handlers.values().stream()
            .filter(h -> h.getCommandType().equals(command.getClass()))
            .findFirst()
            .map(h -> (R) h.handle(command))
            .orElseThrow(() -> new CommandHandlerNotFoundException(command.getClass()));
    }
}
```

**Mecanismo de descubrimiento:**
- Los handlers se registran como beans de Spring (`@Component` con clase que implementa `CommandHandler<MiComando, MiRespuesta>`).
- El CommandBus los descubre por tipo (`getBeansOfType(CommandHandler.class)`).
- Se selecciona el handler cuyo tipo de comando coincide con el del comando recibido.

**Consideraciones:**
- Si hay multiples handlers para el mismo comando, se loguea warning + se usa el primero (fail-safe). Mejora futura: validar en startup que no haya duplicados (`@PostConstruct` o `ApplicationReadyEvent`).
- Si NO hay handler, se lanza `CommandHandlerNotFoundException` con el tipo del comando en el mensaje (facilita debugging).

**Stack tecnologico:**
- Java 25
- Gradle Kotlin DSL
- Spring Boot 4.1.0 (como `implementation`)
- `nova-java-bus-api:1.0.0` como `api` (porque expone tipos `Command`, `CommandBus`, etc. en su API publica)
- `nova-java-ddd-utils:1.0.0` como `api`

**Naming en GitHub Packages:**
- `groupId`: `pe.edu.nova.java.starters` (Nivel 2 = starters/extensions)
- `artifactId`: `nova-java-bus-spring`
- `version`: `1.0.0`

### 3.4. Pieza 4: `nova-java-bus-quarkus` (Nivel 2, Quarkus)

**Proposito:** implementar `CommandBus`, `QueryBus`, `EventBus` usando Quarkus CDI como contenedor de DI.

**Patron de implementacion:**

```java
// CommandBusImpl
@ApplicationScoped
public class QuarkusCommandBus implements CommandBus {
    private final Instance<CommandHandler> handlers;

    public QuarkusCommandBus(Instance<CommandHandler> handlers) {
        this.handlers = handlers;
    }

    @Override
    public <C extends Command, R> R dispatch(C command) {
        return handlers.stream()
            .filter(h -> h.getCommandType().equals(command.getClass()))
            .findFirst()
            .map(h -> (R) h.handle(command))
            .orElseThrow(() -> new CommandHandlerNotFoundException(command.getClass()));
    }
}
```

**Mecanismo de descubrimiento:**
- Los handlers se registran como CDI beans (`@ApplicationScoped` con clase que implementa `CommandHandler<MiComando, MiRespuesta>`).
- El CommandBus los descubre via CDI `Instance<CommandHandler>` (inyeccion de todos los beans de un tipo).
- Se selecciona el handler cuyo tipo de comando coincide.

**Diferencias clave vs Spring:**
- En Quarkus, `@ApplicationScoped` reemplaza a `@Service`/`@Component`.
- En vez de `ApplicationContext.getBeansOfType()`, se usa `Instance<T>` (CDI portable).
- En Quarkus, los handlers se descubren en build-time (Jandex indiza las clases), asi que no hay coste de reflection al startup. **Esto es una ventaja de performance**.

**Stack tecnologico:**
- Java 25
- Gradle Kotlin DSL con `id("io.quarkus")` version `3.37.2`
- Quarkus 3.37.2 (como `implementation` + `enforcedPlatform("io.quarkus.platform:quarkus-bom:3.37.2")`)
- `nova-java-bus-api:1.0.0` como `api`
- `nova-java-ddd-utils:1.0.0` como `api`
- Tests: `@QuarkusTest` + RestAssured

**Naming en GitHub Packages:**
- `groupId`: `pe.edu.nova.java.starters` (Nivel 2 = starters/extensions)
- `artifactId`: `nova-java-bus-quarkus`
- `version`: `1.0.0`

---

## 4. Convenciones de naming alineadas al framework

Para responder concretamente la pregunta del usuario sobre naming consistente con el framework:

| Framework | Naming | Ejemplo | Por que |
|---|---|---|---|
| Spring Boot | `nova-java-<rol>-spring-boot-<tipo>` | `nova-java-commons-spring-boot-starter` | "starter" es el termino canonico en Spring Boot ecosystem |
| Quarkus | `nova-java-<rol>-quarkus-<tipo>` | `nova-java-bus-quarkus-extension`, `nova-java-api-standard-quarkus-extension` | "extension" es el termino canonico en Quarkus ecosystem |
| Generico / Nivel 1 | `nova-java-<rol>` o `nova-java-<rol>-<utils\|api\|core>` | `nova-java-ddd-utils`, `nova-java-bus-api` | Sin sufijo de framework porque es framework-agnostic |

**Conclusion:** `nova-java-bus-quarkus` (NO `starter`, NO `bundle`, NO `addon`) — alineado con la terminologia oficial de Quarkus.

---

## 5. Esfuerzo estimado para las 4 piezas

| Pieza | Esfuerzo | Notas |
|---|---|---|
| `nova-java-ddd-utils` (Nivel 1) | 2-3 dias | Copiar + adaptar del `quarkus-hexagonal-archetype`, escribir tests, configurar CI |
| `nova-java-bus-api` (Nivel 1) | 1 dia | Interfaces + excepciones + tests basicos |
| `nova-java-bus-spring` (Nivel 2) | 1-2 dias | Implementaciones + tests de integracion con `@SpringBootTest` |
| `nova-java-bus-quarkus` (Nivel 2) | 2-3 dias | Implementaciones + tests con `@QuarkusTest` + Jandex + extension metadata |
| **Total** | **6-9 dias de un dev** | Paralelizable: ddd-utils y bus-api pueden empezar en paralelo |

---

## 6. Orden de implementacion recomendado

1. **`nova-java-ddd-utils`** primero — base de todo lo demas.
2. **`nova-java-bus-api`** segundo — depende de ddd-utils.
3. **`nova-java-bus-spring`** tercero — implementacion de referencia (mas simple, ya tenemos 9 repos Spring Boot).
4. **`nova-java-bus-quarkus`** cuarto — implementacion Quarkus (mas nueva, requiere aprender Jandex).

**Verificacion final:** crear un proyecto de prueba (e.g., `examples/code-with-quarkus` extendido) que use `bus-spring` desde una app Spring Boot Y `bus-quarkus` desde una app Quarkus, demostrando que ambas implementaciones cumplen el mismo contrato.

---

## 6.5. Plan detallado de Pieza 1: `nova-java-ddd-utils` (2026-07-15)

Analisis del codigo fuente del `quarkus-hexagonal-archetype` (modulo `shared/`) revela la siguiente estructura:

### 6.5.1. Inventario del shared/ del companero

**Total: 34 archivos Java en `shared/src/main/java/.../shared/`**:
- 22 archivos en `shared/domain/` (los que van en `nova-java-ddd-utils` + `nova-java-bus-api`).
- 12 archivos en `shared/infrastructure/` (NO van en ddd-utils — son Quarkus/CDI-specific, van en `nova-java-bus-quarkus` o se descartan).

### 6.5.2. Archivos del shared/domain/ y a que pieza Nova corresponden

| Archivo companero | Destino Nova | Notas |
|---|---|---|
| `domain/aggregate/AggregateRoot.java` | `nova-java-ddd-utils` | Abstract class base, usa `Identifier` generico |
| `domain/audit/AuditMetadata.java` | `nova-java-ddd-utils` | Interface con createdAt, updatedAt, createdBy, etc. |
| `domain/bus/command/Command.java` | `nova-java-bus-api` | Interface marker |
| `domain/bus/command/CommandBus.java` | `nova-java-bus-api` | Interface |
| `domain/bus/command/CommandHandler.java` | `nova-java-bus-api` | Interface funcional |
| `domain/bus/command/CommandNotRegisteredException.java` | `nova-java-bus-api` | Exception |
| `domain/bus/event/DomainEvent.java` | `nova-java-ddd-utils` | (NO bus-api: es base de eventos de dominio) |
| `domain/bus/event/EventBus.java` | `nova-java-bus-api` | Interface |
| `domain/bus/query/Query.java` | `nova-java-bus-api` | Interface marker |
| `domain/bus/query/QueryBus.java` | `nova-java-bus-api` | Interface |
| `domain/bus/query/QueryHandler.java` | `nova-java-bus-api` | Interface funcional |
| `domain/bus/query/QueryNotRegisteredException.java` | `nova-java-bus-api` | Exception |
| `domain/exception/ConflictException.java` | `nova-java-ddd-utils` | extends DomainException |
| `domain/exception/DomainException.java` | `nova-java-ddd-utils` | abstract base class |
| `domain/exception/NotFoundException.java` | `nova-java-ddd-utils` | extends DomainException |
| `domain/exception/ValidationException.java` | `nova-java-ddd-utils` | extends DomainException |
| `domain/idempotency/IdempotencyRecord.java` | `nova-java-ddd-utils` | Record inmutable |
| `domain/idempotency/IdempotencyStore.java` | `nova-java-ddd-utils` | Interface (port) |
| `domain/query/PageRequest.java` | `nova-java-ddd-utils` | Record (DTO paginacion request) |
| `domain/query/PageResponse.java` | `nova-java-ddd-utils` | Record (DTO paginacion response) |
| `domain/valueobject/AggregateId.java` | `nova-java-ddd-utils` | Abstract class base para IDs |

### 6.5.3. Gaps: clases del doc 08 que NO existen en el companero

El doc 08 §3.1 lista clases que NO estan en el codigo del companero. El companero las implementa inline (ej. `AggregateId` implementa `Identifier` implicitamente). Para hacerlas disponibles como building blocks en Nova, hay que **extraerlas como clases separadas**:

| Clase que el doc 08 menciona | Origen / Decisión |
|---|---|
| `Entity<I>` abstract class | Extraer de `AggregateRoot<I>` (su padre en la jerarquia) |
| `ValueObject` interface/abstract | Extraer patron comun de `AggregateId` y futuros VOs |
| `Identifier<I>` interface marker | Inferir de `AggregateId` (es abstract, espera subclases concretas) |
| `UuidIdentifier`, `LongIdentifier`, `StringIdentifier` records | Crear como records concretos (no existen en el companero) |
| `Repository<A, I>` interface | Crear de cero (el companero usa `PanacheRepositoryBase` directo) |
| `Specification<T>` interface | Crear de cero (no existe) |
| `UseCase<I, O>` interface | Crear de cero (no existe como interface explicita) |
| `BaseDomainEvent` abstract class | Crear de cero (el companero usa `DomainEvent` interface directamente) |

### 6.5.4. Naming y packages

- **Group**: `pe.edu.nova.java.libs` (igual que `nova-java-api-standard`)
- **ArtifactId**: `nova-java-ddd-utils` (20 chars, OK per aprendizaje de Fase 0)
- **Package raiz**: `pe.edu.nova.java.libs.ddd`
- **Subpackages**:
  - `pe.edu.nova.java.libs.ddd.domain` (Aggregate, Entity, VO, Identifier, etc.)
  - `pe.edu.nova.java.libs.ddd.domain.aggregate`
  - `pe.edu.nova.java.libs.ddd.domain.audit`
  - `pe.edu.nova.java.libs.ddd.domain.event` (DomainEvent interface + BaseDomainEvent)
  - `pe.edu.nova.java.libs.ddd.domain.exception`
  - `pe.edu.nova.java.libs.ddd.domain.idempotency`
  - `pe.edu.nova.java.libs.ddd.domain.query`
  - `pe.edu.nova.java.libs.ddd.domain.repository` (Repository interface)
  - `pe.edu.nova.java.libs.ddd.domain.specification` (Specification interface)
  - `pe.edu.nova.java.libs.ddd.domain.usecase` (UseCase interface)
  - `pe.edu.nova.java.libs.ddd.domain.valueobject`

### 6.5.5. Stack tecnologico (lecciones aprendidas de Fase 0)

- **Java 25** (LTS, alineado con extension + instance).
- **Gradle Kotlin DSL** (`build.gradle.kts`).
- **Plugins Gradle**: `java-library`, `maven-publish`, `checkstyle`, `org.owasp.dependencycheck` (todos aplicados desde el inicio para evitar errores "Task not found" en CI).
- **OWASP config**: `autoUpdate = false` + `data.directory = NOVA_OWASP_DATA_DIR` (lección de Fase 0 §13).
- **Checkstyle**: `config/checkstyle/checkstyle.xml` desde el inicio (mismo patron que instance).
- **Sin jandex**: este repo NO es extension Quarkus, no necesita `META-INF/jandex.idx`.
- **Tests**: JUnit 6 + jqwik (property-based) + ArchUnit (architecture tests). Cobertura JaCoCo.
- **Repo path local**: `D:\Nova\java\nova-java-ddd-utils`.
- **Repo path GitHub**: `ahincho/nova-java-ddd-utils` (public).

### 6.5.6. CI / Workflows reusables

Basado en el patron reusable de `nova-devops/.github/workflows/`:

- `reusable-build-gradle.yml` (build + checkstyle + javadoc + test reports)
- `reusable-build-matrix.yml` (Java 21 + 25)
- `reusable-owasp-check.yml` (con autoUpdate=false en build.gradle.kts)
- `reusable-sbom.yml` (CycloneDX)
- `reusable-sonarcloud-gradle.yml` (cuando SONAR_TOKEN este configurado)
- `reusable-release-please.yml` (versionado automatico)
- `reusable-release-publish.yml` (publish al tag `vX.Y.Z`)

Secrets requeridos:
- `GITHUB_TOKEN` (automatico).
- (Opcional) `NVD_API_KEY` — mejora tiempos OWASP pero no es necesario con mirror.
- (Opcional) `SONAR_TOKEN` — cuando se habilite sonar.

### 6.5.7. Riesgos especificos de Pieza 1

| Riesgo | Probabilidad | Impacto | Mitigacion |
|---|---|---|---|
| Package rename incorrecto al copiar del companero (ej. olvidar un import) | Alta | Bajo | Hacer el rename con sed + validar con `gradlew compileJava` |
| Gaps identificados mal (ej. `Identifier` interface que no es realmente necesaria) | Media | Medio | Implementar primero lo que el doc 08 describe, iterar si sobra |
| Tests de AggregateRoot con generics requieren buen diseno | Media | Alto | Copiar tests del companero (`shared/src/test/.../AggregateRootTest.java`) y adaptar |
| OWASP plugin requiere Gradle 8+; nova-devops reusable espera Gradle 9 | Baja | Bajo | Mismo Gradle 9.5.1 que el resto del ecosystem Nova |
| Jandex.idx no aplica a libs puras (no extension Quarkus) | N/A | N/A | NO agregar el plugin jandex; seria error |

### 6.5.8. Estimacion de esfuerzo revisada

| Actividad | Tiempo |
|---|---|
| Crear repo local + remoto | 5 min |
| Configurar build.gradle.kts + gradle.properties + workflows CI | 30 min |
| Copiar + adaptar 18 archivos del shared/domain/ | 1.5 h |
| Crear gaps (Entity, ValueObject, Identifier, Repository, Specification, UseCase, BaseDomainEvent) | 1.5 h |
| Adaptar/crear tests (~10 archivos de test) | 1.5 h |
| Publicar v1.0.0 | 30 min |
| Validar CI end-to-end | 30 min |
| **Total** | **~6 horas de un dev** (vs 2-3 dias estimados inicialmente — el companero ya hizo el trabajo duro) |

### 6.5.9. Pendiente de decision del usuario

Antes de implementar Pieza 1, el usuario debe decidir:

1. **¿Empezamos con `nova-java-ddd-utils` ahora (esta sesion) o en otra sesion?** (El usuario indico "esperar decision y solo documentar plan" — asi que por ahora este doc queda como plan.)
2. **¿`Repository<I, A>` interface se incluye en ddd-utils o se deja a cada repo concreto?** (El companero lo usa como interface pero solo con Panache; deberia quedarse como interface neutral en ddd-utils.)
3. **¿`IdempotencyStore` interface va en ddd-utils o en bus-api?** (Es un port de infraestructura para idempotency, podria ir en ddd-utils como parte del dominio.)
4. **¿`PageRequest`/`PageResponse` van en ddd-utils o se mueven a `nova-java-api-standard`?** (Son DTOs de paginacion, mas cerca de `api-standard` que de ddd.)

---

## 7. Como se consume desde una app

### 7.1. Desde Spring Boot (consumidor)

```kotlin
// build.gradle.kts
dependencies {
    implementation("pe.edu.nova.java.libs:nova-java-ddd-utils:1.0.0")
    implementation("pe.edu.nova.java.libs:nova-java-bus-api:1.0.0")
    implementation("pe.edu.nova.java.starters:nova-java-bus-spring:1.0.0")
}

// src/main/java/.../application/commands/CreateUserHandler.kt
@Component
class CreateUserHandler : CommandHandler<CreateUserCommand, UserId> {
    override fun getCommandType(): Class<CreateUserCommand> = CreateUserCommand::class.java
    override fun handle(command: CreateUserCommand): UserId { /* ... */ }
}

// src/main/java/.../application/CreateUserService.kt
@Service
class CreateUserService(private val commandBus: CommandBus) {
    fun execute(command: CreateUserCommand): UserId = commandBus.dispatch(command)
}
```

### 7.2. Desde Quarkus (consumidor)

```kotlin
// build.gradle.kts
dependencies {
    implementation(enforcedPlatform("io.quarkus.platform:quarkus-bom:3.37.2"))
    implementation("io.quarkus:quarkus-arc")
    implementation("pe.edu.nova.java.libs:nova-java-ddd-utils:1.0.0")
    implementation("pe.edu.nova.java.libs:nova-java-bus-api:1.0.0")
    implementation("pe.edu.nova.java.starters:nova-java-bus-quarkus:1.0.0")
}

// src/main/java/.../application/commands/CreateUserHandler.kt
@ApplicationScoped
class CreateUserHandler : CommandHandler<CreateUserCommand, UserId> {
    override fun getCommandType(): Class<CreateUserCommand> = CreateUserCommand::class.java
    override fun handle(command: CreateUserCommand): UserId { /* ... */ }
}

// src/main/java/.../application/CreateUserService.kt
@ApplicationScoped
class CreateUserService(private val commandBus: CommandBus) {
    fun execute(command: CreateUserCommand): UserId = commandBus.dispatch(command)
}
```

→ La API del consumidor es **identica**. Solo cambia el import del framework (Spring → `@Service` + `@Component`, Quarkus → `@ApplicationScoped`) y el Gradle dependency (`bus-spring` vs `bus-quarkus`).

---

## 8. Riesgos especificos de las piezas DDD/Bus

| Riesgo | Probabilidad | Impacto | Mitigacion |
|---|---|---|---|
| Performance del Bus en Quarkus: busqueda de handler en cada dispatch (no en startup) | Media | Bajo | CDI `Instance<T>` resuelve en O(n) por dispatch; para n=10-20 handlers es despreciable (<1ms). Si crece, considerar precomputar un Map<Class, Handler> en `@PostConstruct` o `@Observes StartupEvent` |
| Jandex no indexa handlers en modulos separados | Baja | Medio | `nova-java-bus-quarkus` debe tener `META-INF/jandex.idx` o configurar Jandex para escanear las deps |
| Spring detecta multiples handlers para el mismo comando (falla de diseno) | Baja | Medio | Documentar convencion: 1 handler por comando. Validar en tests con `@SpringBootTest` que solo haya 1 bean |
| Quarkus CDI no respeta orden de handlers si hay multiples para el mismo comando | Baja | Bajo | Mismo criterio que Spring: 1 handler por comando, documentar convencion |
| Las clases DDD genericas (`AggregateRoot<I>`) requieren buen diseno de generics | Media | Alto | Copiar la implementacion del archetype Quarkus (ya validada), iterar tests |

---

## 9. Conclusion

Las 4 piezas (ddd-utils + bus-api + bus-spring + bus-quarkus) son **el siguiente paso logico** despues de validar Fase 0 (`nova-java-api-standard-quarkus-extension`). Permiten:

1. Compartir DDD primitives entre Spring Boot y Quarkus sin duplicar codigo.
2. Compartir el patron CQRS con implementaciones optimizadas por framework (Spring = runtime, Quarkus = build-time).
3. Tener una API unica para los consumidores (`CommandBus.dispatch(c)` funciona igual en ambos frameworks).

**Esfuerzo total:** ~1-2 semanas de un dev, con todo el codigo de referencia disponible en el `quarkus-hexagonal-archetype`.

---

## 10. Preguntas abiertas

1. **GroupId de `bus-spring` y `bus-quarkus`:** ¿`pe.edu.nova.java.starters` (Nivel 2) o `pe.edu.nova.java.libs` (Nivel 1)? Mi sugerencia: `starters` porque dependen de un framework especifico (Nivel 2). Confirmar.
2. **`nova-java-ddd-utils` y `nova-java-bus-api`:** ¿publicar como `1.0.0` directamente o arrancar con `0.1.0-SNAPSHOT` hasta validar? Mi sugerencia: `0.1.0` (pre-1.0) hasta que se estabilice el API, despues `1.0.0`. Confirmar.
3. **Versionado:** ¿`bus-spring` y `bus-quarkus` siempre con la misma version (bump coordinado), o independientes? Mi sugerencia: **bump coordinado** porque implementan el mismo contrato y deben ser compatibles.
4. **Testing cross-framework:** ¿vale la pena un repo `nova-java-bus-contract-tests` que valide que ambas implementaciones cumplen el mismo contrato? Mi sugerencia: si, util para regression testing, pero NO bloqueante para la primera version.