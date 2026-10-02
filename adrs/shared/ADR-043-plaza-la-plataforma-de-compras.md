# ADR-043: Plaza, la Plataforma de Compras que Demuestra Nova

## Estado

Aceptada (2026-09-29). Angel necesita presentar, como producto final del curso, una plataforma
hecha en Spring Boot, Quarkus y NestJS que evidencie el desarrollo sobre Nova. Pidió una
plataforma de compras con un BFF como orquestador. De la primera versión de este ADR cambió dos
cosas: el nombre, que quiso en inglés o en español, y que los repositorios lleven el nombre de la
plataforma en lugar de `example`. Con eso dio paso a crear los repositorios.
**Enmienda (2026-09-29):** Angel sumó tres decisiones antes de empezar el desarrollo: un servicio
de pagos simulado, Keycloak para el inicio de sesión y el patrón outbox para publicar eventos.
**Enmienda (2026-10-02):** [ADR-056](ADR-056-plaza-fase-1-catalogo-y-pagos-en-nestjs.md) pasa los pagos a
NestJS, en `nova-plaza-05-nestjs-payments`, y define los contratos de la fase 1. Donde este ADR dice
que pagos es de Spring Boot, manda ADR-056.
**Scope:** `shared` (Java + NestJS).
**Aplica:** el estándar de API, [ADR-029](../nest/ADR-029-sin-reintentos-en-el-cliente-http.md),
[ADR-032](ADR-032-observabilidad-como-puerto-conectable.md) y
[ADR-042](ADR-042-secretos-detras-de-un-contrato.md). **Enmienda**
[ADR-038](ADR-038-nombres-de-repositorio-por-tecnologia.md) con la categoría de producto.

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

**Se construye Plaza, una plataforma de compras de ejemplo con un servicio por framework, y un BFF
en NestJS que orquesta la compra.**

### El nombre

*Plaza* es el lugar donde se compra y se vende, y la palabra es la misma en español y en inglés.
Es corta, no aparece en ningún repositorio de Nova y separa a primera vista el producto de la
plataforma: Nova es el marco y Plaza es lo que se construye con él.

### Los servicios

| Servicio | Framework | Es dueño de | Datos |
|---|---|---|---|
| `plaza-bff` | NestJS | la experiencia del cliente y el proceso de compra | ninguno, sin estado |
| `plaza-orders` | Spring Boot | los pedidos y su estado | Postgres |
| `plaza-catalog` | Quarkus | los productos, los precios y el stock | Postgres |
| `plaza-payments` | Spring Boot | la autorización y el reembolso de un pago, simulados | Postgres |

**El carrito no es un servicio:** vive en el cliente, y el BFF recibe los ítems al momento de
comprar. Así no hay un servicio con estado y con su base solo para guardar una lista.

**El pago es simulado:** no habla con ninguna pasarela. Rechaza de forma predecible, por ejemplo
cuando el monto pasa un tope, para que la demo pueda mostrar la compensación a pedido.

**Los servicios de Java no se llaman entre sí.** Todo lo que cruza dominios pasa por el BFF. Por
eso Java no necesita todavía un cliente HTTP propio, y el único cliente HTTP de la compra es el de
NestJS, que ya existe.

Que el BFF de NestJS no tenga datos no es una restricción nueva: es lo que ya dice
[ADR-020](../nest/ADR-020-orm-persistencia.md). La persistencia vive en los servicios de Java.

### La compra, orquestada por el BFF

```
cliente ──► plaza-bff
              1. reservar el stock      ──► plaza-catalog    POST /v1/reservations
              2. crear el pedido         ──► plaza-orders     POST /v1/orders                     (PENDING)
              3. autorizar el pago       ──► plaza-payments   POST /v1/payments
              4. confirmar la reserva   ──► plaza-catalog    POST /v1/reservations/{id}/confirm
              5. confirmar el pedido     ──► plaza-orders     POST /v1/orders/{id}/confirm
```

| Si falla | El BFF deshace |
|---|---|
| 1, reservar | nada: la compra termina ahí |
| 2, crear el pedido | libera la reserva |
| 3, autorizar el pago | cancela el pedido y libera la reserva |
| 4 o 5, confirmar | reembolsa el pago, cancela el pedido y libera la reserva |

