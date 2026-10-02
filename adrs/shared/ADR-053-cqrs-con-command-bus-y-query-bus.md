# ADR-053: CQRS en Nova: los Contratos, el Command Bus y el Query Bus

## Estado

Aceptada (2026-10-02). Angel pidió empezar por CQRS al revisar la rúbrica del curso de Framework
Engineering, que pide el núcleo del patrón y los dos buses con comportamientos transversales, y
ningún repositorio de Nova los tiene. La aprobó el mismo día con dos cambios a las recomendaciones:
los mensajes son tipados de punta a punta y las consultas también se auditan. Las respuestas quedan
escritas en «Preguntas resueltas».
**Scope:** `shared` (Java ahora; NestJS y Quarkus con su primer consumidor).
**Aplica:** [ADR-041](../java/ADR-041-un-repositorio-por-capacidad.md) para la forma del repositorio,
[ADR-015](../java/ADR-015-librerias-puras-sin-dependencias-framework.md) para el núcleo sin framework,
[ADR-034](ADR-034-puertos-con-implementacion-por-defecto.md) para los puertos y
[ADR-031](ADR-031-modulo-de-errores-por-capas-con-trazabilidad.md) para los errores.
**Primer consumidor:** pedidos de Plaza, que es la fase 4 de
[ADR-043](ADR-043-plaza-la-plataforma-de-compras.md).

## Fecha

2026-10-02

## Contexto

**Nova no tiene nada de CQRS.** No hay un `Command` ni un `CommandHandler` en ningún repositorio.
ADR-015 lo anunciaba como parte de unas `ddd-utils` que nunca se escribieron, y ADR-043 lo deja como
fase 4 de Plaza, marcada «falta».

**Pedidos ya tiene la forma del problema.** `OrderService` mezcla en una clase una escritura, `place`,
con `@Transactional`, y dos lecturas, `find` y `list`, con `@Transactional(readOnly = true)`. Cada
método repite a mano lo transversal: la transacción, la validación y el log. Nada de eso es de
pedidos.

**Hay tres cosas que la rúbrica separa y que conviene separar igual aquí:**

1. **Los contratos:** `Command`, `CommandHandler`, `Query` y `QueryHandler`, sin infraestructura.
2. **Los buses:** reciben un mensaje, encuentran su handler y lo ejecutan.
3. **Los comportamientos transversales** alrededor del handler: validación, autorización,
   auditoría, logging y transacción.

**El ecosistema, consultado el 2026-10-02:**

- **Axon Framework** (Apache 2.0) está en la 5.x y soporta Spring Boot 4 desde la 5.0.3. Trae buses,
  pero viene con event sourcing, sagas, su propio modelo de configuración y Axon Server como pieza
  recomendada. Para dos buses síncronos dentro de un servicio es un framework entero.
- **PipelinR** (MIT) es el mediador de Java más cercano a MediatR de .NET: comandos, un pipeline de
  middlewares y handlers, sin dependencias. Va en la 0.11, de un solo mantenedor, y no separa comandos
  de consultas: todo es un `Command`.
- **Spring** no tiene buses. Spring Modulith publica eventos entre módulos, que es otro problema.
- **NestJS** tiene un paquete oficial, `@nestjs/cqrs` 12.1.0, con `CommandBus`, `QueryBus`,
  `EventBus`, `Command<T>` y `Query<T>` tipados por su resultado. No documenta un pipeline de
  comportamientos alrededor de los buses.
- **MediatR**, la referencia del patrón, llama *pipeline behaviors* a lo transversal: cada uno recibe
  el mensaje y el siguiente paso, y decide si sigue.

## Decisión

**Una capacidad propia: el núcleo de CQRS sin framework, con los dos buses y una cadena de
comportamientos, y un starter de Spring Boot que trae los comportamientos de Nova.** Los nombres
siguen a `@nestjs/cqrs`, para que el mismo código se lea igual en los dos stacks.

### Los contratos

