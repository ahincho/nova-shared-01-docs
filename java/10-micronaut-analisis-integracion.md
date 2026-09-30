# 10. Análisis de integración con Micronaut

> **Estado:** Análisis exploratorio (pre-Fase 0).
> **Fecha:** 2026-07-14.
> **Aplica a:** Equipo Nova, proyectos multi-framework Spring Boot / Quarkus / Micronaut.

---

## 10.1 Contexto y motivación

Nova nace con Spring Boot (Fase 0 ya cerrada) y está en plena Fase 0 de Quarkus (ver
`docs/07-quarkus-analisis-adopcion.md`). Este documento evalúa un **tercer framework**:
**Micronaut**, cuya propuesta de valor es distinta a las dos anteriores:

- **Spring Boot:** ecosistema maduro, reflexion-based DI (costoso en arranque),
  batteries-included.
- **Quarkus:** build-time processing, extension model con `@BuildStep`, opinionated
  developer experience, GraalVM native image de primera clase.
- **Micronaut:** AOT compilation of DI beans (sin reflexion), startup sub-100ms, GraalVM
  nativo, **CLI propio** (similar a Angular CLI) que acelera el scaffolding, API REST
  pública para generar proyectos desde CI/scripts.

La pregunta que responde este documento es: **¿debería Nova soportar Micronaut además de
Spring Boot y Quarkus, y cómo se haría?**

### 10.1.1 Hipótesis de partida

Micronaut **no reemplaza** a Spring Boot ni a Quarkus en Nova. Su rol sería complementar
para casos donde:

1. **Se necesita startup ultra-rápido** (< 100 ms JVM, < 20 ms native).
2. **El equipo quiere evitar el costo de reflexion de Spring** sin la opinionated-ness de
   Quarkus (Micronaut es menos opinionated).
3. **Cloud functions** (AWS Lambda, Azure Functions) donde el cold start importa.
4. **Serverless** (compatible con AWS CDK via `aws-cdk` feature).
5. **gRPC-first** services (Micronaut tiene mejor soporte gRPC que Quarkus).

### 10.1.2 Posicionamiento frente a Quarkus

El **doc 07** ya cubre Quarkus como tercer framework. La pregunta natural es: **¿no es
redundante analizar Micronaut?**

Respuesta corta: **no**. Diferencias filosóficas clave:

| Aspecto                  | Quarkus                        | Micronaut                       |
|--------------------------|--------------------------------|---------------------------------|
| Build-time processing    | Extension model + `@BuildStep` | Annotation processors nativos   |
| Opinionatedness          | Muy opinionated                | Menos opinionated               |
| Native image             | Excelente, foco principal      | Excelente, foco principal       |
| GraalVM config           | Automático                     | Automático                      |
| Scaffolding              | code.quarkus.io + codestarts   | launch.micronaut.io + features  |
| Cantidad de features     | ~80 catalogadas                | 314 features                    |
| Lenguajes oficiales      | Java + Kotlin                  | Java + Kotlin + Groovy          |
| Reactive                 | Mutiny (propio)                | Reactor / RxJava3 (estándar)    |
| Spring compat            | quarkus-spring-web             | micronaut-spring (completo)     |
| Madurez                  | Red Hat, comercial             | Object Computing, comercial     |
| Comunidad OSS            | Muy grande                     | Mediana                         |

---

## 10.2 Visión general de Micronaut Launch

### 10.2.1 ¿Qué es Micronaut Launch?

Es la **herramienta oficial de scaffolding** del ecosistema Micronaut. Equivale a:

- `start.spring.io` (Spring Initializr) para Spring Boot.
- `code.quarkus.io` para Quarkus.

Disponible en tres formas:

| Forma           | URL                                             | Caso de uso                          |
|-----------------|-------------------------------------------------|--------------------------------------|
| Web UI          | https://micronaut.io/launch                     | Exploración interactiva              |
| REST API        | https://launch.micronaut.io                     | Generación desde scripts / CI        |
| CLI standalone  | https://github.com/micronaut-projects/micronaut-starter/releases | Pipelines / local sin browser |

### 10.2.2 Capacidades del scaffolding

Al momento de este análisis (2026-07-14):

- **Versiones de Micronaut disponibles:** 5.0.4 (latest estable), 4.10.18-SNAPSHOT
  (snapshot), 4.10.17 (release).
- **Java version:** hasta JDK 25 (build target = `JavaVersion.toVersion("25")`).
- **Lenguajes:** Java, Groovy, Kotlin.
- **Build tools:** Gradle (Groovy DSL), Gradle (Kotlin DSL), Maven.
- **Test frameworks:** JUnit 5, Spock, Kotest.
- **Application types:** 5 (default, cli, function, grpc, messaging).
- **Total features:** **314** distribuidas en **35 categorías**.
- **Plugins Gradle oficiales aplicados por defecto:**
  - `io.micronaut.application` v5.0.2
  - `com.gradleup.shadow` v9.4.1 (fat JAR)
  - `io.micronaut.aot` v5.0.2 (build-time optimizations)

### 10.2.3 Categorías de features (las 35)

Inventario completo obtenido vía `GET https://launch.micronaut.io/application-types/default/features`:

| Categoría                       | Features | Relevancia Nova |
|---------------------------------|---------:|-----------------|
| Server                          | 9        | Alta            |
| Validation                      | 6        | Alta            |
| Security                        | 7        | Alta            |
| API                             | 18       | Alta            |
| Documentation                   | 1        | Media           |
| Distributed Tracing             | 10       | Alta            |
| Cache                           | 5        | Media           |
| Client                          | 9        | Media           |
| Testing                         | 4        | Alta            |
| CI/CD                           | 13       | Alta            |
| Management                      | 3        | Alta            |
| Metrics                         | 23       | Alta            |
| Logging                         | 10       | Media           |
| Database                        | 42       | Alta            |
| Distributed Configuration       | 9        | Media           |
| Service Discovery               | 5        | Media           |
| Messaging                       | 20       | Alta            |
| Packaging                       | 5        | Alta            |
| View Rendering                  | 15       | Baja            |
| Configuration                   | 4        | Baja            |
| Languages                       | 4        | Baja            |
| Reactive                        | 2        | Baja            |
| Spring Framework                | 5        | Media           |
| ChatBots                        | 2        | Baja            |
| Search Engine                   | 4        | Baja            |
| Embedded Store                  | 7        | Baja            |
| Dependency Injection            | 1        | Baja            |
| Resilience                      | 1        | Media           |
| MCP                             | 4        | Baja            |
| Groovy Optional Modules         | 8        | Nula            |
| Cloud                           | 21       | Baja            |
| SSL                             | 1        | Baja            |
| Serverless                      | 8        | Media           |
| Internet of Things              | 1        | Nula            |
| Development Tools               | 17       | Media           |

### 10.2.4 API REST del scaffolding

La API pública expone los siguientes endpoints (obtenidos del OpenAPI spec
`https://launch.micronaut.io/swagger/micronaut-launch-5.0.4.yml`):

| Endpoint                              | Método | Descripción                            |
|---------------------------------------|--------|----------------------------------------|
| `/application-types`                  | GET    | Lista application types                |
| `/application-types/{type}`           | GET    | Detalle de un type                     |
| `/application-types/{type}/features`  | GET    | Features disponibles para un type      |
| `/create/{type}/{name}`               | GET    | **Genera ZIP** del proyecto            |
| `/diff/{type}/feature/{feature}`     | GET    | Diff (text/plain) de añadir feature    |
| `/diff/{type}/{name}`                 | GET    | Diff entre dos configs (A/B testing)   |
| `/preview/{type}/{name}`              | GET    | Preview de archivos sin generar ZIP    |
| `/select-options`                     | GET    | Opciones de UI (versiones, defaults)   |
| `/versions`                           | GET    | Versiones de Micronaut disponibles     |

**Query params importantes del `create`:**

