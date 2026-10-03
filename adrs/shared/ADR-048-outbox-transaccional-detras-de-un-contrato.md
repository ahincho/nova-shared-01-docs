# ADR-048: La Salida de Eventos, con un Outbox Transaccional detrás de un Contrato

## Estado

Aceptada (2026-10-02). Propuesta el 2026-09-30; Angel respondió las preguntas abiertas el
2026-10-02: **Debezium publica**, la implementación es **propia de Nova**, un evento que no se puede
publicar **bloquea y alerta**, y Plaza publica **`OrderCreated`, `OrderConfirmed` y `OrderCancelled`**,
con la auditoría en MongoDB como segundo consumidor.
**Scope:** `shared` (Java y NestJS).
**Aplica:** [ADR-041](../java/ADR-041-un-repositorio-por-capacidad.md) para la forma del repositorio,
[ADR-042](ADR-042-secretos-detras-de-un-contrato.md) y
[ADR-047](ADR-047-idempotencia-detras-de-un-contrato.md) para el contrato con adaptadores,
[ADR-034](ADR-034-puertos-con-implementacion-por-defecto.md) para lo que es regla y lo que es
convención, y [ADR-032](ADR-032-observabilidad-como-puerto-conectable.md) para `traceparent`.
**Consumidores:** pedidos de Plaza escribe los tres eventos; el catálogo consume `OrderConfirmed` para
el ranking de lo más vendido, y la auditoría guarda los tres en MongoDB
([ADR-043](ADR-043-plaza-la-plataforma-de-compras.md)).

## Fecha

2026-09-30, aceptada el 2026-10-02.

## Contexto

ADR-047 resuelve la entrada: un reintento del cliente no compra dos veces. Falta la salida: que un
evento se publique **si y solo si** la transacción del negocio se confirmó. ADR-043 ya lo decidió para
Plaza -el evento se escribe en la misma transacción, un proceso aparte lo publica en Kafka y el
consumidor guarda el id de cada evento procesado- y dejó pendiente «un puerto con Kafka como
adaptador, el outbox y la propagación de la traza».

Publicar directo al broker después del commit, o con `@TransactionalEventListener(AFTER_COMMIT)`,
pierde el evento si el proceso cae entre el commit y el envío. Las transacciones de Kafka tampoco
sirven: son atómicas dentro de Kafka y no incluyen la base de datos.

**Plaza hoy.** Pedidos ya crea, confirma y cancela, y el catálogo existe en Quarkus
([ADR-056](ADR-056-plaza-fase-1-catalogo-y-pagos-en-nestjs.md)). El compose de Plaza no tiene Kafka.

**El ecosistema, consultado el 2026-09-30:**

- **NestJS** tiene un paquete oficial, `@nestjs/outbox` (MIT), pero va en la 0.0.1, del 2026-09-25,
  no trae almacenes SQL y no propaga `traceparent`.
- **Spring Modulith** dice en su propia documentación que su externalización no es un outbox
  completo: no reintenta de forma continua ni ordena. Su modo `outbox`, desde la 2.1, pide Spring
  Boot 4.1; Nova está en 4.0.8.
- **Namastack Outbox** (Apache-2.0) es la mejor opción de la comunidad para Spring, pero es solo para
  Spring, guarda el payload por nombre de clase y desde la 1.7 compila contra Boot 4.1.
- **Quarkus** no tiene outbox en Quarkiverse. La extensión de Debezium solo escribe la fila.
- **Debezium** es maduro y lee el log de PostgreSQL: publica en el orden en que las transacciones se
  confirmaron, sin sondear. Su Event Router convierte una fila del outbox en un registro de Kafka, y
  puede poner columnas como cabeceras. Pide Kafka Connect, `wal_level=logical` y un slot de
  replicación.

**Tres trampas que el diseño tiene que evitar:**

- **La secuencia no es el orden de commit.** Un relevo que lee «id mayor que el último» se salta la
  fila de una transacción que tomó el número antes y confirmó después.
