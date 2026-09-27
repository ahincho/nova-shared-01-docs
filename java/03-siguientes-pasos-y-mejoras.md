# Siguientes Pasos y Puntos de Mejora

## Prioridades Inmediatas (Sprint 1-2)

Las siguientes acciones son **bloqueantes** para avanzar con calidad. Sin ellas, agregar mas funcionalidad solo incrementa la deuda tecnica.

---

### P0: Testing - El Deficit Critico

**Estado actual:** Solo `mask-utils` tiene tests (26 archivos). Los otros 9 modulos tienen zero tests.

**Acciones concretas:**

#### 1.1. Tests para librerias puras (Nivel 1)

Cada libreria pura debe tener al minimo:

| Libreria | Tests Necesarios | Prioridad |
|----------|-----------------|-----------|
| `date-utils` | Unit tests para DateParser, DateFormatter, DateConverter, DateCalculator, RelativeFormatter. Property tests para round-trip parse/format. Edge cases: nulls, formatos invalidos, zonas horarias ambiguas. | ALTA |
| `mapper-utils` | Unit tests para MapperEngine con objetos simples, nested, circulares. Tests de TypeConverters. Tests de NullStrategy (SKIP, MAP, THROW). Property tests con objetos generados. | ALTA |
| `api-standard` | Unit tests para ApiResponse builders, PageInfo calculos, FilterCriteria, HttpStatusCode. Tests para PrettyPrinter round-trip. | MEDIA |
| `observability-utils` | Unit tests para ErrorClassification.classify(). Tests de contrato para GoldenSignalsRecorder. | BAJA (es pequeno) |

**Patron a seguir:** Usar `mask-utils` como referencia. Replicar su estructura de 3 tipos de test:
```
src/test/java/
  unit/           <- JUnit 5 clasico
  property/       <- jqwik property-based
  fuzz/           <- jqwik fuzzing con strings caoticos
```

#### 1.2. Tests de integracion para Starters (Nivel 2)

Los starters necesitan tests que levanten un `ApplicationContext` de Spring Boot y verifiquen:

```java
@SpringBootTest
class MaskAutoConfigurationTest {

    @Autowired(required = false)
    private StrategyRegistry registry;

    @Test
    void shouldAutoConfigureStrategyRegistry() {
        assertThat(registry).isNotNull();
    }

    @Test
    void shouldRespectEnabledProperty() {
        // Test con nova.mask.enabled=false
    }

    @Test
    void shouldRegisterCustomStrategies() {
        // Test con @MaskStrategyBean custom
    }
}
```

| Starter | Tests de Integracion Necesarios |
|---------|-------------------------------|
| `mask-utils-sb-starter` | Auto-config core, Jackson serialization, web advice, actuator health/info, log masking. |
| `api-standard-sb-starter` | Response wrapping, exception handling, property toggle. |
| `observability-sb-starter` | Metrics registration, tracing AOP, filter golden signals, OTLP property mapping. |

#### 1.3. Tests del Meta-Framework Starter (Nivel 3)

```java
@SpringBootTest
class NovaStarterTest {

    @Test
    void shouldBootWithCustomAnnotation() {
        // Verificar que @NovaSpringBootApplication funciona
    }

    @Test
    void shouldFailOnUnsupportedJavaVersion() {
        // Verificar EnvironmentPostProcessor
    }

    @Test
    void shouldLoadAllAutoConfigurations() {
        // Verificar que todos los starters se cargan transitivamente
    }
}
```

---

### P1: Correccion de Inconsistencias

#### 2.1. Estandarizar Build System

**Problema:** Mezcla de Maven y Gradle sin logica clara.

**Recomendacion:** Elegir UNA de estas estrategias:

**Opcion A - Todo Maven (Recomendado para meta-frameworks):**
- Los BOMs, Parents, y artefactos publicados en Maven Central funcionan naturalmente con Maven.
- Convertir `date-utils`, `mapper-utils`, `api-standard` a Maven.
- Mantener el Gradle Plugin como Gradle (es obligatorio).
- Los commons-starters pueden ser Maven multi-module.

**Opcion B - Todo Gradle (excepto BOMs/Parent):**
- Convertir `mask-utils`, `observability-utils`, `spring-boot-starter` a Gradle.
- Mantener BOMs y Parent como Maven POM (no tienen alternativa en Gradle).

**Opcion C - Mantener mixto pero con regla clara:**
- Librerias puras: Gradle (por su mejor soporte de build cache y configuracion).
- BOMs/Parent/Archetype: Maven (es el estandar).
- Starters: Gradle (consistente con librerias).
- Plugin: Gradle (obligatorio).

#### 2.2. Corregir GroupIds de Ejemplos

