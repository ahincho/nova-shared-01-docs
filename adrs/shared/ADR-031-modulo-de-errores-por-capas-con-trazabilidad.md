# ADR-031: El Módulo de Errores por Capas, con Trazabilidad

## Estado

Aceptada (2026-09-30). Se propuso el 2026-09-20, y Angel la aprobó con diez mejoras que quedan
incorporadas en la decisión: el sobre de Nova en vez de RFC 7807, un catálogo de códigos común,
los tipos de cada capa, `Retry-After`, un código por cada 5xx, `platform` como capa, el `traceId`
en `metadata`, un modelo que no arrastra el framework, una suite de contrato y una métrica.
También pidió que el módulo sea **un contrato con una implementación por defecto de Nova**,
extensible por organización, como UTP.
**Scope:** `shared` (Java y NestJS).
**Resuelve:** la pregunta 2 de [ADR-030](ADR-030-contrato-de-plataforma-versionado.md): los errores
se escriben en el sobre de Nova.

## Fecha

2026-09-20; aceptada el 2026-09-30.

## Contexto

Hoy un error en Nova se clasifica por **código HTTP**, y eso obliga a que quien lo lanza ya sepa de
HTTP.

En NestJS, un caso de uso que descubre que un curso no existe escribe
`throw new NotFoundException('Curso no encontrado')`. Funciona, y tiene dos costos. La regla de
negocio importa `@nestjs/common`, así que el dominio queda atado al transporte y ya no se puede
llamar desde un consumidor de cola sin arrastrar una semántica HTTP que ahí no significa nada. Y se
pierde información: un 404 puede ser «el alumno pidió un curso que no existe» o «el upstream
contestó 404», y las dos cosas se ven igual en el log y en el tablero, cuando una es normal y la
otra es un incidente.

En Java no hay ni siquiera eso. `GlobalExceptionHandler` mapea tres tipos, y la extensión de Quarkus
otros tres, distintos. Ninguna tiene noción de capa.

**Los tres stacks tampoco responden lo mismo.** Medido el 2026-09-30:

- `ApiResponse.error` de Java le pone el código `ERROR` a todo; Quarkus usa `BAD_REQUEST`,
  `FORBIDDEN` e `INTERNAL_ERROR`; NestJS deriva el código del status y colapsa todo 5xx a
  `INTERNAL_SERVER_ERROR`. Un cliente que decide por el código se comporta distinto según el stack.
- En Spring, un 201 dice `"status":200` en el cuerpo, un 404 sin cuerpo sale con `success:true`, y
  un header que falta o un cuerpo ilegible salen como 500.
- En otros sistemas que auditamos, el vencimiento de un proveedor sale como 500 en vez de 503, y
  se pierde el nombre del proveedor. Es el defecto que este módulo evita por diseño.

**La trazabilidad está a medias.** El `traceId` existe y viaja en una cabecera, pero no está en el
cuerpo de la respuesta -un alumno que fotografía «Error interno» no tiene nada que citar-, no está
garantizado en la línea de log si el error se registra fuera del contexto de la petición, y la capa
no es un campo que se pueda contar o alertar.

## Decisión

**Un módulo de errores que clasifica por capa, en los tres stacks, definido como un contrato con una
implementación por defecto de Nova.** El mapeo a HTTP lo hace la plataforma, no quien lanza.

### Las capas y sus tipos

| Capa | Tipo | HTTP | Qué significa |
|---|---|---|---|
| `domain` | `NOT_FOUND` | 404 | el recurso de negocio no existe |
| `domain` | `CONFLICT` | 409 | el estado del recurso no admite la operación, como confirmar un pedido cancelado |
| `domain` | `RULE_VIOLATION` | 422 | una regla de negocio dijo que no |
| `application` | `INVALID_INPUT` | 400 | la entrada no es válida; lleva los errores por campo |
| `application` | `CONFLICT` | 409 | la operación choca con otra en curso, como una clave de idempotencia en uso |
| `application` | `UNPROCESSABLE` | 422 | la entrada es válida pero no se puede procesar, como una clave reusada con otro contenido |
| `application` | `UNAUTHENTICATED` | 401 | falta la identidad o no es válida |
| `application` | `FORBIDDEN` | 403 | la identidad no tiene permiso |
| `application` | `RATE_LIMITED` | 429 | se superó un límite |
| `infrastructure` | `UNAVAILABLE` | 503 | una dependencia no está disponible |
| `infrastructure` | `TIMEOUT` | 504 | una dependencia no respondió a tiempo |
| `infrastructure` | `BAD_GATEWAY` | 502 | una dependencia respondió algo inválido |
| `platform` | `INTERNAL` | 500 | un defecto o una falla del propio servicio |

