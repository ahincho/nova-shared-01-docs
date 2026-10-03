# ADR-056: La Fase 1 de Plaza: el Catálogo en Quarkus y los Pagos en NestJS

## Estado

Aceptada (2026-10-02). Angel pidió cerrar la fase 1 de Plaza y que los pagos se hagan en NestJS, igual
que el BFF, y la aprobó el mismo día con las seis respuestas recomendadas, escritas en «Preguntas
resueltas». Enmienda [ADR-043](ADR-043-plaza-la-plataforma-de-compras.md), que los había puesto en
Spring Boot, y reabre [ADR-020](../nest/ADR-020-orm-persistencia.md), que se cerró sin elegir ORM hasta
que un servicio NestJS fuera dueño de datos: pagos es ese servicio.
**Scope:** `shared` (Quarkus y NestJS; pedidos, en Spring Boot, ya está).
**Aplica:** [ADR-049](ADR-049-secretos-en-quarkus-y-nestjs.md) para los secretos,
[ADR-054](ADR-054-persistencia-reutilizable-con-paginacion-por-cursor.md) para la paginación,
[ADR-031](ADR-031-modulo-de-errores-por-capas-con-trazabilidad.md) para los errores y
[ADR-047](ADR-047-idempotencia-detras-de-un-contrato.md) para la compra repetida.

## Fecha

2026-10-02

## Contexto

**La fase 1 de ADR-043 tiene tres servicios, y hoy existe uno:**

| Servicio | Framework en ADR-043 | Estado |
|---|---|---|
| `plaza-orders` | Spring Boot | listo: CQRS, persistencia, idempotencia, secretos de Vault |
| `plaza-catalog` | Quarkus | no existe |
| `plaza-payments` | Spring Boot | no existe |

**Lo que la fase 1 necesitaba de Nova ya está:** la extensión de secretos de Quarkus
(`nova-secrets-quarkus-extension` 1.2.0) y el paquete de Vault de NestJS
(`@ahincho/nova-nestjs-secrets-vault` 0.16.1), los dos de ADR-049.

**Con pagos en Spring Boot, NestJS solo aparece en el BFF**, que no tiene datos. Plaza mostraría un
NestJS sin base, sin secretos de Vault y sin transacciones, y Java tendría dos servicios casi iguales.
Con pagos en NestJS, cada framework tiene al menos un servicio dueño de datos, con su base y sus
secretos.

**ADR-020 dejó escrita la pregunta para este caso:** no «Prisma o TypeORM» en abstracto, sino qué
necesita **este** servicio. Pagos necesita poco: una tabla, una restricción única por pedido para que
autorizar sea idempotente, una transacción por operación y migraciones versionadas.

## Decisión

**Pagos se construye en NestJS, como `nova-plaza-05-nestjs-payments`, con TypeORM como su ORM y sin
capa de persistencia en la plataforma; el catálogo, en Quarkus, como `nova-plaza-04-quarkus-catalog`. Los
dos con Postgres, sus credenciales en Vault y los contratos de abajo.**

### Los servicios de la fase 1

| Servicio | Framework | Repositorio | Puerto local | Base | Secreto en Vault |
|---|---|---|---|---|---|
| `plaza-orders` | Spring Boot | `nova-plaza-03-spring-boot-orders` | 8081 | `orders`, 5433 | `plaza/orders/db` |
| `plaza-catalog` | Quarkus | `nova-plaza-04-quarkus-catalog` | 8082 | `catalog`, 5434 | `plaza/catalog/db` |
| `plaza-payments` | NestJS | `nova-plaza-05-nestjs-payments` | 8083 | `payments`, 5435 | `plaza/payments/db` |

El compose del repo 01 suma la base de pagos y su secreto, con las mismas tres claves: `DB_URL`,
`DB_USERNAME` y `DB_PASSWORD`. La URL de pagos es la de Node (`postgres://…`), no la de JDBC.

### El catálogo

Es dueño de los productos, sus precios y su stock, y de las **reservas**: el stock apartado para una
compra que todavía no terminó.

| Método | Ruta | Qué hace | Errores |
|---|---|---|---|
| `GET` | `/v1/products` | los productos, por cursor (ADR-054) | 400 si el cursor o el límite no sirven |
| `GET` | `/v1/products/{sku}` | un producto, con su precio y su stock disponible | 404 `PRODUCT_NOT_FOUND` |
| `POST` | `/v1/reservations` | aparta el stock de una lista de `sku` y cantidades, y devuelve los precios del momento | 409 `OUT_OF_STOCK`, 404 `PRODUCT_NOT_FOUND` |
| `POST` | `/v1/reservations/{id}/confirm` | descuenta el stock apartado | 409 `RESERVATION_EXPIRED`, 404 `RESERVATION_NOT_FOUND` |
| `POST` | `/v1/reservations/{id}/release` | devuelve el stock apartado | 404 `RESERVATION_NOT_FOUND` |

- **Una reserva vence a los diez minutos**, como dice ADR-043. Una vencida ya no aparta stock: el
  disponible se calcula sin ella, así que una compensación que se pierde no deja stock bloqueado.
- **Confirmar y liberar son idempotentes:** repetir la misma operación devuelve la reserva igual que
  la primera vez. Liberar una confirmada es un 409.
- **El listado usa el núcleo puro de `nova-persistence`**, que no depende de ningún framework: el
  mismo `CursorPage`, el mismo `CursorRequest` y el mismo cursor que pedidos, con el keyset escrito
  sobre Panache. La extensión de Quarkus de ADR-054 queda para cuando haya un segundo consumidor.
