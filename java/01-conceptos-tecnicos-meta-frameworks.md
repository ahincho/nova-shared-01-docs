# Conceptos Tecnicos del Desarrollo de Meta-Frameworks en Java

## 1. Que es un Meta-Framework

Un meta-framework es una **capa de abstraccion construida sobre uno o mas frameworks existentes** que tiene como objetivo:

- **Estandarizar** patrones de desarrollo dentro de una organizacion.
- **Encapsular decisiones tecnicas** (versiones, configuraciones, convenciones) que de otro modo cada equipo tomaria de forma independiente.
- **Reducir el boilerplate** que los desarrolladores deben escribir al iniciar o mantener proyectos.
- **Garantizar coherencia** entre microservicios en areas como observabilidad, manejo de errores, seguridad y enmascaramiento de datos.

Un meta-framework **no reemplaza** al framework base (Spring Boot, Quarkus, Micronaut), sino que lo **extiende y configura** de manera opinada para el contexto empresarial.

### Ejemplos en la industria

| Meta-Framework | Framework Base | Organizacion |
|----------------|---------------|--------------|
| Netflix OSS (Zuul, Eureka, Hystrix) | Spring Boot | Netflix |
| Spring Cloud | Spring Boot | VMware/Pivotal |
| Quarkus Extensions | Quarkus | Red Hat |
| Micronaut Platform | Micronaut | Oracle/OCI |
| Helidon | Netty / CDI | Oracle |
| Backstage (plugins backend) | Express/NestJS | Spotify |

---

## 2. Arquitectura por Niveles (Layers)

Un meta-framework bien estructurado se organiza en **5 niveles jerarquicos**, donde cada nivel depende de los inferiores pero nunca de los superiores:

```
Nivel 5: Build Tooling (Plugins Gradle/Maven, Archetypes, CLI)
   |
Nivel 4: BOMs + Parents (Gestion de versiones y herencia)
   |
Nivel 3: Meta-Framework Starter (Agregador principal)
   |
Nivel 2: Starters / Conectores (Integracion framework-especifica)
   |
Nivel 1: Librerias Puras (Logica de negocio reutilizable, sin framework)
```

### Nivel 1: Librerias Puras (Pure Libraries)

**Proposito:** Codigo Java puro, sin dependencia de ningun framework. Reutilizable en cualquier contexto.

**Caracteristicas:**
- Zero o minimas dependencias externas.
- Testeables con JUnit estandar sin contenedor.
- API publica bien definida (clases de entrada, records, builders).
- Patron comun: `Engine` + `Config` + `Result` + `Exception hierarchy`.
- Publicables como JARs independientes.

**Patrones de diseno frecuentes:**
- **Strategy Pattern** - Para comportamiento intercambiable (ej: estrategias de enmascaramiento por pais).
- **Builder Pattern** - Para configuracion inmutable con validacion.
- **Registry Pattern** - Para descubrimiento y resolucion de implementaciones.
- **Result Pattern** - Para retornar resultados ricos en lugar de lanzar excepciones.

**Ejemplo conceptual:**
```
mask-utils/
  MaskEngine.java          <- Punto de entrada estatico + Builder
  MaskConfig.java           <- Configuracion inmutable
  MaskResult.java           <- Resultado con metadata
  MaskStrategy.java         <- Interface funcional
  strategies/               <- Implementaciones por tipo y pais
  exceptions/               <- Jerarquia de excepciones
```

### Nivel 2: Starters / Conectores (Framework-Specific Adapters)

**Proposito:** Conectar las librerias puras del Nivel 1 con un framework especifico, proporcionando auto-configuracion y convencion sobre configuracion.

**Caracteristicas por framework:**

| Aspecto | Spring Boot | Quarkus | Micronaut |
|---------|-------------|---------|-----------|
| Auto-configuracion | `@AutoConfiguration` + `AutoConfiguration.imports` | `@BuildStep` en extensiones | `@Factory` + `@Bean` |
| Propiedades | `@ConfigurationProperties` | `@ConfigMapping` | `@ConfigurationProperties` |
| Condiciones | `@ConditionalOnClass`, `@ConditionalOnProperty` | Build-time conditions | `@Requires` |
| Registro | `META-INF/spring/` | `META-INF/quarkus-extension.yaml` | `META-INF/services/` |
| Scope | Runtime | Build-time (GraalVM friendly) | Compile-time (AOT) |

