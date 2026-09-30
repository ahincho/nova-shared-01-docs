# ADR-048: La Salida de Eventos, con un Outbox Transaccional detrás de un Contrato

## Estado

Propuesta (2026-09-30). Angel pidió revisar el outbox para Spring, Quarkus y NestJS después de la
idempotencia. Espera su aprobación, con las respuestas a las preguntas abiertas.
**Scope:** `shared` (Java y NestJS).
**Aplica:** [ADR-041](../java/ADR-041-un-repositorio-por-capacidad.md) para la forma del repositorio,
[ADR-042](ADR-042-secretos-detras-de-un-contrato.md) y
[ADR-047](ADR-047-idempotencia-detras-de-un-contrato.md) para el contrato con adaptadores,
[ADR-034](ADR-034-puertos-con-implementacion-por-defecto.md) para lo que es regla y lo que es
convención, y [ADR-032](ADR-032-observabilidad-como-puerto-conectable.md) para `traceparent`.
**Primer consumidor:** pedidos de Plaza publica `OrderConfirmed` y el catálogo lo consume para el
ranking de lo más vendido ([ADR-043](ADR-043-plaza-la-plataforma-de-compras.md)).

## Fecha

2026-09-30

## Contexto

ADR-047 resuelve la entrada: un reintento del cliente no compra dos veces. Falta la salida: que un
evento se publique **si y solo si** la transacción del negocio se confirmó. ADR-043 ya lo decidió para
Plaza -el evento se escribe en la misma transacción, Kafka es el broker, `OrderConfirmed` es el
evento y el consumidor guarda el id de cada evento procesado- y dejó pendiente «un puerto con Kafka
como adaptador, el outbox y la propagación de la traza».

Publicar directo al broker después del commit, o con `@TransactionalEventListener(AFTER_COMMIT)`,
pierde el evento si el proceso cae entre el commit y el envío. Las transacciones de Kafka tampoco
sirven: son atómicas dentro de Kafka y no incluyen la base de datos.

**Plaza hoy.** Pedidos crea, consulta y lista; **no tiene `confirm` ni `cancel`**, así que
`OrderConfirmed` todavía no existe. El catálogo no existe como repositorio, y el compose de Plaza no
tiene Kafka.

**El ecosistema, consultado el 2026-09-30:**

- **NestJS** tiene un paquete oficial, `@nestjs/outbox` (MIT), con arrendamiento con cerco, orden
  por clave, reintentos, tabla de muertos e inbox. Pero va en la 0.0.1, del 2026-09-25, no trae
  almacenes SQL, es ESM y no propaga `traceparent`. Está donde estaba `@nestjs/idempotency` cuando se
  escribió ADR-047.
- **Spring Modulith** dice en su propia documentación que su externalización no es un outbox
  completo: no reintenta de forma continua ni ordena. Su modo `outbox`, desde la 2.1, delega en
  Namastack o JobRunr y pide Spring Boot 4.1; Nova está en 4.0.8.
- **Namastack Outbox** (Apache-2.0, 1.9.0 del 2026-08-28) es la mejor opción de la comunidad, pero
  nació en septiembre de 2025, es solo para Spring, está escrita en Kotlin, guarda el payload por
  nombre de clase y desde la 1.7 compila contra Boot 4.1.
- **Quarkus** no tiene outbox en Quarkiverse. La extensión de Debezium solo escribe la fila: publicar
  exige Debezium en marcha.
- **Debezium** es maduro, pero es infraestructura: Kafka Connect, `wal_level=logical` y un slot de
  replicación. Guarda la traza en un formato propio, no como `traceparent`, y su conversor a
  CloudEvents solo produce el modo estructurado.

**Tres trampas que el diseño tiene que evitar:**

- **La secuencia no es el orden de commit.** Un relevo que lee «id mayor que el último» se salta la
  fila de una transacción que tomó el número antes y confirmó después.
- **`LISTEN/NOTIFY` toma un bloqueo global al confirmar**, y la saturación de su cola hace fallar los
  commits. Sirve de despertador, nunca de canal.
- **No existe «exactamente una vez» de punta a punta.** El relevo puede caer después de publicar y
  antes de anotarlo. La idempotencia del productor de Kafka no cubre un relevo que se reinicia.

Nova ya tenía un boceto de outbox, con un `findPending` sin arrendamiento: con dos réplicas, las dos
publicarían las mismas filas. Es anterior a ADR-041.

