# ADR-050: Los Errores por Capas en Quarkus: la Extensión del Estándar de API 3.0.0

## Estado

Aceptada (2026-10-01), con las recomendaciones de sus preguntas abiertas. Es el segundo punto del plan que Angel aprobó el mismo día: llevar
[ADR-031](../shared/ADR-031-modulo-de-errores-por-capas-con-trazabilidad.md) a la extensión de
Quarkus, que hoy es el único stack que no lo aplica.
**Scope:** `java`, solo Quarkus.
**Aplica:** ADR-031 a `nova-java-10-api-standard-quarkus-extension`, con la forma de extensión de
[ADR-049](../shared/ADR-049-secretos-en-quarkus-y-nestjs.md) y la imagen nativa de
[ADR-045](ADR-045-imagen-nativa-junto-a-la-jvm.md).
**Completa:** lo que ADR-031 no dice de Quarkus: qué excepciones del framework se leen por su
status y cómo se registran los puertos en nativo.

## Fecha

2026-10-01

## Contexto

ADR-031 ya decidió lo esencial para Quarkus: la integración vive en `nova-java-10`, los puertos de
Nova son `@DefaultBean` y la extensión sale con versión mayor. Spring Boot lo implementó en el
starter 3.0.0 y NestJS en la 0.16.0. Quarkus sigue en la 2.0.1, y medido el 2026-10-01 responde
así:

| Qué | Extensión 2.0.1 | Spring 3.0.1 y NestJS 0.16.0 |
|---|---|---|
| `IllegalArgumentException` | 400 `BAD_REQUEST`, con el mensaje de la excepción | 500 `INTERNAL_SERVER_ERROR` |
| `SecurityException` | 403 `FORBIDDEN` | 500 `INTERNAL_SERVER_ERROR` |
| cualquier otro 5xx | `INTERNAL_ERROR`, «Internal server error» | el código de su status y el mensaje del catálogo |
| una ruta que no existe | 500, porque `NotFoundException` cae en el mapper de `Throwable` | 404 `NOT_FOUND` |
| un error de validación o un cuerpo ilegible | 500 | 400 `BAD_REQUEST`, con los errores por campo |
| `metadata.traceId` | no hay `metadata` | siempre |
| la línea de log | sin `traceId`, `layer` ni `upstream` | los cuatro campos, y el nivel sale de la capa |
| el contador `nova.errors` | no existe | con las etiquetas `layer` y `code` |

**Hay un riesgo que ya está activo.** El BOM 3.1.0 gestiona `nova-api-standard` 1.1.0, que trae
`DomainError` y las demás clases de ADR-031, junto a la extensión 2.0.1. Un servicio Quarkus sobre
ese BOM puede lanzar `DomainError.notFound(...)` hoy, y la extensión lo responde como 500, lo
registra como incidente con su stack trace y no le pone `traceId`.

**La extensión es una librería con nombre de extensión.** Es un único `java-library` con un índice
de Jandex, sin módulo de deployment. ADR-049 ya explicó por qué eso no alcanza en nativo, y aquí
aplica dos veces:

- `TraceIdCapture` de `nova-api-standard` encuentra su `TraceIdSource` con `ServiceLoader`, y en una
  imagen nativa de Quarkus `ServiceLoader` solo ve lo que se registró al construirla.
- El sobre se arma dentro de un mapper de excepciones, donde el análisis de la imagen nativa no lo
  ve. Es el mismo defecto que obligó a sacar el starter de Spring 3.0.1: sin registrar los records
  para reflexión, cada respuesta de error termina en 500.

**Los servicios Quarkus arman el sobre de éxito a mano.** Los recursos de los ejemplos 04 y 06
devuelven `ApiResponse.ok(...)`, porque la extensión no registra un filtro de respuesta. ADR-034
pedía medir esto antes de implementar el puerto en Quarkus, y queda medido: hoy ningún consumidor
depende de que una respuesta de éxito salga sin sobre.

## Decisión

**La extensión pasa a la 3.0.0 como una extensión de verdad, con módulo de deployment, y responde
los errores exactamente como el starter de Spring: los mismos puertos, el mismo catálogo, la misma
línea de log y la misma suite de contrato.**

### Una extensión con módulo de deployment

| Módulo | `artifactId` | Qué tiene |
|---|---|---|
| runtime | `nova-api-standard-quarkus-extension` (el mismo de hoy) | los mappers, los productores de los puertos, el `TraceIdSource`, el contador y el `ObjectMapperCustomizer` |
| deployment | `nova-api-standard-quarkus-extension-deployment`, nuevo | los pasos de build: registrar los beans, el `TraceIdSource` y los records del sobre, y activar el contador si hay Micrometer |

Sigue el nombre de ADR-049, `nova-<capacidad>-quarkus-extension-deployment`. Las coordenadas del
runtime no cambian, y Quarkus resuelve el deployment solo, con la misma versión.