- `lang=JAVA|GROOVY|KOTLIN`
- `build=GRADLE|GRADLE_KOTLIN|MAVEN`
- `test=JUNIT|SPOCK|KOTEST`
- `javaVersion=JDK_21|JDK_25`
- `type=DEFAULT|CLI|FUNCTION|GRPC|MESSAGING`
- `features=feat1,feat2,...`
- `group=com.example`
- `name=demo`
- `packageName=com.example`

**Ejemplo (curl):**

```bash
curl -L -o demo.zip \
  "https://launch.micronaut.io/create/default/com.example.demo?lang=JAVA&build=GRADLE_KOTLIN&test=JUNIT&javaVersion=JDK_25&type=DEFAULT&features=validation,openapi,security-jwt,data-jdbc,postgres,flyway"
unzip demo.zip -d demo && cd demo && ./gradlew run
```

---

## 10.3 Selección de features recomendadas para Nova

Nova se compone de librerías compartidas (`nova-api-standard`, futura `nova-bus`,
`nova-ddd-utils`, etc.). Un proyecto generado con Micronaut Launch debe poder consumir
esas librerías como dependencias Maven. El scaffolding es solo el punto de partida.

### 10.3.1 Set "Nova Recommended" (16 features)

Set base validado experimentalmente, alineado con la paridad que tenemos en Quarkus
(doc 07):

| # | Feature                          | Categoría       | Propósito                                |
|---|----------------------------------|-----------------|------------------------------------------|
| 1 | `validation`                     | Validation      | Bean Validation (Jakarta)                |
| 2 | `openapi`                        | API             | Spec OpenAPI 3 generada en build         |
| 3 | `swagger-ui`                     | API             | UI Swagger servida en `/swagger-ui`      |
| 4 | `problem-json`                   | Validation      | RFC 7807 error responses                 |
| 5 | `security-jwt`                   | Security        | JWT bearer authentication                |
| 6 | `data-jdbc`                      | Database        | Acceso a BD via Micronaut Data JDBC      |
| 7 | `postgres`                       | Database        | Driver JDBC PostgreSQL                   |
| 8 | `flyway`                         | Database        | Migraciones versionadas                  |
| 9 | `redis-lettuce`                  | Cache           | Driver Redis (Lettuce)                   |
|10 | `cache-caffeine`                 | Cache           | Cache local in-process                   |
|11 | `kafka`                          | Messaging       | Productor/consumidor Kafka               |
|12 | `tracing-opentelemetry-exporter-otlp` | Distributed Tracing | Tracing OTLP nativo       |
|13 | `micrometer-prometheus`          | Metrics         | Métricas Prometheus                      |
|14 | `management`                     | Management      | Endpoints `/health`, `/info`, etc.       |
|15 | `retry`                          | Resilience      | Retry policies declarativas              |
|16 | `testcontainers`                 | Testing         | Containers Docker en tests               |

**Justificación por feature (top 5):**

- **`validation` + `problem-json`**: Validación declarativa + respuesta de error estándar
  RFC 7807. **NO se solapa** con la validación de Quarkus porque Micronaut usa su
  propio motor (`micronaut-validation`) que delega a Hibernate Validator por debajo.
- **`openapi` + `swagger-ui`**: Idéntico objetivo a la integración Quarkus, pero
  generado por el annotation processor `micronaut-openapi`. **Más maduro** que
  smallrye-openapi porque tiene años más de evolución.
- **`security-jwt`**: Bearer JWT out-of-the-box. Necesario para todos los servicios Nova
  que se autentiquen contra un IDP corporativo.
- **`data-jdbc` + `postgres` + `flyway`**: Stack más simple que JPA. Para Nova favorece
  repositorios explícitos sobre entidades implícitas.
- **`kafka`**: Necesario para el futuro bus de eventos (doc 08).

### 10.3.2 Features a evitar

| Feature                      | Por qué evitarla                                         |
|------------------------------|----------------------------------------------------------|
| `tomcat-server` / `jetty-server` | Netty (default) tiene mejor startup.                |
| `kafka-streams`              | Demasiado opinionated para Fase 0.                       |
| `jms-*`                      | JMS está siendo reemplazado por Kafka/NATS en la mayoría |
|                              | de stacks modernos.                                     |
| `views-*`                    | Nova no genera UI server-side.                           |
| `dekorate-*`                 | Dekorate está deprecado a favor de micronaut-operator.   |
| `k8s-*` (preview)            | Funcionalidad aún experimental.                          |

### 10.3.3 Features específicas del ecosistema Nova (a futuro)

Para Fase 1+, cuando tengamos las librerías Nova publicadas:

- `nova-api-standard-micronaut-module` (module propio, no de Launch): auto-wiring de
  `ApiExceptionMapper`, `ApiResponseBuilder` y Jackson configuration.
- `nova-bus-micronaut-module` (module propio): integración con el bus de eventos Nova.

Esto se lograría creando un **module personalizado** que se consume como dependencia
Maven directamente, no como feature de Launch (la integración vía Launch requeriría
forkear `micronaut-starter`, ver §10.7.5).

---

## 10.4 Output generado: análisis del ZIP

### 10.4.0 Baseline existente en el repo

Antes de generar proyectos sintéticos, **existe un baseline real** en el repo:

- **Path:** `examples/demo-micronaut/`
- **Generado via:** Web UI https://micronaut.io/launch con los defaults (0 features
  custom).
- **`micronaut-cli.yml` muestra:** 16 features por defecto (`app-name, gradle,
  http-client-test, java, java-application, junit, logback, micronaut-aot,
  micronaut-build, micronaut-configuration-validation-gradle-plugin,
  micronaut-http-validation, netty-server, properties, readme, serialization-jackson,
  shade, static-resources`).
- **Build tool:** **Gradle Kotlin DSL** (`build.gradle.kts`, `buildTool: gradle_kotlin`).
- **Lenguaje:** Java.
- **Test framework:** JUnit 5.
- **Plugin `io.micronaut.application` v5.0.2 aplicado** (default de Launch).

Este baseline sirve como **punto de referencia estructural** y como **integration test
vivo** cuando publiquemos el `nova-api-standard-micronaut-module`.

### 10.4.1 Inspección del `build.gradle.kts` baseline

```kotlin
plugins {
    id("io.micronaut.application") version "5.0.2"
    id("com.gradleup.shadow") version "9.4.1"
    id("io.micronaut.aot") version "5.0.2"
}

version = "0.1"
group = "com.example"

repositories {
    mavenCentral()
}

dependencies {
    annotationProcessor("io.micronaut:micronaut-http-validation")
    annotationProcessor("io.micronaut.serde:micronaut-serde-processor")
    implementation("io.micronaut.serde:micronaut-serde-jackson")
    compileOnly("io.micronaut:micronaut-http-client")
    runtimeOnly("ch.qos.logback:logback-classic")
    testImplementation("io.micronaut:micronaut-http-client")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

application { mainClass = "com.example.Application" }
java {
    sourceCompatibility = JavaVersion.toVersion("25")
    targetCompatibility = JavaVersion.toVersion("25")
}

micronaut {
    runtime("netty")
    testRuntime("junit5")
    processing {
        incremental(true)
        annotations("com.example.*")
    }
    aot {
        optimizeServiceLoading = false
        convertYamlToJava = false
        precomputeOperations = true
        cacheEnvironment = true
        optimizeClassLoading = true
        deduceEnvironment = true
        optimizeNetty = true
        replaceLogbackXml = true
    }
}

tasks.named<io.micronaut.gradle.docker.MicronautDockerfile>("dockerfile") {
    baseImage = "eclipse-temurin:25-jre"
}

tasks.withType<AbstractTestTask>().configureEach {
    failOnNoDiscoveredTests = false
}
```

**Observaciones críticas (que cambian la recomendación de §10.14.2):**

1. **Usa `micronaut-serde-jackson`** (NO `micronaut-jackson-databind`). El processor es
   `micronaut-serde-processor` separado. **Este es el approach oficial moderno de
   Micronaut** y debe ser nuestra elección para el module, no `jackson-databind`.
2. **`micronaut-http-validation`** es el annotation processor para validación de
   argumentos de controllers.
