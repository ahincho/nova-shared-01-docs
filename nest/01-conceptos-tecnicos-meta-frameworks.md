# Conceptos Tecnicos del Desarrollo de Meta-Frameworks en NestJS

## 1. Que es un Meta-Framework en el ecosistema Node/NestJS

En el ecosistema Node.js, un meta-framework sobre NestJS cumple el mismo rol que en Java: **estandarizar, encapsular decisiones tecnicas y reducir boilerplate**. Sin embargo, las mecanicas difieren significativamente debido a la naturaleza del ecosistema npm:

- En Java existen BOMs (Maven `dependencyManagement`) y Parent POMs como mecanismos nativos de herencia. En npm **no existen equivalentes nativos**; se simulan con paquetes que re-exportan dependencias y archivos de configuracion compartidos.
- En Java los Starters usan auto-configuracion via classpath scanning. En NestJS los modulos usan **`forRoot()` / `forRootAsync()`** como patron de configuracion dinamica.
- En Java las dependencias transitivas se gestionan con scopes (`compile`, `provided`, `optional`). En npm se usan **`dependencies`** (transitivas), **`peerDependencies`** (el consumidor las provee), y **`devDependencies`** (solo desarrollo).

### Equivalencias entre ecosistemas

| Concepto Java | Equivalente NestJS/npm |
|---------------|----------------------|
| Libreria pura (JAR) | Paquete npm puro (TypeScript, sin NestJS) |
| Spring Boot Starter | NestJS Module con `forRoot()` + Interceptors/Filters |
| BOM (`dependencyManagement`) | Paquete npm con objeto de versiones exportado |
| Parent POM | Paquete npm con configs base (tsconfig, eslint, prettier, jest) |
| Maven Archetype | CLI generator (`nest generate`, `yeoman`, script bash) |
| Gradle Plugin | No hay equivalente directo; se usan presets de config |
| `@AutoConfiguration` | `@Global() @Module()` con providers dinamicos |
| `@ConditionalOnProperty` | Logica condicional en `forRoot()` factory |
| `META-INF/spring.factories` | Barrel `index.ts` con re-exports |

---

## 2. Arquitectura por Niveles para NestJS

La misma estructura de 5 niveles del lado Java se adapta al ecosistema Node:

```
Nivel 5: Build Tooling (CLI generators, schematics, scripts)
   |
Nivel 4: BOM + Parent (version catalog + shared configs)
   |
Nivel 3: Meta-Framework Module (agregador principal)
   |
Nivel 2: NestJS Modules / Starters (integracion framework-especifica)
   |
Nivel 1: Librerias Puras (TypeScript puro, sin NestJS)
```

### Nivel 1: Librerias Puras (Pure TypeScript)

**Proposito:** Codigo TypeScript puro, sin dependencia de NestJS ni Express. Reutilizable en cualquier contexto Node.js (CLI, serverless, testing, otros frameworks como Fastify directo).

**Caracteristicas:**
- Zero dependencias de `@nestjs/*`.
- Solo `reflect-metadata` si usa decoradores.
- Exporta funciones, clases, interfaces, enums.
- Publicable como paquete npm independiente.
- Testeable con Jest sin levantar ninguna aplicacion.

**Patron tipico:**
```
mask-utils/
  src/
    index.ts                  <- Barrel de re-exports
    mask-engine.ts            <- Punto de entrada (clase estatica o funciones)
    models/
      mask-config.ts          <- Configuracion inmutable
      mask-result.ts          <- Resultado tipado
    strategy/
      mask-strategy.interface.ts   <- Interface del Strategy
      strategy-registry.ts         <- Registry con Map
    strategies/
      email-mask.strategy.ts       <- Implementacion concreta
      phone-mask.strategy.ts
    decorators/
      masked.decorator.ts          <- @Masked() usando reflect-metadata
    exceptions/
      strategy-not-found.exception.ts
    enums/
      mask-type.enum.ts
      country-code.enum.ts
```

### Nivel 2: NestJS Modules (Framework-Specific)

**Proposito:** Conectar las librerias puras con NestJS, proporcionando modulos, interceptors, filters, guards, y providers inyectables.