**La regla que ordena todo: `domain` y `application` son esperados, `infrastructure` y `platform`
son incidentes.** Los dos primeros se registran en `warn`, sin stack trace, y no despiertan a
nadie; los dos últimos van en `error`, con la causa completa, y alimentan la tasa de error de los
Four Golden Signals de ADR-014.

Hay **una clase por capa**, con su tipo como enumeración y una fábrica por tipo:
`DomainError.notFound(...)`, `ApplicationError.invalidInput(...)`, `InfrastructureError.timeout(...)`,
`PlatformError.internal(...)`. Una clase por caso multiplicaría la superficie, y un solo tipo con la
capa como texto libre deja que cada servicio invente su nombre.

**`platform` es una capa para las fallas durante una petición.** Un error de configuración al
arrancar no se responde: la aplicación no arranca, como ya hacen secrets y la configuración.

### Qué lleva un error

| Campo | Qué es | Llega al cliente |
|---|---|---|
| capa y tipo | la clasificación de la tabla | solo a través del status y el código |
| código | opcional; por ejemplo `ORDER_NOT_FOUND` | sí, si es 4xx |
| mensaje | un texto para la persona | sí, si es 4xx |
| errores por campo | campo, código y mensaje | sí, en `INVALID_INPUT` |
| `retryAfter` | cuánto esperar antes de reintentar | como header `Retry-After`, en segundos |
| proveedor | la dependencia que falló, en `infrastructure` | **no**: solo en el log |
| causa | la excepción original | **no**: solo en el log |
| `traceId` | tomado del contexto de la petición al construir el error | sí, en `metadata.traceId` |

El modelo **no importa ningún framework web**. Ese es el punto del cambio: el mismo caso de uso corre
detrás de HTTP o de un consumidor de cola.

### Un contrato con la implementación por defecto de Nova

El módulo define el modelo y **tres puertos**. Nova trae la implementación por defecto de cada uno, y
una organización pone la suya sin forkear: lo que es de una organización va en su perfil o su
starter, no en Nova, igual que en ADR-042.

| Puerto | Qué decide | Implementación de Nova |
|---|---|---|
| `ErrorCatalog` | el código y el mensaje genérico que ve el cliente | el código propio del error si es 4xx y lo trae; si no, el del catálogo de la plataforma, abajo |
| `ErrorStatusMapper` | el HTTP de cada capa y tipo | la tabla de arriba |
| `ErrorSerializer` | el cuerpo y los headers de la respuesta | el sobre de Nova, con `metadata.traceId` y `Retry-After` |

Cómo se reemplaza cada uno:

| Stack | Mecanismo |
|---|---|
| Spring Boot | un bean propio del tipo del puerto; el de Nova es `@ConditionalOnMissingBean` |
| Quarkus | un bean propio; el de Nova es `@DefaultBean` |
| NestJS | `NovaModule.forRoot({ errors: { catalog, statusMapper, serializer } })` |

Un perfil como `@ahincho/nova-profile-utp`, o un starter de UTP en Java, puede traer su catálogo con
sus propios códigos y textos, o su serializador, y un servicio de UTP lo activa con solo agregarlo.
Nova no trae ninguna implementación de UTP mientras no haya un consumidor que la use.

### El catálogo de códigos de la plataforma

El mismo en los tres stacks. Sale del que ya tiene NestJS, y le suma un código por cada 5xx.