| Tipo | Qué es |
|---|---|
| `Command<R>` | una intención de cambiar el estado, que devuelve `R` |
| `CommandHandler<C extends Command<R>, R>` | ejecuta un tipo de comando; uno y solo uno por tipo |
| `Query<R>` | una pregunta que no cambia el estado y devuelve `R` |
| `QueryHandler<Q extends Query<R>, R>` | responde un tipo de consulta; uno y solo uno por tipo |
| `CommandBus` | `<R> R execute(Command<R> command)` |
| `QueryBus` | `<R> R execute(Query<R> query)` |
| `CommandBehavior` y `QueryBehavior` | un paso de la cadena: recibe el mensaje y el siguiente paso, y lo llama o no |

- **Todo es tipado de punta a punta.** El resultado sale del tipo del mensaje: `execute(new
  FindOrder(id))` devuelve un `OrderView` sin un cast, y un handler que declara otro resultado no
  compila. Ningún contrato usa `Object`, y el bus no recibe una clase ni un nombre como argumento.
- **Los mensajes son records inmutables.** El tipo del mensaje es lo que encuentra al handler: la
  clase exacta, sin herencia, para que no haya dos handlers posibles para un mismo mensaje.
- **Un comando puede devolver un valor**, y lo recomendado es el identificador de lo que creó. Es la
  forma pragmática: pedidos responde 201 con el `Location` del pedido, y sin el identificador tendría
  que inventarlo antes. Un comando nunca devuelve la vista de lectura.
- **Los buses son síncronos y corren en el mismo hilo.** Un bus asíncrono es mensajería, y eso es la
  capacidad de outbox que propone ADR-048, todavía en revisión, no esta.
- **Un handler no conoce el bus ni los comportamientos.** Se prueba con un `new` y una llamada.

### Las reglas que ningún comportamiento cambia

- **Un tipo de mensaje tiene exactamente un handler.** Dos handlers para el mismo tipo impiden el
  arranque. Un mensaje sin handler es un `PlatformError` con el código `HANDLER_NOT_FOUND`, un 500:
  es un defecto del servicio, no del cliente.
- **Lo que lanza el handler sale tal cual.** Un `DomainError` llega al manejo de ADR-031 con su capa
  y su código; el bus no lo envuelve ni lo traduce.
- **Ni el contenido de un comando ni el resultado de una consulta aparecen en un log.** Solo el tipo,
  la duración y el resultado: éxito o el código del error. Es la misma regla de ADR-047.
- **Una consulta corre de solo lectura** cuando hay transacción, así que una escritura dentro de un
  `QueryHandler` falla en vez de pasar.

### Los comportamientos de Nova

El starter los trae en este orden, de afuera hacia adentro:

| # | Comportamiento | Comandos | Consultas | Qué hace |
|---|---|---|---|---|
| 1 | Observación | sí | sí | una `Observation` de Micrometer por mensaje: timer `nova.cqrs.command` o `nova.cqrs.query` con el tipo y el resultado, y un span en la traza de ADR-031 |
| 2 | Auditoría | sí | sí | registra quién, qué tipo, cuándo, cuánto tardó y con qué resultado, incluido un rechazo |
| 3 | Autorización | sí | sí | pregunta al puerto si el actor puede ejecutar ese tipo; si no, 403 |
| 4 | Validación | sí | sí | Bean Validation sobre el record; si falla, 400 con los errores por campo |
| 5 | Transacción | sí | sí, de solo lectura | `TransactionTemplate` con propagación `REQUIRED` |

- **La auditoría va antes que la autorización** para que quede registrado un intento rechazado: es
  lo que más importa auditar.
- **La transacción va adentro de todo** para que lo transversal no quede dentro del commit, y con
  `REQUIRED` se suma a una que ya exista. Es el caso de pedidos: la idempotencia de ADR-047 abre la
  transacción alrededor del controlador, y el comando tiene que confirmarse en ese mismo commit.
- **Cada comportamiento se apaga** con `nova.cqrs.<nombre>.enabled=false`. Uno propio se suma como
  bean con `@Order`, y queda entre los de Nova según su orden.
- **Cada uno se registra solo si su pieza existe:** la observación si hay Micrometer, la validación
  si hay un `Validator`, la transacción si hay un `PlatformTransactionManager`.

### Los puertos y la implementación por defecto