**Patron de un Starter Spring Boot:**
```
mask-utils-spring-boot-starter/
  autoconfigure/
    MaskAutoConfiguration.java          <- @AutoConfiguration con @ConditionalOn*
  config/
    MaskProperties.java                  <- @ConfigurationProperties
  jackson/
    MaskedFieldSerializer.java           <- Integracion con Jackson
  web/
    MaskResponseBodyAdvice.java          <- Integracion con Spring MVC
  actuator/
    MaskHealthIndicator.java             <- Integracion con Actuator
  META-INF/
    spring/
      ...AutoConfiguration.imports       <- Registro de auto-configuraciones
```

**Patron de una Extension Quarkus (equivalente):**
```
mask-utils-quarkus-extension/
  deployment/                            <- Modulo de build-time
    MaskProcessor.java                   <- @BuildStep para registro de beans
  runtime/                               <- Modulo de runtime
    MaskRecorder.java                    <- @Recorder para instanciacion
    MaskConfig.java                      <- @ConfigMapping
```

**Patron de un Modulo Micronaut (equivalente):**
```
mask-utils-micronaut/
  MaskFactory.java                       <- @Factory con @Bean
  MaskConfiguration.java                 <- @ConfigurationProperties
  MaskFilter.java                        <- @Filter para HTTP
```

### Nivel 3: Meta-Framework Starter (Agregador Principal)

**Proposito:** Un unico artefacto que los proyectos finales incluyen para obtener toda la funcionalidad del meta-framework. Actua como **facade** de los starters del Nivel 2.

**Caracteristicas:**
- Dependencia transitiva hacia todos los starters del Nivel 2.
- Proporciona la "experiencia de desarrollador" unificada.
- Define anotaciones de alto nivel (ej: `@NovaSpringBootApplication`).
- Puede incluir validaciones de entorno (version de Java, version del framework).
- Opcionalmente define un `main()` wrapper para bootstrapping customizado.

**Ejemplo:**
```xml
<!-- El proyecto final solo necesita esto: -->
<dependency>
    <groupId>pe.edu.nova.java.starters</groupId>
    <artifactId>nova-spring-boot-starter</artifactId>
</dependency>
<!-- Esto trae transitivamente: mask-utils, api-standard, observability, etc. -->
```

### Nivel 4: BOMs + Parents (Gestion de Versiones)

**Proposito:** Centralizar la gestion de versiones y la configuracion de build heredable.

#### BOM (Bill of Materials)

Un BOM es un POM con `<packaging>pom</packaging>` que solo contiene `<dependencyManagement>`. Los proyectos lo importan con `scope=import` para recibir versiones coordinadas.

**Estructura multi-BOM (para soporte multi-framework):**
```
nova-bom/                     <- BOM raiz (libs puras)
  pom.xml                                <- dependencyManagement de Nivel 1
  nova-spring-boot-bom/       <- BOM para Spring Boot
    pom.xml                              <- importa spring-boot-dependencies + starters Nivel 2
  nova-quarkus-bom/           <- BOM para Quarkus
    pom.xml                              <- importa quarkus-bom + extensiones Nivel 2
  nova-micronaut-bom/         <- BOM para Micronaut
    pom.xml                              <- importa micronaut-bom + modulos Nivel 2
```

**Diferencia clave BOM vs Parent:**

| Aspecto | BOM | Parent |
|---------|-----|--------|
| Herencia | No (se importa) | Si (`<parent>`) |
| Que controla | Solo versiones de dependencias | Versiones + plugins + propiedades + repositorios |
| Uso | `<dependencyManagement> scope=import` | `<parent>` |
| Un proyecto puede tener multiples | Si (N BOMs importados) | No (solo 1 parent) |
| Ideal para | Librerias que seran consumidas | Aplicaciones finales |

#### Parent POM

Un Parent POM es heredado via `<parent>` y proporciona:
- Versiones de plugins pre-configuradas.
- Configuracion de compilacion (Java version, compiler flags).
- Dependencias comunes (test frameworks).
- Repositorios.
- Profiles.

### Nivel 5: Build Tooling (Plugins, Archetypes, CLI)

**Proposito:** Automatizar la creacion y configuracion de proyectos.

