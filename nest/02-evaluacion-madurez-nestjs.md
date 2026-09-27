# Evaluacion de Madurez - Nova Platform Meta-Framework (NestJS)

> **Documento historico, no describe el estado actual.** Evalua el diseno anterior al colapso
> de 2026-09-05: once paquetes bajo el scope `@ahincho/`, repartidos en cuatro
> repositorios que hoy estan archivados. El stack vive ahora en `ahincho/nova-nestjs` con tres
> paquetes bajo `@ahincho/`. Ver [ADR-025](../adrs/nest/ADR-025-tres-paquetes-en-lugar-de-once.md).
>
> Se conserva porque el inventario y las notas de madurez explican por que se colapso.

## Resumen Ejecutivo

El meta-framework Nova Platform para NestJS se encuentra en **fase Alpha con una base conceptualmente solida** y un nivel de madurez ligeramente superior al lado Java en consistencia de build y patron de configuracion. La arquitectura de 5 niveles esta correctamente implementada: librerias puras en TypeScript, NestJS Modules como starters, un agregador principal, BOM/Parent simulados, y un script de publicacion local. Sin embargo, comparte el deficit critico de testing (solo `mask-utils` tiene tests) y carece de tooling de generacion de proyectos.

**Calificacion general: 4.0 / 10** (ver desglose abajo)

---

## 1. Inventario Completo de Artefactos

### Nivel 1: Librerias Puras

| Artefacto | Paquete npm | Archivos src | Tests | Madurez |
|-----------|-------------|:---:|:---:|:---:|
| `nova-mask-utils` | `@ahincho/nova-mask-utils` | 30 | 15 archivos | 7/10 |
| `nova-date-utils` | `@ahincho/nova-date-utils` | 3 | 0 | 3/10 |
| `nova-mapper-utils` | `@ahincho/nova-mapper-utils` | 4 | 0 | 3/10 |
| `nova-api-standard` | `@ahincho/nova-api-standard` | 7 | 0 | 4/10 |
| `nova-observability-utils` | `@ahincho/nova-observability-utils` | 5 | 0 | 2/10 |

### Nivel 2: NestJS Modules (Starters)

| Artefacto | Paquete npm | Archivos src | Tests | Madurez |
|-----------|-------------|:---:|:---:|:---:|
| `nestjs-mask` (en commons monorepo) | `@ahincho/nova-nestjs-mask` | 6 | 0 | 5/10 |
| `nestjs-api-standard` (en commons monorepo) | `@ahincho/nova-nestjs-api-standard` | 4 | 0 | 4/10 |
| `nestjs-observability` (standalone + monorepo) | `@ahincho/nova-nestjs-observability` | 9 | 0 | 5/10 |

### Nivel 3: Meta-Framework Module

| Artefacto | Paquete npm | Archivos src | Tests | Madurez |
|-----------|-------------|:---:|:---:|:---:|
| `nova-nestjs-starter` | `@ahincho/nova-nestjs-starter` | 5 | 0 | 4/10 |

### Nivel 4: BOM + Parent

| Artefacto | Paquete npm | Madurez |
|-----------|-------------|:---:|
| `nova-bom` | `@ahincho/nova-bom` | 3/10 |
| `nova-nestjs-bom` (dentro de bom/) | `@ahincho/nova-nestjs-bom` | 3/10 |
| `nova-nestjs-parent` | `@ahincho/nova-nestjs-parent` | 6/10 |

### Nivel 5: Build Tooling

| Artefacto | Tipo | Madurez |
|-----------|------|:---:|
| `publish-local.sh` | Script de publicacion a Verdaccio | 4/10 |

### Soporte

| Artefacto | Tipo | Madurez |
|-----------|------|:---:|
| `nova-example` | App de ejemplo | 5/10 |
| `nova-commons-nestjs` | Turborepo monorepo | 5/10 |

---

## 2. Analisis Detallado por Nivel

### Nivel 1: Librerias Puras

#### `@ahincho/nova-mask-utils` -- EL MAS MADURO (7/10)