## Decisión

**Una capacidad propia, con un contrato y la implementación por defecto de Nova. Un servicio declara
el evento dentro de su transacción y nunca sabe cómo ni cuándo sale: cómo sale es un puerto, y cuándo
lo decide el relevo.**

### Las reglas que ningún adaptador cambia

1. **El evento se escribe en la misma transacción del negocio.** Sin transacción activa, agregarlo
   falla: escribir en autocommit es justo la doble escritura que se quiere quitar.
2. **Al menos una vez**, con un `id` estable entre reintentos. El contrato no promete «exactamente
   una vez».
3. **Orden por agregado**, no global.
4. **El payload es opaco:** JSON ya serializado por el servicio. El núcleo no conoce clases del
   dominio ni la versión de Jackson, que es la 3 en Spring Boot 4 y la 2 en Quarkus 3.33.
5. **Ni el payload, ni las cabeceras, ni la clave aparecen en un log.**
6. **Toda llamada al broker lleva timeout** y un presupuesto de reintentos acotado. Agotarlo produce
   una alerta, nunca un descarte silencioso.
7. **Sin almacén persistente el servicio no arranca**, salvo `nova.outbox.store=memory` elegido a
   propósito, como en ADR-047.
8. **La traza continúa:** `traceparent` y `tracestate` se capturan al agregar el evento.
9. **El broker no forma parte de la disponibilidad.** Si Kafka cae, el servicio sigue aceptando
   escrituras, el relevo acumula y el indicador de salud no cae por eso.
10. **Quien consume deduplica**, con el `id` del evento como clave.

El reintento del relevo no contradice [ADR-029](../nest/ADR-029-sin-reintentos-en-el-cliente-http.md):
es idempotente por `id`, tiene un presupuesto acotado y no está en el camino de ninguna petición.

### El cable: CloudEvents 1.0, en modo binario sobre Kafka

Lo que ven los tres stacks es el cable, y el cable es el mismo:

| Atributo | De dónde sale | En Kafka |
|---|---|---|
| `specversion` | `1.0` | `ce_specversion` |
| `id` | un UUID por evento | `ce_id` |
| `source` | la identidad del servicio, como `/plaza/orders` | `ce_source` |
| `type` | el tipo versionado, como `pe.edu.nova.plaza.order.confirmed.v1` | `ce_type` |
| `subject` | el id del agregado | `ce_subject` |
| `time` | el momento en que se agregó | `ce_time` |
| `datacontenttype` | `application/json` | `content-type` |
| `data` | el payload | el valor del registro |
| `partitionkey` | el id del agregado | **la clave del registro** |
| `traceparent`, `tracestate` | el contexto de creación | `ce_traceparent`, `ce_tracestate` |

- **Un tópico por tipo de agregado**, como `plaza.orders`, y no por tipo de evento: así los eventos
  del mismo pedido caen en la misma partición y conservan su orden. Es también el valor por defecto
  de Debezium.
- **Un cambio incompatible es otro tipo**, con otro sufijo de versión. El esquema de cada evento es
  un JSON Schema en el repositorio, sin registro de esquemas.
- **El mapeo es propio**, sin depender del SDK de CloudEvents, porque son diez cabeceras. El SDK
  queda para las pruebas de conformidad.

### La traza: una sola, de la compra al ranking

`ce_traceparent` conserva intacto el contexto en que se creó el evento. El relevo abre un span
`outbox.publish` **hijo** de ese contexto, y el cliente de Kafka inyecta el `traceparent` del salto.
El consumidor continúa desde `traceparent` y, si falta, desde `ce_traceparent`. Así Tempo muestra una
sola traza del BFF a pedidos, al outbox, a Kafka y al catálogo, que es lo que promete ADR-043.

### El contrato y la implementación por defecto de Nova

La misma forma que ADR-042 y ADR-047: el núcleo fija las reglas, cada pieza es un puerto, Nova trae
la implementación por defecto, y una organización pone la suya sin forkear.

| Puerto | Qué decide | Implementación de Nova |
|---|---|---|
| `Outbox` | recibir el evento dentro de la transacción | lo escribe por el almacén en la transacción vigente y despierta al relevo después del commit |
| `OutboxStore` | agregar, reclamar con arrendamiento, cerrar con cerco por dueño, reprogramar, mandar a muertos, purgar y dar estadísticas; cada operación, atómica | PostgreSQL por JDBC; en memoria para desarrollo y pruebas |
| `OutboxPublisher` | llevar un registro al broker, con timeout | Kafka |
| `TraceContext` | capturar y restaurar el contexto de la traza | Micrometer en Spring |

