# ADR-054: La Persistencia Reutilizable, con Paginación por Cursor

## Estado

Aceptada (2026-10-02). Es el criterio 05 de la rúbrica del curso de Framework Engineering, que pide
componentes reutilizables de persistencia con su consumo desde un servicio. Angel pidió que la
paginación sea de scroll infinito, es decir, por cursor, y la aprobó el mismo día con las seis
respuestas recomendadas, que quedan escritas en «Preguntas resueltas».
**Scope:** `shared` (el contrato por HTTP vale para los tres stacks; la implementación es de Spring
ahora).
**Aplica:** [ADR-041](../java/ADR-041-un-repositorio-por-capacidad.md) para la forma del repositorio,
[ADR-015](../java/ADR-015-librerias-puras-sin-dependencias-framework.md) para el núcleo sin framework,
[ADR-031](ADR-031-modulo-de-errores-por-capas-con-trazabilidad.md) para los errores y
[ADR-053](ADR-053-cqrs-con-command-bus-y-query-bus.md) para los buses.
**Primer consumidor:** pedidos de Plaza, cuyo `GET /v1/orders` hoy devuelve todos los pedidos del
cliente de una vez.

## Fecha

2026-10-02

## Contexto

**Nova no tiene nada de persistencia.** Cada servicio escribe sus columnas de auditoría, su
`@Version` y su paginación a mano, y una excepción de la base sale como un 500.

**Pedidos ya muestra los tres problemas:**

- `ListOrders` devuelve todos los pedidos del cliente, sin límite. Con mil pedidos son mil filas y
  sus líneas en una sola respuesta.
- `Order` lleva su propio `createdAt` y no tiene `updatedAt`, ni quién lo creó, ni versión. Dos
  confirmaciones simultáneas del mismo pedido, cuando existan, se pisarían sin aviso.
- Una clave duplicada o una base caída responden 500 con el mensaje genérico: el cliente no sabe si
  reintentar.

**El sobre ya trae un `pageInfo`, pero es por offset:** página, tamaño, total y número de páginas.
Solo existe en Java (ADR-030, pregunta 1), y ningún servicio lo usa; solo está registrado para la
imagen nativa.

**Scroll infinito es paginación por cursor, y no por offset:**

| | Offset (`?page=40&size=20`) | Cursor (`?cursor=…&limit=20`) |
|---|---|---|
| Lo que hace la base | lee y descarta las 800 filas anteriores | salta al cursor por el índice |
| Costo de la página 40 | crece con cada página | el mismo que el de la primera |
| Si entra un pedido nuevo mientras se navega | la página siguiente repite un elemento | no repite ni salta nada |
| Contar el total | hace falta para saber si hay más | no hace falta |
| Saltar a la página 40 | se puede | no se puede, y un scroll infinito no lo necesita |

El cursor guarda los valores del orden del último elemento entregado. La página siguiente pide «los
que vienen después de este», con un `WHERE (created_at, id) < (?, ?)` que usa el índice.

**El ecosistema, consultado el 2026-10-02:**

- **Spring Data** trae el scroll por keyset desde la 3.1: un repositorio devuelve `Window<T>`, recibe
  un `ScrollPosition` y un `Limit`, y `Window.positionAt(i)` da la posición del último elemento.
  Agrega la clave primaria al orden para que sea único, y exige que las columnas del orden no sean
  nulas. Pero la posición es un objeto de Java: no dice cómo viaja por HTTP.
- **Relay** (GraphQL) fijó la forma más copiada: `edges`, y `pageInfo` con `endCursor` y
  `hasNextPage`.
- **Stripe** responde `data` y `has_more`, y el cliente pide la siguiente con `starting_after`.
- **Slack** responde `response_metadata.next_cursor`, opaco, vacío al final.

Los tres coinciden en lo que importa: un cursor **opaco** para el cliente, un indicador de si hay más,
y ningún total.

## Decisión

**Una capacidad propia: el contrato de paginación por cursor sin framework, y un starter de Spring Boot
con lo reutilizable de JPA, construido sobre el scroll por keyset de Spring Data.**

### El contrato por HTTP

La petición lleva dos parámetros de query:

| Parámetro | Qué es | Por defecto |
|---|---|---|
| `limit` | cuántos elementos trae la página, entre 1 y el máximo | 20; máximo 100 |
| `cursor` | el `nextCursor` de la página anterior, tal como llegó | sin él, la primera página |

La respuesta es el sobre de Nova de siempre, y la página va en `data`:

```json
{
  "success": true,
  "status": 200,
  "data": {
    "items": [ { "id": "…", "status": "PENDING" }, { "id": "…", "status": "PAID" } ],
    "nextCursor": "eyJ2IjoxLCJrIjp7ImNyZWF0ZWRBdCI6Ij…",
    "hasNext": true
  }
}
```

- **La página va en `data` y no en el sobre.** No cambia `ApiResponse` ni ningún stack, así que
  NestJS y Quarkus responden lo mismo sin tocar su sobre, y un BFF pasa el cursor sin reescribir
  nada.
- **En la última página, `hasNext` es `false` y `nextCursor` es `null`.**
- **No hay total ni página anterior.** Un scroll infinito solo avanza, y contar cuesta un recorrido
  entero de la tabla.
- **Un cursor mal formado, de otra versión o de otro orden** es un 400 `INVALID_INPUT` con el campo
  `cursor`. Un `limit` fuera de rango es un 400 con el campo `limit`.

### El cursor

- **Es opaco:** Base64 URL-safe sin relleno (RFC 4648, sección 5) de un JSON con la versión del
  formato, el nombre del orden y los valores de su clave, con su tipo. El cliente no lo arma ni lo
  lee.
- **No se firma.** Un cursor alterado solo mueve la posición dentro de la misma consulta: los filtros,
  como el cliente dueño de los pedidos, los pone el servidor y no viajan en el cursor. Que no pueda
  salir de su consulta es una regla, no una consecuencia de la firma.
- **Está atado a su orden.** Un cursor de `createdAt DESC` no sirve para otro orden: se rechaza con
  el 400, en lugar de devolver una página que no corresponde.
- **El orden siempre termina en la clave primaria**, para que dos filas con el mismo `createdAt`
  nunca se repitan ni se salten. Las columnas del orden no admiten nulos, que es lo que pide Spring
  Data.

### Lo reutilizable de JPA

| Pieza | Qué hace |
|---|---|
| `AuditableEntity` | una `@MappedSuperclass` con `createdAt`, `updatedAt`, `createdBy`, `updatedBy` y `@Version`, llenados por la auditoría de Spring Data |
| El auditor | `createdBy` y `updatedBy` salen del `ActorResolver` de ADR-053, el mismo actor que la auditoría de los buses; sin CQRS, del de Spring Security |
| `CursorPages` | convierte un `Window<E>` de Spring Data en un `CursorPage<R>`, con el mapeo a la vista, y un `CursorRequest` en el `ScrollPosition` y el `Limit` del repositorio |
| El parámetro del controlador | un `CursorRequest` se recibe como argumento y llega validado, con los 400 de arriba |
| La traducción de errores | un comportamiento de los buses de ADR-053 que hace `flush` al terminar cada comando y traduce las excepciones de la base a ADR-031 |

**La traducción de errores:**

| Excepción | Error de ADR-031 | HTTP |
|---|---|---|
| bloqueo optimista, al pisar una versión | `ApplicationError` `CONFLICT`, con el código `CONCURRENT_MODIFICATION` | 409 |
| una restricción única o de integridad | `ApplicationError` `CONFLICT`, con el código `DATA_CONFLICT` | 409 |
| una base caída o una conexión que no llega | `InfrastructureError` `UNAVAILABLE`, con la base como dependencia | 503 |
| una consulta que pasa su timeout | `InfrastructureError` `TIMEOUT`, con la base como dependencia | 504 |

El `flush` al terminar el comando es lo que hace posible la traducción: sin él, la escritura llega a
la base recién en el commit, y en pedidos el commit lo hace la idempotencia, fuera del bus. Así un
conflicto se responde como 409 y no como 500.

**Una página nunca hace `fetch join` de una colección.** Hibernate aplica el límite en memoria cuando
la consulta trae las líneas del pedido en el mismo `join`, y la paginación deja de servir. Se pagina la
raíz y las colecciones se cargan por lotes, con `@BatchSize`.

### Dónde vive

| Stack | Dónde | Qué trae ahora |
|---|---|---|
| Java | `nova-java-28-persistence`, familia `nova-persistence` | `nova-persistence` (`pe.edu.nova.java.libs`): `CursorPage`, `CursorRequest` y el códec del cursor, sin framework; `nova-persistence-spring-boot-starter` (`pe.edu.nova.java.starters`): todo lo de JPA de la tabla de arriba |
| NestJS | — | el mismo contrato por HTTP cuando un servicio con datos lo necesite |
| Quarkus | — | una extensión con su primer consumidor, el catálogo de Plaza, sobre el keyset de Panache |

- **Sale en la 0.1.0 y pasa a la 1.0.0 cuando pedidos lo use en `main`**, como CQRS.
- **No entra en el meta-starter:** trae JPA, y un servicio sin base de datos no lo necesita. Cumple
  la regla de ADR-052 solo para quien ya usa JPA, así que se declara aparte.

