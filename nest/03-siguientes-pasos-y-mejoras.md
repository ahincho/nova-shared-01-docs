# Siguientes Pasos y Puntos de Mejora (NestJS)

## Prioridades Inmediatas (Sprint 1-2)

### P0: Testing - El Deficit Critico

**Estado actual:** Solo `mask-utils` tiene tests (15 archivos). Los otros 9 modulos tienen zero.

#### 1.1. Tests para librerias puras (Nivel 1)

| Libreria | Tests Necesarios | Prioridad |
|----------|-----------------|-----------|
| `date-utils` | `formatISO()`, `formatDate()`, `parseDate()` con todos los patterns. Edge cases: fechas invalidas, strings vacios, formatos ambiguos. | ALTA |
| `mapper-utils` | `mapByConvention()`, `mapWithConfig()`, `createMapper()`. Campos faltantes, transforms, strict mode, arrays, nulls. | ALTA |
| `api-standard` | `ApiResponse.ok()`, `.created()`, `.noContent()`, `.error()`. Validar inmutabilidad, tipado generico, auto-generacion de error codes. | MEDIA |
| `observability-utils` | Tests de decoradores `@Traced` y `@Metered` (verificar metadata almacenada). Tests de `ErrorClassification`. | BAJA |

**Patron a seguir** (de mask-utils):
```
src/
  mask-engine.ts
  mask-engine.test.ts          <- Test co-ubicado con el fuente
  models/
    mask-config.ts
    mask-config.test.ts
  strategies/
    email-mask.strategy.ts
    email-mask.strategy.test.ts
```

#### 1.2. Tests de integracion para NestJS Modules (Nivel 2)

Los modulos NestJS necesitan tests con `@nestjs/testing`:

```typescript
import { Test, TestingModule } from '@nestjs/testing';
import { MaskModule, MaskService } from '@ahincho/nova-nestjs-mask';

describe('MaskModule', () => {
  let module: TestingModule;
  let service: MaskService;

  beforeEach(async () => {
    module = await Test.createTestingModule({
      imports: [MaskModule.forRoot({ enabled: true, defaultCountry: CountryCode.PE })],
    }).compile();
    service = module.get(MaskService);
  });

  it('should register MaskService', () => {
    expect(service).toBeDefined();
  });

  it('should mask email with default country', () => {
    const result = service.mask('user@mail.com', MaskType.EMAIL);
    expect(result.applied).toBe(true);
  });

  it('should respect enabled=false', async () => {
    const mod = await Test.createTestingModule({
      imports: [MaskModule.forRoot({ enabled: false })],
    }).compile();
    // Verificar que el interceptor no se registra
  });
});
```

| Module | Tests de Integracion Necesarios |
|--------|-------------------------------|
| `nestjs-mask` | forRoot() registration, MaskService injection, MaskInterceptor behavior con mocks HTTP, prioridad de decoradores. | 
| `nestjs-api-standard` | Response wrapping, exception filter con HttpException, exception filter con error desconocido, skip si ya es ApiResponse. |
| `nestjs-observability` | forRoot() registration, OtelSdkInitializer.initialize() mock, CollectorHealthIndicator con endpoint activo/inactivo. |

#### 1.3. Tests del Meta-Framework Starter (Nivel 3)

```typescript
describe('NovaFactory', () => {
  it('should create NestJS application', async () => {
    const app = await NovaFactory.create(AppModule);
    expect(app).toBeDefined();
    await app.close();
  });

  it('should validate Node.js version', () => {
    // Mock process.version
  });
});

describe('NovaModule', () => {
  it('should register MaskModule and ApiStandardModule', async () => {
    const module = await Test.createTestingModule({
      imports: [NovaModule.forRoot()],
    }).compile();
    expect(module.get(MaskService)).toBeDefined();
  });
});
```

---

### P1: Resolver Duplicacion de Observabilidad

**Problema:** `@ahincho/nova-nestjs-observability` existe en dos lugares:
1. `nova-commons-nestjs/packages/nestjs-observability/` -- solo config/interfaces.
2. `nova-observability-nestjs-starter/` -- implementacion completa (OTel SDK, Pino, health).

**Accion:** Elegir UNA de estas estrategias:

**Opcion A (Recomendada) - Todo en el monorepo:**
- Mover el codigo completo de `nova-observability-nestjs-starter/` a `nova-commons-nestjs/packages/nestjs-observability/`.
- Eliminar `nova-observability-nestjs-starter/` como proyecto standalone.
- El monorepo queda con 3 paquetes: nestjs-mask, nestjs-api-standard, nestjs-observability.
- Actualizar `publish-local.sh` para reflejar el cambio.

**Opcion B - Todo standalone:**
- Mantener `nova-observability-nestjs-starter/` como canonico.
- Eliminar `nova-commons-nestjs/packages/nestjs-observability/`.
- El monorepo queda solo con nestjs-mask y nestjs-api-standard.

---

### P2: Correccion de Inconsistencias

#### 2.1. Versiones de Node.js

`NovaFactory` valida Node.js >= 24 y `assertNodeVersion` valida lo mismo. Node 24 no es LTS (Node 22 es el LTS actual). Esto bloquea la adopcion.

**Accion:** Cambiar a Node.js >= 22 como minimo, o hacerlo configurable:

```typescript
static async create(
  module: Type<any>,
  options?: NovaFactoryOptions & { minNodeVersion?: number },
): Promise<INestApplication> {
  const minVersion = options?.minNodeVersion ?? 22;
  assertNodeVersion(minVersion);
  // ...
}
```

#### 2.2. Integrar ObservabilityModule en el Starter

Actualmente el desarrollador debe importar `ObservabilityModule` por separado:

```typescript
// ACTUAL - dos imports separados
@Module({
  imports: [
    NovaModule.forRoot(),
    ObservabilityModule.forRoot({ ... }),  // Manual
  ],
})
```

**Accion:** Agregar observabilidad como opcion del starter:

```typescript
// PROPUESTO - todo en uno
@Module({
  imports: [
    NovaModule.forRoot({
      mask: { defaultCountry: CountryCode.PE },
      observability: {
        serviceName: 'my-app',
        otlp: { endpoint: 'http://localhost:4318' },
      },
    }),
  ],
})
```

#### 2.3. BOM sin valor real

Los paquetes `@ahincho/nova-bom` y `@ahincho/nova-nestjs-bom` exportan objetos con versiones pero nadie los consume. No hay ninguna herramienta que los lea.

**Opciones:**
1. **Eliminarlos** y documentar las versiones en un README o CHANGELOG.
2. **Crear un validator** que el starter ejecute al arrancar: lee las versiones instaladas de `node_modules` y las compara con el BOM. Loguea warnings si hay discrepancias.
3. **Usar npm `overrides`** (npm 8.3+) en un template `package.json` que haga enforcement real.

#### 2.4. Fix del script de publicacion

En `mask-utils/package.json`, el script `prepublishOnly` usa `&` (ejecuta en background) en lugar de `&&` (secuencial):

```json
// BUG
"prepublishOnly": "npm run clean & npm run build"

// CORRECTO
"prepublishOnly": "npm run clean && npm run build"
```

Verificar si este bug existe en otros paquetes.

---

## Mejoras de Funcionalidad (Sprint 3-5)

### 3. Completar las Librerias Puras

#### 3.1. `date-utils` - Alcanzar paridad con Java

El modulo Java tiene 14 clases y ~2300 lineas. El NestJS tiene 3 archivos y ~250 lineas.

**Funcionalidad faltante:**

| Feature | Java | NestJS | Accion |
|---------|:---:|:---:|--------|
| Relative formatting ("hace 5 min") | SI | NO | Implementar `relativeFormat()` con i18n |
| Timezone conversion | SI | NO | Implementar con `Intl.DateTimeFormat` |
| Date calculation (add/subtract) | SI | NO | Implementar `addDays()`, `subtractMonths()`, etc. |
| Date ranges | SI | NO | Implementar `DateRange` con `contains()`, `overlaps()` |
| Business days | SI | NO | Implementar `addBusinessDays()`, `isBusinessDay()` |
| Period start/end | SI | NO | Implementar `startOfMonth()`, `endOfYear()`, etc. |

**Nota:** Evaluar si es mejor implementar esto desde cero o usar `date-fns` como dependencia y crear wrappers con la API del meta-framework. `date-fns` es tree-shakeable y muy mantenida.

#### 3.2. `mapper-utils` - Alcanzar paridad con Java