**Fortalezas:**
- Arquitectura Strategy Pattern identica al lado Java: `MaskEngine`, `StrategyRegistry`, `MaskStrategy`.
- 7 estrategias de enmascaramiento con soporte multi-pais (PE, US, GENERIC).
- Decoradores TypeScript (`@Masked`, `@MaskedClass`, `@SkipMasking`) con `reflect-metadata`.
- Inferencia automatica de tipo por nombre de campo (26 patrones ES+EN en `FIELD_INFERENCE_MAP`).
- **15 archivos de test** cubriendo cada componente individualmente.
- Excepciones tipadas (`StrategyNotFoundException`, `InvalidFormatException`).
- Factory methods inmutables en `MaskConfig` y `MaskResult` (`MaskConfig.default()`, `MaskResult.success()`).

**Debilidades:**
- El `prepublishOnly` script usa `&` (background) en lugar de `&&` (secuencial) -- bug potencial.
- No tiene tests de integracion end-to-end (solo unitarios).

#### `@ahincho/nova-date-utils` (3/10)

**Fortalezas:**
- API funcional: `formatISO()`, `formatDate()` (token replacement), `parseDate()` (multi-pattern con 5 regex).
- Enum `DatePattern` con patrones comunes (ISO, DMY, MDY, 24H).
- Validacion con `isValidDate()`.

**Debilidades:**
- **Zero tests.**
- Solo 3 archivos fuente (~250 lineas total) -- es muy pequeno comparado con su equivalente Java (14 archivos, ~2300 lineas).
- Falta: relative formatting, timezone handling, date calculation, date ranges.
- `parseDate()` usa regex manual en lugar de librerias probadas (`date-fns`, `luxon`, `dayjs`).

#### `@ahincho/nova-mapper-utils` (3/10)

**Fortalezas:**
- Interfaces bien definidas: `FieldMapping`, `MapperOptions`, `ObjectMapper<S,T>`.
- `mapByConvention()` (copia por nombre), `mapWithConfig()` (mappings explicitos + transforms).
- `createMapper()` retorna un `ObjectMapper` reutilizable -- buen patron factory.

**Debilidades:**
- **Zero tests.**
- No soporta nested mapping recursivo (a diferencia del Java).
- No tiene deteccion de referencias circulares.
- No tiene type converters registrables.
- No tiene `MappingResult` con metadata (campos mapeados, omitidos, warnings).
- ~160 lineas -- funcionalidad basica.

#### `@ahincho/nova-api-standard` (4/10)

**Fortalezas:**
- `ApiResponse<T>` generico con factory methods inmutables: `ok()`, `created()`, `noContent()`, `error()`.
- Interfaces bien tipadas: `ApiError`, `ApiLink`, `ApiMetadata`, `PageInfo`, `RateLimitInfo`.
- Auto-generacion de codigo de error (`ERR_{status}`) para errores simples.
- Constructor privado -- solo se puede instanciar via factories.

**Debilidades:**
- **Zero tests.**
- Menos funcionalidad que el equivalente Java: no tiene `HttpStatusCode` enum, no tiene `FilterCriteria`/`SortCriteria`, no tiene `PrettyPrinter`, no tiene `UserAgentParser`.
- `PageInfo` no calcula `totalPages` automaticamente (a diferencia del Java que si lo hace).

#### `@ahincho/nova-observability-utils` (2/10)

**Fortalezas:**
- Contratos bien definidos: `GoldenSignalsRecorder` interface, `MetricNames` constants.
- Decoradores `@Traced` y `@Metered` con metadata via Symbols.
- `ErrorClassification` enum (CLIENT_ERROR, SERVER_ERROR, TIMEOUT, UNKNOWN).
- Zero dependencias de OTel -- verdaderamente puro.

**Debilidades:**
- **Zero tests.**
- No tiene `jest.config.ts` -- ni siquiera la infraestructura de testing esta configurada.
- Solo interfaces y decoradores -- toda la implementacion esta en el starter.
- ~170 lineas total en 5 archivos.

---

### Nivel 2: NestJS Modules (Starters)

#### `@ahincho/nova-nestjs-mask` (5/10)

**Fortalezas:**
- `MaskModule.forRoot()` con `@Global()` -- se registra una vez y esta disponible en toda la app.
- `MaskInterceptor` (220 lineas) con logica de resolucion de prioridad bien implementada:
  1. `@SkipMasking()` en campo -> skip
  2. `@Masked()` en campo -> mask con opciones explicitas
  3. `@SkipMasking()` en clase -> skip todo
  4. `@MaskedClass()` en clase -> mask todos los campos string
  5. Inferencia por nombre de campo -> mask automatico