- **El precio lo pone el catálogo, nunca el cliente.** La reserva devuelve los precios del momento,
  y el pedido se crea con esos.
- **Es una saga orquestada,** y su estado vive solo en la petición.
- **Nada se reintenta,** por ADR-029. Cada llamada lleva timeout, y un fallo compensa en lugar de
  repetir.
- **Una compensación que se pierde no deja stock bloqueado:** la reserva vence sola a los diez
  minutos. Por eso el BFF no necesita una base de datos para la saga.
- **El cliente puede reintentar sin comprar dos veces:** la compra lleva un `Idempotency-Key`, el
  pedido lo guarda y el pago se identifica por su pedido.

### El inicio de sesión

**Keycloak es el proveedor de identidad, y el BFF es el único que valida el token.** El cliente
inicia sesión en Keycloak por OIDC y llama al BFF con su token. El BFF lo valida con el módulo de
autenticación de Nova para NestJS, que ya verifica la firma contra las claves públicas del emisor, y
pasa el cliente a los servicios en cada llamada.

Los servicios de Java confían en el BFF y no validan el token. Es aceptable en Plaza porque solo el
BFF queda expuesto, y queda dicho como deuda: los repos 06 y 11 de Keycloak en Java solo tienen un
README, y validar en cada servicio es otra capacidad, con su propio ADR.

El compose del repo 01 levanta Keycloak con un realm `plaza` importado, sus clientes y dos clientes
de prueba, uno por cada caso de la demo.

### Los eventos, con outbox

Cuando un pedido se confirma, `plaza-orders` publica `OrderConfirmed`. **El evento no se publica
en la misma línea que guarda el pedido:** se escribe en una tabla `outbox` dentro de la misma
transacción, y un proceso aparte lo lee y lo publica en Kafka. Así el pedido y su evento se
guardan juntos o no se guarda ninguno, y una caída de Kafka retrasa el evento en lugar de perderlo.

El consumidor recibe el evento al menos una vez, así que lo trata como idempotente: guarda el id de
cada evento que ya procesó.

### Lo que se deja fuera a propósito

| Pieza | Por qué no hace falta |
|---|---|
| Descubrimiento de servicios, como Eureka | las direcciones llegan por variables de entorno |
| Servidor de configuración | la configuración va en cada servicio, y los secretos en Vault |
| Un API Gateway aparte | el BFF ya es la única entrada |
| Service mesh, Kubernetes, event sourcing | son más grandes que el problema |

El curso usaba Eureka y un servidor de configuración. Dejarlos fuera con la razón escrita es parte
de lo que se muestra.

### Lo que muestra de Nova

| Capacidad | Dónde se ve | Estado en Nova |
|---|---|---|
| Estándar de API, con el mismo sobre y los mismos errores | los tres servicios; sin stock, Quarkus responde 409 y el BFF lo entrega con la misma forma | existe en los tres stacks |
| Una traza por compra | Grafana muestra la compra cruzando NestJS, Spring y Quarkus | existe en los tres stacks |
| Secretos | las credenciales de Postgres salen de Vault en los tres servicios de Java | existe en Spring (`nova-secrets` 1.0.0); **falta la extensión de Quarkus** |
| Inicio de sesión | Keycloak emite el token y el BFF lo valida | existe en NestJS; **falta** en Java |
| Mensajería con outbox | `plaza-orders` publica `OrderConfirmed` en Kafka por su outbox y `plaza-catalog` lo consume para llevar el ranking de lo más vendido | **falta**: un puerto con Kafka como adaptador, el outbox y la propagación de la traza |
| CQRS | `plaza-orders` separa los comandos (crear, confirmar, cancelar) de las consultas | **falta** |
| Generación de servicios | un servicio nuevo sale del arquetipo en vivo y el CI compartido lo verifica | **falta arreglar** los arquetipos 17 y 18 y la plantilla 19, que hoy generan proyectos que no compilan |

Cada capacidad que falta es su propio repositorio con su propio ADR, por
[ADR-041](../java/ADR-041-un-repositorio-por-capacidad.md), y Plaza es su primer consumidor.