**Componentes:**

1. **Gradle Plugin** - `Plugin<Project>` que aplica plugins base, configura repositorios, agrega dependencias del meta-framework y configura toolchains.

2. **Maven Archetype** - Template para `mvn archetype:generate` que scaffoldea un proyecto completo con la estructura y dependencias del meta-framework.

3. **CLI (avanzado)** - Herramienta de linea de comandos para generar proyectos, modulos, controladores, etc. Similar a `quarkus create app` o `spring init`.

---

## 3. Conceptos Transversales

### 3.1. Soporte Multi-Framework

El reto principal de un meta-framework multi-framework es mantener la **logica de negocio en el Nivel 1** y solo tener codigo framework-especifico en el Nivel 2.

```
                          Nivel 1 (Puro)
                              |
              +---------------+---------------+
              |               |               |
        Spring Boot      Quarkus         Micronaut
        (Nivel 2)        (Nivel 2)       (Nivel 2)
              |               |               |
        SB Starter      QK Extension     MN Module
        (Nivel 3)        (Nivel 3)       (Nivel 3)
              |               |               |
        SB BOM+Parent   QK BOM           MN BOM
        (Nivel 4)        (Nivel 4)       (Nivel 4)
              |               |               |
        SB Gradle       QK Maven         MN Gradle
        Plugin          Plugin           Plugin
        (Nivel 5)        (Nivel 5)       (Nivel 5)
```

### 3.2. Versionado Coordinado

Todos los artefactos del meta-framework deben publicarse con versiones coordinadas. Un BOM garantiza que la version `1.0.0` de `mask-utils` es compatible con la version `1.0.0` de `mask-utils-spring-boot-starter`.

**Estrategia recomendada:**
- Semantic Versioning (SemVer): `MAJOR.MINOR.PATCH`.
- Todos los modulos avanzan juntos (release train) o independientemente con compatibility matrix.
- CI/CD automatiza el bump de version basado en labels de PR (`major`, `minor`, `patch`).

### 3.3. Dependencias Transitivas vs Opcionales

| Tipo | Cuando usar | Ejemplo |
|------|------------|---------|
| `compile` / `api` | El consumidor NECESITA la dependencia en su classpath | `mask-utils` desde `mask-utils-spring-boot-starter` |
| `compileOnly` / `provided` | Solo necesaria en compilacion, el runtime la provee | `spring-boot-autoconfigure` en un starter |
| `runtimeOnly` | Solo necesaria en ejecucion | Drivers JDBC |
| `optional` / `compileOnly` | Habilitar funcionalidad si el consumidor ya tiene la dep | Soporte de Jackson si ya esta en el classpath |

### 3.4. Auto-Configuracion Condicional

La auto-configuracion debe ser **no invasiva**: solo se activa si las condiciones se cumplen.

**Spring Boot:**
```java
@AutoConfiguration
@ConditionalOnClass(MaskEngine.class)           // Solo si mask-utils esta en classpath
@ConditionalOnProperty(
    prefix = "nova.mask",
    name = "enabled",
    havingValue = "true",
    matchIfMissing = true                        // Habilitado por defecto
)
public class MaskAutoConfiguration { ... }
```

### 3.5. Observabilidad como Ciudadano de Primera Clase

Un meta-framework empresarial debe integrar observabilidad de forma transparente:

- **Metricas** - Four Golden Signals (latencia, trafico, errores, saturacion) via Micrometer.
- **Trazas** - Distributed tracing via OpenTelemetry con propagacion automatica.
- **Logs** - Correlacion de logs con trace/span IDs via MDC.
- **Profiles** - Integracion con Pyroscope para continuous profiling.

### 3.6. Compatibilidad con GraalVM Native Image

Para soportar Quarkus y Micronaut en modo nativo, las librerias del Nivel 1 deben evitar:
- Reflection sin registrar (usar `reflect-config.json` o anotaciones de registro).
- Dynamic proxies sin declarar.
- Classpath scanning en runtime.
- Serialization sin registrar.

---

## 4. Build Systems: Maven vs Gradle

Un meta-framework debe soportar ambos build systems porque los equipos de la organizacion pueden usar cualquiera.