**La tabla también es contrato.** Lleva `seq`, `id`, `aggregate_type`, `aggregate_id`, `type`,
`source`, `payload` (`jsonb`), `headers` (`jsonb`), los campos de reintento (`created_at`,
`next_attempt_at`, `attempts`, `last_error`) y los del arrendamiento (`lease_owner`, `lease_until`),
más una tabla de muertos. La crea el servicio con su migración, copiando el DDL que documenta la
biblioteca; nada se crea solo en producción. Como las columnas están nombradas, el Event Router de
Debezium puede leerla con su configuración, y el relevo se cambia sin tocar el servicio:
`nova.outbox.relay.enabled=false` significa «lo publica un proceso externo».

**El relevo por defecto** es un bucle dentro del servicio, en un hilo virtual:

- **Reclama por arrendamiento**, nunca por cursor: una transacción corta marca `lease_owner` y
  `lease_until` con `FOR UPDATE SKIP LOCKED`, publica fuera de la transacción y cierra con una
  escritura que repite `lease_owner` en su `WHERE`. Un relevo que se durmió más allá de su
  arrendamiento no cambia nada.
- **Cabeza de línea por agregado:** solo se reclama el evento pendiente más antiguo de cada agregado.
  La inserción de dos eventos del mismo agregado ya se serializa por el bloqueo del propio agregado
  (`@Version` en pedidos).
- **Un solo líder**, con un bloqueo asesor de sesión: la réplica que lo tiene publica, y si su
  conexión cae, otra lo toma.
- **Se despierta después del commit**, dentro del proceso, y sondea como red de seguridad. Sin
  `LISTEN/NOTIFY`.

**El publicador de Kafka** usa `acks=all` y la idempotencia del productor, que ya vienen por defecto,
y espera el acuse antes de cerrar la fila.

**Los valores por defecto**, configurables bajo `nova.outbox.*`, son los de `@nestjs/outbox` salvo
el sondeo, para que los dos stacks se comporten igual:

| Parámetro | Valor |
|---|---|
| Sondeo | 1 s, además del despertar después del commit |
| Lote | 100 |
| Arrendamiento | 30 s |
| Timeout de publicación | 10 s, un tercio del arrendamiento |
| Reintentos | 20, con retroceso de 1 s a 5 min y jitter |
| Al agotarse | se bloquea el agregado y se alerta (pregunta abierta 3) |
| Publicados | se borran al publicarse |
| Muertos | se conservan hasta que una persona los reencole o los descarte |

**Las métricas** siguen el prefijo de `nova.errors` y llevan solo etiquetas de baja cardinalidad, el
tipo de agregado y el de evento, nunca un id: `nova.outbox.pending`, `nova.outbox.oldest.age`,
`nova.outbox.published`, `nova.outbox.publish.duration`, `nova.outbox.failures` y
`nova.outbox.dead`. La que se vigila es `nova.outbox.oldest.age`: crece mientras el broker está caído.

### El inbox, para quien consume

Un puerto `Inbox` de una sola operación: registrar, en la transacción que aplica el efecto, que un
consumidor ya procesó el evento de un `source` con un `id`. Si el efecto se revierte, el registro
también; un duplicado concurrente espera al primero por el índice único. Se retiene más tiempo que el
tópico, porque Kafka permite releer.

**No es el `IdempotencyStore` de ADR-047.** Comparten el principio, unicidad en la misma transacción,
pero no el contrato: allá hay huella, lock renovable y respuesta guardada, y acá basta una inserción
condicional. Llega con el primer consumidor, el catálogo; no antes.

### Qué hace cada stack

| Stack | Escribe | Publica | Consume |
|---|---|---|---|
| Spring Boot, pedidos | el outbox, en la transacción del negocio | el relevo de Nova y el publicador de Kafka | no |
| Quarkus, catálogo | no | no | SmallRye `@Incoming` con `@Transactional`, y el `Inbox` de Nova |
| NestJS, el BFF | no, porque no tiene datos (ADR-020) | no | no |

### Dónde vive