- `MaskService` inyectable con default country configurable.
- Recursion en objetos nested y arrays.

**Debilidades:**
- **Zero tests.** Un interceptor de 220 lineas sin tests es un riesgo alto.
- No hay `forRootAsync()` para configuracion asincrona (ej: leer config de base de datos).
- No tiene health indicator ni info contributor.
- No tiene integracion con class-serializer de NestJS.

#### `@ahincho/nova-nestjs-api-standard` (4/10)

**Fortalezas:**
- `ApiStandardModule.forRoot()` registra interceptor y exception filter.
- `ApiStandardInterceptor` envuelve respuestas en `ApiResponse.ok()` o `.created()`.
- `ApiStandardExceptionFilter` convierte excepciones a `ApiResponse.error()`.
- Detecta si la respuesta ya es un `ApiResponse` para evitar doble wrapping.

**Debilidades:**
- **Zero tests.**
- El exception filter solo maneja `HttpException` y `Error` generico -- falta:
  - `ValidationPipe` errors (class-validator).
  - `BadRequestException` con detalles de validacion.
  - Errores de parsing de body.
  - Errores de TypeORM/Prisma/Mongoose.
- No hay opciones para deshabilitarlo (`enabled: false`).
- No soporta exclusion de rutas (ej: health checks, swagger).

#### `@ahincho/nova-nestjs-observability` (5/10)

**Fortalezas:**
- `ObservabilityModule.forRoot()` con configuracion completa: OTLP endpoint, metricas, trazas, logs.
- `OtelSdkInitializer` (144 lineas) configura `NodeSDK` con:
  - Resource attributes (service name, namespace, environment).
  - Trace exporter (OTLP HTTP).
  - Metric reader con exportacion periodica.
  - Log exporter.
  - Auto-instrumentations (`@opentelemetry/auto-instrumentations-node`).
  - Sampler configurable (TraceIdRatioBasedSampler).
  - Graceful shutdown via `OnModuleDestroy`.
- `resolveOptions()` con deep merge de defaults + environment variables override.
- `CollectorHealthIndicator` con `@nestjs/terminus` y timeout de 3 segundos.
- `createPinoLoggerOptions()` para logging estructurado con correlacion de traces.
- Principio de resiliencia: errores de OTel se loguean pero nunca crashean la app.

**Debilidades:**
- **Zero tests.**
- Existe **duplicacion**: la misma logica esta tanto en `nova-commons-nestjs/packages/nestjs-observability/` (monorepo) como en `nova-observability-nestjs-starter/` (standalone). Dos copias del mismo codigo.
- No implementa `GoldenSignalsRecorder` de observability-utils -- la interface existe pero no tiene implementacion NestJS.
- No tiene `@Traced` ni `@Metered` interceptors/decorators funcionales -- los decoradores existen en observability-utils pero no hay ningun interceptor NestJS que los procese.
- Falta `GoldenSignalsFilter` equivalente al de Java (que mide latencia, trafico, errores, saturacion por endpoint).

---

### Nivel 3: Meta-Framework Module

#### `@ahincho/nova-nestjs-starter` (4/10)

**Fortalezas:**
- `NovaModule.forRoot()` registra MaskModule + ApiStandardModule en una sola linea.
- `NovaFactory.create()` valida Node.js >= 24 y NestJS == 11.x antes de crear la app.
- Barrel `index.ts` (109 lineas) re-exporta todo: single import experience.
- Acepta `NovaFactoryOptions` con logger y `skipEnvValidation`.
- Acepta `NovaModuleOptions` con opciones de mask.

**Debilidades:**
- **Zero tests.**
- `NovaFactory.create()` valida Node.js >= 24 -- esto es restrictivo (Node 22 es LTS actual).
- No integra `ObservabilityModule` -- el desarrollador tiene que importarlo por separado.
- El barrel re-exporta 30+ simbolos de mask-utils directamente -- esto contamina el namespace del importador.
- No hay `NovaModuleOptions` para configurar api-standard ni observability.
- No hay banner/log al arrancar el framework.

---

### Nivel 4: BOM + Parent