Cambiar los microservicios de ejemplo de `com.nova.generics` a algo consistente:

```xml
<!-- ACTUAL -->
<groupId>com.nova.generics</groupId>

<!-- CORREGIDO -->
<groupId>pe.edu.nova.java.examples</groupId>
```

#### 2.3. Versiones SNAPSHOT

Cambiar todas las versiones de `1.0.0` a `0.1.0-SNAPSHOT` hasta que el framework este listo para release:

```xml
<version>0.1.0-SNAPSHOT</version>
```

#### 2.4. Limpieza de Repositorios

- Eliminar archivos `.idea/` de todos los repos (agregar a `.gitignore`).
- Eliminar `build/` del gradle plugin (agregar a `.gitignore`).
- Eliminar `Main.java` de `date-utils`.

---

## Mejoras de Funcionalidad (Sprint 3-5)

### 3. Completar el BOM

**Problema:** El BOM actual no incluye todos los artefactos.

```xml
<!-- nova-bom/pom.xml - ESTADO ACTUAL -->
<dependencyManagement>
    <dependencies>
        <dependency>mask-utils</dependency>
        <dependency>date-utils</dependency>
        <dependency>mapper-utils</dependency>
        <dependency>api-standard</dependency>
        <!-- FALTA: observability-utils -->
    </dependencies>
</dependencyManagement>
```

```xml
<!-- nova-spring-boot-bom/pom.xml - ESTADO ACTUAL -->
<dependencyManagement>
    <dependencies>
        <dependency>mask-utils-spring-boot-starter</dependency>
        <dependency>api-standard-spring-boot-starter</dependency>
        <dependency>nova-spring-boot-starter</dependency>
        <!-- FALTA: observability-spring-boot-starter -->
    </dependencies>
</dependencyManagement>
```

**Accion:** Agregar los artefactos faltantes a ambos BOMs.

---

### 4. Mejorar el api-standard-spring-boot-starter

El `GlobalExceptionHandler` actual solo maneja 3 excepciones. Deberia cubrir al menos:

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    // EXISTENTES (3):
    @ExceptionHandler(NoResourceFoundException.class)           // 404
    @ExceptionHandler(IllegalArgumentException.class)           // 400
    @ExceptionHandler(Exception.class)                          // 500

    // FALTANTES - Spring MVC:
    @ExceptionHandler(MethodArgumentNotValidException.class)    // 400 - @Valid errors
    @ExceptionHandler(ConstraintViolationException.class)       // 400 - Bean Validation
    @ExceptionHandler(HttpMessageNotReadableException.class)    // 400 - JSON parse error
    @ExceptionHandler(MethodNotAllowedException.class)          // 405
    @ExceptionHandler(HttpMediaTypeNotSupportedException.class) // 415
    @ExceptionHandler(HttpMediaTypeNotAcceptableException.class)// 406
    @ExceptionHandler(MissingServletRequestParameterException.class) // 400
    @ExceptionHandler(TypeMismatchException.class)              // 400

    // FALTANTES - Negocio:
    @ExceptionHandler(AccessDeniedException.class)              // 403
    @ExceptionHandler(AuthenticationException.class)            // 401
}
```

Tambien falta:
- Soporte para paginacion automatica (`Page<T>` -> `ApiResponse` con `PageInfo`).
- Integracion con Bean Validation para convertir `ConstraintViolation` a `ApiError`.
- Soporte para HATEOAS links automaticos.
- Content negotiation (JSON/XML).

---

### 5. Mejorar el Gradle Plugin

El plugin actual es un script de 53 lineas sin configurabilidad. Deberia tener:

```kotlin
// DSL Extension para configuracion
abstract class NovaExtension {
    abstract val javaVersion: Property<Int>           // default: 25
    abstract val enableMasking: Property<Boolean>     // default: true
    abstract val enableObservability: Property<Boolean> // default: true
    abstract val enableApiStandard: Property<Boolean>  // default: true
    abstract val starterVersion: Property<String>      // default: plugin version
}

// Uso en el proyecto:
plugins {
    id("pe.edu.nova.spring-boot") version "1.0.0"
}

nova {
    javaVersion = 21
    enableMasking = true
    enableObservability = true
    enableApiStandard = false
}
```

Tambien deberia:
- Configurar JaCoCo, Checkstyle automaticamente.
- NO hardcodear `mavenLocal()` como primer repositorio.
- Usar la version del plugin como version del starter (no hardcodear `1.0.0`).
- Incluir tests funcionales con `GradleRunner`.

---

### 6. Mejorar el Archetype

El archetype actual genera un proyecto minimo. Deberia generar:

```
my-app/
  pom.xml (o build.gradle.kts)
  .gitignore
  .editorconfig
  Dockerfile
  docker-compose.yml (con observability stack)
  src/main/java/com/example/
    Application.java
    controller/
      HealthController.java
    config/
      ApplicationConfig.java
  src/main/resources/
    application.yaml
    application-dev.yaml
    application-prod.yaml
    logback-spring.xml
  src/test/java/com/example/
    ApplicationTest.java
    controller/
      HealthControllerTest.java
  .github/workflows/
    ci.yml (usando los reusable workflows)
