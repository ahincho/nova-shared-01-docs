# Plan de Adopcion: Puntos Fuertes del Quarkus Hexagonal Archetype

## Objetivo

Identificar los puntos fuertes concretos del archetype desarrollado por el companero y definir como incorporarlos al meta-framework Nova Platform, manteniendo la compatibilidad con la arquitectura de 5 niveles ya existente y el soporte multi-framework (Spring Boot / Quarkus / Micronaut).

---

## 1. Shared Kernel DDD como Libreria Pura (Nivel 1)

### Que tiene el companero

El modulo `shared/domain/` contiene un kernel DDD completo en Java puro (zero imports de framework):

| Clase | Lineas | Proposito |
|-------|--------|-----------|
| `AggregateRoot` | 44 | Base class con `record(event)` + `pullDomainEvents()` |
| `AggregateId` | 72 | UUID-backed identity base con equals/hashCode por valor |
| `Command` | 9 | Marker interface para CQRS commands |
| `CommandBus` | 16 | Port interface: `dispatch(command)` |
| `CommandHandler<C>` | 18 | Handler generico parametrizado |
| `Query<R>` | 11 | Marker interface con tipo de retorno generico |
| `QueryBus` | 18 | Port interface: `ask(query) -> R` |
| `QueryHandler<Q,R>` | 20 | Handler generico parametrizado |
| `DomainEvent` | 31 | Base class con aggregateId, occurredAt, eventId, eventType |
| `EventBus` | 20 | Port interface: `publish(List<DomainEvent>)` |
| `DomainException` | 18 | Base RuntimeException de dominio |
| `NotFoundException` | 16 | 404 con factory method `of(entity, id)` |
| `ConflictException` | 12 | 409 |
| `ValidationException` | 12 | 422 |
| `PageRequest` | 44 | Paginacion con sort, max size, offset calculado |
| `PageResponse<T>` | 47 | Respuesta paginada con totalPages, hasNext, hasPrev |
| `AuditMetadata` | 36 | Record con createdBy/updatedBy/createdAt/updatedAt |
| `IdempotencyStore` | 41 | Port interface para deteccion de duplicados |
| `IdempotencyRecord` | 24 | Record del resultado de un command ejecutado |

**Todo esto es Java puro.** No importa `jakarta.*`, ni `io.quarkus.*`, ni `org.springframework.*`.

### Como adoptarlo en Nova Platform

**Crear una nueva libreria de Nivel 1:** `nova-ddd-utils`

Esta libreria encaja naturalmente en el Nivel 1 junto a `mask-utils`, `date-utils`, `mapper-utils`, etc. Es codigo Java puro reutilizable por cualquier framework.

```
java/
  nova-ddd-utils/            <- NUEVA LIBRERIA
    pom.xml (o build.gradle)
    src/main/java/pe/edu/nova/java/libs/ddd/
      aggregate/
        AggregateRoot.java
      bus/
        command/
          Command.java
          CommandBus.java
          CommandHandler.java
        query/
          Query.java
          QueryBus.java
          QueryHandler.java
        event/
          DomainEvent.java
          EventBus.java
      valueobject/
        AggregateId.java
      exception/
        DomainException.java
        NotFoundException.java
        ConflictException.java
        ValidationException.java
      query/
        PageRequest.java
        PageResponse.java
      audit/
        AuditMetadata.java
      idempotency/
        IdempotencyStore.java
        IdempotencyRecord.java
```

**Adaptaciones necesarias al portarlo:**

1. Cambiar el paquete de `pe.edu.utp.archetype.shared.domain` a `pe.edu.nova.java.libs.ddd`.
2. Agregar al BOM raiz (`nova-bom/pom.xml`).
3. El codigo es 100% portable tal cual -- no requiere cambios funcionales.
4. Agregar tests unitarios (el companero tiene 9 archivos de test para el shared domain).

**Valor:** Cualquier proyecto que use el meta-framework puede importar `ddd-utils` y obtener los building blocks de DDD sin estar atado a Quarkus, Spring Boot ni Micronaut.

---

## 2. Implementaciones de Bus por Framework (Nivel 2)

### Que tiene el companero