#### `@ahincho/nova-bom` + `@ahincho/nova-nestjs-bom` (3/10)

**Fortalezas:**
- Estructura correcta: BOM raiz con versiones de librerias puras, NestJS BOM que extiende con versiones de NestJS.
- Tipado con interfaces (`BomVersions`, `NestjsBomVersions`).

**Debilidades:**
- **No enfuerza nada.** A diferencia de Maven donde un BOM controla versiones transitivas, estos paquetes solo exportan un objeto JavaScript con strings de version. El consumidor tiene que leer el objeto y usarlo manualmente -- nadie lo hace.
- No hay un mecanismo que valide que las versiones declaradas en el BOM coinciden con las realmente instaladas.
- El BOM tiene su propia `tsconfig.json` standalone en lugar de extender el parent -- inconsistencia.

#### `@ahincho/nova-nestjs-parent` (6/10)

**Fortalezas:**
- Configs base bien definidas: `tsconfig.base.json`, `eslint.config.mjs`, `prettier.config.mjs`, `jest.config.base.ts`, `typedoc.base.json`.
- `tsconfig.base.json` con configuracion estricta: `strict`, `noUnusedLocals`, `noUnusedParameters`, `noImplicitReturns`, `experimentalDecorators`, `emitDecoratorMetadata`.
- `jest.config.base.ts` con thresholds de cobertura al 80% (branches, functions, lines, statements).
- `eslint.config.mjs` con `typescript-eslint` y reglas strict.
- `prettier.config.mjs` con convencion definida (singleQuote, trailingComma, semi).
- `environment-validator.ts` con `validateEnvironment()` y `assertNodeVersion()`.
- Uso correcto de `exports` en package.json para exponer configs como subpath imports.

**Debilidades:**
- Las versiones de herramientas estan en `dependencies` en lugar de `peerDependencies` -- esto puede causar conflictos si el proyecto hijo quiere una version diferente de TypeScript o ESLint.
- Node 24 hardcodeado en `assertNodeVersion` -- deberia ser configurable.
- No incluye configs para herramientas de CI (GitHub Actions workflows, Dockerfile base, .dockerignore).

---

### Nivel 5: Build Tooling

#### `publish-local.sh` (4/10)

**Fortalezas:**
- Publica todos los paquetes en orden correcto de dependencia a Verdaccio local.
- Cubre los 10 paquetes del ecosistema.

**Debilidades:**
- Solo Bash (no funciona en Windows sin WSL).
- No hay equivalente para publicacion a GitHub Packages (solo configuracion en package.json).
- No hay validacion de que Verdaccio este corriendo.
- No hay script de clean/unpublish.
- No hay generador de proyectos ni CLI.

---

## 3. Analisis Transversal

### 3.1. Cobertura de Tests

| Nivel | Modulo | Tests |
|-------|--------|:---:|
| 1 | mask-utils | SI (15 archivos) |
| 1 | date-utils | NO |
| 1 | mapper-utils | NO |
| 1 | api-standard | NO |
| 1 | observability-utils | NO (ni jest.config) |
| 2 | nestjs-mask | NO |
| 2 | nestjs-api-standard | NO |
| 2 | nestjs-observability | NO |
| 3 | nestjs-starter | NO |
| 4 | nestjs-parent | NO |

**Conclusion:** 1 de 10 modulos tiene tests. Identico al lado Java.

### 3.2. Consistencia de Build

A diferencia del lado Java (mezcla Maven/Gradle), el lado NestJS es **consistente**:
- Todos usan `tsc` para compilar.
- Todos extienden `@ahincho/nova-nestjs-parent` para configs.
- Todos publican a GitHub Packages / Verdaccio.
- El monorepo usa Turborepo para orquestar builds.

Esto es una ventaja sobre Java.

### 3.3. Duplicacion de Codigo

Hay un **problema de duplicacion significativo**:

El paquete `@ahincho/nova-nestjs-observability` existe en **dos lugares**:
1. `nova-commons-nestjs/packages/nestjs-observability/` -- dentro del monorepo Turborepo.
2. `nova-observability-nestjs-starter/` -- como proyecto standalone.

El standalone tiene mas codigo (OtelSdkInitializer, Pino logger, health indicator) mientras que el del monorepo solo tiene las interfaces y la resolucion de opciones. No esta claro cual es el canonico.

