# ADR-031: Modulo Base de Errores por Capas, con Trazabilidad

## Estado

Propuesta
**Scope:** `shared` (Java + NestJS)
**Depende de:** ADR-030, pregunta abierta 2 (RFC 7807 o el sobre). Este ADR esta disenado para
no quedar bloqueado por esa decision; como, esta en la seccion «El modelo y su serializacion van
separados».

## Fecha

2026-09-20

## Contexto

Hoy un error en Nova se clasifica por **codigo HTTP**, y eso obliga a que quien lo lanza ya sepa
de HTTP.

En NestJS, un caso de uso que descubre que un curso no existe escribe
`throw new NotFoundException('Curso no encontrado')`. Funciona, y tiene dos costos. El primero es
que la regla de negocio importa `@nestjs/common`: la capa de dominio queda atada al transporte, y
ese mismo caso de uso ya no se puede llamar desde un consumidor de cola o un job sin arrastrar una
semantica HTTP que ahi no significa nada. El segundo es que se pierde informacion: un 404 puede
ser «el alumno pidio un curso que no existe» o «el upstream que consultamos contesto 404», y las
dos cosas se ven igual en el log y en el tablero, cuando una es normal y la otra es un incidente.

`AllExceptionsFilter` hace bien lo que puede con lo que recibe: colapsa todo 5xx a un mensaje
generico para no filtrar el detalle, respeta `errorCode` por debajo de 500 y trata
`ValidationException` aparte. Pero solo puede clasificar por `getStatus()`, porque es lo unico que
la excepcion le dice.

En Java no hay ni siquiera eso. `GlobalExceptionHandler` mapea tres tipos -`NoResourceFoundException`,
`IllegalArgumentException` y `Exception`- y la extension de Quarkus mapea otros tres, distintos.
Ninguna de las dos tiene noción de capa.

### La trazabilidad esta a medias

El `traceId` existe: `RequestContextService` lo genera o lo toma de `x-request-id`, viaja a los
upstreams solo y vuelve en una cabecera de respuesta. Lo que falta es lo que lo hace util cuando
algo se rompe:

- **No esta en el cuerpo de la respuesta.** Un alumno que ve «Error interno del servidor» en
  pantalla no tiene nada que citar, y quien lo atiende no tiene por donde entrar a OpenSearch.
  La cabecera existe, pero nadie mira cabeceras en una captura de pantalla.
- **No esta garantizado en la linea de log del error.** Si la excepcion se registra fuera del
  contexto de la peticion -un `catch` en un `finally`, un handler de rechazo- el contexto ya no
  esta y el log sale sin correlacion.
- **La capa no es un campo.** Distinguir «fallo un upstream» de «tenemos un defecto» exige leer
  el stack trace, y eso no se puede agregar ni alertar.

## Decision

**Agregar un modulo de errores a `packages/core` -y su equivalente en los dos stacks Java- que
clasifique por capa en vez de por codigo HTTP, y que capture la trazabilidad en el momento en que
el error nace.**

### Las capas

Un error declara de que capa viene. El mapeo a HTTP lo hace la plataforma, no quien lanza.

| Capa | Que significa | Sale como | Detalle al cliente |
|---|---|---|---|
| `domain` | una regla de negocio dijo que no | 404, 409, 422 segun el tipo | si: es informacion que el usuario necesita |
| `application` | la entrada o una precondicion del caso de uso fallo | 400, 422 | si, por campo cuando aplica |
| `infrastructure` | una dependencia fallo: base de datos, upstream, cola | 502, 503, 504 | no: solo el codigo generico y el traceId |
| `platform` | el framework mismo: configuracion ausente, secreto ilegible | 500 | no |

**La regla que ordena todo: `domain` y `application` son esperados, `infrastructure` y `platform`
son incidentes.** De ahi sale el resto sin tener que decidirlo caso por caso: los dos primeros se
registran en `warn` y no despiertan a nadie; los dos ultimos van en `error`, con la causa
completa, y son los que alimentan la tasa de error de los Four Golden Signals del ADR-014.

Una excepcion de dominio **no importa nada del framework web**. Ese es el punto del cambio, y es
lo que permite que el mismo caso de uso corra detras de HTTP o de un consumidor de cola.

### La trazabilidad se captura al nacer, no al serializar

Un error de Nova lleva su `traceId` desde el constructor, tomado del contexto de peticion vigente
en ese instante. No se busca al momento de responder, que es cuando el contexto puede haberse
perdido.

Con eso, tres cosas pasan a estar garantizadas:

**El `traceId` va en el cuerpo de la respuesta de error**, no solo en la cabecera. Es lo que hace
que un reporte de un alumno sea accionable: el identificador esta en la pantalla que fotografia.

**La linea de log lleva `traceId` y `layer` como campos**, no dentro del mensaje. Un tablero puede
contar errores de `infrastructure` por hora sin parsear texto, y una consulta por `traceId` en
OpenSearch devuelve la cadena completa a traves de los saltos.

**Un 5xx sigue sin filtrar el detalle.** La causa completa va al log; al cliente le llega el
codigo generico y el `traceId`. Eso no cambia respecto de hoy, y es deliberado.

### El modelo y su serializacion van separados

Es la parte de la decision que evita el bloqueo con ADR-030.

El modulo define **el modelo de error** -capa, tipo, codigo, mensaje, campo, causa, traceId- y por
separado **como se escribe en el cuerpo**. La serializacion es un punto de extension con una
implementacion por defecto.