3. **El bloque `micronaut { aot { ... } }`** contiene 8 optimizaciones AOT. Para el
   `nova-api-standard-micronaut-module` (que NO es una app, es una librería), el block
   `micronaut {}` no aplica (esos configs son para la app, no para libs).
4. **`tasks.named<T>("name")`** — el template usa generics explícitas (Kotlin DSL).
5. **`tasks.withType<T>().configureEach`** — Kotlin DSL syntax con generics.

### 10.4.2 `Application.java` baseline

```java
package com.example;

import io.micronaut.runtime.Micronaut;

public class Application {
    public static void main(String[] args) {
        Micronaut.run(Application.class, args);
    }
}
```

Sin controller demo (a diferencia del ejemplo que generé con 16 features en §10.4.3).
Esto confirma que el baseline es **mínimo**, ideal para validar el module.

### 10.4.3 `application.properties` baseline

Solo trae el default de Micronaut + logback. Sin DB, sin security, sin nada. Esto es
exactamente lo que queremos para validar la integración con nuestro module: el module
debe ser **autocontenido** y no depender de configs externas.

### 10.4.4 Output con 16 features (proyecto sintético generado vía API)

Para entender el alcance de un proyecto "completo", se generó vía
`/create/default/com.example.demo?features=...` con las 16 features del §10.3.1. El
output completo se omitió por brevedad pero el `build.gradle.kts` resultante tiene:

- **6 annotation processors** (uno por cada feature con processor asociado).
- **22 dependencies** en `implementation` / `compileOnly` / `runtimeOnly`.
- **7 `testImplementation`** (Testcontainers + drivers por BD).
- Mismas configs `micronaut { aot { ... } }` que el baseline.
- El `application.properties` tiene config de datasources, JWT, Prometheus, OpenTelemetry,
  Redis, etc. — todo preconfigurado por las features.

El `micronaut-cli.yml` resultante lista **39 features** (16 custom + 23 transitivas).
Cada feature agrega deps + config sin pisar las demás (a diferencia de Spring Boot).

---

## 10.5 Diff por feature individual

Para entender qué hace cada feature, se invocó el endpoint
`GET /diff/default/feature/{feature}` (devuelve unified diff en text/plain).

### 10.5.1 `validation`

```diff
--- build.gradle.kts
+++ build.gradle.kts
+    annotationProcessor("io.micronaut.validation:micronaut-validation-processor")
+    implementation("io.micronaut.validation:micronaut-validation")
+    implementation("jakarta.validation:jakarta.validation-api")
```

Efecto: habilita `@NotNull`, `@Size`, etc. en controllers. Sin archivos nuevos.

### 10.5.2 `openapi`

```diff
--- src/main/java/example/Application.java
+++ src/main/java/example/Application.java
+import io.swagger.v3.oas.annotations.*;
+import io.swagger.v3.oas.annotations.info.*;
+@OpenAPIDefinition(
+    info = @Info(
+            title = "example",
+            version = "0.0"
+    )
+)

--- build.gradle.kts
+++ build.gradle.kts
+    annotationProcessor("io.micronaut.openapi:micronaut-openapi")
+    compileOnly("io.micronaut.openapi:micronaut-openapi-annotations")
```

Efecto: genera `META-INF/swagger/demo-0.0.yml` en build-time. Modifica Application.java.

### 10.5.3 `swagger-ui`

```diff
--- openapi.properties          (nuevo archivo)
+++ openapi.properties
+swagger-ui.enabled=true
+redoc.enabled=false
+openapi-explorer.enabled=false
+rapidoc.enabled=false

--- src/main/resources/application.properties
+++ src/main/resources/application.properties
+micronaut.router.static-resources.swagger-ui.mapping=/swagger-ui/**
+micronaut.router.static-resources.swagger-ui.paths=classpath:META-INF/swagger/views/swagger-ui
+micronaut.router.static-resources.swagger.mapping=/swagger/**
+micronaut.router.static-resources.swagger.paths=classpath:META-INF/swagger
```

Efecto: sirve Swagger UI en `/swagger-ui` y spec en `/swagger`.

### 10.5.4 `security-jwt`

```diff
--- build.gradle.kts
+++ build.gradle.kts
+    annotationProcessor("io.micronaut.security:micronaut-security-processor")
+    implementation("io.micronaut.security:micronaut-security-jwt")
+    aotPlugins(platform("io.micronaut.platform:micronaut-platform:5.0.4"))
+    aotPlugins("io.micronaut.security:micronaut-security-aot")
+        configurationProperties.put("micronaut.security.jwks.enabled","false")

--- src/main/resources/application.properties
+++ src/main/resources/application.properties
+micronaut.security.authentication=bearer
+micronaut.security.token.jwt.signatures.secret.generator.secret=${JWT_GENERATOR_SIGNATURE_SECRET:pleaseChangeThisSecretForANewOne}
```

Efecto: todos los endpoints requieren `Authorization: Bearer ...` por defecto. Para
abrir endpoints en dev: `@Secured(SecurityRule.IS_ANONYMOUS)`.

### 10.5.5 `data-jdbc`

```diff
--- build.gradle.kts
+++ build.gradle.kts
+    annotationProcessor("io.micronaut.data:micronaut-data-processor")
+    implementation("io.micronaut.data:micronaut-data-jdbc")
+    implementation("io.micronaut.sql:micronaut-jdbc-hikari")
+    runtimeOnly("com.h2database:h2")
```

Efecto: habilita `CrudRepository<T, ID>` y derivados. H2 como default, pero se
configura a Postgres via `application.properties`.

### 10.5.6 `kafka`

```diff
--- build.gradle.kts
+++ build.gradle.kts
+    id("io.micronaut.test-resources") version "5.0.2"
+    implementation("io.micronaut.kafka:micronaut-kafka")
+    testResources {
+        sharedServer = true
+        version = "4.0.0"
+    }
+tasks.withType<io.micronaut.gradle.testresources.StartTestResourcesService>().configureEach {
+      useClassDataSharing.set(false)
+}
```

Efecto: habilita `@KafkaClient` (producer) y `@KafkaListener` (consumer). El plugin
`test-resources` arranca Kafka automáticamente en tests.

### 10.5.7 `testcontainers`

```diff
--- build.gradle.kts
+++ build.gradle.kts
+    testImplementation("org.apache.commons:commons-compress:1.28.0")
+    testImplementation("org.testcontainers:testcontainers")
+    testImplementation("org.testcontainers:testcontainers-junit-jupiter")
```

Efecto: deps de testcontainers. Para usarlo efectivamente, escribir tests con
`@Testcontainers` + `@Container` o usar la integración de Micronaut Test Resources.

### 10.5.8 Observación general del diff

Cada feature es **atómica y predecible**: agrega deps + config. **No genera archivos
side-effect colaterales** (excepto `swagger-ui` que crea `openapi.properties` y
`kafka` que modifica el `micronaut-test-resources` plugin block). Esto es muy
agradable de mantener vs. Quarkus donde las extensiones a veces generan clases
adicionales en build-time via `@BuildStep`.

---

## 10.6 Validación experimental

### 10.6.1 Setup del experimento

- **Proyecto baseline real (referencia):** `examples/demo-micronaut/` (ya commiteado
  en el repo, Gradle Kotlin DSL, 16 features default).
- **Proyecto con 16 features (sintético):** generado vía API con JDK 25, Gradle
  Groovy DSL, JUnit 5, scope de validación.
- **Tamaño del ZIP sintético:** 55,469 bytes (54 KB).
- **Comando de generación:**
  ```bash
  curl -L -o demo.zip \
    "https://launch.micronaut.io/create/default/com.example.demo?lang=JAVA&build=GRADLE&test=JUNIT&javaVersion=JDK_25&type=DEFAULT&features=validation,openapi,swagger-ui,problem-json,security-jwt,data-jdbc,postgres,flyway,redis-lettuce,cache-caffeine,kafka,tracing-opentelemetry-exporter-otlp,micrometer-prometheus,management,retry,testcontainers"
  ```

