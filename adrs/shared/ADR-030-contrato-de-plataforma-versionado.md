# ADR-030: Contrato de Plataforma Versionado, Independiente del Codigo

## Estado

Propuesta
**Scope:** `shared` (Java + NestJS)

## Fecha

2026-09-20

## Contexto

El invariante que sostiene Nova es que **los tres stacks digan lo mismo por HTTP**. Un frontend
que habla con un BFF NestJS y con un microservicio Quarkus deberia poder escribir un solo parser,
un solo manejo de error y un solo tablero.

Hoy no puede, y no es una hipotesis: esta medido en el codigo de los tres stacks.

### El sobre no tiene la misma forma

| | NestJS (`api-standard/api-response.ts`) | Java (`ApiResponse.java`) |
|---|---|---|
| Campos | `success`, `status`, `data`, `errors` | los mismos, mas `metadata`, `links`, `rateLimitInfo`, `pageInfo` |
| Entrada de error | `code`, `message`, `field` | `code`, `message`, `field`, `details` |
| `traceId` | **no viaja en el cuerpo**, solo en la cabecera de respuesta | dentro de `metadata`, junto a `timestamp`, `apiVersion` y `processingTimeMs` |

Un cliente que lea `response.metadata.traceId` funciona contra Java y falla contra NestJS. Uno
que lea la cabecera funciona contra NestJS y no encuentra nada garantizado en Java.

### El codigo de error no significa lo mismo

Es la divergencia mas grave, porque `code` existe justamente para que el cliente ramifique sobre
el en vez de sobre el `status`.

| Situacion | NestJS | Spring Boot | Quarkus |
|---|---|---|---|
| 5xx no controlado | `INTERNAL_SERVER_ERROR` | `ERROR` | `INTERNAL_ERROR` |
| 400 | `BAD_REQUEST` | `ERROR` | `BAD_REQUEST` |
| 404 | `NOT_FOUND` | `ERROR` | (cae a 500) |
| Validacion de DTO | `VALIDATION_ERROR`, una entrada por campo | no cubierto | no cubierto |

En Spring **el codigo es una constante**: `ApiResponse.error(int, String)` construye siempre
`ApiError.of("ERROR", message)`, asi que el campo no lleva informacion. En Quarkus el 5xx dice
`INTERNAL_ERROR` y en NestJS `INTERNAL_SERVER_ERROR`; son dos cadenas distintas para el mismo
hecho, y un `switch` del cliente falla en uno de los dos.

Hay ademas un defecto que esta divergencia tapa: `GlobalExceptionHandler` de Spring es un
`@RestControllerAdvice` plano, no extiende `ResponseEntityExceptionHandler` y no maneja
`MethodArgumentNotValidException`. Un DTO invalido cae en `@ExceptionHandler(Exception.class)` y
sale como **500 "Error interno del servidor"** en vez de 400 con el detalle por campo. La suite
de conformidad del ADR siguiente es lo que lo probaria.

### Las sondas no estan en el mismo sitio

NestJS sirve `/health/live` y `/health/ready`, mas una ruta heredada configurable. Spring expone
las suyas por Actuator y Quarkus por SmallRye. Tres conjuntos de rutas distintos, asi que el
target group de un servicio no se puede configurar igual que el del vecino.

### Por que ocurrio

**Porque el contrato solo existe como codigo, y existe tres veces.** No hay ningun artefacto que
las tres implementaciones tengan que satisfacer: cada una es su propia definicion, y cuando dos
definiciones se separan nada lo reporta. Los README documentan el contrato, pero un README no
falla un build.

## Decision

**Extraer el contrato a una especificacion independiente del codigo, versionada por separado de
las implementaciones, dentro de `nova-docs`.**

```
spec/
  CHANGELOG.md
  VERSION                     la version del contrato, propia
  envelope/                   forma del sobre, en JSON Schema
  errors/                     catalogo de codigos, normativo
  health/                     contrato de las sondas, fragmento OpenAPI
  tracing/                    cabeceras de correlacion y su propagacion
  config/                     nombres de las claves de configuracion
  logging/                    formato del log estructurado
```

Tres propiedades, y las tres son la decision:

**La especificacion es normativa y el codigo la implementa**, no al reves. Cuando el codigo y la
spec discrepan, el defecto esta en el codigo. Eso invierte lo que pasa hoy.

**Se versiona con su propio numero**, no con el de `@ahincho/nova-nestjs` ni con el del BOM de
Java. Un stack puede publicar diez veces sin tocar el contrato, y el contrato puede subir de
version sin que ningun stack se haya movido todavia. Atarlos obligaria a publicar tres artefactos
para arreglar una coma de la spec.

**Se expresa en formatos que una maquina puede verificar**: JSON Schema para el sobre y las
entradas de error, fragmentos OpenAPI para las rutas de salud. Un documento en prosa vuelve a ser
un README, y ya sabemos que eso no detiene una divergencia.

Lo que **no** entra en la spec: nada de dominio, y nada que solo una organizacion necesite. El
prefijo `SECRET_` de UTP, la ruta `api/v1/health` heredada y la lista de ambientes son adaptacion
de entorno, no contrato de plataforma.