El modulo `shared/infrastructure/` tiene implementaciones CDI de los buses:

| Clase | Lineas | Proposito |
|-------|--------|-----------|
| `CdiCommandBus` | 70 | Descubre `CommandHandler<?>` via CDI `Instance<>`, registra en `ConcurrentHashMap`, despacha |
| `CdiQueryBus` | 63 | Mismo patron para queries |
| `SynchronousCdiEventBus` | 35 | Usa CDI `Event<DomainEvent>` para fire sincrono |
| `GenericTypeResolver` | 54 | Resuelve el tipo generico de un handler en runtime |

### Como adoptarlo en Nova Platform

Crear starters framework-especificos que implementen los buses:

**Para Spring Boot:** `nova-ddd-spring-boot-starter`
```java
// Equivalente del CdiCommandBus pero con Spring
@Component
public class SpringCommandBus implements CommandBus {
    private final Map<Class<?>, CommandHandler<?>> registry = new ConcurrentHashMap<>();

    public SpringCommandBus(List<CommandHandler<?>> handlers) {
        // Spring inyecta todas las implementaciones de CommandHandler
        for (CommandHandler<?> handler : handlers) {
            Class<?> commandType = GenericTypeResolver.resolveTypeArgument(
                handler.getClass(), CommandHandler.class, 0);
            if (commandType != null) registry.put(commandType, handler);
        }
    }

    @Override
    @SuppressWarnings({"rawtypes", "unchecked"})
    public void dispatch(Command command) {
        CommandHandler handler = registry.get(command.getClass());
        if (handler == null) throw new CommandNotRegisteredException(command.getClass());
        handler.handle(command);
    }
}
```

**Para Quarkus:** Portar `CdiCommandBus`/`CdiQueryBus` directamente.

**Para Micronaut:** Implementar con Micronaut DI (`@Singleton`, `BeanContext`).

**Estructura resultante:**
```
nova-ddd-utils/                        <- Nivel 1: interfaces puras
nova-ddd-spring-boot-starter/          <- Nivel 2: SpringCommandBus, SpringQueryBus, SpringEventBus
nova-ddd-quarkus-extension/            <- Nivel 2: CdiCommandBus, CdiQueryBus, CdiEventBus
nova-ddd-micronaut-module/             <- Nivel 2: MicronautCommandBus, etc.
```

---

## 3. Tests de Arquitectura con ArchUnit

### Que tiene el companero

Dos clases de ArchUnit que se ejecutan en cada `./gradlew test`:

**`SharedArchitectureTest`** -- verifica que `shared/domain/` no importa:
- `jakarta.enterprise..` (CDI)
- `jakarta.ws.rs..` (JAX-RS)
- `io.quarkus..`
- `jakarta.persistence..` (JPA)

**`ProductArchitectureTest`** -- verifica que:
- `product/domain/` no importa infraestructura ni frameworks.
- `product/application/` no importa infraestructura ni JAX-RS.

Esto convierte reglas arquitectonicas en **tests que fallan si se violan**.

### Como adoptarlo en Nova Platform

**Accion 1:** Agregar ArchUnit como dependencia de test en el `nova-spring-boot-parent`:

```xml
<dependency>
    <groupId>com.tngtech.archunit</groupId>
    <artifactId>archunit-junit5</artifactId>
    <version>1.3.0</version>
    <scope>test</scope>
</dependency>
```

**Accion 2:** El archetype generado deberia incluir un test de arquitectura:

```java
// Generado por el archetype en src/test/java/{package}/architecture/
@DisplayName("Architecture rules")
class ArchitectureTest {

    @Test
    @DisplayName("Libs del meta-framework no dependen de Spring internamente")
    void libsShouldNotDependOnSpring() {
        JavaClasses classes = new ClassFileImporter()
            .importPackages("pe.edu.nova.java.libs");

        ArchRule rule = noClasses()
            .should().dependOnClassesThat()
            .resideInAnyPackage(
                "org.springframework..",
                "io.quarkus..",
                "io.micronaut..");

        rule.check(classes);
    }
}
```

**Accion 3:** Cada libreria pura del Nivel 1 deberia tener su propio ArchUnit test que verifique que no importa ningun framework.