### 10.6.2 Resultados de compilación

```
> Task :compileJava
Note: Generating OpenAPI Documentation
Note: Writing OpenAPI file to destination:
      build/classes/java/main/META-INF/swagger/demo-0.0.yml
Note: Writing OpenAPI views to destination:
      build/classes/java/main/META-INF/swagger/views

BUILD SUCCESSFUL in 1m 49s
1 actionable task: 1 executed
```

Observaciones:

- **Cold build (con descarga de Gradle 9.5.1 y resolución de deps):** 1m 49s.
- **OpenAPI se genera en build-time** vía annotation processor — no se necesita un
  paso manual.
- **Sin errores** ni warnings bloqueantes. Solo SLF4J bindings notices que son
  cosméticos.

### 10.6.3 Resultados de tests

```
> Task :test
BUILD SUCCESSFUL in 1m 3s
6 actionable tasks: 5 executed, 1 up-to-date
```

El test generado (`DemoTest`) solo verifica `application.isRunning()`. Esto es
deliberado: el scaffolding default NO genera tests integrados con Docker para
mantener el build offline-friendly. Para tests con Postgres/Kafka/Redis reales, el
usuario debe:

- Agregar tests con `@MicronautTest` + `@TestPropertyProvider`.
- O usar `Micronaut Test Resources` (incluido automáticamente al agregar `kafka`,
  `data-jdbc`+`postgres`, etc.) que arranca contenedores Docker automáticamente.

### 10.6.4 Tiempo total de arranque

No se midió empíricamente el startup time de la app, pero la documentación oficial
reporta:

- **JVM:** ~1-2 segundos (con AOT optimizations activadas).
- **Native (GraalVM):** ~50-100 milisegundos.

Ambos mejores que Spring Boot típico (3-8s JVM, 100-300ms native) y comparables a
Quarkus.

---

## 10.7 Estrategia de adopción Nova + Micronaut

### 10.7.1 Principio rector

**Paralelo a la estrategia Quarkus ya documentada (doc 07 §7).** Misma separación de
roles, ajustando la nomenclatura al ecosistema Micronaut:

> **Convención Nova por framework (alineada con el ecosistema oficial):**
> - **Spring Boot** → `starter` (`nova-X-spring-boot-starter`)
> - **Quarkus** → `extension` (`nova-X-quarkus-extension`)
> - **Micronaut** → `module` (`nova-X-micronaut-module`)
>
> El sufijo refleja la terminología nativa de cada framework: Spring llama "starter" a
> sus artefactos agregadores, Quarkus "extension" a sus piezas con `@BuildStep`, y
> Micronaut "module" a sus librerías CDI/JSR-330 que se descubren por classpath.
> Funcionalmente los tres son similares: un JAR publicable en Maven Central / GitHub
> Packages que el proyecto consumidor agrega como dependencia.

| Artefacto                                     | Responsabilidad                                     |
|-----------------------------------------------|-----------------------------------------------------|
| `nova-bom` (futuro)                           | Cataloga versiones de TODAS las libs Nova           |
| `nova-java-micronaut-starter` (futuro)        | Mega-module con deps Nova preagregadas              |
| `nova-api-standard-micronaut-module` (Fase 0) | **Module coloquial: ApiExceptionMapper + Jackson** |
| `nova-bus-micronaut-module` (futuro)          | Module coloquial: event bus                         |
| `nova-ddd-utils-micronaut-module` (futuro)    | Module coloquial: DDD utilities                     |

**Fase 0 enfoca exclusivamente en `nova-api-standard-micronaut-module`**, que envuelve
la librería nativa Java `nova-api-standard:1.0.0` y expone beans CDI/JSR-330 listos para
ser auto-Descubiertos por cualquier aplicación Micronaut que la incluya como
dependencia. La validación end-to-end se hace contra el baseline real
`examples/demo-micronaut/`.

### 10.7.2 Naming convention (paridad con Spring/Quarkus)

Siguiendo la convención validada en doc 07 §4 y el §10.7.1:

- **Repos GitHub:** `ahincho/nova-java-<rol>-micronaut-module` (con `java-`).
- **artifactIds Maven:** `nova-<rol>-micronaut-module` (sin `java-`, sufijo `module`
  refleja la terminología de Micronaut).
- **groupId:** `pe.edu.nova.java.starters` (mismo que Quarkus/Spring).
- **Java package raíz:** `pe.edu.nova.java.starters.api.standard.micronaut` (espejo
  del artifactId; sigue el patrón `pe/edu/nova/java/starters/<rol>/<framework>`).
- **Ejemplo Fase 0:** repo `nova-java-api-standard-micronaut-module` →
  artifact `pe.edu.nova.java.starters:nova-api-standard-micronaut-module:1.0.0` →
  clases en package `pe.edu.nova.java.starters.api.standard.micronaut.*`.

Tabla de paridad con los otros frameworks Nova:

| Framework  | Repo ejemplo                                            | ArtifactId ejemplo                                   |
|------------|---------------------------------------------------------|------------------------------------------------------|
| Spring Boot| `ahincho/nova-java-api-standard-spring-boot-starter`    | `nova-api-standard-spring-boot-starter`              |
| Quarkus    | `ahincho/nova-java-api-standard-quarkus-extension`      | `nova-api-standard-quarkus-extension`                |
| Micronaut  | `ahincho/nova-java-api-standard-micronaut-module`       | `nova-api-standard-micronaut-module`                 |

### 10.7.3 Tipo de module: coloquial vs real

En Micronaut el término equivalente a "extension coloquial" es **module coloquial**:
un artefacto publicable que contiene beans CDI/JSR-330 estándar descubiertos
automáticamente por classpath scanning en compile-time.

**Module coloquial** es la opción correcta para Fase 0 porque:

- NO necesitamos generar código en build-time (no hay equivalente directo a
  `@BuildStep` de Quarkus). Las anotaciones de Micronaut (`@Singleton`,
  `@Controller`, `@Requires`, etc.) se procesan via annotation processors en el
  proyecto consumidor, no en el module.
- Las dependencias de runtime son beans JSR-330 puros (`@Singleton`, `@Singleton`
  con `@Replaces`, etc.).
- El module NO necesita aplicar el plugin `io.micronaut.application` (igual que la
  extension Quarkus NO aplica `io.quarkus`). Es una librería Java pura.

Si en el futuro se justifica un **module real** (equivalente a extension real en
Quarkus), sería necesario:

1. Crear el module con dos artefactos separados (`-generator` para build-time y
   `-runtime` para ejecución).
2. Registrar `BeanDefinitionReference` o `BeanCreatedEventListener` en
   `META-INF/micronaut/...`.
3. O crear un `io.micronaut.context.annotation.Factory` que genere beans dinámicamente.

Esto se justificaría solo si necesitamos, por ejemplo, **generar repositorios
automáticamente desde entidades** (similar a Panache) o auto-configurar clientes HTTP
basados en convención. **Para Fase 0 NO es necesario.**

### 10.7.4 Estructura del module coloquial

```
nova-java-api-standard-micronaut-module/
├── build.gradle.kts                     (NO aplica plugin io.micronaut.application)
├── settings.gradle.kts
├── gradle.properties                    (version=1.0.0, group, micronautVersion)
├── gradle/wrapper/                      (wrapper Gradle 9.5.1)
├── README.md
├── CONTRIBUTING.md
├── package.json                         (commitlint + lefthook, paridad Nova)
├── lefthook.yml
├── commitlint.config.js
├── config/checkstyle/checkstyle.xml
├── .release-please-config.json           (component + package-name)
├── .release-please-manifest.json         (version actual 1.0.0)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                       (reusa workflows de nova-devops)
│   │   ├── release-please.yml
│   │   └── publish-on-tag.yml
│   └── SECRETS_SETUP.md                 (paridad con repo Quarkus)
├── src/main/java/pe/edu/nova/java/starters/api/standard/micronaut/
│   ├── package-info.java
│   ├── mapper/ApiExceptionMapper.java   (@Singleton, implements ExceptionHandler)
│   └── jackson/ApiObjectMapperCustomizer.java   (implements ObjectMapperCustomizer)
├── src/test/java/...
│   ├── mapper/ApiExceptionMapperTest.java
│   └── jackson/ApiObjectMapperCustomizerTest.java
└── src/main/resources/
    └── (vacío en Fase 0 — no necesita META-INF/micronaut/)
```