```

**Opcion avanzada:** Crear un CLI tipo `nova init` que permita seleccionar features interactivamente (similar a `spring init` o `quarkus create app`).

---

### 7. Documentacion de Properties (Spring Configuration Metadata)

Solo `observability-spring-boot-starter` tiene `additional-spring-configuration-metadata.json`. Todos los starters deberian tenerlo para autocompletado en IDE:

```json
{
  "groups": [
    {
      "name": "nova.mask",
      "type": "...MaskProperties",
      "description": "Configuration for Nova Platform data masking"
    }
  ],
  "properties": [
    {
      "name": "nova.mask.enabled",
      "type": "java.lang.Boolean",
      "defaultValue": true,
      "description": "Enable/disable automatic data masking"
    }
  ]
}
```

Mejor aun: usar `spring-boot-configuration-processor` para generarlo automaticamente:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-configuration-processor</artifactId>
    <optional>true</optional>
</dependency>
```

---

## Soporte Multi-Framework (Sprint 6-10)

### 8. Roadmap para Quarkus

**Fase 1 - Extension basica:**
1. Crear `nova-quarkus-extension/` con modulos `deployment/` y `runtime/`.
2. Implementar `@BuildStep` para registrar beans de las librerias puras.
3. Crear `MaskConfig` con `@ConfigMapping` (equivalente a `@ConfigurationProperties`).
4. Implementar `MaskProcessor` para registro en build-time.

**Fase 2 - Observabilidad:**
1. Quarkus ya tiene soporte nativo para OpenTelemetry y Micrometer.
2. Crear extension que registre los aspects de `@Traced` y `@Metered` via ArC.
3. Implementar `GoldenSignalsFilter` como `@ServerFilter` de Quarkus.

**Fase 3 - API Standard:**
1. Implementar `ExceptionMapper<Exception>` para JAX-RS (equivalente a `@ControllerAdvice`).
2. Implementar `WriterInterceptor` para wrapping automatico en `ApiResponse`.

**Estructura esperada:**
```
nova-quarkus-extension/
  deployment/
    src/main/java/.../deployment/
      MaskProcessor.java
      ApiStandardProcessor.java
      ObservabilityProcessor.java
  runtime/
    src/main/java/.../runtime/
      MaskConfig.java
      MaskRecorder.java
      ApiStandardConfig.java
      ObservabilityConfig.java
  pom.xml (multi-module)
```

### 9. Roadmap para Micronaut

**Fase 1 - Modulo basico:**
1. Crear `nova-micronaut-module/`.
2. Implementar `@Factory` con `@Bean` para registrar beans de librerias puras.
3. Crear `@ConfigurationProperties` para configuracion.

**Fase 2 - Observabilidad:**
1. Micronaut ya tiene soporte para Micrometer y tracing.
2. Implementar `@Filter` para Golden Signals.
3. Implementar AOP interceptors para `@Traced` y `@Metered`.

**Fase 3 - API Standard:**
1. Implementar `ExceptionHandler<Exception, HttpResponse>` para Micronaut HTTP.
2. Implementar `HttpServerFilter` para response wrapping.

---

## Mejoras de Calidad (Continuo)

### 10. Configurar Analisis Estatico

Agregar a todos los modulos:

| Herramienta | Proposito | Configuracion |
|-------------|-----------|---------------|
| Checkstyle | Estilo de codigo | `checkstyle.xml` compartido |
| SpotBugs | Deteccion de bugs | Plugin en Parent/Plugin |
| JaCoCo | Cobertura de tests | Minimo 80% en librerias puras |
| Pitest | Mutation testing | Ya configurado en mask-utils y date-utils |
| ErrorProne | Errores comunes en compilacion | Plugin de compiler |

### 11. Documentacion

| Documento | Contenido | Prioridad |
|-----------|-----------|-----------|
| Getting Started Guide | Como crear un proyecto nuevo con el meta-framework | ALTA |
| Migration Guide | Como migrar un proyecto Spring Boot existente | ALTA |
| API Reference | Javadoc publicado de todas las librerias | MEDIA |
| Architecture Decision Records | Por que se tomaron ciertas decisiones | MEDIA |
| Changelog | Por version, que cambio | ALTA |
| Contributing Guide | Como contribuir al meta-framework | BAJA |
| Compatibility Matrix | Que versiones de Java/Spring/Quarkus son soportadas | ALTA |