- **`LISTEN/NOTIFY` toma un bloqueo global al confirmar**, y la saturación de su cola hace fallar los
  commits.
- **No existe «exactamente una vez» de punta a punta.** Un publicador puede caer después de publicar
  y antes de anotarlo.

Debezium esquiva las dos primeras por construcción: lee el log en orden de commit y no toca la base
con consultas. La tercera la resuelve el consumidor.

## Decisión

**Una capacidad propia para escribir el evento y para deduplicarlo, y Debezium para publicarlo. Un
servicio declara el evento dentro de su transacción y nunca sabe cómo ni cuándo sale: no conoce
Kafka, ni su dirección, ni su cliente.**

### Las reglas que ningún adaptador cambia

1. **El evento se escribe en la misma transacción del negocio.** Sin transacción activa, agregarlo
   falla: escribir en autocommit es justo la doble escritura que se quiere quitar.
2. **Al menos una vez**, con un `id` estable. El contrato no promete «exactamente una vez».
3. **Orden por agregado**, no global.
4. **El payload es opaco:** JSON ya serializado por el servicio. El núcleo no conoce clases del
   dominio ni la versión de Jackson, que es la 3 en Spring Boot 4 y la 2 en Quarkus 3.33.
5. **Ni el payload, ni las cabeceras, ni la clave aparecen en un log.**
6. **Un evento que no se puede publicar detiene la salida y alerta**, nunca se descarta en silencio
   ni se adelanta el siguiente.
7. **Sin almacén persistente el servicio no arranca**, salvo `nova.outbox.store=memory` elegido a
   propósito, como en ADR-047.
8. **La traza continúa:** `traceparent` y `tracestate` se capturan al agregar el evento.
9. **El broker no forma parte de la disponibilidad.** El servicio no habla con Kafka: si Kafka o
   Kafka Connect caen, sigue aceptando escrituras y el log acumula.
10. **Quien consume deduplica**, con el `id` del evento como clave.

### Quién publica: Debezium, con el Event Router

Kafka Connect corre el conector de PostgreSQL de Debezium contra la base de pedidos, filtrado a la
tabla `outbox`, con el Event Router y su configuración versionada en el repositorio del producto:

| Qué | Configuración |
|---|---|
| El tópico | `route.by.field=aggregate_type` y `route.topic.replacement=plaza.${routedByValue}`: los pedidos van a `plaza.orders` |
| La clave del registro | `table.field.event.key=aggregate_id` |
| El valor | `table.field.event.payload=payload`, como texto JSON con `StringConverter` |
| Las cabeceras | `table.fields.additional.placement` con las columnas del cable, más `InsertHeader` para `content-type` |
| La credencial | `${env:...}` con el `EnvVarConfigProvider` de Kafka, nunca escrita en el JSON |

**La fila se borra en la misma transacción en que se inserta**
(`nova.outbox.remove-after-insert=true`), como hace la extensión de Quarkus de Debezium: el log
conserva la inserción, el Event Router ignora el borrado y la tabla no crece. Con `false` la fila
queda para depurar, y purgarla es tarea de quien eligió guardarla.

**Bloquear y alertar** es el comportamiento por defecto de Kafka Connect con
`errors.tolerance=none`: un registro que no se puede transformar o publicar deja la tarea en
`FAILED`, y el offset del log no avanza, así que nada se adelanta. Se vigilan dos cosas: el estado
del conector en la API de Kafka Connect, y el retraso del slot en `pg_replication_slots`, que crece
mientras la salida está detenida. Saltar es una decisión explícita, `errors.tolerance=all`, y no es
la de Plaza.

### El cable: CloudEvents 1.0, en modo binario sobre Kafka

Lo que ven los consumidores es el cable, y el cable no depende de quién publica:

| Atributo | De dónde sale | En Kafka |
|---|---|---|
| `specversion` | la columna `specversion`, que la tabla llena con `1.0` | `ce_specversion` |
| `id` | un UUID por evento, columna `id` | `ce_id` |
| `source` | la identidad del servicio, como `/plaza/orders` | `ce_source` |
| `type` | el tipo versionado, como `pe.edu.nova.plaza.order.confirmed.v1` | `ce_type` |
| `subject` | el id del agregado | `ce_subject` |
| `time` | el momento en que se agregó | `ce_time` |
| `datacontenttype` | `application/json`, constante | `content-type` |
| `data` | el payload | el valor del registro |
| `partitionkey` | el id del agregado | **la clave del registro** |
| `traceparent`, `tracestate` | el contexto de creación | `ce_traceparent`, `ce_tracestate`, y `traceparent` |

- **Un tópico por tipo de agregado**, como `plaza.orders`, y no por tipo de evento: así los eventos
  del mismo pedido caen en la misma partición y conservan su orden.
- **Un cambio incompatible es otro tipo**, con otro sufijo de versión.
- **El mapeo es propio**, sin el SDK de CloudEvents, porque son diez cabeceras.

### La traza: una sola, de la compra al ranking

La columna `traceparent` guarda el contexto en que se agregó el evento, y Debezium la pone en dos
cabeceras: `ce_traceparent`, que conserva el contexto de creación como dice CloudEvents, y
`traceparent`, la que lee la instrumentación de Kafka de OpenTelemetry. Así el consumidor continúa la
traza sin código propio, y Tempo muestra una sola traza del BFF a pedidos, y de ahí al catálogo y a
la auditoría. Kafka Connect no agrega un span propio: el salto por el log no se ve, y no hace falta.

### El contrato y la implementación por defecto de Nova

| Puerto | Qué decide | Implementación de Nova |
|---|---|---|
| `Outbox` | recibir el evento dentro de la transacción | arma el evento, captura la traza, lo escribe por el almacén y, si se pidió, lo borra en la misma transacción |
| `OutboxStore` | escribir y borrar la fila en la transacción vigente | PostgreSQL por JDBC; en memoria para desarrollo y pruebas |
| `Transactions` | decir si hay una transacción activa | la de Spring en el starter |
| `TraceContext` | capturar el contexto de la traza | Micrometer Tracing en Spring |
| `Inbox` | registrar, en la transacción del efecto, que un consumidor ya procesó un evento | PostgreSQL por JDBC; en memoria |

**La tabla también es contrato.** `outbox` lleva `id` (`uuid`), `aggregate_type`, `aggregate_id`,
`type`, `source`, `time` (`timestamptz`), `payload` (`jsonb`), `traceparent`, `tracestate` y `specversion`, con
`1.0` por defecto: `InsertHeader` convierte el texto `1.0` en un número, así que la constante vive en la tabla. La crea
el servicio con su migración, copiando el DDL que documenta la biblioteca; nada se crea solo en
producción. Sin columnas de reintento ni de arrendamiento: con Debezium no hacen falta.

**El inbox** es una inserción condicional en `inbox_message` (`consumer`, `source`, `id`, con su clave
primaria) dentro de la transacción que aplica el efecto: si el efecto se revierte, el registro
también, y un duplicado concurrente espera al primero por la clave. **No es el `IdempotencyStore` de
ADR-047:** comparten el principio, pero acá basta una inserción.

El almacén JDBC recibe las conexiones por una interfaz de una línea, para sumarse a la transacción
de cualquier stack: Spring las toma con `DataSourceUtils`, y Quarkus con su `DataSource`, que Agroal
enlista en la transacción JTA.

### Qué hace cada stack

| Stack | Escribe | Consume |
|---|---|---|
| Spring Boot, pedidos | el outbox, con el starter, en la transacción del comando | no |
| Quarkus, catálogo | no | `OrderConfirmed`, con SmallRye `@Incoming`, `@Transactional` y el `Inbox` de Nova sobre JDBC |
| Spring Boot, auditoría | no | los tres eventos, con Spring for Apache Kafka, en MongoDB |
| NestJS, el BFF | no, porque no tiene datos (ADR-020) | no |