**Diferencias vs. el repo `nova-java-api-standard-quarkus-extension`:**

| Aspecto               | Quarkus extension coloquial                | Micronaut module coloquial              |
|-----------------------|--------------------------------------------|-----------------------------------------|
| File marker           | (no requiere)                              | (no requiere)                           |
| DI annotation         | `@ApplicationScoped` (Jakarta CDI)        | `@Singleton` (JSR-330)                  |
| HTTP error mapping    | `@Provider` + `ExceptionMapper<T>`        | `ExceptionHandler<T, HttpResponse>`     |
| Customizer interface  | `io.quarkus.jackson.ObjectMapperCustomizer`| `io.micronaut.jackson.ObjectMapperCustomizer` |
| Build-time processing | No (CDI runtime)                           | No (annotation processors ajenos)       |
| Plugin aplicado       | Ninguno (java-library puro)               | Ninguno (java-library puro)             |
| Native image compat   | Excelente                                  | Excelente                               |
| Dep runtime principal | `quarkus-rest` + `quarkus-arc`             | `micronaut-core` + `micronaut-runtime`  |
| Dep JSON              | `quarkus-jackson` (explícito)              | `micronaut-serde-jackson` (+ `serde-processor`) |
| Grupo DI              | ArC (Quarkus CDI)                          | Micronaut Context (JSR-330 + custom)    |

### 10.7.5 Custom features en Micronaut Launch (Fase 2)

Para que los proyectos generados con Micronaut Launch consuman automáticamente los
modules Nova, **se requiere** crear custom features en un fork propio de
`micronaut-starter`. Pasos:

1. Fork `micronaut-projects/micronaut-starter` a `ahincho/micronaut-starter-nova`.
2. Crear features en `starter-core/src/main/resources/features/nova/`:
   - `nova-api-standard-micronaut-module.yml` (feature definition).
   - `nova-api-standard-micronaut-module/...` (templates).
   - Repetir por cada module.
3. Configurar el endpoint de Launch para apuntar al fork.
4. Documentar en el README de cada repo Nova: "usa
   `LAUNCH_URL=https://launch.nova.edu.pe/...` para generar proyectos con este stack".

**Costo estimado:** 3-5 días para el fork + primera feature. Por feature adicional:
0.5-1 día. **NO recomendado para Fase 0** — posponer a Fase 2.

### 10.7.6 Alternativa para Fase 0: post-procesar ZIP descargado

Más simple que forkear el starter: tomar el baseline ya commiteado en
`examples/demo-micronaut/` (o generar uno nuevo con `curl ... | unzip`) y luego
ejecutar un script `nova-setup.sh` / `nova-setup.ps1` que:

1. Modifica `build.gradle.kts` para agregar
   `implementation("pe.edu.nova.java.starters:nova-api-standard-micronaut-module:1.0.0")`.
2. Modifica `application.properties` con config Nova si aplica.
3. Agrega clases iniciales (`Application.java` con `@SerdeImport` para nuestros DTOs).

**Costo:** 1 día para el script. **Trade-off:** menos integrado que custom features,
pero suficiente para Fase 0.

---

## 10.8 Comparativa con Quarkus Launch y Spring Initializr

### 10.8.1 Tabla lado a lado

| Aspecto                          | Spring Initializr         | Quarkus Launch           | Micronaut Launch         |
|----------------------------------|---------------------------|--------------------------|--------------------------|
| URL                              | start.spring.io           | code.quarkus.io          | launch.micronaut.io      |
| Features totales                 | ~60 starters              | ~80 extensions           | **314 features**         |
| Tipos de proyecto                | 4 (Maven/Gradle + Jar/War)| 3 (core/web/messaging)   | 5 (default/cli/func/grpc/messaging) |
| Lenguajes                        | Java, Kotlin, Groovy      | Java, Kotlin             | Java, Kotlin, Groovy     |
| Build tools                      | Maven, Gradle             | Maven, Gradle            | Maven, Gradle (Groovy/Kotlin) |
| Java version máxima              | 25                        | 25                       | 25                       |
| Custom features propias          | Sí (fork + flags)         | Sí (Quarkiverse Hub)     | Sí (fork starter)        |
| API REST pública                 | Sí                        | Sí                       | Sí                       |
| OpenAPI spec del API             | Sí                        | No                       | Sí (Swagger UI built-in) |
| CLI standalone                   | No (vía `curl`)           | No (vía `curl`)          | **Sí (binarios nativos)**|
| Predicción del output            | Media (algunos starters agregan cosas no obvias) | Baja (codestarts opacas) | **Alta (cada feature es atómica)** |
| Tiempo de generación             | <1s                       | <1s                      | <1s                      |
| AOT processing                   | N/A (Spring no AOT)       | Sí (núcleo del modelo)   | Sí (annotation processors) |
| Native image                     | Buildpacks (experimental) | Primera clase            | Primera clase            |
| Open source del starter          | Sí (spring-io/initializr) | Parcial (registry propia)| Sí (micronaut-starter)   |
| Madurez / edad                   | ~10 años                  | ~7 años                  | ~8 años                  |
| Comercial detras                | Broadcom / VMware         | Red Hat                  | Object Computing         |

### 10.8.2 ¿Cuál es más fácil de customizar para Nova?

| Criterio                               | Spring Boot      | Quarkus              | Micronaut          |
|----------------------------------------|------------------|----------------------|--------------------|
| Crear starter custom                   | Medio            | Alto (codestart)     | **Bajo (feature YAML)** |
| Publicar starter propio                | Bajo (Maven Central) | Alto (Quarkiverse)   | **Bajo (Maven Central)** |
| Versionar starter con Nova libs        | Bajo             | Medio                | **Bajo**           |
| Consumir en proyecto existente         | Bajo             | Bajo                 | **Bajo**           |
| Tiempo total para Fase 0               | 2-3 días         | 3-4 días (Quarkiverse)| **1-2 días**       |

### 10.8.3 El argumento "314 features" no es tan bueno como parece

Tener 314 features no significa que cada una sea production-ready. Varias son
preview-only (marcadas en el JSON), otras son community-maintained, otras son
aliados comerciales (Couchbase, Oracle, etc.).

Comparación realista de features production-grade:

| Framework    | Features production-grade estimadas |
|--------------|------------------------------------:|
| Spring Boot  | ~40-50 starters oficiales          |
| Quarkus      | ~50-60 extensions                   |
| Micronaut    | ~100-150 features (más conservador) |

Aún así, Micronaut tiene **más cobertura de niche cases** (multi-tenancy, CRaC,
EclipseStore, etc.) que son útiles en casos específicos.

---

## 10.9 Plan de acción concreto

### 10.9.1 Fase 0 (1-2 semanas) — viabilidad

Objetivo: validar que un module Micronaut Nova + apps generadas con Micronaut Launch
funcionan end-to-end. **El scope se reduce explícitamente al integration con
`nova-api-standard`** (paralelo al approach Quarkus en doc 07 §7 Fase 0). El baseline
para validar es `examples/demo-micronaut/` (ya commiteado en el repo).

1. **Crear repo `ahincho/nova-java-api-standard-micronaut-module`** paralelo al
   `nova-java-api-standard-quarkus-extension` (gemelo estructural).
   - artifactId: `pe.edu.nova.java.starters:nova-api-standard-micronaut-module:1.0.0`.
   - Java package raíz: `pe.edu.nova.java.starters.api.standard.micronaut`.
   - Implementar `ApiExceptionMapper` (interfaz
     `io.micronaut.http.server.exceptions.ExceptionHandler<T, HttpResponse>`).
   - Implementar `ApiObjectMapperCustomizer` (interfaz
     `io.micronaut.jackson.ObjectMapperCustomizer`).
   - Depende de `pe.edu.nova.java.libs:nova-api-standard:1.0.0`.
   - Tests unitarios con JUnit 5 (mismo approach que Quarkus: sin `@MicronautTest`
     porque el plugin `io.micronaut.application` NO se aplica en el repo del module).
