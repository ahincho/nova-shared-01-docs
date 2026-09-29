# ADR-043: Qhatu, la Plataforma de Compras que Demuestra Nova

## Estado

Propuesta (2026-09-29). Angel necesita presentar, como producto final del curso, una plataforma
hecha en Spring Boot, Quarkus y NestJS que evidencie el desarrollo sobre Nova. Pidió una
plataforma de compras con un BFF como orquestador, y que primero lleve un nombre.
**Scope:** `shared` (Java + NestJS). Son ejemplos, en la categoría `example` de
[ADR-038](ADR-038-nombres-de-repositorio-por-tecnologia.md).
**Aplica:** el estándar de API, [ADR-029](../nest/ADR-029-sin-reintentos-en-el-cliente-http.md),
[ADR-032](ADR-032-observabilidad-como-puerto-conectable.md) y
[ADR-042](ADR-042-secretos-detras-de-un-contrato.md).

## Fecha

2026-09-29

## Contexto

Nova tiene ocho ejemplos, y cada uno muestra un stack solo: el 01 y el 04 son la referencia de
Spring y de Quarkus, el 02 y el 05 el mismo `ms-course` en los dos, el 07 la referencia de NestJS.
Ninguno llama a otro servicio, ninguno tiene base de datos y ninguno necesita un secreto. Eso deja
tres cosas sin demostrar:

- **Que los tres stacks dicen lo mismo por HTTP.** Es un invariante de la plataforma, y hoy solo
  se ve comparando respuestas a mano.
- **Que una traza cruza los tres frameworks.** La observabilidad está en los tres, pero nunca en
  la misma petición.
- **Que las capacidades tienen un consumidor real.** Otro invariante: no hay API sin un
  consumidor. ADR-042 dejó escrito que ningún ejemplo necesita un secreto, y que la capacidad no se
  da por terminada hasta que uno la use.

El curso trabajó un proceso de compra: un servicio de pedidos que consulta productos y revisa
stock. Es un dominio que el jurado ya conoce, y tiene una dependencia natural entre servicios que
`ms-course` no tiene.

## Decisión

**Se construye Qhatu, una plataforma de compras de ejemplo con un servicio por framework, y un BFF
en NestJS que orquesta la compra.**

### El nombre

*Qhatu* es la palabra quechua para el mercado: el lugar donde se compra y se vende. Es corta,
no aparece en ningún repositorio de Nova, y separa a primera vista el
producto de la plataforma: Nova es el marco y Qhatu es lo que se construye con él.

### Los servicios

| Servicio | Framework | Es dueño de | Datos |
|---|---|---|---|
| `qhatu-bff` | NestJS | la experiencia del cliente y el proceso de compra | ninguno, sin estado |
| `qhatu-orders` | Spring Boot | los pedidos y su estado | Postgres |
| `qhatu-catalog` | Quarkus | los productos, los precios y el stock | Postgres |

**Los servicios de Java no se llaman entre sí.** Todo lo que cruza dominios pasa por el BFF. Por
eso Java no necesita todavía un cliente HTTP propio, y el único cliente HTTP de la compra es el de
NestJS, que ya existe.

Que el BFF de NestJS no tenga datos no es una restricción nueva: es lo que ya dice
[ADR-020](../nest/ADR-020-orm-persistencia.md). La persistencia vive en los servicios de Java.

### La compra, orquestada por el BFF

```
cliente ──► qhatu-bff
              1. reservar el stock      ──► qhatu-catalog   POST /v1/reservations
              2. crear el pedido         ──► qhatu-orders    POST /v1/orders          (PENDING)
              3. confirmar la reserva   ──► qhatu-catalog   POST /v1/reservations/{id}/confirm
              4. confirmar el pedido     ──► qhatu-orders    POST /v1/orders/{id}/confirm
```

- **El precio lo pone el catálogo, nunca el cliente.** La reserva devuelve los precios del momento,
  y el pedido se crea con esos.
- **Si un paso falla, el BFF deshace los anteriores:** libera la reserva y cancela el pedido. Es
  una saga orquestada, y su estado vive solo en la petición.
- **Nada se reintenta,** por ADR-029. Cada llamada lleva timeout, y un fallo compensa en lugar de
  repetir.
- **Una compensación que se pierde no deja stock bloqueado:** la reserva vence sola a los diez
  minutos. Por eso el BFF no necesita una base de datos para la saga.
- **El cliente puede reintentar sin comprar dos veces:** la compra lleva un `Idempotency-Key`, y el
  pedido lo guarda.

### Lo que muestra de Nova