| Status | Código | Status | Código |
|---|---|---|---|
| 400 | `BAD_REQUEST` | 410 | `GONE` |
| 401 | `UNAUTHORIZED` | 415 | `UNSUPPORTED_MEDIA_TYPE` |
| 403 | `FORBIDDEN` | 422 | `UNPROCESSABLE_ENTITY` |
| 404 | `NOT_FOUND` | 429 | `TOO_MANY_REQUESTS` |
| 405 | `METHOD_NOT_ALLOWED` | 500 | `INTERNAL_SERVER_ERROR` |
| 406 | `NOT_ACCEPTABLE` | 502 | `BAD_GATEWAY` |
| 408 | `REQUEST_TIMEOUT` | 503 | `SERVICE_UNAVAILABLE` |
| 409 | `CONFLICT` | 504 | `GATEWAY_TIMEOUT` |

Cualquier otro 4xx lleva `REQUEST_ERROR`, y cualquier otro 5xx, `INTERNAL_SERVER_ERROR`.

**Un 5xx nunca revela al proveedor.** El cuerpo lleva el código genérico de su status y el `traceId`.
Con eso el cliente sabe si conviene reintentar -un 503 o un 504 sí, un 500 no- sin conocer la
topología. El nombre del proveedor va solo al log, en el campo `upstream`.

### La trazabilidad se captura al nacer

Un error de Nova toma su `traceId` en el constructor, del contexto de petición vigente en ese
instante, y no al momento de responder, cuando el contexto puede haberse perdido.

- **En el cuerpo:** `metadata.traceId`, en los tres stacks. Java ya tiene ese campo en
  `ApiMetadata`; NestJS suma `metadata` a su sobre.
- **En el log:** `traceId`, `layer`, `code` y, si hay, `upstream`, como campos y no dentro del
  mensaje.
- **En las métricas:** un contador `nova.errors` con las etiquetas `layer` y `code`, en el registro de
  métricas del servicio, si lo tiene.

### Reintentar: `Retry-After`

Un error que se puede reintentar lleva `retryAfter`, y el serializador lo escribe como header
`Retry-After`, en segundos. Aplica a un `CONFLICT` de `application` por una operación en curso, a
`RATE_LIMITED` y a `UNAVAILABLE`. Es lo que necesita la idempotencia, y es la señal que ADR-029 nombra
para revisar su decisión de no reintentar.

### Lo que ya existe

- Las excepciones propias de cada framework se leen como `application` según su status: en Spring,
  las que implementan `ErrorResponse`; en NestJS, `HttpException`.
- `UpstreamHttpError` de NestJS es `infrastructure`.
- Cualquier otra excepción es `platform`, y sale como 500.

Así un servicio migra de a poco: lo que no cambió sigue respondiendo con el status correcto y el
código del catálogo.

### Dónde vive

| Stack | El modelo y los puertos, sin framework | La integración |
|---|---|---|
| Java | `nova-java-01-api-standard`, paquete `pe.edu.nova.java.libs.api.standard.error` | Spring: el starter de `nova-java-08`; Quarkus: la extensión de `nova-java-10` |
| NestJS | el subpath `@ahincho/nova-nestjs/errors`, que no importa Nest, con una regla de lint que lo verifica | `AllExceptionsFilter` y `NovaModule.forRoot` |

### La suite de contrato

Los tres stacks tienen que responder lo mismo, y eso se prueba con los mismos casos:

| Caso | Status | Código | Además |
|---|---|---|---|
| `DomainError.notFound` con código propio | 404 | `ORDER_NOT_FOUND` | el mensaje del error |
| `DomainError.conflict` sin código | 409 | `CONFLICT` | |
| `ApplicationError.invalidInput` con dos campos | 400 | `BAD_REQUEST` | un error por campo, con `field` |
| `ApplicationError.conflict` con `retryAfter` de 1 s | 409 | `CONFLICT` | `Retry-After: 1` |
| `ApplicationError.rateLimited` con 30 s | 429 | `TOO_MANY_REQUESTS` | `Retry-After: 30` |
| `InfrastructureError.timeout` de un proveedor | 504 | `GATEWAY_TIMEOUT` | el cuerpo no nombra al proveedor; el log sí |
| `InfrastructureError.unavailable` | 503 | `SERVICE_UNAVAILABLE` | |
| una excepción cualquiera | 500 | `INTERNAL_SERVER_ERROR` | el mensaje genérico |
| un catálogo propio registrado por el servicio | el del puerto | el del catálogo propio | prueba que el puerto se puede reemplazar |

En todos: `success: false`, `status` igual al HTTP y `metadata.traceId` presente. Hoy cada stack
corre estos casos en sus propias pruebas; un ejecutor compartido queda como pregunta abierta.