- **Los productos de la demo** llegan con una migración de Flyway, con su precio y su stock.

### Los pagos

Es dueño de los pagos simulados: **no habla con ninguna pasarela.**

| Método | Ruta | Qué hace | Errores |
|---|---|---|---|
| `POST` | `/v1/payments` | autoriza el pago de un pedido: `orderId`, `amount`, `currency` | 422 `PAYMENT_DECLINED`, 409 `PAYMENT_CONFLICT` |
| `GET` | `/v1/payments/{id}` | un pago | 404 `PAYMENT_NOT_FOUND` |
| `POST` | `/v1/payments/{id}/refund` | reembolsa un pago autorizado | 404 `PAYMENT_NOT_FOUND`, 409 `PAYMENT_NOT_REFUNDABLE` |

- **Rechaza de forma predecible:** un monto por encima del tope, 1000 por defecto y configurable, es un
  422. Así la demo muestra la compensación a pedido.
- **Un pedido tiene un solo pago.** Autorizar otra vez el mismo pedido con el mismo monto devuelve el
  pago que ya existe; con otro monto, 409. Es lo que ADR-043 llama identificar el pago por su pedido, y
  lo garantiza una restricción única en la base, no el código.
- **Reembolsar es idempotente:** un pago reembolsado responde igual.

### TypeORM, solo en pagos

**La plataforma sigue sin capa de persistencia en NestJS**, como dice ADR-020: pagos declara
`@nestjs/typeorm` y `typeorm` como cualquier otra dependencia del servicio.

- **TypeORM** porque es la integración que mantiene el equipo de NestJS (`@nestjs/typeorm`), trae
  migraciones versionadas en TypeScript, transacciones y restricciones únicas, y no necesita un paso de
  generación de código ni un motor aparte.
- **Las migraciones las corre el servicio al arrancar**, como Flyway en Java. `synchronize` queda
  apagado: el esquema lo dicen las migraciones, no las entidades.
- **El chequeo de disponibilidad mira la base:** `NovaHealthModule` recibe un `readinessCheck` que
  hace un `SELECT 1`, el mecanismo que ADR-020 dejó listo.
- **Si un segundo servicio NestJS tiene datos**, se decide si eso pasa a la plataforma, con su ADR.

### Lo que muestra de Nova, en la fase 1

| Capacidad | Pedidos (Spring) | Catálogo (Quarkus) | Pagos (NestJS) |
|---|---|---|---|
| El mismo sobre y los mismos errores por capas | sí | sí | sí |
| Secretos de Vault | `spring.config.import` | `nova.secrets.import` | `imports` de `bootstrap()` |
| La misma paginación por cursor | sí | sí, con el núcleo puro | no la necesita |
| Una traza por petición | sí | sí | sí |

## Alternativas descartadas

- **Pagos en Spring Boot**, como decía ADR-043. NestJS quedaría solo en el BFF, sin base ni secretos.
- **Prisma.** Pide generar el cliente en cada build y un esquema propio fuera de TypeScript; para una
  tabla, es más maquinaria que la que se usa.
- **Un cliente SQL a secas**, como `pg`. ADR-020 lo dejó abierto para un ACL que lee un esquema ajeno;
  pagos es dueño del suyo y necesita migraciones.
- **Una capa de persistencia en `@ahincho/nova-nestjs`.** Tendría un consumidor; ADR-020 pide esperar
  al segundo.
- **La extensión de persistencia de Quarkus ahora.** El núcleo puro ya da el contrato; la extensión
  agrega la conexión con Panache, que con un consumidor se escribe en el servicio.

## Preguntas resueltas

Angel las resolvió el 2026-10-02, todas con la respuesta recomendada.

1. **El ORM de pagos.** Resuelta: **TypeORM**, por lo de arriba. La otra opción es Prisma.
2. **El tope de un pago.** Resuelta: **1000**, en la moneda del pago, configurable con
   `PAYMENTS_MAX_AMOUNT`.
3. **El puerto local de pagos.** Resuelta: **8083**, el siguiente libre.
4. **El listado del catálogo por cursor ahora**, con el núcleo puro. Resuelta: **sí**: muestra que el
   contrato de ADR-054 es el mismo en Spring y en Quarkus.
5. **Confirmar y cancelar un pedido.** Resuelta: **en la fase 2**, con la compra orquestada, que es
   quien los usa.
6. **El orden.** Resuelta: **primero el catálogo**, que es el primer paso de la compra, y después
   pagos.

## Consecuencias

### Positivas

- **Cada framework tiene un servicio con datos**, base y secretos de Vault, y no solo el BFF.
- **El contrato de paginación se ve en dos stacks** con el mismo cursor.
- **ADR-020 se responde con un caso real**, que es lo que pedía.

### Negativas

- **Pagos es el primer servicio NestJS con base**, así que su configuración de TypeORM, sus migraciones
  y su chequeo de salud son nuevos para la plataforma, y se escriben en el servicio.
- **El listado del catálogo escribe su keyset a mano** hasta que exista la extensión de Quarkus.
- **El compose de Plaza crece:** tres bases, Vault y, en la fase 2, Keycloak.

## Fuentes

- NestJS, *Database*, docs.nestjs.com/techniques/database, consultado el 2026-10-02.
- TypeORM, *Migrations*, typeorm.io, consultado el 2026-10-02.
- Quarkus, *Simplified Hibernate ORM with Panache*, quarkus.io/guides, consultado el 2026-10-02.
