# ADR-047: La Idempotencia de las Operaciones, detrás de un Contrato

## Estado

Propuesta (2026-09-30). Angel pidió una capacidad de idempotencia con adaptadores para los tres
stacks, y que un subagente cree su repositorio y la implemente. Este ADR fija el diseño antes de
crearlo.
**Scope:** `shared` (Java y NestJS).
**Aplica:** [ADR-041](../java/ADR-041-un-repositorio-por-capacidad.md) para la forma del repositorio,
[ADR-042](ADR-042-secretos-detras-de-un-contrato.md) para el contrato con adaptadores y
[ADR-031](ADR-031-modulo-de-errores-por-capas-con-trazabilidad.md) para los errores.
**Primer consumidor:** pedidos de Plaza ([ADR-043](ADR-043-plaza-la-plataforma-de-compras.md)).

## Fecha

2026-09-30

## Contexto

En Plaza, el cliente puede reintentar una compra sin comprar dos veces: la compra lleva un
`Idempotency-Key`, y el pedido lo guarda (ADR-043). Pedidos lo resuelve hoy por su cuenta, y el
código tiene cinco defectos:

| Caso | Hoy | Lo que corresponde |
|---|---|---|
| El cliente B manda la clave del cliente A | **200 con el pedido de A**: sus líneas, su total y su reserva | la clave vale por cliente |
| La misma clave con otro cuerpo | 200 con el pedido original | 422 |
| Dos peticiones simultáneas con la misma clave | una gana; la otra, 500 | 409 con `Retry-After` |
| Falta la clave | 500 | 400 |
| Repetir una petición ya respondida | reconstruye el estado actual del pedido | la respuesta guardada |

Además, la clave no vence nunca. El primero es un defecto de seguridad: entrega los datos de otro
cliente.

En NestJS, la plataforma no tiene nada: CORS no deja pasar `Idempotency-Key` desde un navegador, y
el cliente HTTP no la propaga a los servicios.

**El estándar.** El borrador del IETF *The Idempotency-Key HTTP Header Field* llegó a la versión 07
(2025-10-15) y venció el 2026-04-18 sin ser RFC, pero es lo que siguen todas las implementaciones:
400 si falta la clave, 422 si llega con otro contenido, 409 si la original sigue en curso, y la
respuesta anterior si ya terminó. Stripe, la referencia de facto, guarda la respuesta 24 horas y la
marca con `Idempotent-Replayed: true`.

**El ecosistema, consultado el 2026-09-30:**

- **NestJS** tiene un paquete oficial, `@nestjs/idempotency` (MIT), que sigue el borrador: 400, 409
  con `Retry-After`, 422, replay con `Idempotent-Replayed`, un lock que se renueva con un token de
  dueño, huella SHA-256 y almacenes intercambiables. Pero va en la 0.0.1, publicada el 2026-09-25, y
  solo trae el almacén en memoria.
- **Spring Boot** no tiene nada oficial. Las librerías de la comunidad son 0.x o 1.0 de semanas, de
  un solo mantenedor, y difieren en lo que ve el cliente: una responde 422 cuando falta la clave,
  otra usa `Idempotent-Replay` sin la «ed», otra acota la clave globalmente por defecto, que es el
  mismo defecto de pedidos.
- **Quarkus** tiene `quarkus-http-idempotency` en Quarkiverse, marcada experimental, sin renovación
  del lock ni token de dueño: si un pago tarda más que el lock, otro intento lo puede ejecutar de
  nuevo. Además protege todo POST y PATCH por defecto.

## Decisión

**Una capacidad propia, con un contrato y la implementación por defecto de Nova, que responde por
HTTP igual que `@nestjs/idempotency` en los tres stacks.**

### El contrato por HTTP