### 3.4. Comparacion de Paridad con Java

| Componente | Java | NestJS | Paridad |
|------------|:---:|:---:|:---:|
| mask-utils | 35 clases, 26 tests | 30 archivos, 15 tests | Similar |
| date-utils | 14 clases, 0 tests | 3 archivos, 0 tests | NestJS muy reducido |
| mapper-utils | 18 clases, 0 tests | 4 archivos, 0 tests | NestJS muy reducido |
| api-standard | 21 clases, 0 tests | 7 archivos, 0 tests | NestJS reducido |
| observability-utils | 5 clases, 0 tests | 5 archivos, 0 tests | Paridad |
| mask-starter | 17 clases, 0 tests | 6 archivos, 0 tests | Java tiene mas integraciones |
| api-standard-starter | 3 clases, 0 tests | 4 archivos, 0 tests | Similar |
| observability-starter | 12 clases, 0 tests | 9 archivos, 0 tests | Java mas completo (Golden Signals Filter) |
| meta-framework starter | 4 clases, 0 tests | 5 archivos, 0 tests | Similar |
| BOM | 3 POMs | 2 paquetes | Ambos basicos |
| Parent | 1 POM | 1 paquete + configs | NestJS mas util (configs reales) |
| Gradle Plugin / CLI | 1 plugin | No existe | Java adelante |
| Archetype | 1 archetype | No existe | Java adelante |
| CI/CD workflows | 8 workflows | No existe | Java adelante |
| Infrastructure | Docker Compose | No existe | Java adelante |

---

## 4. Evaluacion por Criterio

| Criterio | Score | Justificacion |
|----------|:-----:|---------------|
| Arquitectura conceptual | **7** | 5 niveles correctos, buena separacion de responsabilidades |
| Implementacion de librerias | **4** | mask-utils completo, el resto basico. date-utils y mapper-utils muy reducidos vs Java |
| NestJS Modules (starters) | **5** | Patron forRoot() correcto, interceptors bien implementados, falta forRootAsync y tests |
| Gestion de versiones (BOM) | **2** | BOMs no enfuerzan nada en npm. Es un patron decorativo |
| Parent (configs compartidas) | **6** | Bien implementado con exports y configs base. Unico punto fuerte claro sobre Java |
| Testing | **1** | Solo mask-utils tiene tests |
| Documentacion | **1** | Zero documentacion. Ni READMEs, ni guias, ni API docs |
| CI/CD | **1** | Solo publish-local.sh. No hay GitHub Actions workflows |
| Observabilidad | **5** | OTel SDK bien configurado, Pino logger, health check. Pero no hay Golden Signals filter ni interceptors para @Traced/@Metered |
| Build tooling | **2** | No hay generador, no hay CLI, no hay schematics |
| Produccion-readiness | **2** | Falta testing, documentacion, CI/CD. No apto |
| **PROMEDIO** | **3.3** | |

---

## 5. Lo Que Esta Bien Hecho

1. **Consistencia de build system** - Todo TypeScript con tsc, todo extiende el Parent. Superior a Java en este aspecto.
2. **mask-utils como referencia** - 30 archivos con Strategy pattern, decoradores, inferencia, y 15 archivos de test.
3. **Parent package con configs reales** - tsconfig, eslint, prettier, jest con thresholds. Los proyectos hijos son thin wrappers de 1-2 lineas.
4. **Interceptors bien implementados** - `MaskInterceptor` (220 lineas) con logica de prioridad de decoradores y recursion en objetos nested.
5. **OTel SDK Initializer** - Configuracion completa de NodeSDK con resiliencia (errores logueados, nunca crashes).
6. **Turborepo para monorepo** - Los NestJS modules estan en un workspace con task pipeline.
7. **Decoradores TypeScript** - `@Masked`, `@MaskedClass`, `@SkipMasking`, `@Traced`, `@Metered` con reflect-metadata.
8. **Inmutabilidad** - `ApiResponse`, `MaskConfig`, `MaskResult` usan constructores privados + factory methods.
9. **peerDependencies correctas** - Los NestJS modules declaran `@nestjs/*` como peer, no como dependency.
10. **Deep merge de opciones** - `resolveOptions()` en observability hace merge con defaults + env vars.