### Los repositorios

**Un producto construido sobre Nova es su propia categoría, con su propio contador:**
`nova-<producto>-<NN>-<tecnología>-<nombre>`. Es la misma forma que ADR-038 dio a los ejemplos,
con el nombre del producto en el lugar de `example`. Un ejemplo muestra cómo se usa una pieza; un
producto es un sistema con varios servicios que se entienden entre sí, y el nombre lo dice.

| # | Repositorio | Contenido |
|---|---|---|
| 01 | `nova-plaza-01-shared-platform` | el producto: la descripción, el compose que levanta todo y el guion de la demo |
| 02 | `nova-plaza-02-nestjs-bff` | el BFF |
| 03 | `nova-plaza-03-spring-boot-orders` | pedidos |
| 04 | `nova-plaza-04-quarkus-catalog` | catálogo y stock |
| 05 | `nova-plaza-05-spring-boot-payments` | pagos simulados |

Un servicio por repositorio, como en un producto real: cada uno con su CI, su versión y su imagen.
El 01 es la entrada al producto; con un solo comando levanta lo que los servicios necesitan:
Postgres, Vault y Keycloak. El stack de observabilidad de `nova-shared-03-infrastructure` se levanta
aparte.

### Las fases

1. **El producto y los servicios de Java.** El repo 01 con su compose; los pedidos, el catálogo y
   los pagos con el estándar de API, sus bases y sus secretos en Vault. Incluye la extensión de
   secretos para Quarkus.
2. **El BFF, Keycloak y la compra orquestada**, con sus compensaciones. Con esta fase ya hay una
   demo que cruza los tres frameworks.
3. **La mensajería con outbox**, con el ranking de lo más vendido.
4. **CQRS** en los pedidos.
5. **Los arquetipos**, y el servicio nuevo generado en vivo.

## Fuera de alcance

- **Una pasarela de pago real.** El servicio de pagos es simulado.
- **Un frontend.** La demo se hace con una colección de peticiones contra el BFF y su OpenAPI.
- **El despliegue en la nube.** Plaza corre en local con el compose del repo 01.

## Preguntas abiertas

1. **La auditoría a MongoDB del curso.** El curso mandaba la auditoría por Kafka a MongoDB. Encaja
   en la fase 3, pero agrega un consumidor y una base más.
2. **La fecha de la presentación.** Decide si se llega a las cinco fases o se corta en la segunda.

## Alternativas descartadas

- **Que los servicios se llamen entre sí**, con los pedidos consultando el stock. Angel eligió el
  BFF como orquestador. Además, llevaría el cliente HTTP de Java a la fase 1 y la compensación a
  un servicio de negocio.
- **El nombre *Qhatu*,** la palabra quechua para el mercado. Angel lo prefirió en inglés o en
  español.
- **La categoría `example`** para estos repositorios. Angel pidió que lleven el nombre de la
  plataforma.
- **Un servicio de carrito.** Guardaría una lista que el cliente ya tiene.
- **Validar el token en cada servicio de Java** desde la fase 2. Obliga a construir Keycloak en Java
  antes de tener la compra.
- **Publicar el evento directo a Kafka** al confirmar el pedido. Si Kafka cae después de guardar, el
  evento se pierde; si se publica antes, puede salir un evento de un pedido que nunca se guardó.
- **Reusar `ms-course`.** No tiene una dependencia natural entre servicios, y no es el proceso del
  curso.
- **Un solo repositorio para todo Plaza.** Es más cómodo, pero no muestra lo que Nova resuelve:
  servicios separados que se ven y se comportan igual.

## Consecuencias

### Positivas

- Los invariantes de la plataforma se ven en vivo, en una petición, en lugar de describirse.
- Cada capacidad nueva nace con un consumidor real.
- La demo sigue el proceso del curso, así que se puede comparar pieza por pieza con lo que se vio en clase.

### Negativas

- Son cinco repositorios más que mantener, con su CI.
- La fase 1 depende de la extensión de secretos para Quarkus, que todavía no existe.
- Los servicios de Java confían en el BFF sin validar el token hasta que exista Keycloak en Java.