| Feature | Java | NestJS | Accion |
|---------|:---:|:---:|--------|
| Nested recursive mapping | SI | NO | Implementar mapping recursivo con config nested |
| Circular reference detection | SI | NO | Implementar con Set de referencias visitadas |
| Type converters registrables | SI | NO | Implementar `TypeConverter` interface + registry |
| MappingResult con metadata | SI | NO | Implementar resultado con campos mapeados/omitidos/warnings |
| Null strategy (SKIP/MAP/THROW) | SI | NO | Implementar enum + logica en mapByConvention |

#### 3.3. `api-standard` - Agregar funcionalidad

| Feature | Accion |
|---------|--------|
| `PageInfo.totalPages` auto-calculado | `Math.ceil(totalElements / size)` |
| `PageInfo.hasNext` / `hasPrevious` | Booleanos derivados |
| Metodo `withMetadata()` en ApiResponse | Builder fluent para agregar metadata |
| Metodo `withLinks()` en ApiResponse | Builder fluent para HATEOAS |
| Metodo `withPagination()` en ApiResponse | Builder fluent para PageInfo |

---

### 4. Implementar @Traced y @Metered en NestJS

Los decoradores existen en `observability-utils` pero **no hay ningun interceptor NestJS que los procese**. En Java, esto funciona via AOP aspects (`TracedAspect`, `MeteredAspect`). En NestJS, se necesita un interceptor:

```typescript
@Injectable()
export class TracedInterceptor implements NestInterceptor {
  constructor(private readonly tracer: Tracer) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const handler = context.getHandler();
    const metadata: TracedMetadata = Reflect.getMetadata(TRACED_METADATA_KEY, handler);
    
    if (!metadata) return next.handle();

    const span = this.tracer.startSpan(metadata.spanName ?? `${context.getClass().name}.${handler.name}`);
    
    return next.handle().pipe(
      tap(() => span.setStatus({ code: SpanStatusCode.OK })),
      catchError(err => {
        span.setStatus({ code: SpanStatusCode.ERROR, message: err.message });
        span.recordException(err);
        throw err;
      }),
      finalize(() => span.end()),
    );
  }
}
```

Lo mismo para `@Metered` con un `MeteredInterceptor` que use el `MeterProvider` de OTel.

---

### 5. Implementar Golden Signals Filter

El lado Java tiene un `GoldenSignalsFilter` completo (latencia, trafico, errores, saturacion). El lado NestJS no tiene equivalente.

```typescript
@Injectable()
export class GoldenSignalsMiddleware implements NestMiddleware {
  private readonly requestDuration: Histogram;
  private readonly requestsTotal: Counter;
  private readonly errorsTotal: Counter;
  private readonly activeRequests: UpDownCounter;

  constructor(@Inject(OBSERVABILITY_OPTIONS) private options: ResolvedObservabilityOptions) {
    const meter = metrics.getMeter('golden-signals');
    this.requestDuration = meter.createHistogram(MetricNames.HTTP_REQUEST_DURATION_SECONDS);
    this.requestsTotal = meter.createCounter(MetricNames.HTTP_REQUESTS_TOTAL);
    this.errorsTotal = meter.createCounter(MetricNames.HTTP_ERRORS_TOTAL);
    this.activeRequests = meter.createUpDownCounter(MetricNames.HTTP_REQUESTS_IN_FLIGHT);
  }

  use(req: Request, res: Response, next: NextFunction): void {
    const start = performance.now();
    this.activeRequests.add(1);
    this.requestsTotal.add(1, { method: req.method, route: req.path });

    res.on('finish', () => {
      const duration = (performance.now() - start) / 1000;
      this.requestDuration.record(duration, { method: req.method, route: req.path, status: String(res.statusCode) });
      this.activeRequests.add(-1);
      if (res.statusCode >= 400) {
        this.errorsTotal.add(1, { method: req.method, route: req.path, status: String(res.statusCode) });
      }
    });

    next();
  }
}
```

---

### 6. Mejorar el Exception Filter

El `ApiStandardExceptionFilter` actual solo maneja `HttpException` y `Error` generico. Deberia cubrir:

```typescript
@Catch()
export class ApiStandardExceptionFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentHost): void {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse();

    if (exception instanceof HttpException) {
      const status = exception.getStatus();
      const exceptionResponse = exception.getResponse();

      // Manejo especial para ValidationPipe errors (class-validator)
      if (typeof exceptionResponse === 'object' && 'message' in exceptionResponse) {
        const messages = Array.isArray(exceptionResponse.message)
          ? exceptionResponse.message
          : [exceptionResponse.message];
        const errors: ApiError[] = messages.map(msg => ({ code: `VALIDATION_${status}`, message: msg }));
        return response.status(status).json(ApiResponse.error(status, errors));
      }

      return response.status(status).json(ApiResponse.error(status, exception.message));
    }

    // TypeORM / Prisma errors
    if (exception instanceof QueryFailedError) { /* 409 o 500 */ }
    
    // Timeout errors
    if (exception instanceof TimeoutError) { /* 504 */ }

    // Fallback
    response.status(500).json(ApiResponse.error(500, 'Internal Server Error'));
  }
}
```

---

### 7. Agregar `forRootAsync()` a todos los modules

Actualmente los modules solo soportan `forRoot()` sincrono. Se necesita `forRootAsync()` para inyectar `ConfigService`:

```typescript
// Caso de uso: leer config de .env via @nestjs/config
NovaModule.forRootAsync({
  imports: [ConfigModule],
  inject: [ConfigService],
  useFactory: (config: ConfigService) => ({
    mask: {
      enabled: config.get('MASK_ENABLED', true),
      defaultCountry: config.get('MASK_DEFAULT_COUNTRY', 'PE'),
    },
  }),
}),
```

Esto requiere implementar el patron `createAsyncProviders()` en cada module.

---

## Build Tooling y DX (Sprint 4-6)

### 8. Crear un Generador de Proyectos

No existe ningun mecanismo para scaffoldear un proyecto nuevo con el meta-framework NestJS.

**Opciones:**

| Opcion | Esfuerzo | UX | Distribucion |
|--------|----------|-----|-------------|
| Script bash (`init.sh`) | Bajo | Buena (interactivo) | Requiere clonar repo |
| `create-nova` npm package | Medio | Excelente (`npm init @nova`) | npm registry |
| NestJS Schematics plugin | Alto | Integrado con `nest generate` | npm registry |
| Nx Plugin | Alto | Excelente para monorepos | npm registry |

**Recomendacion:** `create-nova` como paquete npm con `npx`:

```bash
npx @ahincho/nova-create my-app

# Genera:
my-app/
  package.json           <- deps: nestjs-starter, nestjs-observability
  tsconfig.json          <- extends @ahincho/nova-nestjs-parent/tsconfig
  eslint.config.mjs      <- extends parent
  prettier.config.mjs    <- extends parent
  jest.config.ts         <- extends parent
  .env.example
  .gitignore
  Dockerfile
  docker-compose.yml
  src/
    main.ts              <- NovaFactory.create()
    app.module.ts         <- NovaModule.forRoot() + ObservabilityModule.forRoot()
    health/
      health.controller.ts
  test/
    app.e2e-spec.ts
```

---

### 9. Crear CI/CD Workflows

El lado Java tiene 8 workflows reutilizables. El lado NestJS tiene zero.

**Workflows necesarios:**

| Workflow | Contenido |
|----------|-----------|
| `reusable-build-node.yml` | Checkout, setup Node, `npm ci`, `npm run build`, `npm test` |
| `reusable-lint-node.yml` | `npm run lint`, `npm run format:check` |
| `reusable-publish-node.yml` | `npm publish` a GitHub Packages |
| `reusable-version-bump-node.yml` | Bump version en package.json basado en labels de PR |
| `reusable-security-node.yml` | `npm audit --audit-level=high` |

---

### 10. Crear Infrastructure

El lado Java tiene `nova-infrastructure/` con Docker Compose para OTel Collector + Grafana stack. El lado NestJS no tiene nada.

**Accion:** Reutilizar el mismo `nova-infrastructure/` del lado Java. El stack de observabilidad (OTel Collector, Tempo, Loki, Mimir, Grafana) es independiente del lenguaje.

Agregar al ejemplo NestJS un `docker-compose.yml` que referencia la infraestructura compartida o incluye su propia version minima.

---

## Documentacion (Sprint 3+)

### 11. READMEs por Paquete

Actualmente **ningun paquete tiene README**. Cada uno necesita al minimo:

```markdown
# @ahincho/nova-mask-utils

> Libreria pura de enmascaramiento de datos sensibles.

## Instalacion
npm install @ahincho/nova-mask-utils

## Uso Rapido
import { MaskEngine, MaskType } from '@ahincho/nova-mask-utils';

const result = MaskEngine.mask('user@mail.com', MaskType.EMAIL);
console.log(result.maskedValue); // u***@mail.com

## API
- MaskEngine.mask(value, type, config?)
- @Masked(options?)
- @MaskedClass()
- @SkipMasking()

## Estrategias soportadas
| Tipo | Ejemplo | Resultado |
...
```

### 12. Guia de Inicio Rapido

Un documento central que explique como usar el meta-framework:

```markdown
# Nova Platform NestJS - Getting Started

## 1. Crear proyecto
npm init @nova my-app

## 2. Configurar
Editar .env con las variables de entorno.

## 3. Ejecutar
npm run start:dev

## 4. Verificar
curl http://localhost:3000/health
```

---

## Roadmap Visual

```
Fase 1 (Sprint 1-2): Fundamentos
  [x] Arquitectura de 5 niveles definida
  [x] Librerias puras implementadas (5)
  [x] NestJS Modules implementados (3)
  [x] Meta-framework starter
  [x] BOM + Parent
  [x] Ejemplo funcional
  [ ] Tests para date-utils
  [ ] Tests para mapper-utils
  [ ] Tests para api-standard
  [ ] Tests para observability-utils
  [ ] Tests de integracion para NestJS modules
  [ ] Resolver duplicacion de nestjs-observability
  [ ] Fix version Node.js (>= 22 en vez de >= 24)
  [ ] Integrar ObservabilityModule en el starter

Fase 2 (Sprint 3-5): Solidificacion
  [ ] Completar date-utils (paridad con Java)
  [ ] Completar mapper-utils (nested, circular, converters)
  [ ] Implementar TracedInterceptor y MeteredInterceptor
  [ ] Implementar GoldenSignalsMiddleware
  [ ] Mejorar ApiStandardExceptionFilter (validation, ORM errors)
  [ ] Agregar forRootAsync() a todos los modules
  [ ] READMEs por paquete
  [ ] CI/CD workflows (build, lint, publish, security)
  [ ] Generador de proyectos (create-nova)

Fase 3 (Sprint 6-8): Produccion
  [ ] Cobertura minima 80%
  [ ] Documentacion completa (Getting Started, API, Migration)
  [ ] Docker Compose para ejemplo (reutilizar infra de Java)
  [ ] Publicacion a GitHub Packages (o npm)
  [ ] NestJS Schematics (nest generate nova-module)
  [ ] Soporte para Fastify (ademas de Express)
  [ ] Security module (JWT, Guards, RBAC)
  [ ] Database module (TypeORM/Prisma helpers, migrations)
```

---

## Metricas de Exito

| Metrica | Valor Actual | Objetivo Fase 1 | Objetivo Fase 2 |
|---------|:---:|:---:|:---:|
| Modulos con tests | 1/10 | 10/10 | 10/10 |
| Cobertura promedio | ~0% | >60% | >80% |
| Documentacion (READMEs) | 0/10 | 10/10 | 10/10 + guias |
| CI/CD workflows | 0 | 5 | 5+ |
| Paridad de features con Java | ~60% | ~80% | ~95% |
| Tiempo para nuevo proyecto | Manual | <2 min (generator) | <1 min (npx) |

---

## Decisiones Pendientes

1. **Resolver duplicacion de nestjs-observability:** Monorepo (Turborepo) vs standalone. Ver seccion P1.
2. **Version minima de Node.js:** 22 (LTS) vs 24 (current). Recomendacion: 22.
3. **NestJS 11 exclusivo vs backward compat:** Soportar NestJS 10 ampliaria la adopcion.
4. **Mono-repo vs multi-repo:** Actualmente cada paquete es un directorio separado excepto commons que es Turborepo. Evaluar consolidar todo en un solo Turborepo.
5. **date-utils: implementar vs usar date-fns:** date-fns es tree-shakeable y bien mantenido. Wrapper vs reimplementacion.
6. **BOM: mantener vs eliminar:** Los BOMs npm no enfuerzan versiones. Podrian eliminarse y documentar versiones en un CHANGELOG.
7. **Verdaccio vs link local:** Actualmente se usa Verdaccio para desarrollo local. Alternativa: `npm link` o `file:` references (ya se usan parcialmente).
8. **Express vs Fastify:** El starter asume Express. NestJS soporta Fastify nativamente. Decidir si soportar ambos.
