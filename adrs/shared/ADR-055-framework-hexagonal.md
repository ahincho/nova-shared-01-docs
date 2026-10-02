# ADR-055: El Framework Hexagonal: la Estructura, los Contratos y las Reglas de Puertos y Adaptadores

## Estado

Propuesta (2026-10-02). Es el criterio 08 de la rúbrica del curso de Framework Engineering, que pide al menos
un framework especializado que facilite un estilo arquitectónico, con su estructura, sus contratos, sus
convenciones y sus componentes reutilizables. Las preguntas abiertas llevan su respuesta recomendada.
**Scope:** `shared` (la estructura y las reglas son las mismas en los tres stacks; lo que cambia es la
herramienta que las comprueba).
**Aplica:** [ADR-053](ADR-053-cqrs-con-command-bus-y-query-bus.md) para los puertos de entrada,
[ADR-054](ADR-054-persistencia-reutilizable-con-paginacion-por-cursor.md) para el adaptador de persistencia,
[ADR-031](ADR-031-modulo-de-errores-por-capas-con-trazabilidad.md) para los errores y
[ADR-026](../nest/ADR-026-generador-de-servicio-y-reglas-de-arquitectura.md) para las reglas de NestJS.
**Primer consumidor:** pedidos de Plaza, que hoy es por capas.

## Fecha

2026-10-02

## Contexto

**Nova ya tiene arquitectura hexagonal, pero solo fuera de Java Spring:**

| Dónde | Qué hay | Cómo se comprueba |
|---|---|---|
| NestJS, schematic `service --style acl` | por contexto acotado: `adapter/in`, `adapter/out`, `domain/`, `exception/`, `port/in`, `port/out`, `service/` | `.dependency-cruiser.js`, con nueve reglas con nombre y motivo, dentro de `nova verify` |
| Quarkus, `nova-java-19-quarkus-template` | la misma forma por contexto, con un ejemplo de matrícula | un `ArchitectureTest` propio de la plantilla, con dos reglas |
| Spring Boot, `nova-architecture-rules` 1.2.0 | solo `LayeredArchitectureTest`, por capas | ArchUnit |

**`nova-architecture-rules` promete otra forma.** Su README y `NovaArchitectureStyle` anuncian un
`HexagonalArchitectureTest` «de fase 2» con `domain..`, `application..` y `adapters..`, que no coincide con
lo que generan NestJS y Quarkus, y que nadie usa.

**Pedidos muestra el límite del estilo por capas.** Su `entity/Order` es a la vez el modelo del negocio y la
tabla: lleva `@Entity`, hereda de `AuditableEntity` y su forma depende de JPA. Su `ListOrdersHandler`
conoce el `Window` de Spring Data. El negocio no se puede probar sin la base, y cambiar de base toca el
negocio.

**Lo que dice el estilo** (Alistair Cockburn, 2005): el núcleo de la aplicación expone **puertos**, y cada
tecnología se conecta por un **adaptador**. Los de entrada (*driving*) llaman al núcleo, como un controlador;
los de salida (*driven*) los llama el núcleo, como un repositorio. Las dependencias apuntan siempre hacia
adentro.

**Lo que ya resolvió el ecosistema, consultado el 2026-10-02:**

- **ArchUnit** trae `onionArchitecture()`, con dominio, aplicación y adaptadores, y `slices()` para que dos
  partes no se conozcan. No sabe de contextos acotados ni de puertos de entrada y salida separados.
- **jMolecules** trae anotaciones (`@PrimaryPort`, `@SecondaryAdapter`, `@AggregateRoot`) y reglas de
  ArchUnit sobre ellas. Marca el estilo clase por clase, con una dependencia en el código de producción, y
  no existe en NestJS.
- **Spring Modulith** verifica módulos por paquete, pero no las capas de adentro de un módulo.

Ninguno da lo que Nova necesita: la **misma** estructura y las **mismas** reglas en los tres stacks.

## Decisión

**Nova adopta un solo estilo hexagonal, el que ya generan NestJS y Quarkus, y lo lleva a Java Spring como
framework: una estructura por contexto acotado, cuatro contratos, un conjunto de reglas con el mismo nombre
en los tres stacks, y pedidos de Plaza como primer servicio que lo usa.**

### La estructura

Un servicio se divide en **contextos acotados**, cada uno un paquete bajo la raíz, con siete partes:

```
pe.edu.nova.plaza.orders/
├── OrdersApplication.java
├── config/                     lo transversal del servicio: reloj, actor, beans
└── order/                      un contexto acotado
    ├── domain/                 el modelo del negocio: agregados y value objects, sin framework
    ├── exception/              los errores del dominio (ADR-031), sin framework
    ├── port/
    │   ├── in/                 los casos de uso: los comandos y consultas de CQRS, y sus vistas
    │   └── out/                lo que el núcleo necesita de afuera: interfaces, sin framework
    ├── service/                los handlers que implementan los casos de uso
    └── adapter/
        ├── in/web/             el controlador, con request/ y response/
        └── out/persistence/    las entidades JPA y la implementación del puerto de salida
```