## Alternativas descartadas

**Elegir un stack como referencia y generar los otros.** Es lo que haria un generador de codigo a
partir de OpenAPI, y no aplica: los tres runtimes tienen modelos de ejecucion distintos y lo que
se comparte es la forma de la respuesta, no la implementacion. Ademas deja al stack de referencia
sin nadie que lo verifique.

**Publicar el contrato como un paquete de codigo compartido.** No hay un artefacto que sea a la
vez dependencia Maven y dependencia npm. Cualquier intento termina en dos paquetes que hay que
mantener sincronizados, que es el problema actual con un paso mas.

**Dejar el contrato en los README y agregar tests en cada repo.** Es mas barato y es casi lo que
hay. Falla por lo mismo: tres suites escritas contra tres lecturas del mismo texto no detectan
que las lecturas difieren. Solo un artefacto compartido lo hace.

**Adoptar RFC 7807 y retirar el sobre.** No se descarta: se deja abierta abajo, porque la decision
tiene consecuencias que exceden a este ADR.

## Preguntas abiertas

Tres puntos que este ADR **no** resuelve a proposito, porque resolverlos en silencio seria elegir
por el equipo.

**1. Cual sobre gana.** Java tiene ocho campos y NestJS cuatro. Converger rompe a alguien: si gana
el de cuatro, los servicios Java pierden `metadata.traceId`, `links` y `pageInfo`; si gana el de
ocho, NestJS agrega cuatro campos que hoy ningun consumidor pide y que estarian casi siempre en
null. Una tercera via es declarar los cuatro campos como el nucleo obligatorio y los otros cuatro
como extensiones opcionales, lo que hace la spec mas debil pero no rompe a nadie.

**2. RFC 7807 o el sobre.** El encargo pide alinear los errores con RFC 7807, y **son
incompatibles**: 7807 define un cuerpo plano -`type`, `title`, `status`, `detail`, `instance`- con
`Content-Type: application/problem+json`, sin `success` y sin lista de errores. Adoptarlo no es
alinear el sobre, es reemplazarlo en las respuestas de error, y con eso el cliente pasa a tener
dos formas de cuerpo segun el resultado. Lo que 7807 da a cambio es un formato que herramientas de
terceros ya entienden. Se decide antes de escribir `errors/`, no despues.

**Resuelta (2026-09-30), en [ADR-031](ADR-031-modulo-de-errores-por-capas-con-trazabilidad.md):** los
errores se escriben en el sobre de Nova, igual en los tres stacks. RFC 7807 queda posible como otro
`ErrorSerializer`, detrás del puerto que define ese ADR. De paso, `metadata.traceId` pasa a ser
común: NestJS suma `metadata` a su sobre. El resto de la pregunta 1 sigue abierta.

**3. Que significa un major del contrato.** Si la spec sube a 2.0, que pasa con un servicio
desplegado que implementa la 1.x. Depende de la politica de soporte y por ahora no tiene
respuesta.

## Consecuencias

### Positivas

- La divergencia deja de ser invisible: pasa a ser un archivo que dos implementaciones citan.
- Habilita la suite de conformidad cruzada, que sin un artefacto normativo no tiene contra que
  verificar.
- Un consumidor puede leer el contrato sin leer tres bases de codigo en dos lenguajes.
- El contrato se puede versionar y deprecar como producto, que es lo que pide la politica de
  soporte.

### Negativas

- **Aparece un artefacto mas que mantener**, y uno que puede quedarse viejo en silencio igual que
  los README. Solo la suite de conformidad lo evita, asi que este ADR sin el siguiente no sirve
  de mucho.
- **Converger el sobre y los codigos es un cambio incompatible en al menos dos stacks.** No hay
  version de esto que no rompa a alguien, y el costo real lo pagan los servicios desplegados.
- **Escribir la spec revela mas defectos de los que arregla en el corto plazo.** El 500 en las
  validaciones de Spring es el primero; es probable que no sea el ultimo.
- El stack Java queda con mas trabajo que NestJS, porque su implementacion esta repartida entre
  la libreria pura, el starter de Spring y la extension de Quarkus.

## Referencias

- [ADR-001: Arquitectura del Meta-Framework en 5 Niveles](ADR-001-arquitectura-meta-framework-cinco-niveles.md)
- [ADR-014: Observabilidad - Four Golden Signals](ADR-014-observabilidad-four-golden-signals.md)
- [ADR-029: Sin Reintentos ni Corte de Circuito en el Cliente HTTP](../nest/ADR-029-sin-reintentos-en-el-cliente-http.md)
- `nova-java-api-standard`: `response/ApiResponse.java`, `error/ApiError.java`, `metadata/ApiMetadata.java`
- `nova-java-commons-spring-boot-starter`: `nova-api-standard-starter/.../web/GlobalExceptionHandler.java`
- `nova-java-api-standard-quarkus-extension`: `mapper/ApiExceptionMapper.java`
- `nova-nestjs`: `packages/core/src/api-standard/`, `packages/core/src/health/`, `packages/core/src/observability/`
- RFC 7807, *Problem Details for HTTP APIs*