### Versión y migración

El cambio de `ERROR` a los códigos del catálogo cambia lo que ve un cliente de un servicio Java, así
que el starter de Spring y la extensión de Quarkus salen con **versión mayor**. La receta: un cliente
que comparaba contra `ERROR` pasa a comparar contra el código del catálogo o el código propio del
error; `ERROR` deja de aparecer. En NestJS los códigos ya eran los del catálogo, y lo nuevo es
`metadata`, que es aditivo.

## Alternativas descartadas

- **RFC 7807 como formato por defecto.** Es incompatible con el sobre: reemplaza el cuerpo de las
  respuestas de error, y el cliente pasaría a tener dos formas de cuerpo según el resultado. Queda
  posible como otro `ErrorSerializer`.
- **Seguir clasificando por código HTTP y solo agregar el `traceId` al cuerpo.** Resuelve la mitad
  visible del problema y deja el acoplamiento del dominio al transporte, que es lo que produce las
  falsas alertas.
- **Un solo tipo de error con la capa como texto libre.** Sin tipos, cada servicio inventa su nombre
  de capa y el tablero vuelve a agrupar por cadenas que no coinciden.
- **Una clase por cada caso.** Multiplica la superficie que los servicios tocan todos los días; una
  clase por capa con su tipo enumerado cubre lo mismo.
- **Las jerarquías de excepciones de cada framework**, como `ResponseStatusException` o
  `WebApplicationException`. Son tres jerarquías distintas, así que el resultado por HTTP volvería a
  depender del stack.
- **Reintentar o degradar automáticamente ante un error de `infrastructure`.** Ya decidido en ADR-029:
  el módulo clasifica y reporta, y no cambia el comportamiento ante el fallo.

## Preguntas abiertas

1. **Un ejecutor compartido de la suite de contrato**, que corra los mismos casos contra un servicio
   de cada stack. Por ahora cada stack los implementa en sus pruebas.
2. **Los textos por idioma.** Los mensajes genéricos van en español; una organización que necesite
   otros los pone en su `ErrorCatalog`. Si aparece más de un idioma por servicio, se decide aquí.
3. **El resto del sobre.** `links`, `pageInfo` y `rateLimitInfo` siguen existiendo solo en Java. Es
   la pregunta 1 de ADR-030.

## Consecuencias

### Positivas

- El dominio deja de importar el framework web, y el mismo caso de uso sirve para HTTP y para un
  consumidor.
- Un error reportado por un alumno se rastrea con lo que se ve en la pantalla.
- Se puede alertar sobre `infrastructure` sin que los 404 de negocio ensucien la señal.
- Los tres stacks responden los mismos códigos, y una suite lo comprueba.
- Una organización adapta códigos, textos o formato sin forkear.

### Negativas

- **Es superficie nueva en los tres stacks**, que los servicios van a tocar todos los días.
  Equivocarse en los nombres es caro de revertir.
- **Migrar un servicio existente no es automático del todo.** Decidir de qué capa es cada error
  existente lo tiene que mirar una persona.
- **Los servicios Java cambian sus códigos de error**, y eso pide una versión mayor.
- Durante la migración conviven dos caminos de error, y es cuando más fácil es equivocarse.

## Referencias

- [ADR-030: Contrato de Plataforma Versionado](ADR-030-contrato-de-plataforma-versionado.md)
- [ADR-014: Observabilidad - Four Golden Signals](ADR-014-observabilidad-four-golden-signals.md)
- [ADR-029: Sin Reintentos ni Corte de Circuito en el Cliente HTTP](../nest/ADR-029-sin-reintentos-en-el-cliente-http.md)
- [ADR-042: Secretos detrás de un Contrato](ADR-042-secretos-detras-de-un-contrato.md)
- `nova-nestjs`: `packages/core/src/api/filters/all-exceptions.filter.ts`,
  `packages/core/src/api-standard/error-code.ts`, `packages/core/src/http/upstream-http.error.ts`
- `nova-java-08-commons-spring-boot-starter`: `GlobalExceptionHandler`, `ApiResponseInterceptor`
- `nova-java-10-api-standard-quarkus-extension`: `ApiExceptionMapper`