Los pasos de build son tres:

- `AdditionalBeanBuildItem` por cada bean de la extensión. Desde ahí, un servicio ya no necesita
  `quarkus.index-dependency` para que la extensión funcione, como hoy declara el ejemplo 06.
- `ServiceProviderBuildItem` para `TraceIdSource`, y `ReflectiveClassBuildItem` para `ApiResponse`,
  `ApiError`, `ApiMetadata` y los demás records que viajan en el cuerpo.
- El contador `nova.errors` se registra solo si está la capacidad `io.quarkus.micrometer`. Sin ella,
  el contador es el vacío y la extensión no arrastra Micrometer.

### Los puertos, reemplazables con un bean

| Bean | Implementación de Nova |
|---|---|
| `ErrorStatusMapper` | `NovaErrorStatusMapper` |
| `ErrorCatalog` | `NovaErrorCatalog` |
| `ErrorSerializer` | `NovaErrorSerializer` |
| `ErrorPorts` | los tres de arriba |
| `ErrorCounter` | vacío, o el de Micrometer |

Cada uno sale de un productor `@DefaultBean @Singleton`, así que un servicio o una extensión de una
organización lo reemplaza declarando el suyo. Es el mecanismo que ADR-031 nombra para Quarkus, y el
mismo papel de `@ConditionalOnMissingBean` en Spring. Los mappers no son reemplazables, porque son
el núcleo: escriben el log y sanean antes de llamar a los puertos, que es la regla de ADR-034.

`ErrorCounter` es de la integración, no del modelo, porque depende de Micrometer. La extensión
declara el suyo, con el mismo nombre y la misma forma que el del starter de Spring.

### Qué excepciones se leen y cómo

| Excepción | Status | Capa | Mensaje al cliente |
|---|---|---|---|
| un `NovaError` | el de `ErrorStatusMapper` | la del error | el propio si es 4xx; si no, el del catálogo |
| `WebApplicationException` y sus subclases (`NotFoundException`, `NotAllowedException`, `NotSupportedException`...) | el de su respuesta | 4xx `application`; 502, 503 o 504 `infrastructure`; otro 5xx `platform` | el del catálogo |
| `ConstraintViolationException` sobre la entrada | 400 | `application` | `BAD_REQUEST`, con un error por violación |
| `ConstraintViolationException` sobre el valor de retorno | 500 | `platform` | el del catálogo |
| el cuerpo que Jackson no puede leer | 400 | `application` | «No se pudo leer el cuerpo de la solicitud», el mismo texto fijo que Spring |
| `UnauthorizedException` y `AuthenticationFailedException` de Quarkus Security | 401 | `application` | el del catálogo |
| `ForbiddenException` de Quarkus Security | 403 | `application` | el del catálogo |
| cualquier otra, incluidas `IllegalArgumentException` y `SecurityException` | 500 | `platform` | el del catálogo |

Es la regla de ADR-031: **una excepción del framework se lee por su status**. En Quarkus el papel del
`ErrorResponse` de Spring y del `HttpException` de NestJS lo hace `WebApplicationException`. Quarkus
Security no extiende `WebApplicationException`, pero sus excepciones tienen un status inequívoco y se
leen igual. Una `SecurityException` del JDK no es del framework: no dice si falta la identidad o si
falta el permiso, y por eso sale como 500, igual que en Spring.

- **El campo de una violación** es el último nodo de su ruta de propiedad: `create.request.name` se
  escribe `name`. Una violación de toda la clase lleva `field` vacío, como pide ADR-031.
- **Una `WebApplicationException` conserva sus headers**, como `Allow` en un 405. El cuerpo sí lo
  escribe el serializador.

### La trazabilidad y el log

- **`TraceIdSource` lee la clave `traceId` del MDC de JBoss Logging**, que llena
  `quarkus-opentelemetry`. Es la misma clave que lee el starter de Spring.
- **Si no hay `traceId`**, el mapper genera uno, lo pone en el MDC para la línea de log y escribe el
  mismo en `metadata.traceId`. Así lo que el cliente cita siempre está en el log.
- **La línea de log** lleva `traceId`, `layer`, `code`, `status` y, si hay, `upstream` como entradas
  del MDC, de modo que `quarkus-logging-json` las escribe como campos. `domain` y `application` van
  en `WARN` sin stack trace; `infrastructure` y `platform`, en `ERROR` con la causa.
- **`Retry-After`** pasa de los headers de `SerializedError` a la respuesta de JAX-RS.

### Cómo se prueba

- **La suite de contrato de ADR-031**, los nueve casos, como `@QuarkusTest` en el módulo de
  deployment, igual que la extensión de secretos. Suma la línea de log, el `traceId` generado, los
  headers de un 405 y un catálogo propio registrado como bean.