2. **Publicar a GitHub Packages** (1.0.0) reusando los workflows de `nova-devops`.
3. **Modificar `examples/demo-micronaut/`** para consumir el module:
   - Agregar dep al `build.gradle.kts`.
   - Agregar un controller demo que use `ApiResponse`.
   - Validar que `./gradlew run` arriba y el endpoint devuelve JSON `ApiResponse<T>`.
4. **Validar end-to-end:**
   - `./gradlew build` debe pasar en el repo del module.
   - `./gradlew build` debe pasar en `examples/demo-micronaut/` modificado.
   - El endpoint demo debe responder JSON envuelto en `ApiResponse<T>` con headers
     correctos.
5. **Documentar resultado** en este doc (§10.10).

### 10.9.2 Fase 1 (2-3 semanas) — starter pack

Si Fase 0 es positiva:

1. **Crear `nova-java-micronaut-starter`** (mega-module).
2. **Documentar `micronaut-cli.yml` template** que los equipos pueden copiar.
3. **Publicar guía "Cómo iniciar un servicio Micronaut en Nova"** en docs.

### 10.9.3 Fase 2 (3-4 semanas) — custom features

Solo si se justifica por volumen de proyectos generados:

1. Fork de `micronaut-starter` a `ahincho/micronaut-starter-nova`.
2. Crear 3-4 custom features: `nova-api-standard-micronaut-module`,
   `nova-bus-micronaut-module`, `nova-ddd-utils-micronaut-module`,
   `nova-tracing-micronaut-module`.
3. Hostear una instancia propia de Micronaut Launch en
   `https://launch.nova.edu.pe/` (opcional, puede ser costoso).

### 10.9.4 Fase 3+ (futuro)

- Más modules Nova paralelos a los de Quarkus y Spring Boot.
- Considerar **Helidon** como cuarto framework si el equipo lo justifica (Oracle, AOT,
  MicroProfile).

---

## 10.10 Riesgos y decisiones abiertas

### 10.10.1 Riesgos técnicos

| Riesgo                                          | Severidad | Mitigación                              |
|-------------------------------------------------|-----------|-----------------------------------------|
| Java 25 support en Micronaut 5.0.4              | Bajo      | Ya validado: build con JDK 25 OK        |
| Diferencias en DI lifecycle vs Quarkus          | Medio     | Tests exhaustivos en Fase 0             |
| Reactive model distinto (Reactor vs Mutiny)     | Medio     | Nova usa imperative API → no impacto    |
| Native image con libs Nova                      | Alto      | Test Fase 0 con `nativeCompile`         |
| GitHub Packages auth para cross-repo deps       | Bajo      | Mismo patrón que Quarkus (doc 07)       |
| Tiempo del equipo para 3er framework           | Alto      | **Solo si hay demanda real**            |

### 10.10.2 Decisiones abiertas

1. **¿Vale la pena el esfuerzo vs. consolidar Quarkus?**
   - Si Nova tiene 5+ servicios, sí (diversificación).
   - Si tiene <5 servicios, no (mejor profundizar Quarkus primero).
2. **¿Custom features en fork, o post-procesar ZIP?**
   - Custom features: mejor UX, más trabajo inicial.
   - Post-procesar: más simple, menos pulido. **Recomendado para Fase 0.**
3. **¿Migrar servicios Spring Boot existentes a Micronaut?**
   - **No recomendado.** Costo/beneficio negativo salvo casos específicos (cold start).
4. **¿Naming convention `nova-X-micronaut-module` o `nova-micronaut-X`?**
   - **Decidido (§10.7.1):** `nova-X-micronaut-module`. El sufijo `module` refleja
     la terminología oficial de Micronaut, paralela a `starter` (Spring) y
     `extension` (Quarkus).
5. **¿Helidon como cuarto framework?**
   - Postergar. Solo si la organización tiene alineación con Oracle.

### 10.10.3 Veredicto

**Recomendación: SÍ adoptar Micronaut en Fase 0 como framework complementario, pero
solo si se cumplen al menos 2 de estas condiciones:**

- [ ] Hay al menos 1 caso de uso donde el startup time importa decisivamente (Lambda,
      edge, CLI server).
- [ ] El equipo tiene bandwidth para mantener 3 frameworks en simultáneo.
- [ ] Se va a hacer un fork del starter (Fase 2) para Nova features propias.

**Si no se cumplen**, mantener Nova en Spring Boot + Quarkus solamente y cerrar este
documento como referencia futura.

---

## 10.11 CI/CD reuse review (análisis de workflows reusables)