| Capacidad | Dónde se ve | Estado en Nova |
|---|---|---|
| Estándar de API, con el mismo sobre y los mismos errores | los tres servicios; sin stock, Quarkus responde 409 y el BFF lo entrega con la misma forma | existe en los tres stacks |
| Una traza por compra | Grafana muestra la compra cruzando NestJS, Spring y Quarkus | existe en los tres stacks |
| Secretos | las credenciales de Postgres salen de Vault en los dos servicios de Java | existe en Spring (`nova-secrets` 1.0.0); **falta la extensión de Quarkus** |
| Mensajería | `qhatu-orders` publica `OrderConfirmed` en Kafka y `qhatu-catalog` lo consume para llevar el ranking de lo más vendido | **falta**: un puerto con Kafka como adaptador, que propague la traza |
| CQRS | `qhatu-orders` separa los comandos (crear, confirmar, cancelar) de las consultas | **falta** |
| Generación de servicios | un servicio nuevo sale del arquetipo en vivo y el CI compartido lo verifica | **falta arreglar** los arquetipos 17 y 18 y la plantilla 19, que hoy generan proyectos que no compilan |

Cada capacidad que falta es su propio repositorio con su propio ADR, por
[ADR-041](../java/ADR-041-un-repositorio-por-capacidad.md), y Qhatu es su primer consumidor.

### Los repositorios

| # | Repositorio | Contenido |
|---|---|---|
| 09 | `nova-example-09-shared-qhatu` | el producto: la descripción, el compose que levanta todo y el guion de la demo |
| 10 | `nova-example-10-nestjs-qhatu-bff` | el BFF |
| 11 | `nova-example-11-spring-boot-qhatu-orders` | pedidos |
| 12 | `nova-example-12-quarkus-qhatu-catalog` | catálogo y stock |

Un servicio por repositorio, como en un producto real: cada uno con su CI, su versión y su imagen.
El 09 es la entrada al producto; con un solo comando levanta los servicios, Postgres, Vault y el
stack de observabilidad de `nova-shared-03-infrastructure`.

### Las fases

1. **El producto y los dos servicios de Java.** El repo 09 con su compose, el catálogo y los
   pedidos con el estándar de API, sus bases y sus secretos en Vault. Incluye la extensión de
   secretos para Quarkus.
2. **El BFF y la compra orquestada**, con sus compensaciones. Con esta fase ya hay una demo que
   cruza los tres frameworks.
3. **La mensajería**, con el ranking de lo más vendido.
4. **CQRS** en los pedidos.
5. **Los arquetipos**, y el servicio nuevo generado en vivo.

## Fuera de alcance

- **El pago.** La compra termina con el pedido confirmado. Un servicio de pagos simulado puede venir
  después como un cuarto servicio.
- **Un frontend.** La demo se hace con una colección de peticiones contra el BFF y su OpenAPI.
- **El despliegue en la nube.** Qhatu corre en local con el compose del repo 09.

## Preguntas abiertas

1. **El nombre.** Se propone *Qhatu*. Si no convence, las alternativas son *Nova Market* o *Tambo*.
2. **La autenticación.** El módulo de NestJS existe, pero los repos 06 y 11 de Keycloak en Java
   solo tienen un README. Hay dos caminos: que el BFF valide el token y los servicios confíen en
   él, o construir Keycloak en Java como otra capacidad.
3. **La auditoría a MongoDB del curso.** El curso mandaba la auditoría por Kafka a MongoDB. Encaja
   en la fase 3, pero agrega un consumidor y una base más.
4. **La fecha de la presentación.** Decide si se llega a las cinco fases o se corta en la segunda.

## Alternativas descartadas

- **Que los servicios se llamen entre sí**, con los pedidos consultando el stock. Angel eligió el
  BFF como orquestador. Además, llevaría el cliente HTTP de Java a la fase 1 y la compensación a
  un servicio de negocio.
- **Reusar `ms-course`.** No tiene una dependencia natural entre servicios, y no es el proceso del
  curso.
- **Un solo repositorio para todo Qhatu.** Es más cómodo, pero no muestra lo que Nova resuelve:
  servicios separados que se ven y se comportan igual.

## Consecuencias

### Positivas

- Los invariantes de la plataforma se ven en vivo, en una petición, en lugar de describirse.
- Cada capacidad nueva nace con un consumidor real.
- La demo sigue el proceso del curso, así que se puede comparar pieza por pieza con lo que se vio en clase.

### Negativas

- Son cuatro repositorios más que mantener, con su CI.
- La fase 1 depende de la extensión de secretos para Quarkus, que todavía no existe.