- **Una prueba en nativo en el PR de release**, como pide ADR-049 para sus extensiones: un error de
  cada capa con un `traceId` en el cuerpo, sobre la imagen compilada.
- **Las pruebas unitarias de hoy se reescriben**, porque afirman el comportamiento que esta versión
  cambia.

### Versión 3.0.0 y la receta

Es mayor porque cambia lo que un cliente recibe ante un error, como dice ADR-031. La receta va en el
README de la extensión, en «Migrating to 3.0.0», y el BOM la resume:

| Antes (2.x) | Desde la 3.0.0 | Qué hacer |
|---|---|---|
| `IllegalArgumentException` respondida como 400 con su mensaje | un `PlatformError`, respondido como 500 | lanzar `ApplicationError.invalidInput(...)` ante una entrada inválida |
| `SecurityException` respondida como 403 | 500 | lanzar `ApplicationError.forbidden(...)`, o dejar que Quarkus Security responda |
| `INTERNAL_ERROR` en todo 5xx | el código del status: `INTERNAL_SERVER_ERROR`, `BAD_GATEWAY`, `SERVICE_UNAVAILABLE` o `GATEWAY_TIMEOUT` | comparar contra el código del catálogo |
| mensajes genéricos en inglés, como `Internal server error` | los mensajes del catálogo en español | no comparar contra el texto del mensaje |
| un 404, 405 o 415 de Quarkus REST respondido como 500 | su status, con el código del catálogo | nada |
| un cuerpo sin `metadata` | `metadata.traceId` y `metadata.timestamp` | nada; es aditivo |
| `ApiExceptionMapper` | reemplazado por los mappers del núcleo y los puertos | reemplazar un puerto con un bean propio, en vez de un mapper más específico |
| `quarkus.index-dependency` para la extensión | innecesario | quitarlo |

### Lo que se mueve con ella

| Repositorio | Cambio |
|---|---|
| `nova-java-13-bom` | la 4.0.0: `nova-quarkus-bom` gestiona la extensión 3.0.0. Es mayor por la misma razón que lo fue la 3.0.0 con el starter de Spring |
| `nova-java-15-quarkus-parent` | importa el BOM 4.0.0 |
| `nova-example-04-quarkus-reference` y `nova-example-06-quarkus-code-with-nova` | aplican la receta: sus recursos lanzan `IllegalArgumentException` y sus pruebas esperan 400 |

Cada fila es su propio PR, en ese orden, después de publicar la extensión.

## Alternativas descartadas

**Seguir sin módulo de deployment.** Basta en la JVM, pero en nativo no encuentra el
`TraceIdSource` ni puede serializar el sobre. Es el mismo argumento de ADR-049.

**Una versión menor con un interruptor de transición**, que deje los códigos viejos detrás de una
propiedad. La enmienda de ADR-031 la descartó para Spring: dos comportamientos por una versión es
cuando más fácil es equivocarse, y la receta cabe en una tabla.

**Los mappers que Quarkus ya trae para la validación y la seguridad.** Responden con su propio cuerpo,
y el resultado por HTTP volvería a depender del stack.

**RFC 7807, con `quarkus-resteasy-problem`.** ADR-031 lo descartó como formato por defecto; queda
posible como otro `ErrorSerializer`.

**Mover la extensión al repositorio de `nova-api-standard`**, como pediría ADR-041 para una
capacidad nueva. Rompe las coordenadas de dos repositorios y su historia. ADR-041 rige para las
capacidades que nacen desde ahí, y el estándar de API es anterior.

## Preguntas resueltas

Angel aprobó las recomendaciones el 2026-10-01.

**1. El sobre de éxito, ¿en esta misma versión mayor?** ADR-034 deja pendiente un filtro de
respuesta que envuelva el éxito en Quarkus, como `ApiResponseInterceptor` en Spring. Los ejemplos ya
arman el sobre a mano, y un filtro que no toca una `ApiResponse` no los cambia. Lo que sí cambia es
un recurso que devuelve un objeto suelto, así que agregarlo después costaría una 4.0.0.
Resuelta: **incluirlo en la 3.0.0, en su propio PR**, con la regla de Spring de no envolver lo
que ya es un sobre ni las sondas de salud.

**2. Las pilas de errores propias de la plantilla y del arquetipo.** `nova-java-19-quarkus-template`
tiene su `DomainExceptionMapper` y su `GenericExceptionMapper`, y `nova-java-18-quarkus-archetype`
genera un mapper con RFC 7807, que ADR-031 descartó como formato por defecto. Ninguno usa la
extensión. Resuelta: **migrarlos después de la 3.0.0, un PR por repositorio**, para que lo que
generan responda como el resto.