La misma forma que ADR-034 y ADR-047: el núcleo fija las reglas, cada decisión de una organización
es un puerto, y Nova trae la implementación por defecto.

| Puerto | Qué decide | Implementación de Nova |
|---|---|---|
| `ActorResolver` | quién ejecuta el mensaje | el nombre de la autenticación de Spring Security si existe; si no, ninguno |
| `AccessPolicy` | si un actor puede ejecutar un tipo de mensaje | permitir todo, para que el starter no cambie nada sin configurarlo |
| `AuditSink` | dónde va el registro de auditoría | una línea estructurada en el logger `nova.audit`, sin el contenido del mensaje |

Pedidos pone su propio `ActorResolver`, que toma el `X-Customer-Id` que manda el BFF de Plaza. Una
organización manda la auditoría a Kafka o a MongoDB, como pedía el curso, con su propio `AuditSink`.

### Los eventos de dominio

**`nova-cqrs` no trae un `EventBus`.** Un bus de eventos en memoria pierde un evento si el proceso
cae entre el commit y la entrega, y no dice nada. Los eventos se manejan así hasta que exista la
capacidad de outbox:

| Quién reacciona | Cómo |
|---|---|
| Algo dentro del mismo servicio | el agregado registra el evento con `AbstractAggregateRoot` de Spring Data, que lo publica al guardar, y quien reacciona usa `@TransactionalEventListener(phase = AFTER_COMMIT)` |
| Otro servicio | la capacidad de outbox de ADR-048: el evento se guarda en la misma transacción que el cambio y se entrega después |

- **Con `AFTER_COMMIT`, una reacción nunca ve un cambio que no se confirmó**, y un rollback descarta
  el evento. Si la reacción cambia estado, lo hace ejecutando un comando por el bus, en su propia
  transacción, así que también pasa por la auditoría y la autorización.
- **Un evento es un record inmutable con nombre en pasado**, como `OrderPlaced`. Lleva
  identificadores y no entidades, y no lleva datos personales que no necesite quien reacciona.
- **Nova no define un contrato `DomainEvent` todavía.** Su primer consumidor es el outbox, que
  necesita el identificador del evento, su instante y el `traceId` para serializarlo. El contrato
  nace ahí, con ADR-048, y no antes, por la regla de no agregar superficie sin consumidor.

### Dónde vive

| Stack | Dónde | Qué trae ahora |
|---|---|---|
| Java | `nova-java-27-cqrs`, familia `nova-cqrs` | `nova-cqrs` (`pe.edu.nova.java.libs`): contratos, buses, cadena y puertos, sin framework; `nova-cqrs-spring-boot-starter` (`pe.edu.nova.java.starters`): descubre los handlers como beans, valida que no haya duplicados al arrancar y registra los comportamientos |
| NestJS | — | nada todavía: el BFF de Plaza no tiene estado. Cuando un servicio con datos lo necesite, se adopta `@nestjs/cqrs` con los mismos nombres y se le suman los comportamientos |
| Quarkus | — | una extensión con su primer consumidor, que será el catálogo de Plaza |

- **El número 27 y no el 26:** ADR-052 reservó el 26 para la meta-extensión de Quarkus.
- **El starter cumple la condición de ADR-052 para el meta-starter:** sin un handler, los buses no
  hacen nada. Entra en el meta-starter cuando llegue a la 1.0.0.
- **Sale en la 0.1.0 y pasa a la 1.0.0 cuando pedidos lo use en `main`.**

### Pedidos migra

| Hoy, en `OrderService` | Con el bus |
|---|---|
| `place(customerId, key, request)` con `@Transactional` | `PlaceOrder` y `PlaceOrderHandler`, que devuelve el identificador |
| `find(customerId, id)` con `@Transactional(readOnly = true)` | `FindOrder` y `FindOrderHandler` |
| `list(customerId)` con `@Transactional(readOnly = true)` | `ListOrders` y `ListOrdersHandler` |

El controlador depende solo de `CommandBus` y `QueryBus`. Las reglas de arquitectura ya se lo
permiten: las interfaces viven en `nova-cqrs`, bajo `pe.edu.nova.java.libs..`, que el controlador
alcanza desde `nova-architecture-rules` 1.2.0. Confirmar y cancelar un pedido llegan como comandos
nuevos, sin tocar los existentes.