Nova tiene centralizados los workflows de CI/CD en
[`ahincho/nova-devops`](https://github.com/ahincho/nova-devops/tree/main/.github/workflows).
El **objetivo es reusar al máximo** estos workflows para el module Micronaut, evitando
duplicar configuración.

### 10.11.1 Inventario de workflows reusables disponibles

| Workflow reutilizable                          | Propósito                              | Default Java | Inputs principales                              |
|------------------------------------------------|----------------------------------------|:------------:|-------------------------------------------------|
| `reusable-build-gradle.yml`                    | Build + tests + checkstyle + javadoc   | 25           | `java-version`                                  |
| `reusable-sonarcloud-gradle.yml`               | Análisis SonarCloud con JaCoCo         | 25           | `sonar-org`, `sonar-project-key`, `SONAR_TOKEN` |
| `reusable-build-matrix.yml`                    | Matrix multi-Java (default 21 + 25)    | 21 / 25      | `java-versions`, `build-tool`, `fail-fast`      |
| `reusable-owasp-check.yml`                     | OWASP dependency-check                 | 25           | `fail-on-cvss`, `NVD_API_KEY`, suppression-file |
| `reusable-sbom.yml`                            | CycloneDX SBOM (json/xml)              | 25           | `sbom-format`, `attach-to-release`              |
| `reusable-release-please.yml`                  | release-please con conventional commits| 20 (Node)    | `release-type`, `path`, `config-file`           |
| `reusable-release-publish.yml`                 | publish tras release-please (alternativo) | 25         | -                                               |
| `reusable-publish-gradle.yml`                  | Publish a GitHub Packages / Maven Central | 25         | registry + token                                |
| `publish-on-tag.yml` (no reusable)             | Publica al tag `vX.Y.Z`                | 25           | -                                               |

### 10.11.2 Plan de reuso para `nova-java-api-standard-micronaut-module`

Mismo patrón que `nova-java-api-standard-quarkus-extension`:

```yaml
# .github/workflows/ci.yml
jobs:
  build:   { uses: ahincho/nova-devops/.github/workflows/reusable-build-gradle.yml@main, secrets: inherit }
  sonar:   { uses: ahincho/nova-devops/.github/workflows/reusable-sonarcloud-gradle.yml@main, with: { ... }, secrets: inherit }
  matrix:  { uses: ahincho/nova-devops/.github/workflows/reusable-build-matrix.yml@main, with: { build-tool: gradle }, secrets: inherit }
  owasp:   { uses: ahincho/nova-devops/.github/workflows/reusable-owasp-check.yml@main, with: { build-tool: gradle }, secrets: inherit }
  sbom:    { uses: ahincho/nova-devops/.github/workflows/reusable-sbom.yml@main, with: { build-tool: gradle }, permissions: { contents: write }, secrets: inherit }
```

```yaml
# .github/workflows/release-please.yml (idéntico a Quarkus)
on: { push: { branches: [main] } }
permissions: { contents: write, pull-requests: write }
jobs:
  release-please:
    uses: ahincho/nova-devops/.github/workflows/reusable-release-please.yml@main
    with:
      release-type: java
      config-file: .release-please-config.json
    secrets: { GH_TOKEN: ${{ secrets.NOVA_RELEASE_PAT || secrets.GITHUB_TOKEN }} }
```

```yaml
# .github/workflows/publish-on-tag.yml (idéntico a Quarkus, mismo template)
on: { push: { tags: ["v[0-9]+.[0-9]+.[0-9]+"] } }
jobs:
  publish:
    permissions: { contents: read, packages: write }
    steps: ...
```

### 10.11.3 Items críticos a VERIFICAR durante Fase 0

Estos son los puntos donde el module Micronaut podría divergir del flow conocido de
Quarkus. **El agente implementador debe validar cada uno:**

| # | Punto crítico                                                                                                              | Acción de verificación                                                                                              | Riesgo si no se valida                                                          |
|---|----------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| 1 | `reusable-build-gradle.yml` ejecuta `./gradlew checkstyleMain` y `./gradlew javadoc`. ¿Nuestro `build.gradle.kts` Micronaut los expone? | Correr `./gradlew tasks --all` y confirmar que existen. Si no, ajustar el plugin o excluir del workflow.          | Build falla en CI silenciosamente                                                |
| 2 | `reusable-sbom.yml` requiere `id("org.cyclonedx.bom") version "3.2.4"` aplicado en `build.gradle.kts`.                  | Agregar el plugin al `build.gradle.kts` del module (igual que se haría en Quarkus si se quisiera SBOM).            | SBOM step falla y rompe CI                                                      |
| 3 | `reusable-build-matrix.yml` tiene `min-java-version: '21'`. ¿Micronaut 5.0.4 compila con JDK 21?                          | Compilar localmente con JDK 21: `JAVA_HOME=/path/jdk21 ./gradlew build`. Si falla, ajustar matrix a solo `[25]`.   | Matrix job falla para JDK 21                                                     |
| 4 | `publish-on-tag.yml` usa `sed -i "s/^version=.*/version=${VERSION}/" gradle.properties`. ¿Nuestro `gradle.properties` tiene `version=1.0.0`? | Verificar formato. Si está OK, no tocar.                                                                            | Tag no actualiza `version` correctamente                                        |
| 5 | `reusable-owasp-check.yml` por defecto falla con CVSS >= 7. ¿Alguna dep transitiva de Micronaut tiene CVE >= 7 conocido?  | Correr `./gradlew dependencyCheckAnalyze` localmente y revisar reporte.                                             | OWASP job falla en CI                                                           |
| 6 | `reusable-sonarcloud-gradle.yml` ejecuta `./gradlew build jacocoTestReport`. ¿El module tiene tests JaCoCo?               | Verificar que `testImplementation("org.junit.jupiter:junit-jupiter")` está y `jacoco` plugin aplicado.             | SonarCloud falla por no encontrar reporte                                       |
| 7 | ¿El `package.json` con commitlint + lefthook funciona en Windows? (paridad con repo Quarkus ya validado)                  | Correr `npm install && npx lefthook run pre-commit` localmente.                                                    | Commits sin lint en CI                                                          |
| 8 | `.release-please-config.json` debe tener `package-name: pe.edu.nova.java.starters:nova-api-standard-micronaut-module`    | Editar y comparar con el del repo Quarkus.                                                                          | Release-please crea tag con nombre incorrecto                                    |
| 9 | ¿`reusable-publish-gradle.yml` o `publish-on-tag.yml` necesita configuración especial para Micronaut artifacts?          | Comparar con la config del repo Quarkus (que ya funciona). Si idéntica, OK.                                        | Publish falla silenciosamente                                                    |

### 10.11.4 Permisos por job (lección aprendida del repo Quarkus)

Cuando un reusable workflow declara `permissions:` a nivel de job, **el caller
DEBE otorgarlos explícitamente** o GitHub falla con error
`requesting 'contents: write' but is only allowed 'contents: read'`.

Para Fase 0, esto significa que `ci.yml` debe declarar permissions en el job `sbom`
(ya validado en repo Quarkus commit `71bfe42`):

```yaml
sbom:
  if: github.event_name == 'pull_request'
  uses: ahincho/nova-devops/.github/workflows/reusable-sbom.yml@main
  with: { build-tool: gradle }
  permissions:
    contents: write      # requerido por reusable-sbom.yml job
  secrets: inherit
```

### 10.11.5 Secrets requeridos (idénticos a Quarkus)

Reusar la plantilla `.github/SECRETS_SETUP.md` ya escrita para el repo Quarkus. Los
secrets a configurar son los mismos:

| Secret                       | Tipo      | Scope                                  | Estado            |
|------------------------------|-----------|----------------------------------------|-------------------|
| `NOVA_RELEASE_PAT`           | PAT       | `contents: R/W` + `pull-requests: R/W` | **REQUERIDO**     |
| `NOVA_PACKAGES_READ_TOKEN`   | PAT       | `read:packages`                        | Opcional (recomendado) |
| `NVD_API_KEY`                | API key   | NIST NVD                                | Opcional (velocidad)   |
| `NOVA_PACKAGE_VISIBILITY`    | Variable  | `public` / `private`                   | Opcional (default `public`) |

### 10.11.6 Diferencias esperadas vs. el repo Quarkus

A priori **ninguna diferencia significativa** — el module se compila y testea igual
que la extension Quarkus. La única diferencia observable:

- El **artifactId** en `gradle.properties` será `nova-api-standard-micronaut-module`
  en vez de `nova-api-standard-quarkus-extension`.
- El `package-name` en `.release-please-config.json` será
  `pe.edu.nova.java.starters:nova-api-standard-micronaut-module`.
- El **Java package raíz** del código fuente será
  `pe.edu.nova.java.starters.api.standard.micronaut` en vez de
  `pe.edu.nova.java.starters.api.standard.quarkus`.
- Las **dependencias de runtime** cambian: `quarkus-rest + quarkus-arc + quarkus-jackson`
  → `micronaut-core + micronaut-runtime + micronaut-serde-jackson` (+ annotation
  processor `micronaut-serde-processor`).

### 10.11.7 Veredicto CI/CD

**Se puede reusar 100% de los workflows de `nova-devops` sin modificaciones.** El
único trabajo es copiar los archivos `.github/workflows/*.yml` del repo Quarkus,
ajustar `package-name` y `artifactId` en `.release-please-config.json`, y declarar
`permissions: contents: write` en el job `sbom` (fix ya conocido).

---

## 10.12 Verification checklist durante construcción

Esta checklist la ejecuta el agente implementador **durante la Fase 0**. Cada item
tiene una respuesta binaria (✅/❌) o un valor numérico esperado.

### 10.12.1 Pre-implementación (antes de escribir código)

- [ ] Confirmar que `pe.edu.nova.java.libs:nova-api-standard:1.0.0` está publicado en
      Maven Local O que `GITHUB_TOKEN` está disponible (sino el `compileJava` falla
      con 401).
- [ ] Confirmar versión exacta de Micronaut Platform BOM a usar: `5.0.4`.
- [ ] Confirmar versión de `micronaut-core` a importar manualmente (no del BOM): ej.
      `5.0.4`.
- [ ] Verificar que el repo Quarkus
      (`ahincho/nova-java-api-standard-quarkus-extension`) está creado y sirve como
      referencia estructural.
- [ ] Verificar que `examples/demo-micronaut/` compila localmente:
      `cd examples/demo-micronaut && ./gradlew build`.
- [ ] Releer §10.11 (CI/CD reuse review) y entender qué puntos validar.

### 10.12.2 Decisiones de implementación a tomar en el momento

Estos puntos NO se deciden en el doc — se deciden cuando se está escribiendo el
código. Se listan como guía para el agente:

| # | Decisión                                                                                  | Recomendación inicial                                          | Trade-off                                                  |
|---|-------------------------------------------------------------------------------------------|----------------------------------------------------------------|------------------------------------------------------------|
| 1 | ¿Aplicar `id("io.micronaut.application")` al `build.gradle.kts` del module?              | **NO**, igual que Quarkus. Solo `java-library` puro.           | Si se aplica, `@MicronautTest` se vuelve posible localmente. |
| 2 | ¿Usar `micronaut-jackson-databind` o `micronaut-serde-jackson`?                          | **`micronaut-serde-jackson`** (es lo que usa el baseline oficial de Launch, validado en `examples/demo-micronaut/`). | `micronaut-jackson-databind` directo es más familiar pero ya está deprecado por Micronaut como approach oficial. |
| 3 | ¿Cómo declarar beans? ¿`@Singleton` o `@Bean` + `@Factory`?                              | **`@Singleton`** directo para clases simples.                 | `@Factory` solo si se necesita lógica de construcción.      |
| 4 | ¿Anotación del ExceptionHandler? ¿`@Produces` o sin anotación?                           | **Sin anotación** (Micronaut detecta `ExceptionHandler<T,HttpResponse>` por generics). | `@Produces` solo si hay múltiples handlers para el mismo tipo. |
| 5 | ¿Tests con `@MicronautTest` o JUnit puro?                                                | **JUnit puro** (paridad con Quarkus, no aplica plugin).        | Si se quiere `@MicronautTest`, hay que aplicar el plugin.   |
| 6 | ¿Plugin CycloneDX para SBOM?                                                              | **Sí, aplicar.** Mismo patrón que se decida para Quarkus.      | Si NO se aplica, SBOM job falla.                            |

### 10.12.3 Criterios de aceptación (Definition of Done — Fase 0)

El module se considera "listo para Fase 1" cuando se cumplen TODOS estos:

- [ ] Repo `ahincho/nova-java-api-standard-micronaut-module` creado y público.
- [ ] `build.gradle.kts` configurado con: `java-library` plugin,
      `mavenCentral()` + GitHub Packages condicional, deps runtime Micronaut
      (incluyendo `micronaut-serde-jackson` + processor) +
      `nova-api-standard:1.0.0`.
- [ ] `gradle.properties` con `version=1.0.0`, `group=pe.edu.nova.java.starters`.
- [ ] `gradle/wrapper/` con Gradle 9.5.1.
- [ ] `.release-please-config.json` con `package-name:
      pe.edu.nova.java.starters:nova-api-standard-micronaut-module`,
      `component: nova-api-standard-micronaut-module`.
- [ ] `.release-please-manifest.json` con `".": "1.0.0"`.
- [ ] `.github/workflows/ci.yml` con los 5 jobs (build, sonar, matrix, owasp, sbom)
      reusando `nova-devops`. `sbom` con `permissions: contents: write`.
- [ ] `.github/workflows/release-please.yml` y `.github/workflows/publish-on-tag.yml`
      idénticos al repo Quarkus (ajustando solo package-name).
- [ ] `.github/SECRETS_SETUP.md` presente.
- [ ] `README.md` con: descripción del module, naming convention,
      dependencia de `nova-api-standard`, ejemplo de uso, sección testing strategy.
- [ ] `CONTRIBUTING.md` presente.
- [ ] `config/checkstyle/checkstyle.xml` presente.
- [ ] `package.json` + `lefthook.yml` + `commitlint.config.js` presentes.
- [ ] Clase `ApiExceptionMapper.java` en package
      `pe.edu.nova.java.starters.api.standard.micronaut.mapper` con
      `@Singleton implements ExceptionHandler<Exception, HttpResponse>`.
- [ ] Clase `ApiObjectMapperCustomizer.java` en package
      `pe.edu.nova.java.starters.api.standard.micronaut.jackson` con
      `implements io.micronaut.jackson.ObjectMapperCustomizer`.
- [ ] Tests unitarios JUnit 5: mínimo 7 (cubrir IllegalArgumentException,
      SecurityException, RuntimeException + nulls + edge cases).
- [ ] `./gradlew compileJava` pasa localmente.
- [ ] `./gradlew test` pasa localmente (todos los tests ✅).
- [ ] `./gradlew build` pasa localmente (compile + test + jar + check + build).
- [ ] Commit inicial + push a `main` ejecutados.
- [ ] Workflows CI disparados (pueden fallar por falta de secrets — eso es esperado).
- [ ] Issue en el repo con checklist de secrets a configurar.
- [ ] **Proyecto demo end-to-end** (`examples/demo-micronaut/` modificado): el
      baseline real del repo, modificado para consumir el module, `./gradlew run`
      arriba, endpoint devuelve JSON `ApiResponse<T>` correctamente.

### 10.12.4 Validación end-to-end (smoke test post-release)

Una vez el module esté publicado a GitHub Packages (tras configurar `NOVA_RELEASE_PAT`
y merge del primer PR de release):

- [ ] En un proyecto Micronaut nuevo (o en `examples/demo-micronaut/`), confirmar que
      la dep
      `implementation("pe.edu.nova.java.starters:nova-api-standard-micronaut-module:1.0.0")`
      resuelve correctamente.
- [ ] Agregar un controller de prueba que lance una `IllegalArgumentException`.
- [ ] Verificar que la respuesta es JSON con formato `ApiResponse` (no el default de
      Micronaut `Problem` JSON).
- [ ] Verificar que `LocalDateTime` se serializa como ISO-8601 (no como timestamp).
- [ ] Verificar logs: que el customizer se invocó al arranque.

---

## 10.13 Apéndice: comandos útiles

### 10.13.1 Trabajar con `examples/demo-micronaut/` (baseline real)

```bash
cd examples/demo-micronaut
./gradlew build         # compilar + test
./gradlew test          # solo tests
./gradlew run           # arrancar app
```

### 10.13.2 Generar proyecto demo desde cero (sintético)

```bash
# Con features recomendadas
curl -L -o demo.zip \
  "https://launch.micronaut.io/create/default/com.example.demo?lang=JAVA&build=GRADLE&test=JUNIT&javaVersion=JDK_25&type=DEFAULT&features=validation,openapi,swagger-ui,problem-json,security-jwt,data-jdbc,postgres,flyway,redis-lettuce,cache-caffeine,kafka,tracing-opentelemetry-exporter-otlp,micrometer-prometheus,management,retry,testcontainers"

unzip demo.zip -d demo && cd demo
./gradlew build
./gradlew test
./gradlew run
```

### 10.13.3 Listar features disponibles

```bash
# Todas las features
curl -L "https://launch.micronaut.io/application-types/default/features" | jq

# Solo nombres
curl -L "https://launch.micronaut.io/application-types/default/features" \
  | jq -r '.features[].name'
```

### 10.13.4 Ver diff por feature

```bash
curl -L "https://launch.micronaut.io/diff/default/feature/security-jwt" \
  -H "Accept: text/plain"
```

### 10.13.5 Regenerar desde micronaut-cli.yml

```bash
# Asumiendo CLI instalado
mn create-app --reload demo.zip
```

### 10.13.6 Generar para gRPC

```bash
curl -L -o grpc-demo.zip \
  "https://launch.micronaut.io/create/grpc/com.example.grpc?lang=JAVA&build=GRADLE&test=JUNIT&javaVersion=JDK_25&type=GRPC&features=..."
```

---

## 10.14 Referencias

- [Micronaut Launch](https://micronaut.io/launch) — UI oficial.
- [Micronaut Starter GitHub](https://github.com/micronaut-projects/micronaut-starter) —
  código fuente del scaffolding.
- [Micronaut Documentation 5.0.4](https://docs.micronaut.io/5.0.4/guide/index.html).
- [Spring Initializr](https://start.spring.io) — comparación.
- [Quarkus code.quarkus.io](https://code.quarkus.io) — comparación.
- Doc 07 `07-quarkus-analisis-adopcion.md` — estrategia Quarkus paralela.
- Doc 08 `08-ddd-utils-y-bus-multi-framework.md` — bus multi-framework.
- Doc 09 `09-scaffolding-quarkus-archetypes-y-codestarts.md` — scaffolding Quarkus.
- `examples/demo-micronaut/` — baseline real generado vía Launch (Gradle Kotlin DSL,
  JDK 25, defaults).