**Patron `forRoot()` (equivalente a auto-configuracion):**
```typescript
@Global()
@Module({})
export class MaskModule {
  static forRoot(options?: MaskModuleOptions): DynamicModule {
    return {
      module: MaskModule,
      providers: [
        { provide: MASK_MODULE_OPTIONS, useValue: options ?? {} },
        MaskService,
        { provide: APP_INTERCEPTOR, useClass: MaskInterceptor },
      ],
      exports: [MaskService],
    };
  }
}
```

**Componentes tipicos de un NestJS Module:**

| Componente NestJS | Equivalente Spring Boot | Funcion |
|-------------------|------------------------|---------|
| `@Module()` con `forRoot()` | `@AutoConfiguration` | Registro y configuracion |
| `@Injectable() Service` | `@Bean` | Logica reutilizable como provider |
| `APP_INTERCEPTOR` | `ResponseBodyAdvice` | Interceptar request/response |
| `APP_FILTER` | `@ControllerAdvice` | Manejar excepciones |
| `APP_GUARD` | `SecurityFilterChain` | Autorizacion/autenticacion |
| `APP_PIPE` | `Validator` | Validacion de entrada |
| `HealthIndicator` | `AbstractHealthIndicator` | Health checks |

**Condicionalidad (equivalente a `@ConditionalOn*`):**

NestJS no tiene un sistema de condiciones declarativo como Spring Boot. Se implementa via logica en `forRoot()`:

```typescript
static forRoot(options?: MaskModuleOptions): DynamicModule {
  const providers: Provider[] = [MaskService];

  // Equivalente a @ConditionalOnProperty("nova.mask.enabled")
  if (options?.enabled !== false) {
    providers.push({ provide: APP_INTERCEPTOR, useClass: MaskInterceptor });
  }

  return { module: MaskModule, providers, exports: [MaskService] };
}
```

### Nivel 3: Meta-Framework Module (Agregador)

**Proposito:** Un unico paquete npm y un unico `Module.forRoot()` que el desarrollador importa para obtener toda la funcionalidad.

```typescript
// El proyecto final solo necesita esto:
import { NovaModule } from '@ahincho/nova-nestjs-starter';

@Module({
  imports: [NovaModule.forRoot()],
})
export class AppModule {}
```

Internamente, `NovaModule.forRoot()` registra:
- `MaskModule.forRoot()` (enmascaramiento automatico)
- `ApiStandardModule.forRoot()` (envelope de respuestas)
- Re-exporta todas las librerias puras

Adicionalmente, el paquete puede proveer un **Factory** para el bootstrap:

```typescript
// En lugar de:
const app = await NestFactory.create(AppModule);

// Se usa:
const app = await NovaFactory.create(AppModule);
// Esto valida Node.js version, NestJS version, configura logger, etc.
```

### Nivel 4: BOM + Parent

#### BOM (Version Catalog)

En npm no existe un mecanismo nativo de BOM. Se simula con un paquete que exporta un objeto con versiones:

```typescript
// @ahincho/nova-bom
export const versions = {
  maskUtils: '1.0.0',
  dateUtils: '1.0.0',
  mapperUtils: '1.0.0',
  apiStandard: '1.0.0',
};
```

**Limitacion critica:** A diferencia de Maven donde `<dependencyManagement>` realmente controla versiones de dependencias transitivas, un BOM en npm es **solo informativo**. No fuerza versiones. Para eso se necesitan:
- `peerDependencies` con ranges estrictos.
- `overrides` en el `package.json` del consumidor (npm 8.3+).
- `resolutions` si se usa yarn.

#### Parent (Shared Configs)

Un paquete npm que exporta configuraciones base via `exports` en `package.json`:

```json
{
  "name": "@ahincho/nova-nestjs-parent",
  "exports": {
    "./tsconfig": "./tsconfig.base.json",
    "./eslint": "./eslint.config.mjs",
    "./prettier": "./prettier.config.mjs",
    "./jest": "./jest.config.base.ts"
  }
}
```

Los proyectos hijos extienden con archivos thin wrapper:

```json
// tsconfig.json del hijo
{ "extends": "@ahincho/nova-nestjs-parent/tsconfig" }
```

```javascript
// eslint.config.mjs del hijo
import base from '@ahincho/nova-nestjs-parent/eslint';
export default [...base];
```