Asi, si la pregunta abierta 2 de ADR-030 se resuelve en RFC 7807, lo que cambia es el serializador:
`type`, `title`, `status`, `detail`, `instance` mas una extension con el `traceId`, y
`application/problem+json`. El modelo de capas, los mapeos y la captura de trazabilidad quedan
intactos. Si se resuelve en el sobre actual, tampoco cambia nada del modelo.

**Se puede construir el modulo antes de que esa pregunta se responda.** Lo unico que no se puede
es fijar el formato del cuerpo, y eso es justamente lo que queda detras del punto de extension.

### Se puede sobreescribir entero

Por el invariante 2: el mapa de capa a codigo HTTP es un valor por defecto, no una constante. Un
servicio que necesite que su `domain` conflictivo salga 400 en vez de 409 lo cambia en
`forRoot()` en Nest y con un bean propio en Spring, sin forkear.

## Alternativas descartadas

**Seguir clasificando por codigo HTTP y solo agregar el `traceId` al cuerpo.** Es mucho mas barato
y resuelve la mitad visible del problema. Se descarta porque deja el acoplamiento del dominio al
transporte, que es la causa de que hoy no se distinga un 404 de negocio de un 404 de upstream. La
mitad que no resuelve es la que produce falsas alertas.

**Un solo tipo de error con un campo `layer` de texto libre.** Mas simple de escribir y
practicamente imposible de mantener: sin tipos, cada servicio inventa su nombre de capa y el
tablero vuelve a agrupar por cadenas que no coinciden. Es el mismo defecto que hoy tiene el
catalogo de codigos entre stacks, medido en ADR-030.

**Adoptar las jerarquias de excepciones que cada framework ya trae** -`ResponseStatusException`,
`WebApplicationException`- y mapear sobre ellas. Se descarta por el invariante 5: son tres
jerarquias distintas, asi que el resultado por HTTP volveria a depender del stack, que es
exactamente el riesgo que el contrato existe para cerrar.

**Reintentar o degradar automaticamente ante un error de `infrastructure`.** Fuera de alcance y ya
decidido en ADR-029: el cliente HTTP no reintenta. Este modulo clasifica y reporta; no cambia el
comportamiento ante el fallo.

## Preguntas abiertas

**1. Cuantos tipos por capa.** La tabla nombra las capas pero no cierra el catalogo de tipos
dentro de cada una -`NotFound`, `Conflict`, `RuleViolated` dentro de `domain`, por ejemplo-. Un
catalogo corto se queda corto y uno largo nadie lo usa entero. Conviene fijarlo con los casos
reales del servicio de ejemplo y no en abstracto, por el invariante de no agregar superficie sin
consumidor.

**2. Si `platform` es una capa o es otra cosa.** Un error de configuracion casi siempre ocurre en
el arranque, no atendiendo una peticion, y ahi no hay `traceId` ni respuesta que dar: lo correcto
es no arrancar. Puede que `platform` no pertenezca a esta taxonomia y sea un mecanismo aparte.

**3. Que pasa con el codigo de dominio en un 5xx.** Hoy `errorCode` se lee solo por debajo de 500,
a proposito. Un `infrastructure` es 5xx por definicion, asi que con la regla actual todos se ven
iguales para el cliente. Hay un argumento para distinguir «upstream caido» de «upstream lento» sin
revelar cual upstream, y otro para no dar ninguna pista de la topologia. No esta resuelto.

## Consecuencias

### Positivas

- El dominio deja de importar el framework web, y el mismo caso de uso sirve para HTTP y para un
  consumidor.
- Un error reportado por un alumno se puede rastrear con lo que se ve en pantalla.
- Se puede alertar sobre `infrastructure` sin que los 404 de negocio ensucien la senal.
- Cierra el hueco de Java, que hoy no tiene taxonomia en ninguno de sus dos stacks.
- La decision de RFC 7807 deja de bloquear: entra por el punto de extension cuando se tome.

### Negativas

- **Es superficie de API nueva en los tres stacks**, y superficie que los servicios van a tocar
  todos los dias. Equivocarse en los nombres es caro de revertir.
- **Migrar un servicio existente no es automatico del todo.** Cambiar `NotFoundException` por el
  equivalente de dominio es mecanico y lo cubre un codemod; decidir de que capa es cada error
  existente no lo es, y eso lo tiene que mirar una persona.
- **El mapa de capa a codigo HTTP es una decision que alguien va a querer discutir.** Que un
  conflicto de dominio salga 409 y no 400 es defendible pero no obvio, y ser configurable no
  quita que el valor por defecto sea el que casi todos van a usar.
- Convivir con el filtro actual durante la migracion significa dos caminos de error vivos al mismo
  tiempo, y el periodo en que ambos existen es cuando mas facil es equivocarse.

## Referencias

- [ADR-030: Contrato de Plataforma Versionado](ADR-030-contrato-de-plataforma-versionado.md)
- [ADR-014: Observabilidad - Four Golden Signals](ADR-014-observabilidad-four-golden-signals.md)
- [ADR-029: Sin Reintentos ni Corte de Circuito en el Cliente HTTP](../nest/ADR-029-sin-reintentos-en-el-cliente-http.md)
- `nova-nestjs`: `packages/core/src/api/filters/all-exceptions.filter.ts`,
  `packages/core/src/observability/request-context.service.ts`,
  `packages/core/src/http/upstream-http.error.ts`
- `nova-java-commons-spring-boot-starter`: `nova-api-standard-starter/.../web/GlobalExceptionHandler.java`
- `nova-java-api-standard-quarkus-extension`: `mapper/ApiExceptionMapper.java`