### 12. Configuracion de CI/CD por Modulo

Cada modulo deberia tener su propio workflow de CI que use los reusable workflows:

```yaml
# .github/workflows/ci.yml (en cada repo de libreria)
name: CI
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build:
    uses: nova-devops/.github/workflows/reusable-build-gradle.yml@main
    with:
      java-version: '25'

  quality:
    needs: build
    uses: nova-devops/.github/workflows/reusable-sonarcloud-gradle.yml@main
    with:
      sonar-org: 'nova'
      sonar-project-key: 'nova-date-utils'
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

  publish:
    needs: quality
    if: github.ref == 'refs/heads/main'
    uses: nova-devops/.github/workflows/reusable-publish-gradle.yml@main
    secrets:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Roadmap Visual

```
Fase 1 (Sprint 1-2): Fundamentos
  [x] Arquitectura de 5 niveles definida
  [x] Librerias puras implementadas (5)
  [x] Starters Spring Boot implementados (3)
  [x] Meta-framework starter Spring Boot
  [x] BOM + Parent para Spring Boot
  [x] Gradle Plugin + Maven Archetype
  [x] CI/CD reusable workflows
  [x] Infrastructure observability stack
  [ ] Tests para date-utils
  [ ] Tests para mapper-utils
  [ ] Tests para api-standard
  [ ] Tests para observability-utils
  [ ] Tests de integracion para starters
  [ ] Corregir inconsistencias (build system, groupIds, versiones)
  [ ] Completar BOMs (artefactos faltantes)

Fase 2 (Sprint 3-5): Solidificacion Spring Boot
  [ ] Mejorar GlobalExceptionHandler (15+ excepciones)
  [ ] Mejorar Gradle Plugin (Extension DSL, tests)
  [ ] Mejorar Archetype (estructura completa)
  [ ] Spring Configuration Metadata en todos los starters
  [ ] Documentacion (Getting Started, Migration, API)
  [ ] CI/CD por modulo
  [ ] Analisis estatico en todos los modulos
  [ ] Cobertura minima 80%

Fase 3 (Sprint 6-8): Quarkus
  [ ] Extension basica Quarkus (mask, api-standard)
  [ ] Extension observability Quarkus
  [ ] BOM Quarkus completo
  [ ] Ejemplos Quarkus
  [ ] Tests de compatibilidad

Fase 4 (Sprint 9-10): Micronaut
  [ ] Modulo basico Micronaut (mask, api-standard)
  [ ] Modulo observability Micronaut
  [ ] BOM Micronaut completo
  [ ] Ejemplos Micronaut
  [ ] Tests de compatibilidad

Fase 5 (Sprint 11+): Produccion
  [ ] CLI (`nova init`)
  [ ] Publicacion en Maven Central
  [ ] Compatibility matrix automatizada
  [ ] Upgrade guides por version
  [ ] Soporte GraalVM Native Image
  [ ] Security starter (JWT, OAuth2)
  [ ] Database starter (JPA, Flyway/Liquibase)
```

---

## Metricas de Exito

| Metrica | Valor Actual | Objetivo Fase 1 | Objetivo Fase 2 |
|---------|:---:|:---:|:---:|
| Modulos con tests | 1/10 | 10/10 | 10/10 |
| Cobertura promedio | ~0% | >60% | >80% |
| Frameworks soportados | 1/3 | 1/3 | 1/3 |
| Starters funcionales | 3 | 3 | 5+ |
| Documentacion (paginas) | 1 | 5 | 15+ |
| Proyectos usando el framework | 3 demos | 3 demos + 1 real | 5+ reales |
| Tiempo para nuevo proyecto | ~30 min | <5 min (archetype) | <2 min (CLI) |

---

## Decisiones Pendientes

Estas decisiones deben tomarse antes de avanzar:

1. **Build System unificado:** Elegir entre Maven-first, Gradle-first, o mixto con regla clara.
2. **Version de Java minima:** Java 25 es muy restrictivo. Considerar soportar Java 21 (LTS) como minimo con 25 como opcional.
3. **Spring Boot 4 exclusivo vs backward compat:** Spring Boot 4 acaba de salir. Soportar 3.x amplificaria la adopcion.
4. **Mono-repo vs multi-repo:** Actualmente cada modulo parece un repo independiente. Un mono-repo simplificaria el desarrollo coordinado. Un multi-repo da independencia de releases.
5. **Nombre del framework:** `nova` sugiere que es educativo. Si es para produccion empresarial, considerar un nombre definitivo.
6. **Governance model:** Quien aprueba cambios al framework? Hay un RFC process? Code owners?
7. **Licencia:** No se encontro archivo LICENSE en ningun modulo.