**La auditoría deduplica con MongoDB:** cada evento es un documento con `_id` igual a `ce_id`, y un
duplicado choca con la clave. El `Inbox` de Nova es SQL y ahí no hace falta.

### Dónde vive

| Qué | Dónde |
|---|---|
| Java | `nova-java-26-outbox`: `nova-outbox` (contrato, núcleo, almacenes JDBC y en memoria, e inbox) y `nova-outbox-spring-boot-starter` |
| Kafka, Kafka Connect y la configuración del conector | el compose de `nova-plaza-01-shared-platform`: `apache/kafka` 4.3.1 en KRaft de un nodo y `quay.io/debezium/connect` 3.7.0.Final |
| La auditoría | `nova-plaza-06-spring-boot-audit`, con MongoDB 8.0 en el mismo compose |

**Llegan con su consumidor**, por la regla de no agregar superficie sin uno:

- **Un relevo dentro del servicio**, por sondeo con arrendamiento: cuando una organización no pueda
  operar Kafka Connect. La tabla admite sumarle las columnas de reintento sin romper a Debezium.
- **Un adaptador de Namastack:** cuando un equipo lo pida y Nova esté en Boot 4.1.
- **SNS y SQS:** cuando una organización en AWS lo necesite.
- **La extensión de Quarkus que escribe:** con el primer productor en Quarkus.
- **NestJS:** con el primer servicio Nest dueño de datos que publique.

### Los eventos de Plaza

| Tipo | Cuándo | Qué lleva |
|---|---|---|
| `pe.edu.nova.plaza.order.created.v1` | al crear el pedido | id, moneda, total, ítems y momento |
| `pe.edu.nova.plaza.order.confirmed.v1` | al pasar a confirmado | id, moneda, total, ítems y momento |
| `pe.edu.nova.plaza.order.cancelled.v1` | al pasar a cancelado | id y momento |

Repetir una confirmación o una cancelación no cambia el estado, así que no escribe otro evento.
**Ninguno lleva `customerId`:** ni el ranking ni la auditoría por pedido lo necesitan, y el BFF
comprueba que el pedido sea del cliente antes de mostrar su historia.

### El orden de trabajo

1. **Kafka, Kafka Connect y MongoDB entran en el compose** de Plaza, con `wal_level=logical` en la
   base de pedidos y el conector registrado al levantar.
2. **`nova-java-26-outbox`:** el núcleo, el almacén JDBC, el inbox y el starter de Spring.
3. **Pedidos escribe los tres eventos** en el mismo commit que el cambio de estado.
4. **El catálogo consume `OrderConfirmed`** con el `Inbox` y lleva el ranking.
5. **La auditoría guarda los tres** y responde la historia de un pedido.
6. **El BFF expone el ranking y la historia.**

### Cómo se prueba

- **La biblioteca**, con Testcontainers para PostgreSQL: sin transacción falla; un rollback no deja
  fila; un commit sí, con la traza; borrar después de insertar deja la tabla vacía; el mismo evento
  dos veces lo descarta el inbox, también entre dos transacciones concurrentes.
- **El cable**, en el CI del repo 01: levanta el compose, inserta una fila en `outbox` y lee
  `plaza.orders` para comprobar la clave, las cabeceras y el payload.
- **Cada consumidor**, con su evento de entrada y el mismo evento repetido.

## Alternativas descartadas

- **Publicar al broker después del commit**, directo o con `@TransactionalEventListener`: una caída
  entre los dos pierde el evento. Ya lo descartó ADR-043.
- **Las transacciones de Kafka:** no incluyen la base de datos.
- **Un relevo por sondeo dentro del servicio como mecanismo por defecto:** era la recomendación de la
  propuesta. Angel eligió Debezium: lee en orden de commit sin sondear, saca a Kafka del servicio y es
  lo que se usa en producción. Queda como adaptador futuro.