### Pedidos migra

- `ListOrders` recibe un `CursorRequest` y devuelve `CursorPage<OrderResponse>`, ordenado por
  `createdAt DESC` y el `id`. El repositorio pasa a devolver un `Window<Order>`, sin el `fetch join`
  de las líneas.
- `Order` hereda de `AuditableEntity`, con una migración de Flyway que suma las columnas nuevas.
- `GET /v1/orders` cambia de forma: de una lista a una página. Es un cambio incompatible del servicio,
  y hoy no tiene consumidores: el BFF de Plaza todavía no existe.

## Alternativas descartadas

- **El `pageInfo` del sobre, rehecho para cursores.** Habría que cambiar `ApiResponse`, que es un
  record: es una versión mayor de `nova-api-standard` y de todo lo que la usa, en los tres stacks.
  Además, el `pageInfo` actual no lo usa nadie. Queda como está, y se retira en la próxima mayor del
  estándar.
- **Paginación por offset.** Es la que no sirve para scroll infinito: cada página cuesta más, y un
  pedido nuevo hace repetir un elemento.
- **Un enlace `rel="next"` en `links`.** Es el estándar de RFC 8288, pero el enlace lleva la ruta
  interna del servicio, y el BFF tendría que reescribirlo antes de entregarlo. Un cursor opaco pasa
  tal cual.
- **Un cursor firmado.** Protege contra algo que la consulta ya impide, a cambio de una clave que
  operar y rotar en cada servicio.
- **Escribir el keyset a mano.** Spring Data ya lo resuelve, con la clave primaria agregada al orden;
  Nova solo pone el contrato por HTTP encima.

## Preguntas resueltas

Angel las resolvió el 2026-10-02, todas con la respuesta recomendada.

1. **Dónde va la página.** Resuelta: **en `data`, como `items`, `nextCursor` y `hasNext`**, sin
   tocar el sobre.
2. **Si hay página anterior.** Resuelta: **no por ahora.** Un scroll infinito solo avanza; si un
   cliente necesita volver, se suma un `previousCursor` sin romper nada.
3. **Si la página trae el total.** Resuelta: **no.** Un `count` recorre la tabla entera en cada
   página, y el scroll infinito no lo muestra.
4. **El límite.** Resuelta: **20 por defecto y 100 como máximo**, configurables por servicio bajo
   `nova.persistence.pagination.*`.
5. **El identificador de las entidades nuevas.** Resuelta: **un UUID ordenable por tiempo
   (versión 7), generado por la aplicación.** `Order` conserva sus identificadores actuales.
6. **El `pageInfo` por offset del sobre.** Resuelta: **queda sin uso y se marca como deprecado**, y
   se retira en la próxima mayor de `nova-api-standard`.

## Consecuencias

### Positivas

- La rúbrica pide persistencia reutilizable y manejo estandarizado de excepciones con su consumo, y
  quedan cubiertos con pedidos como consumidor.
- Cada página cuesta lo mismo, sin importar cuánto haya avanzado el cliente.
- Un servicio deja de escribir sus columnas de auditoría y su `@Version`, y quién creó cada fila es
  el mismo actor que registra la auditoría de los buses.
- Un conflicto de versión o de clave responde 409, y una base caída 503 o 504, en lugar de un 500.

### Negativas

- Es un repositorio más, con dos módulos.
- El cursor no permite saltar a una página: una tabla de administración con páginas numeradas
  necesitaría otro mecanismo.
- `GET /v1/orders` cambia de forma.
- El `flush` al final de cada comando adelanta la escritura: un comando que escribe y después falla
  por otra razón hace un viaje a la base que antes no hacía. La transacción se deshace igual.

## Fuentes

Consultadas el 2026-10-02.

- [Spring Data Commons: Scrolling](https://docs.spring.io/spring-data/commons/reference/repositories/scrolling.html)
- [Spring Data JPA: Query Methods](https://docs.spring.io/spring-data/jpa/reference/repositories/query-methods-details.html)
- [Relay: GraphQL Cursor Connections Specification](https://relay.dev/graphql/connections.htm)
- [Stripe: Pagination](https://docs.stripe.com/api/pagination)
- [Slack: Pagination](https://docs.slack.dev/apis/web-api/pagination)
- [Markus Winand: We need tool support for keyset pagination](https://use-the-index-luke.com/no-offset)
- [RFC 4648, sección 5: Base 64 Encoding with URL and Filename Safe Alphabet](https://www.rfc-editor.org/rfc/rfc4648#section-5)