## Alternativas descartadas

- **Axon Framework.** Resuelve un problema más grande: event sourcing, sagas y un servidor propio.
  Adoptarlo para dos buses obliga a su modelo de configuración en todo servicio.
- **PipelinR.** Es lo más cercano, pero va en 0.x con un solo mantenedor, no separa comandos de
  consultas y Nova tendría que envolverlo igual para poner sus puertos y sus errores.
- **Servicios de aplicación sin bus**, un método por caso de uso. Es lo que tiene pedidos hoy: cada
  método repite la transacción, la validación y el log, y no hay dónde enchufar la auditoría o la
  autorización sin tocarlos todos.
- **Un solo bus para comandos y consultas.** Pierde la regla más útil del patrón: que una consulta
  corra de solo lectura, y que su auditoría la distinga de una escritura.
- **AOP sobre anotaciones en los servicios**, como `@Audited`. Funciona solo con beans de Spring,
  depende de proxies y no es un contrato que un handler pueda probar sin el contenedor.

## Preguntas resueltas

Angel las resolvió el 2026-10-02.

1. **El nombre del método de los buses.** Resuelta: **`execute` en los dos**, como `@nestjs/cqrs`, y
   con los mensajes **tipados de punta a punta**: el resultado sale del tipo del mensaje, sin casts
   ni `Object`.
2. **Si un comando puede devolver un valor.** Resuelta: **sí, tipado por su `Command<R>`**, y lo
   recomendado es el identificador de lo que creó, nunca la vista de lectura.
3. **Si las consultas se auditan.** Resuelta: **sí, igual que los comandos**, porque la auditoría
   importa también para saber quién leyó qué. El registro no lleva el contenido del mensaje ni el
   resultado, así que su costo es una línea por consulta. Un servicio que no lo quiera para sus
   consultas lo apaga con `nova.cqrs.audit.queries=false`.
4. **El destino de la auditoría por defecto.** Se mantiene la recomendada: **el logger
   `nova.audit`**, que ya llega a la pila de observabilidad, y un `AuditSink` propio para cualquier
   otro destino.
5. **La autorización.** Resuelta: **un mecanismo general, el puerto `AccessPolicy`**, que por defecto
   permite todo para que el starter no rompa al servicio que lo agrega. Los roles y permisos de
   Keycloak entran como una implementación de ese puerto, que lee los roles del token del actor,
   cuando llegue la seguridad de Spring; no hace falta otro mecanismo para eso.
6. **Los eventos de dominio.** Resuelta: **sin `EventBus` en esta capacidad**, con la forma que dice
   «Los eventos de dominio», arriba.

## Consecuencias

### Positivas

- La rúbrica pide CQRS, Command Bus y Query Bus con comportamientos transversales, y quedan
  cubiertos con una capacidad que tiene un consumidor real.
- Lo transversal se escribe una vez: un caso de uso nuevo en pedidos es un record y un handler.
- La auditoría y la autorización tienen un lugar, y una organización las cambia con un bean.
- Un handler se prueba sin Spring.

### Negativas

- Es un repositorio más, con dos módulos.
- Un caso de uso pasa de un método a dos tipos, el mensaje y su handler.
- El orden de los comportamientos es parte del contrato: cambiarlo es una versión mayor.
- La traza gana un span por mensaje.

## Fuentes

Consultadas el 2026-10-02.

- [Axon Framework 5.0: Spring Boot Integration](https://docs.axoniq.io/axon-framework-reference/5.0/spring-boot-integration/)
- [Axon Framework 4.13.0, anuncio](https://discuss.axoniq.io/t/axon-framework-release-4-13-0/6606)
- [sizovs/PipelinR](https://github.com/sizovs/PipelinR)
- [NestJS: CQRS](https://docs.nestjs.com/recipes/cqrs)
- [Martin Fowler: CQRS](https://martinfowler.com/bliki/CQRS.html)
- [MediatR: Behaviors](https://github.com/LuckyPennySoftware/MediatR/wiki/Behaviors)