- **Spring Modulith o Namastack como implementación por defecto:** solo para Spring, y el segundo
  compila contra Boot 4.1. Namastack queda como adaptador.
- **El formato de Debezium para la traza** (`tracingspancontext` y su SMT de tracing): exige el
  agente de OpenTelemetry dentro de Kafka Connect y no produce `traceparent`.
- **`LISTEN/NOTIFY` como canal y el outbox sin tabla** con `pg_logical_emit_message`: por las trampas
  del contexto, y porque lo último no deja un DDL que documentar.
- **Adoptar `@nestjs/outbox` ahora:** no hay productor en NestJS.

## Preguntas resueltas

1. **¿Quién publica?** Debezium, con el Event Router.
2. **¿Implementación propia o Namastack?** Propia, para escribir y para deduplicar.
3. **¿Qué pasa si un evento no se puede publicar?** Se bloquea la salida y se alerta; saltar es
   `errors.tolerance=all`, elegido a propósito.
4. **¿Un solo líder o relevos particionados?** Ya no aplica: el conector de PostgreSQL de Debezium
   corre en una sola tarea por slot.
5. **¿Qué eventos publica Plaza?** `OrderCreated`, `OrderConfirmed` y `OrderCancelled`, con la
   auditoría en MongoDB como segundo consumidor. Resuelve la pregunta 1 de ADR-043.
6. **¿Nova pasa a Spring Boot 4.1?** Se decide aparte, antes del 2026-12-31, cuando la 4.0 deja de
   tener soporte OSS.

## Consecuencias

### Positivas

- Un evento sale si y solo si la transacción confirmó, en el orden de commit, y un reintento del
  cliente, sumado a ADR-047, no produce un segundo evento.
- El servicio no depende de Kafka: no trae su cliente, no conoce su dirección y no cae con él.
- Los consumidores de dos stacks leen el mismo cable, y una compra se ve como una sola traza.

### Negativas

- Kafka y Kafka Connect entran al compose de Plaza, con su consumo de memoria.
- Un slot de replicación detenido retiene log en el disco de PostgreSQL. Se acota con
  `max_slot_wal_keep_size`, y vigilarlo es parte de operar el outbox.
- La base de pedidos necesita `wal_level=logical` y un usuario con permiso de replicación.
- El inbox suma una tabla y una escritura por evento consumido.

## Fuentes

Consultadas el 2026-09-30 y el 2026-10-02.

- [Debezium: Outbox Event Router](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html)
- [Debezium: conector de PostgreSQL](https://debezium.io/documentation/reference/stable/connectors/postgresql.html)
- [Debezium: extensión de Quarkus para el outbox](https://debezium.io/documentation/reference/stable/integrations/outbox.html)
- [Kafka Connect: InsertHeader y los proveedores de configuración](https://kafka.apache.org/43/configuration/kafka-connect-configs/)
- [NestJS: Transactional outbox](https://docs.nestjs.com/reliability/outbox)
- [Spring Modulith: Working with Application Events](https://docs.spring.io/spring-modulith/reference/events.html)
- [Namastack Outbox](https://www.namastack.io/docs/)
- [Quarkus 3.33: Kafka](https://quarkus.io/version/3.33/guides/kafka)
- [Microservices.io: Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html)
- [Microservices.io: Transaction log tailing](https://microservices.io/patterns/data/transaction-log-tailing.html)
- [PostgreSQL: replicación lógica y slots](https://www.postgresql.org/docs/current/logicaldecoding-explanation.html)
- [PostgreSQL: NOTIFY](https://www.postgresql.org/docs/current/sql-notify.html)
- [CloudEvents: especificación](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md)
- [CloudEvents: enlace con Kafka](https://github.com/cloudevents/spec/blob/main/cloudevents/bindings/kafka-protocol-binding.md)
- [CloudEvents: extensión de trazado distribuido](https://github.com/cloudevents/spec/blob/main/cloudevents/extensions/distributed-tracing.md)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