### Nivel 5: Build Tooling

En el ecosistema NestJS, las opciones de generacion son:

| Herramienta | Tipo | Ventajas | Desventajas |
|-------------|------|----------|-------------|
| NestJS CLI Schematics | Plugin de `@nestjs/cli` | Integrado con `nest generate` | Solo genera dentro de un proyecto existente |
| Yeoman Generator | Generador independiente | Cross-platform, interactivo | Ecosistema en declive |
| `create-*` package | `npm init @nova` | Convencion npm estandar | Requiere publicar en npm |
| Script bash | `init.sh` | Flexible, rapido de implementar | No cross-platform, no publicable |
| Nx Plugin | Plugin de Nx workspace | Monorepo-native, generadores potentes | Acoplamiento a Nx |

---

## 3. Gestion de Dependencias en npm vs Maven

### 3.1. Tipos de dependencias

| npm | Maven | Comportamiento |
|-----|-------|---------------|
| `dependencies` | `compile` | Se instala transitivamente para el consumidor |
| `devDependencies` | `test` / `provided` | Solo para desarrollo, no se instala para el consumidor |
| `peerDependencies` | `provided` | El consumidor debe proveerla, no se instala automaticamente |
| `optionalDependencies` | `optional` | Si falla la instalacion, npm continua sin error |

### 3.2. peerDependencies: el patron clave para NestJS Modules

Un NestJS Module (starter) debe declarar NestJS como `peerDependency`, no como `dependency`:

```json
{
  "peerDependencies": {
    "@nestjs/core": "^11.0.0",
    "@nestjs/common": "^11.0.0",
    "rxjs": "^7.8.0",
    "reflect-metadata": "~0.2.2"
  },
  "dependencies": {
    "@ahincho/nova-mask-utils": "1.0.0"
  }
}
```

Esto garantiza que:
- El consumidor usa **una sola instancia** de `@nestjs/core` (evita el error clasico de "multiple NestJS instances").
- La libreria pura (`mask-utils`) si se instala transitivamente (es una `dependency` real).
- NestJS y rxjs son provistos por la aplicacion final.

### 3.3. Publicacion: npm Registry vs Verdaccio

| Destino | Uso | Configuracion |
|---------|-----|---------------|
| npm public | Librerias open source | Default |
| GitHub Packages | Organizacion con GitHub | `@scope:registry=https://npm.pkg.github.com` |
| Verdaccio | Desarrollo local | `@scope:registry=http://localhost:4873` |
| Nexus / Artifactory | Empresarial | Registry privado |

---

## 4. Monorepo vs Multi-repo en NestJS

### Opciones de monorepo

| Herramienta | Ventajas | Desventajas |
|-------------|----------|-------------|
| **Turborepo** | Cache inteligente, task pipeline, minima config | No tiene generators ni plugins propios |
| **Nx** | Generators, dependency graph, affected commands | Mas pesado, curva de aprendizaje |
| **npm workspaces** | Nativo, sin herramientas extra | Sin cache, sin task pipeline |
| **Lerna** | Versionado coordinado, publish | Requiere Nx o Turborepo para performance |
| **pnpm workspaces** | Instalacion eficiente, strict por defecto | Requiere pnpm |

### Estructura tipica con Turborepo

```
nova-commons-nestjs/
  turbo.json                   <- Task pipeline (build, test, lint)
  package.json                 <- workspaces: ["packages/*"]
  packages/
    nestjs-mask/               <- NestJS module para masking
    nestjs-api-standard/       <- NestJS module para API standard
    nestjs-observability/      <- NestJS module para observabilidad
```

**Ventaja clave:** Un solo `turbo run build` compila todos los paquetes en orden de dependencia con cache.

---

## 5. Patrones de Auto-Configuracion en NestJS

### 5.1. Dynamic Module con `forRoot()` / `forRootAsync()`