**`config` y `shared` quedan fuera de los contextos:** son del servicio entero. Un adaptador de otra
tecnología es otra carpeta bajo `adapter/in` o `adapter/out`: `adapter/in/listener`, `adapter/out/restclient`.

### Los contratos

| Contrato | Qué es en Nova | Dónde vive |
|---|---|---|
| **Puerto de entrada** | un `Command<R>` o una `Query<R>` de ADR-053, con su vista de salida si la tiene. El adaptador de entrada lo ejecuta por el `CommandBus` o el `QueryBus`, así que la validación, la autorización, la auditoría y la transacción llegan solas | `port/in` |
| **Caso de uso** | el `CommandHandler` o `QueryHandler` del mensaje | `service` |
| **Puerto de salida** | una interfaz con el nombre de lo que hace, como `OrderStore`, en el lenguaje del dominio: recibe y devuelve el modelo, nunca una entidad JPA ni un tipo de Spring Data | `port/out` |
| **Adaptador** | la implementación de un puerto de salida contra una tecnología, o un controlador que ejecuta puertos de entrada | `adapter/out/<tecnología>`, `adapter/in/<tecnología>` |

- **No hay un `UseCase` propio:** el mensaje tipado de CQRS ya es el puerto de entrada, y el bus ya es la
  forma de llamarlo. Una interfaz más por caso de uso duplicaría el handler.
- **No hay un `Repository<T, ID>` genérico:** un puerto de salida dice lo que el negocio necesita, como
  `page(customerId, request)`, y no lo que ofrece una base.
- **Lo de la base es del adaptador.** `AuditableEntity` de ADR-054 va en la entidad JPA del adaptador, y
  el `CursorPage` llega al núcleo ya armado: el puerto devuelve un `CursorPage` del modelo, y el adaptador lo
  arma con `CursorPages` sobre el keyset.

### Las reglas

Las mismas nueve de NestJS, con **el mismo nombre**, para que una violación se lea igual en cualquier stack.
En Java las comprueba un `HexagonalArchitectureTest` nuevo en `nova-architecture-rules`:

| Regla | Qué prohíbe |
|---|---|
| `domain-depends-on-nothing` | que `domain` conozca `port`, `service`, `adapter` o `exception` de su contexto, o un framework |
| `exceptions-depend-on-nothing` | que `exception` conozca `port`, `service`, `adapter` o `domain`, o un framework |
| `service-must-not-import-adapter` | que un caso de uso conozca un adaptador |
| `port-must-not-import-adapter` | que un puerto conozca un adaptador o un caso de uso |
| `edges-must-not-know-each-other` | que dos adaptadores se conozcan: entrada y salida se hablan solo por el núcleo |
| `upstream-dtos-stay-in-their-adapter` | que el modelo de un sistema externo salga de `adapter/out/restclient` |
| `web-contracts-stay-at-the-web-edge` | que `request/` y `response/` se usen fuera de `adapter/in/web` |
| `context-must-not-import-another-context` | que un contexto acotado conozca otro |
| `no-circular-dependencies` | los ciclos entre contextos |

- **Ningún framework en el núcleo:** `domain`, `exception` y `port` no conocen Spring, Quarkus, JPA ni
  Jackson; sí las librerías puras de Nova (`pe.edu.nova.java.libs..`), como los errores de ADR-031, los
  mensajes de ADR-053 y la página de ADR-054, y Bean Validation en `port/in`, porque el bus valida el mensaje.
  `service` solo agrega la anotación de estereotipo que registra el bean.
- **Una regla no enumera contextos:** se aplica a cualquier paquete bajo la raíz que no sea `config` ni
  `shared`, así que un contexto nuevo queda cubierto sin tocar la prueba. Es el mismo comodín de NestJS.
- **Una parte vacía hace fallar su regla**, como en `LayeredArchitectureTest`: atrapa una raíz mal escrita
  o una carpeta mal nombrada.

### Dónde vive

| Pieza | Repositorio | Versión |
|---|---|---|
| `HexagonalArchitectureTest` y la corrección de `NovaArchitectureStyle` | `nova-java-07-architecture-rules` | 1.3.0, menor: suma una clase |
| la estructura y las reglas en NestJS | `nova-nestjs-01-platform`, schematic `acl` | ya existen |
| la plantilla de Quarkus pasa a las nueve reglas | `nova-java-19-quarkus-template` | cuando se renombre a `nova-template-02` (ADR-051) |