---

## 4. Outbox Pattern como Componente Reutilizable

### Que tiene el companero

Un Outbox Pattern completo implementado en el bounded context `product`:

| Clase | Lineas | Proposito |
|-------|--------|-----------|
| `OutboxEventEntity` | 63 | JPA entity para `domain_events_outbox` con retry, error tracking |
| `OutboxPanacheRepository` | 29 | Panache repo con queries para pending/failed events |
| `OutboxEventBus` | 71 | `EventBus` implementation que escribe a outbox en la misma TX |
| `OutboxScheduler` | 96 | Scheduler cada 5s que lee pending, publica, marca published |

Migraciones SQL:
- `V3__create_domain_events_outbox.sql` (tabla con retry_count, error_message, published_at)
- `V5__create_command_idempotency.sql` (tabla para idempotencia)

### Como adoptarlo en Nova Platform

El Outbox Pattern es transversal -- no deberia vivir dentro de un bounded context. Deberia ser parte del shared kernel o un starter dedicado.

**Opcion A (Recomendada) - Agregar a `ddd-utils` + starters:**

Interfaces en `nova-ddd-utils` (Nivel 1):
```java
// Puerto puro
public interface OutboxRepository {
    void save(OutboxEvent event);
    List<OutboxEvent> findPending(int batchSize);
    void markPublished(String eventId);
    void markFailed(String eventId, String error);
}

public record OutboxEvent(
    String id, String aggregateId, String aggregateType,
    String eventType, String payload, Instant occurredAt,
    Instant publishedAt, int retryCount, String errorMessage
) { ... }
```

Implementaciones en los starters framework-especificos (Nivel 2):
- `nova-ddd-spring-boot-starter`: `JpaOutboxRepository`, `OutboxScheduler` con `@Scheduled`
- `nova-ddd-quarkus-extension`: `PanacheOutboxRepository`, `OutboxScheduler` con `@Scheduled`

**Accion concreta:** Incluir la migracion SQL como recurso del starter, que se auto-aplique con Flyway/Liquibase.

---

## 5. Request Context y Correlation ID

### Que tiene el companero

| Clase | Lineas | Proposito |
|-------|--------|-----------|
| `RequestContext` | 37 | CDI `@RequestScoped` bean con userId, transactionId, tenantId |
| `MdcRequestFilter` | 66 | Extrae headers HTTP -> RequestContext + MDC para logs |
| `CorrelationIdClientFilter` | 51 | Propaga correlationId a llamadas HTTP salientes |

Headers procesados:
- `X-User-Id` -> userId
- `X-Transaction-Id` -> transactionId (correlationId)
- `X-Tenant-Id` -> tenantId

### Como adoptarlo en Nova Platform

Nova Platform ya tiene `RequestContext` en `api-standard`, pero es menos rico. El del companero agrega:
- Propagacion a MDC (logging estructurado con correlationId en cada linea).
- Propagacion a llamadas HTTP salientes (trazabilidad entre microservicios).
- Tenant support (multi-tenancy).

**Accion:** Enriquecer el `nova-api-standard` con:

1. Agregar `tenantId` al `RequestContext` existente.
2. Crear un `MdcPopulatingFilter` en el `api-standard-spring-boot-starter` que haga el equivalente:

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class MdcPopulatingFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        String correlationId = Optional.ofNullable(req.getHeader("X-Transaction-Id"))
            .filter(s -> !s.isBlank())
            .orElse(UUID.randomUUID().toString());

        MDC.put("correlationId", correlationId);
        MDC.put("userId", req.getHeader("X-User-Id"));
        MDC.put("tenantId", req.getHeader("X-Tenant-Id"));
        try {
            chain.doFilter(req, res);
        } finally {
            MDC.clear();
        }
    }
}
```

3. Crear un `CorrelationIdInterceptor` para `RestClient` / `RestTemplate` en Spring Boot:

```java
@Component
public class CorrelationIdInterceptor implements ClientHttpRequestInterceptor {
    @Override
    public ClientHttpResponse intercept(HttpRequest request, byte[] body,
            ClientHttpRequestExecution execution) throws IOException {
        String cid = Optional.ofNullable(MDC.get("correlationId")).orElse(UUID.randomUUID().toString());
        request.getHeaders().set("X-Transaction-Id", cid);
        String tenant = MDC.get("tenantId");
        if (tenant != null) request.getHeaders().set("X-Tenant-Id", tenant);
        return execution.execute(request, body);
    }
}
```

---

## 6. RFC 7807 Problem Details para Errores

### Que tiene el companero

```java
public record ProblemDetail(String type, String title, int status, String detail,
                            String instance, Instant timestamp) {
    public static ProblemDetail of(int status, String title, String detail, String instance) {
        String typeSlug = title.toLowerCase().replace(' ', '-').replaceAll("[^a-z0-9-]", "");
        return new ProblemDetail("https://utp.edu.pe/errors/" + typeSlug, title, status, detail, instance, Instant.now());
    }
}
```

Y un `DomainExceptionMapper` que mapea `DomainException` subclasses a HTTP status codes y retorna `ProblemDetail`.

### Como adoptarlo en Nova Platform

El `api-standard` actual usa `ApiResponse.error()` para errores. RFC 7807 es el estandar de la industria (`application/problem+json`).

**Accion:** Agregar `ProblemDetail` a `nova-api-standard` (Nivel 1):

```java
// En nova-api-standard
public record ProblemDetail(
    String type,        // URI que identifica el tipo de error
    String title,       // Titulo legible
    int status,         // HTTP status code
    String detail,      // Descripcion especifica de la instancia
    String instance,    // URI del recurso que causo el error
    Instant timestamp
) {
    public static ProblemDetail of(int status, String title, String detail) { ... }
}
```

Y en el `GlobalExceptionHandler` del `api-standard-spring-boot-starter`, usar `ProblemDetail` para errores (manteniendo `ApiResponse` para respuestas exitosas):
- Respuesta exitosa: `ApiResponse.ok(data)`
- Respuesta de error: `ProblemDetail` con `Content-Type: application/problem+json`

**Nota:** Spring Boot 3+ ya tiene `org.springframework.http.ProblemDetail` nativo. El starter puede detectar si existe y usarlo, o caer al propio si no esta disponible.

---

## 7. Resilience Patterns (Composed Annotation)

### Que tiene el companero

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
@Timeout(value = 500, unit = ChronoUnit.MILLIS)
@Retry(maxRetries = 3, delay = 200, delayUnit = ChronoUnit.MILLIS)
@CircuitBreaker(requestVolumeThreshold = 10, failureRatio = 0.5, delay = 5, delayUnit = ChronoUnit.SECONDS)
public @interface ExternalServiceCall {}
```

Una sola anotacion que combina timeout + retry + circuit breaker con defaults sensatos.

### Como adoptarlo en Nova Platform

En Spring Boot, el equivalente usa `spring-retry` o `resilience4j`:

**Accion:** Crear una composed annotation en las librerias del meta-framework:

```java
// En nova-api-standard o un nuevo nova-resilience-utils
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface ExternalServiceCall {
    int timeoutMs() default 500;
    int maxRetries() default 3;
    int retryDelayMs() default 200;
}
```

Y en el starter de Spring Boot, crear un AOP aspect que lea esta anotacion y aplique los patrones usando resilience4j.

---

## 8. ADRs (Architecture Decision Records)

### Que tiene el companero

8 ADRs documentados en `docs/adr/`:

| ADR | Decision |
|-----|----------|
| ADR-001 | Hexagonal Architecture |
| ADR-002 | CDI-based CQRS buses |
| ADR-003 | Outbox Pattern |
| ADR-004 | Soft Delete |
| ADR-005 | OIDC profile strategy |
| ADR-006 | RFC 7807 Problem Details |
| ADR-007 | Two-tier idempotency |
| ADR-008 | Optimistic locking |

Y un `template.md` para nuevos ADRs.

### Como adoptarlo en Nova Platform

**Accion 1:** Crear `docs/adr/` en el meta-framework con ADRs de las decisiones ya tomadas:

| ADR | Decision del Meta-Framework |
|-----|---------------------------|
| ADR-001 | Arquitectura de 5 niveles (libs, starters, aggregator, BOM/parent, tooling) |
| ADR-002 | Librerias puras sin dependencia de framework |
| ADR-003 | Strategy Pattern para masking |
| ADR-004 | Auto-configuracion condicional en starters |
| ADR-005 | Four Golden Signals para observabilidad |
| ADR-006 | Soporte multi-framework (Spring Boot, Quarkus, Micronaut) |
| ADR-007 | Maven para BOMs/Parents, Gradle para plugins |
| ADR-008 | Versionado coordinado via BOM |

**Accion 2:** El archetype generado deberia incluir `docs/adr/template.md` para que los proyectos finales documenten sus propias decisiones.

---

## 9. Object Mother Pattern para Tests

### Que tiene el companero

```java
public final class ProductMother {
    public static Product active() { ... }
    public static Product archived() { ... }
    public static Product withName(String name) { ... }
    public static Product withPrice(double price) { ... }
    public static Product reconstituted() { ... }
}
```

Factories reutilizables para crear objetos de test en estados especificos, ubicados en `src/test/java/.../mother/`.

### Como adoptarlo en Nova Platform

**Accion:** Incluir el patron Object Mother en la guia de testing del meta-framework y generar un ejemplo en el archetype.

El `mask-utils` de Java ya usa algo similar con `MaskTestGenerators` para jqwik. Estandarizar la convencion:
- Directorio: `src/test/java/.../mother/`
- Naming: `{Entity}Mother.java`
- Metodos: `static` factories que retornan objetos en estados especificos.

---

## 10. Makefile como Interfaz de Desarrollo

### Que tiene el companero

```makefile
make init       # Generar proyecto
make dev        # PostgreSQL + Quarkus dev mode
make test       # Suite completa + coverage
make unit       # Solo unit tests
make mutation   # PIT mutation testing
make security   # OWASP CVE scan
make build      # JAR
make native     # GraalVM native
make coverage   # JaCoCo report
make clean      # Limpiar
```

### Como adoptarlo en Nova Platform

**Accion:** Agregar un `Makefile` (o `Justfile` para cross-platform) al archetype generado:

```makefile
.PHONY: dev test build clean

dev: ## Start with Spring Boot DevTools
	./mvnw spring-boot:run -Dspring-boot.run.profiles=dev

test: ## Run full test suite with coverage
	./mvnw verify jacoco:report

unit: ## Run only unit tests
	./mvnw test -Dgroups=unit

build: ## Build JAR
	./mvnw package -DskipTests

clean: ## Clean build artifacts
	./mvnw clean

lint: ## Run Checkstyle
	./mvnw checkstyle:check

security: ## OWASP dependency check
	./mvnw dependency-check:check

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
```

---

## 11. Coverage Enforcement por Capa

### Que tiene el companero

```groovy
jacocoTestCoverageVerification {
    violationRules {
        rule {
            element = 'PACKAGE'
            includes = ['...product.domain.*']
            limit { counter = 'LINE'; minimum = 0.90 }   // 90% domain
        }
        rule {
            includes = ['...product.application.*']
            limit { counter = 'LINE'; minimum = 0.85 }   // 85% application
        }
        rule {
            includes = ['...product.infrastructure.*']
            limit { counter = 'LINE'; minimum = 0.60 }   // 60% infrastructure
        }
    }
}
```

El build **falla** si la cobertura cae por debajo de estos umbrales.

### Como adoptarlo en Nova Platform

**Accion:** Configurar JaCoCo en el `nova-spring-boot-parent`:

```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.14</version>
    <executions>
        <execution>
            <goals><goal>prepare-agent</goal></goals>
        </execution>
        <execution>
            <id>check</id>
            <phase>verify</phase>
            <goals><goal>check</goal></goals>
            <configuration>
                <rules>
                    <rule>
                        <element>BUNDLE</element>
                        <limits>
                            <limit>
                                <counter>LINE</counter>
                                <minimum>0.80</minimum>
                            </limit>
                        </limits>
                    </rule>
                </rules>
            </configuration>
        </execution>
    </executions>
</plugin>
```