| Qué | Dónde |
|---|---|
| Java | `nova-java-26-outbox`, familia `nova-outbox`: `nova-outbox` (contrato, núcleo, relevo, almacén en memoria y suites de contrato), `nova-outbox-jdbc`, `nova-outbox-kafka` y `nova-outbox-spring-boot-starter` |
| El cable y la tabla | este ADR; cuando se acepte ADR-030, como `spec/events/` |
| Kafka local | el compose de `nova-plaza-01-shared-platform`: `apache/kafka` 4.3.1 en KRaft de un nodo, con el heap y la memoria del contenedor acotados |

**Llegan con su consumidor**, por la regla de no agregar superficie sin uno:

- **El relevo con Debezium:** cuando un consumidor pida más latencia o volumen del que da el sondeo.
  La tabla ya está pensada para eso.
- **Un adaptador de Namastack:** cuando un equipo lo pida y Nova esté en Boot 4.1.
- **SNS y SQS:** cuando una organización en AWS lo necesite.
- **La extensión de Quarkus que produce:** con el primer productor en Quarkus. El catálogo solo
  consume, y le alcanza el `Inbox` sobre JDBC, que se suma a la transacción de Quarkus; una prueba lo
  tiene que confirmar.
- **NestJS:** con el primer servicio Nest dueño de datos, adoptando `@nestjs/outbox` detrás de este
  contrato cuando salga de 0.0.x.

### El orden de trabajo

1. **Pedidos implementa `confirm` y `cancel`**, con `Idempotency-Key` (ADR-047) y un 409 por
   `@Version` cuando dos confirmaciones chocan.
2. **Kafka entra en el compose** de Plaza, con el tópico `plaza.orders`.
3. **`nova-java-26-outbox`:** el núcleo, el almacén JDBC, el publicador de Kafka y el starter de
   Spring, con sus suites.
4. **Pedidos publica `OrderConfirmed`** en el mismo commit que el cambio de estado y el registro de la
   clave de idempotencia: tres escrituras, un commit. Hasta que exista el catálogo, un consumidor de
   prueba valida las cabeceras, la clave y la traza.
5. **El catálogo consume**, con el `Inbox`, y actualiza el ranking en la misma transacción.

`OrderConfirmed` lleva el id del pedido, la moneda, el total, los ítems (sku, cantidad y precio
unitario) y el momento de la confirmación. **No lleva `customerId`:** el ranking no lo necesita.

### Cómo se prueba

Con Testcontainers para PostgreSQL y Kafka: un rollback no publica; un commit sí; cuatro relevos
reclamando a la vez no duplican; un relevo vencido no pisa al que tomó su lugar; el orden por
agregado se mantiene con transacciones solapadas; el broker caído retrasa sin perder; el mismo evento
dos veces lo descarta el inbox. Son los mismos casos que exporta `@nestjs/outbox` para sus
almacenes, así que sirven de base a la suite común con ADR-031 y ADR-047.

## Alternativas descartadas

- **Publicar al broker después del commit**, directo o con `@TransactionalEventListener`: una caída
  entre los dos pierde el evento. Ya lo descartó ADR-043.
- **Las transacciones de Kafka:** no incluyen la base de datos.
- **Spring Modulith como implementación por defecto:** sin reintento continuo ni orden, solo para
  Spring, y su propia documentación remite a un outbox completo.
- **Namastack como implementación por defecto:** solo para Spring, en Kotlin, con esquema propio y el
  payload tipado por clase, y compilada contra Boot 4.1. Queda como adaptador.
- **gruelbox `transaction-outbox`:** es una cola de invocaciones de método, no de eventos.
- **Debezium como único mecanismo:** exige infraestructura que Plaza no tiene y no sirve para probar
  en local sin Kafka Connect.
- **`LISTEN/NOTIFY` como canal, el sondeo por cursor y el outbox sin tabla** con
  `pg_logical_emit_message`: por las trampas del contexto, y porque lo último no deja nada que
  auditar ni un relevo de respaldo.
- **Adoptar `@nestjs/outbox` ahora:** no hay consumidor en NestJS.

## Preguntas abiertas

Cada una con la respuesta recomendada.

1. **¿Quién publica por defecto, un relevo dentro del servicio o Debezium?** ADR-043 dice «un proceso
   aparte». *Recomendación:* el relevo por sondeo dentro del servicio, con la tabla lista para que
   Debezium la lea después. Es lo que menos infraestructura pide y sirve igual en Spring y en Quarkus.