`LayeredArchitectureTest` se queda: es el estilo de `nova-template-01` y de un servicio chico sin
integraciones.

### Pedidos migra

Pedidos pasa de capas a un contexto `order`, **sin cambiar su API ni su esquema**:

| Hoy | Después |
|---|---|
| `controller/OrderController` | `order/adapter/in/web/OrderController` |
| `dto/CreateOrderRequest`, `dto/OrderResponse` | `order/adapter/in/web/request/` y `response/` |
| `service/PlaceOrder`, `FindOrder`, `ListOrders` | `order/port/in/`, con la vista `OrderView` |
| `service/*Handler` | `order/service/` |
| `entity/Order` y `OrderItem`, con JPA | `order/domain/Order`, sin JPA, y `order/adapter/out/persistence/OrderEntity`, que hereda de `AuditableEntity` |
| `repository/OrderRepository` | `order/port/out/OrderStore` y su adaptador `JpaOrderStore` |
| el `ORDER_NOT_FOUND` de `FindOrderHandler` | `order/exception/OrderErrors` |

Sus pruebas de la API no cambian, y su `ArchitectureTest` pasa a extender `HexagonalArchitectureTest`.

## Alternativas descartadas

- **El layout que anunciaba `nova-architecture-rules`** (`domain`, `application`, `adapters`). Es otra forma
  que la de NestJS y Quarkus, y una regla con otro nombre en cada stack obliga a traducir.
- **jMolecules.** Sus anotaciones marcan cada clase y entran al código de producción, y no tiene par en
  NestJS. Las reglas por paquete no piden nada al código.
- **`onionArchitecture()` de ArchUnit sola.** No separa puertos de entrada y salida, no conoce los contextos y
  sus mensajes no son los de NestJS.
- **Clean Architecture como segundo estilo ahora.** No tiene consumidor: queda nombrado
  en `NovaArchitectureStyle` y entra con un servicio que lo pida.
- **Una interfaz `UseCase` por caso de uso.** El mensaje de CQRS ya lo es, con el bus y sus comportamientos.

## Preguntas abiertas

Cada una lleva la respuesta recomendada.

1. **El estilo.** Recomendado: **hexagonal**, porque ya es el de NestJS y Quarkus. Layered sigue para los
   servicios chicos.
2. **El primer consumidor.** Recomendado: **migrar pedidos**, que ya usa CQRS y la persistencia y es el
   servicio de la demo. La otra opción es una plantilla hexagonal nueva, sin servicio que la use.
3. **Spring en la capa de aplicación.** Recomendado: **`service` lleva solo la anotación de estereotipo**,
   como el `@Injectable` de NestJS y el `@ApplicationScoped` de Quarkus. La otra opción es registrar los
   handlers por convención, sin anotación, con un starter más.
4. **Los bloques de DDD** (`AggregateRoot`, `ValueObject`, `DomainEvent`). Recomendado: **todavía no**. Un
   record ya es un value object, y un `AggregateRoot` con eventos llega con el outbox de ADR-048, que es
   quien los publica. Hoy no tendrían consumidor.
5. **El nombre del contexto de pedidos.** Recomendado: **`order`**, en singular, como el agregado.
6. **Una plantilla hexagonal de Spring Boot.** Recomendado: **no por ahora**; ADR-051 dice que una plantilla
   entra cuando un servicio real la necesita, y pedidos ya es el ejemplo.

## Consecuencias

### Positivas

- **Un solo estilo hexagonal en Nova**, con las mismas carpetas y las mismas reglas en los tres stacks.
- **El negocio de pedidos se prueba sin la base**, y cambiar la persistencia toca solo su adaptador.
- **La rúbrica queda cubierta con un servicio real**, que además muestra CQRS y la persistencia en su lugar
  del hexágono.

### Negativas

- **Más clases en pedidos:** el modelo y la entidad JPA se separan, con su conversión, y la vista se separa
  de la respuesta HTTP. Es el costo del estilo, y se paga para que el núcleo no dependa de la base.
- **La plantilla de Quarkus sigue con sus dos reglas** hasta que se renombre.
- **Las reglas son por paquete:** una clase mal ubicada pasa si su paquete es el correcto. Lo mismo vale en
  NestJS.

## Fuentes

- Alistair Cockburn, *Hexagonal Architecture* (2005), alistair.cockburn.us.
- ArchUnit, *Architectures* y *Slices*, archunit.org/userguide, consultado el 2026-10-02.
- jMolecules, *Architecture*, github.com/xmolecules/jmolecules, consultado el 2026-10-02.
- `nova-nestjs-01-platform/packages/schematics`, `.dependency-cruiser.js` del estilo `acl`.