| Situación | Respuesta |
|---|---|
| Falta la clave en una operación que la exige | 400, `IDEMPOTENCY_KEY_REQUIRED` |
| La clave no tiene entre 1 y 255 caracteres ASCII imprimibles | 400, `IDEMPOTENCY_KEY_INVALID` |
| La misma clave sigue en curso | 409, `IDEMPOTENCY_KEY_IN_USE`, con `Retry-After: 1` |
| La misma clave llega con otro contenido | 422, `IDEMPOTENCY_KEY_REUSED` |
| La misma clave ya se respondió | la respuesta guardada, con `Idempotent-Replayed: true` |
| La operación falló con un 5xx | no se guarda: la clave se libera y el cliente puede reintentar |

- **Los errores son los de ADR-031**, con esos códigos propios y en el sobre de Nova:
  `ApplicationError` de tipo `INVALID_INPUT`, `CONFLICT` con `retryAfter` y `UNPROCESSABLE`.
- **El replay repite el status, el cuerpo y solo estos headers:** `Location`, `Content-Type`,
  `Content-Language`, `Content-Location`, `ETag` y `Last-Modified`. Nunca cookies, credenciales ni
  headers de CORS.
- **Es opcional por operación,** con `@Idempotent`. No se aplica a todo POST por defecto.

### Los valores por defecto

| Parámetro | Valor | Por qué |
|---|---|---|
| Retención de la respuesta | 24 horas | la de Stripe y la de `@nestjs/idempotency` |
| Lock de una ejecución en curso | 60 s, renovado cada 20 s | cubre un proveedor lento sin dejar la clave tomada si el proceso muere |
| Token de dueño | uno por intento | una renovación o un cierre de otro intento se rechazan: evita la doble ejecución |
| Huella | SHA-256 del alcance, el método, la ruta y el cuerpo con las claves ordenadas | un cliente que reserializa el mismo JSON no recibe un 422 falso |
| Alcance | la identidad del cliente | la misma clave de dos clientes son dos claves distintas |

Todos se configuran por servicio, bajo `nova.idempotency.*`.

### El contrato y la implementación por defecto de Nova

La misma forma que ADR-042 y ADR-031: el núcleo fija las reglas, cada pieza es un puerto, Nova trae
la implementación por defecto, y una organización como UTP pone la suya sin forkear.

| Puerto | Qué decide | Implementación de Nova |
|---|---|---|
| `IdempotencyStore` | adquirir, completar, liberar y renovar un registro, y purgar los vencidos; cada operación es atómica y lleva el token de dueño | en memoria, para desarrollo y pruebas; JDBC para Postgres |
| `ScopeResolver` | de quién es la clave | la identidad autenticada, o un header configurable, como el `X-Customer-Id` que pasa el BFF de Plaza |
| `Fingerprinter` | la huella de la petición | la de la tabla de arriba |

**Las reglas que ningún adaptador cambia:**
- el alcance siempre es parte de la clave;
- un 5xx nunca se guarda;
- el replay nunca repite cookies ni credenciales;
- ni la clave ni el cuerpo aparecen en un log;
- toda llamada al almacén lleva timeout.

### La transacción

**El almacén JDBC se puede sumar a la transacción del negocio.** Con eso, el registro de la clave y
el pedido se confirman juntos, en el mismo commit. Sin eso, una caída entre el commit del negocio y
el cierre del registro vuelve a ejecutar la operación. Pedidos usa el modo en la misma transacción.

### Dónde vive

| Stack | Dónde | Qué trae ahora |
|---|---|---|
| Java | `nova-java-25-idempotency`, familia `nova-idempotency` | `nova-idempotency` (contrato, núcleo y almacén en memoria), `nova-idempotency-jdbc` y `nova-idempotency-spring-boot-starter` |
| NestJS | `@ahincho/nova-nestjs` | CORS deja pasar `Idempotency-Key`, y el cliente HTTP la propaga a los upstreams, como ya hace con `x-request-id` |

- **Una extensión de Quarkus y un almacén Redis llegan con su primer consumidor.** Serán el catálogo
  de Plaza y un servicio con varias réplicas sin Postgres, por la regla de no agregar superficie sin
  consumidor.