Y en el Gradle Plugin:
```kotlin
tasks.jacocoTestCoverageVerification {
    violationRules {
        rule {
            limit { minimum = "0.80".toBigDecimal() }
        }
    }
}
tasks.check { dependsOn(tasks.jacocoTestCoverageVerification) }
```

---

## 12. Security Headers por Defecto

### Que tiene el companero

```properties
quarkus.http.header."X-Content-Type-Options".value=nosniff
quarkus.http.header."X-Frame-Options".value=DENY
quarkus.http.header."X-XSS-Protection".value=1; mode=block
quarkus.http.header."Referrer-Policy".value=strict-origin-when-cross-origin
quarkus.http.header."Permissions-Policy".value=geolocation=(), microphone=(), camera=()
%prod.quarkus.http.header."Strict-Transport-Security".value=max-age=31536000; includeSubDomains
```

### Como adoptarlo en Nova Platform

**Accion:** Agregar security headers en el `NovaAutoConfiguration` o en un nuevo auto-configuration:

```java
@AutoConfiguration
@ConditionalOnWebApplication(type = ConditionalOnWebApplication.Type.SERVLET)
@ConditionalOnProperty(prefix = "nova.security.headers", name = "enabled",
    havingValue = "true", matchIfMissing = true)
public class SecurityHeadersAutoConfiguration {

    @Bean
    public FilterRegistrationBean<SecurityHeadersFilter> securityHeadersFilter() {
        FilterRegistrationBean<SecurityHeadersFilter> reg = new FilterRegistrationBean<>();
        reg.setFilter(new SecurityHeadersFilter());
        reg.setOrder(Ordered.HIGHEST_PRECEDENCE);
        return reg;
    }
}
```

---

## Resumen: Prioridad de Adopcion

| # | Que adoptar | Donde va en Nova Platform | Esfuerzo | Impacto |
|---|-----------|---------------------------|----------|---------|
| 1 | **Shared Kernel DDD** (AggregateRoot, buses, VOs, exceptions) | Nueva lib: `nova-ddd-utils` (Nivel 1) | Alto | Muy alto |
| 2 | **ArchUnit tests** para enforcement de arquitectura | Parent POM (dep) + archetype (test generado) | Bajo | Alto |
| 3 | **Coverage enforcement** con JaCoCo por capa | Parent POM + Gradle Plugin | Bajo | Alto |
| 4 | **Request Context + MDC + Correlation ID** | Enriquecer `api-standard-spring-boot-starter` | Medio | Alto |
| 5 | **RFC 7807 ProblemDetail** para errores | Agregar a `nova-api-standard` (Nivel 1) | Bajo | Medio |
| 6 | **ADRs** para el meta-framework | `docs/adr/` + template en archetype | Bajo | Medio |
| 7 | **Makefile** en archetype generado | `nova-spring-boot-archetype` | Bajo | Medio |
| 8 | **Object Mother** pattern en guia de testing | Archetype + documentacion | Bajo | Medio |
| 9 | **Security headers** por defecto | Nuevo auto-configuration en starter | Bajo | Medio |
| 10 | **Outbox Pattern** como componente reutilizable | `ddd-utils` (interface) + starters (impl) | Alto | Medio |
| 11 | **Resilience annotation** (`@ExternalServiceCall`) | Nuevo `nova-resilience-utils` | Medio | Medio |
| 12 | **Bus implementations** por framework | Starters de DDD (Spring/Quarkus/Micronaut) | Alto | Alto |

### Orden de ejecucion recomendado

**Fase inmediata** (Sprint 1-2, bajo esfuerzo + alto impacto):
- ArchUnit tests (#2)
- Coverage enforcement (#3)
- RFC 7807 ProblemDetail (#5)
- ADRs (#6)
- Makefile (#7)
- Security headers (#9)
- Object Mother (#8)

**Fase siguiente** (Sprint 3-5, esfuerzo medio):
- Request Context + MDC + Correlation ID (#4)
- Resilience annotation (#11)

**Fase DDD** (Sprint 6-8, alto esfuerzo + alto impacto):
- Shared Kernel DDD como libreria pura (#1)
- Bus implementations por framework (#12)
- Outbox Pattern (#10)