```typescript
@Global()
@Module({})
export class ObservabilityModule {
  // Configuracion sincrona
  static forRoot(options?: ObservabilityModuleOptions): DynamicModule {
    const resolved = resolveOptions(options);
    return {
      module: ObservabilityModule,
      providers: [
        { provide: OBSERVABILITY_OPTIONS, useValue: resolved },
        OtelSdkInitializer,
        CollectorHealthIndicator,
      ],
      exports: [CollectorHealthIndicator],
    };
  }

  // Configuracion asincrona (ej: leer de ConfigService)
  static forRootAsync(options: {
    imports?: Type<any>[];
    inject?: any[];
    useFactory: (...args: any[]) => ObservabilityModuleOptions | Promise<ObservabilityModuleOptions>;
  }): DynamicModule {
    return {
      module: ObservabilityModule,
      imports: options.imports ?? [],
      providers: [
        {
          provide: OBSERVABILITY_OPTIONS,
          useFactory: async (...args) => resolveOptions(await options.useFactory(...args)),
          inject: options.inject ?? [],
        },
        OtelSdkInitializer,
        CollectorHealthIndicator,
      ],
      exports: [CollectorHealthIndicator],
    };
  }
}
```

### 5.2. Interceptors como ResponseBodyAdvice

En NestJS, los interceptors son el equivalente a `ResponseBodyAdvice` de Spring:

```typescript
@Injectable()
export class MaskInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    return next.handle().pipe(
      map(data => this.maskRecursive(data)),  // Transforma la respuesta
    );
  }
}
```

### 5.3. Exception Filters como @ControllerAdvice

```typescript
@Catch()
export class ApiStandardExceptionFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentHost): void {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse();
    const status = exception instanceof HttpException ? exception.getStatus() : 500;
    response.status(status).json(ApiResponse.error(status, message));
  }
}
```

---

## 6. Observabilidad en NestJS

### Stack tipica

| Capa | Java (Spring Boot) | NestJS |
|------|-------------------|--------|
| Traces | OpenTelemetry Java Agent | `@opentelemetry/sdk-node` + auto-instrumentations |
| Metrics | Micrometer + Prometheus | OpenTelemetry Metrics o `prom-client` |
| Logs | SLF4J + Logback + MDC | Pino con `pino-opentelemetry-transport` |
| Health | Spring Actuator | `@nestjs/terminus` |

### Inicializacion del SDK de OpenTelemetry

A diferencia de Java donde el agente OTel se inyecta como JVM agent, en Node.js se debe inicializar el SDK **antes** de importar cualquier modulo instrumentado:

```typescript
const sdk = new NodeSDK({
  resource: new Resource({ 'service.name': 'my-app' }),
  traceExporter: new OTLPTraceExporter({ url: 'http://localhost:4318/v1/traces' }),
  metricReader: new PeriodicExportingMetricReader({
    exporter: new OTLPMetricExporter({ url: 'http://localhost:4318/v1/metrics' }),
  }),
  instrumentations: [getNodeAutoInstrumentations()],
});
sdk.start();
```

### Correlacion de logs con traces

Pino + `pino-opentelemetry-transport` inyecta `traceId` y `spanId` automaticamente en cada linea de log, similar a MDC en Java.

---

## 7. Diferencias Clave con el Meta-Framework Java

| Aspecto | Java | NestJS |
|---------|------|--------|
| BOM | Mecanismo nativo de Maven | Simulado con paquete de versiones (no enforcement real) |
| Parent | Herencia via `<parent>` | Configs compartidas via `exports` en package.json |
| Auto-configuracion | Classpath scanning + conditions | `forRoot()` con logica imperativa |
| Interceptors | `ResponseBodyAdvice`, `HandlerInterceptor` | `NestInterceptor` con RxJS `Observable` |
| Exception handling | `@ControllerAdvice` + `@ExceptionHandler` | `@Catch()` + `ExceptionFilter` |
| DI | Constructor injection automatica | Constructor injection con decoradores `@Inject()` |
| Decoradores | Anotaciones Java (`@Traced`, `@Masked`) | Decoradores TypeScript con `reflect-metadata` |
| Build | Maven/Gradle (compilacion a bytecode) | tsc (transpilacion a JS) |
| Registry | Maven Central, GitHub Packages | npm, GitHub Packages, Verdaccio |
| Monorepo | Multi-module Maven/Gradle | Turborepo, Nx, npm workspaces |
| Testing | JUnit 5, Mockito, Spring Test | Jest, supertest, `@nestjs/testing` |
| Native compilation | GraalVM | No aplica (interpretado) |