**3. La autenticación que se rechaza antes de llegar a REST.** Con la autenticación proactiva de
Quarkus, un token inválido se responde en la capa HTTP, sin pasar por ningún mapper, y sale sin
cuerpo. Eso es de `nova-java-11-keycloak-quarkus-extension`. Resuelta: **medirlo con esa
extensión y decidirlo en su propio PR**. La 3.0.0 cubre las excepciones de seguridad que sí llegan
a REST.

## Implementación (2026-10-01)

La 3.0.0 salió con las dos partes. Lo que el contexto dice del sobre de éxito describe la 2.x: desde la
3.0.0 la extensión registra `ApiResponseFilter`, un `@ServerResponseFilter` que espeja
`ApiResponseInterceptor` de Spring. Un recurso devuelve el objeto y sale en el sobre con su status
real; una `ApiResponse` armada a mano pasa intacta, así que los ejemplos 04 y 06 no cambian en el
cable.

Difiere de Spring en seis puntos, todos a propósito y escritos en el README de la extensión:

| Caso | Spring | Quarkus 3.0.0 | Por qué |
|---|---|---|---|
| Respuesta de un mapper del servicio | se envuelve | sale tal cual | no se distingue del mapper de la extensión sin marcar cada respuesta |
| 206 y 3xx | se envuelven | salen tal cual | un 206 es un fragmento y el cuerpo de una redirección no lo lee nadie |
| Método que devuelve `null` | 200 con `data: null` | 204 | es la regla de JAX-RS |
| Número o booleano sin `@Produces(JSON)` | se envuelve | sale como texto | Quarkus REST lo escribe como texto |
| Excluir un método | no hay anotación | no hay anotación | se sale del sobre con `String`, `byte[]` o un flujo |
| `Accept` ilegible | — | la respuesta sale como está | el filtro no convierte en 500 lo que Quarkus REST contesta |

SmallRye Health, las métricas, OpenAPI y la Dev UI no pasan por el filtro, porque son rutas de Vert.x.
Un servicio que declara `quarkus.index-dependency` sobre la extensión no arranca con la 3.0.0:
el índice completo encuentra a la vez los dos productores del contador y los mappers de las
extensiones opcionales. Esas líneas no hacen falta desde que la extensión tiene módulo de deployment,
y la receta de migración manda quitarlas.

## Consecuencias

### Positivas

- Los tres stacks responden los mismos códigos y los mismos textos ante un error, y la suite de
  contrato lo comprueba también en Quarkus.
- Se cierra el riesgo del BOM 3.1.0: un `DomainError` deja de salir como 500.
- La segunda extensión de Nova con módulo de deployment, y la primera del estándar de API que
  funciona en nativo con su `traceId`.
- Una organización reemplaza el catálogo o el serializador con un bean, igual que en Spring.

### Negativas

- **Cambian los códigos de error de los servicios Quarkus.** Por eso la versión mayor y la receta.
- **El repositorio pasa de un módulo a dos**, con el build de extensión de Quarkus y sus tareas
  incompatibles con la caché de configuración, como en `nova-java-23-secrets`.
- **Quien declaraba un mapper más específico para cambiar el error** tiene que pasar a un puerto. Es
  lo que ADR-034 quería, pero es trabajo para ese servicio.

## Referencias

- [ADR-031: El Módulo de Errores por Capas, con Trazabilidad](../shared/ADR-031-modulo-de-errores-por-capas-con-trazabilidad.md)
- [ADR-034: Lo Duro y lo Reemplazable](../shared/ADR-034-puertos-con-implementacion-por-defecto.md)
- [ADR-035: Fallos de Upstream Clasificados con el Registro de RFC 9209](../shared/ADR-035-fallos-de-upstream-rfc-9209.md)
- [ADR-039: Nombres de Artefacto Derivados del Repositorio](../shared/ADR-039-nombres-de-artefacto-derivados-del-repositorio.md)
- [ADR-041: Un Repositorio por Capacidad](ADR-041-un-repositorio-por-capacidad.md)
- [ADR-045: La Imagen Nativa de GraalVM, junto a la JVM](ADR-045-imagen-nativa-junto-a-la-jvm.md)
- [ADR-049: Los Secretos en Quarkus y NestJS](../shared/ADR-049-secretos-en-quarkus-y-nestjs.md)
- `nova-java-10-api-standard-quarkus-extension`: `mapper/ApiExceptionMapper.java`
- `nova-java-08-commons-spring-boot-starter`: `GlobalExceptionHandler`, `ApiStandardAutoConfiguration`,
  `MdcTraceIdSource`, `ErrorCounter`
- `nova-java-23-secrets`: `NovaSecretsProcessor`, el primer módulo de deployment de Nova
- Quarkus, *Writing Your Own Extension*: `AdditionalBeanBuildItem`, `ServiceProviderBuildItem`,
  `ReflectiveClassBuildItem`