2. **¿Implementación propia o Namastack detrás del puerto?** *Recomendación:* propia, por el mismo
   comportamiento en Spring y Quarkus, el payload opaco y la tabla compatible con Debezium. El costo
   es mantener una pieza de concurrencia, la más delicada de Nova.
3. **¿Qué pasa al agotarse los reintentos: bloquear el agregado o saltar el evento?**
   *Recomendación:* bloquear el agregado y alertar, nunca adelantar en silencio, con
   `on-exhausted=skip` configurable. `@nestjs/outbox` salta; gruelbox y Namastack bloquean.
4. **¿Un solo líder o relevos particionados?** *Recomendación:* un solo líder en la primera versión.
   El puerto `OutboxStore` deja abierto el reclamo particionado sin cambiar el contrato.
5. **¿Qué eventos publica Plaza?** *Recomendación:* solo `OrderConfirmed`. La auditoría con MongoDB
   (pregunta 1 de ADR-043) queda como fase opcional; si se acepta, `OrderCreated` y `OrderCancelled`
   ganan un consumidor.
6. **¿Nova pasa a Spring Boot 4.1?** No es de este ADR, pero lo afecta: la 4.0 deja de tener soporte
   OSS el 2026-12-31, y Modulith 2.1 y Namastack 1.7 en adelante piden la 4.1. *Recomendación:*
   decidirlo aparte antes de esa fecha, y probar el starter contra las dos.

## Consecuencias

### Positivas

- Un evento sale si y solo si la transacción confirmó, y un reintento del cliente, sumado a ADR-047,
  no produce un segundo evento.
- El relevo se cambia sin tocar el servicio: Nova, Debezium o el que traiga una organización.
- Los tres stacks dicen lo mismo en el cable, y una compra se ve como una sola traza.

### Negativas

- Es un repositorio más, con la pieza de concurrencia más delicada de la plataforma.
- Hay una tabla de cola que operar, purgar y vigilar, y el inbox suma una tabla y una escritura por
  evento consumido.
- Kafka entra al compose de Plaza, con su consumo de memoria.
- Hay que probar en nativo el cliente de Kafka (ADR-045) y, mientras dure la transición, dos
  versiones de Spring Boot.

## Fuentes

Consultadas el 2026-09-30.

- [NestJS: Transactional outbox](https://docs.nestjs.com/reliability/outbox)
- [nestjs/outbox](https://github.com/nestjs/outbox)
- [Spring Modulith: Working with Application Events](https://docs.spring.io/spring-modulith/reference/events.html)
- [Spring Modulith 2.1 GA](https://spring.io/blog/2026/06/11/spring-modulith-2-1-ga-2-0-7-and-1-4-12-released/)
- [Namastack Outbox](https://www.namastack.io/docs/)
- [gruelbox transaction-outbox](https://github.com/gruelbox/transaction-outbox)
- [Debezium: Outbox Event Router](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html)
- [Debezium: extensión de Quarkus para el outbox](https://debezium.io/documentation/reference/stable/integrations/outbox.html)
- [Quarkus 3.33: Kafka](https://quarkus.io/version/3.33/guides/kafka)
- [Microservices.io: Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html)
- [Microservices.io: Polling Publisher](https://microservices.io/patterns/data/polling-publisher.html)
- [PostgreSQL: SELECT, la cláusula de bloqueo](https://www.postgresql.org/docs/current/sql-select.html)
- [PostgreSQL: bloqueos explícitos y asesores](https://www.postgresql.org/docs/current/explicit-locking.html)
- [PostgreSQL: NOTIFY](https://www.postgresql.org/docs/current/sql-notify.html)
- [Recall.ai: Postgres LISTEN/NOTIFY does not scale](https://www.recall.ai/blog/postgres-listen-notify-does-not-scale)
- [Event-Driven.io: el orden en un outbox de Postgres](https://event-driven.io/en/ordering_in_postgres_outbox/)
- [CloudEvents: especificación](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md)
- [CloudEvents: enlace con Kafka](https://github.com/cloudevents/spec/blob/main/cloudevents/bindings/kafka-protocol-binding.md)
- [CloudEvents: extensión de trazado distribuido](https://github.com/cloudevents/spec/blob/main/cloudevents/extensions/distributed-tracing.md)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [OpenTelemetry: convenciones de mensajería](https://opentelemetry.io/docs/specs/semconv/messaging/messaging-spans/)
- [Apache Kafka 4.3: configuración del productor](https://kafka.apache.org/43/configuration/producer-configs/)