- **En NestJS no hay almacén todavía,** porque el BFF de Plaza no tiene estado (ADR-043): solo
  propaga la clave, y la idempotencia la aplica pedidos. Cuando un servicio NestJS con datos la
  necesite, se adopta `@nestjs/idempotency` detrás de este contrato.

### Pedidos migra

Pedidos reemplaza su implementación propia por la capacidad, y con eso se cierran los cinco
defectos. La tabla de pedidos deja de ser la dueña de la clave, y su restricción única pasa a
acotarse por cliente.

## Alternativas descartadas

- **Adoptar una librería de la comunidad en Spring.** Son 0.x, de un solo mantenedor, y difieren en
  lo que ve el cliente. Una de ellas cambió el formato de su almacén sin migración en una versión
  menor.
- **La extensión de Quarkiverse.** Es experimental, y sin renovación del lock ni token de dueño
  corre el riesgo de ejecutar dos veces un pago lento.
- **AWS Powertools.** En Java solo trae DynamoDB, pide AspectJ, está pensado para Lambda y responde
  con excepciones en vez de semántica HTTP.
- **Que cada servicio la resuelva por su cuenta.** Es lo que tiene pedidos, con cinco defectos.
- **La idempotencia en el BFF.** El BFF no tiene estado por decisión (ADR-020 y ADR-043), y
  necesitaría un almacén propio.

## Preguntas abiertas

1. **El almacén en memoria en producción.** `@nestjs/idempotency` se niega a arrancar con él en
   producción. En Java no hay una señal universal de «producción»; una opción es exigir un almacén
   explícito salvo que una propiedad declare el modo de desarrollo.
2. **La clave entre comillas.** El borrador la define como un string de Structured Fields
   (`"abc"`), y Stripe y NestJS la aceptan sin comillas. ¿Se aceptan las dos formas?
3. **El cifrado de las respuestas guardadas,** con AES-256-GCM, como ofrece NestJS. Entra cuando un
   consumidor guarde datos sensibles, como pagos.
4. **La retención.** 24 horas es lo habitual; la API v2 de Stripe usa 30 días.
5. **Una suite de contrato común** con la de ADR-031, que corra los mismos casos en los tres stacks.

## Consecuencias

### Positivas

- Un reintento del cliente nunca compra dos veces, y nunca entrega datos de otro cliente.
- Los tres stacks responden igual, siguiendo el borrador que sigue todo el ecosistema.
- Una organización cambia el almacén, el alcance o la huella sin forkear.

### Negativas

- Es un repositorio más, con un almacén que hay que operar y purgar.
- Mientras el borrador no sea RFC, puede cambiar. El contrato sigue a `@nestjs/idempotency`, y un
  cambio del borrador se evalúa aquí.
- La migración de pedidos toca su tabla y su restricción única.

## Fuentes

Consultadas el 2026-09-30.

- [IETF: The Idempotency-Key HTTP Header Field, versión 07](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-idempotency-key-header-07)
- [IETF: el estado del borrador](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/)
- [NestJS: Idempotency](https://docs.nestjs.com/reliability/idempotency)
- [nestjs/idempotency](https://github.com/nestjs/idempotency)
- [Stripe: Idempotent requests](https://docs.stripe.com/api/idempotent_requests)
- [Quarkiverse: quarkus-http-idempotency](https://docs.quarkiverse.io/quarkus-http-idempotency/dev/index.html)
- [Spring Integration: Idempotent Receiver](https://docs.spring.io/spring-integration/reference/handler-advice/idempotent-receiver.html)
- [idempotency4j](https://github.com/josipmusa/idempotency4j)
- [AWS Powertools for Java: Idempotency](https://docs.aws.amazon.com/powertools/java/latest/utilities/idempotency/)
- [Brandur: Implementing Stripe-like Idempotency Keys in Postgres](https://brandur.org/idempotency-keys)
- [Martin Kleppmann: How to do distributed locking](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html)
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785)