| Aspecto | Maven | Gradle |
|---------|-------|--------|
| BOM | `<dependencyManagement>` con `scope=import` | `platform()` o `enforcedPlatform()` |
| Parent | `<parent>` | No existe equivalente directo; se usa un plugin custom |
| Plugin | Maven Plugin (Mojo) | Gradle Plugin (`Plugin<Project>`) |
| Archetype | `maven-archetype-plugin` | No hay equivalente directo; se usa `init` tasks |
| Publicacion | `maven-deploy-plugin` o `nexus-staging` | `maven-publish` plugin |
| Cache | Local (`~/.m2`) | Local + build cache + configuration cache |
| Reproducibilidad | `mvn verify` | `--configuration-cache`, lockfiles |

### Equivalencias de Configuracion

**Maven (via Parent POM):**
```xml
<parent>
    <groupId>pe.edu.nova.java</groupId>
    <artifactId>nova-spring-boot-parent</artifactId>
    <version>1.0.0</version>
</parent>
```

**Gradle (via Plugin custom):**
```kotlin
plugins {
    id("pe.edu.nova.spring-boot") version "1.0.0"
}
```

Ambos producen el mismo resultado: Java 25 toolchain, dependencias del meta-framework, y configuracion de plugins de build.

---

## 5. Pipeline CI/CD para Meta-Frameworks

El CI/CD de un meta-framework es mas complejo que el de una aplicacion porque debe:

1. **Construir y testear** todos los modulos en orden de dependencia.
2. **Publicar artefactos** en un repositorio de paquetes (Maven Central, GitHub Packages, Nexus, Artifactory).
3. **Versionar coordinadamente** todos los artefactos.
4. **Validar compatibilidad** ejecutando los ejemplos contra las nuevas versiones.

**Workflows reutilizables necesarios:**

| Workflow | Proposito |
|----------|-----------|
| `reusable-build-maven.yml` | Compilar + test + checkstyle + javadoc (Maven) |
| `reusable-build-gradle.yml` | Compilar + test + checkstyle + javadoc (Gradle) |
| `reusable-sonarcloud-maven.yml` | Analisis de calidad + cobertura (Maven) |
| `reusable-sonarcloud-gradle.yml` | Analisis de calidad + cobertura (Gradle) |
| `reusable-version-bump-maven.yml` | Bump de version semantico (Maven) |
| `reusable-version-bump-gradle.yml` | Bump de version semantico (Gradle) |
| `reusable-publish-maven.yml` | Publicar a GitHub Packages (Maven) |
| `reusable-publish-gradle.yml` | Publicar a GitHub Packages (Gradle) |

---

## 6. Anti-Patrones a Evitar

| Anti-Patron | Problema | Solucion |
|-------------|----------|----------|
| Logica de negocio en starters | Acoplamiento al framework | Mover a libreria pura (Nivel 1) |
| Starter monolitico | Todo o nada, dificil de actualizar | Starters modulares y composables |
| Versiones no coordinadas | Incompatibilidades entre modulos | BOM centralizado + release train |
| Auto-configuracion sin condiciones | Conflictos con la configuracion del usuario | `@ConditionalOn*` en toda auto-config |
| Reflection excesiva | Incompatible con GraalVM, lento | Compile-time processing donde sea posible |
| Forzar una unica version de Java | Limita adopcion | Compilar con source/target compatible, testear con multiples JDKs |
| Ignorar backward compatibility | Rompe proyectos existentes | Deprecation cycle, migration guides |
| Sin documentacion de propiedades | Los usuarios no saben que configurar | `additional-spring-configuration-metadata.json` |

---

## 7. Referencias y Recursos

- [Spring Boot Auto-configuration](https://docs.spring.io/spring-boot/reference/using/auto-configuration.html)
- [Creating Your Own Starter (Spring Boot)](https://docs.spring.io/spring-boot/reference/features/developing-auto-configuration.html)
- [Quarkus Extension Guide](https://quarkus.io/guides/writing-extensions)
- [Micronaut Module Guide](https://docs.micronaut.io/latest/guide/)
- [Maven BOM Best Practices](https://maven.apache.org/guides/introduction/introduction-to-dependency-mechanism.html)
- [Gradle Plugin Development](https://docs.gradle.org/current/userguide/custom_plugins.html)
- [OpenTelemetry Java SDK](https://opentelemetry.io/docs/languages/java/)
- [Micrometer Metrics](https://micrometer.io/docs)
