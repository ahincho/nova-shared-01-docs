# ADR-035: Fallos de Upstream Clasificados con el Registro de RFC 9209

## Estado

Aceptada (2026-09-22). La clasificación se implementa primero en NestJS; `Proxy-Status` y el
equivalente en Java quedan para una entrega posterior, como dice la decisión.
**Enmendada (2026-09-23):** cada fallo deja una sola línea de log, la del filtro de errores, y lo
que se relanza de `forwardError` sale clasificado. La prueba en vivo del perfil de UTP mostró dos
líneas de error por cada fallo, y al revisar esa ruta apareció el 500 de un error de
`forwardError` relanzado.
**Scope:** `shared` (Java + NestJS)
**Completa:** ADR-031, capa `infrastructure`: responde su pregunta abierta 1 -qué tipos hay
dentro de la capa- para el caso de una llamada saliente. **Respeta:** ADR-029, sin reintentos; y
ADR-034, el estándar sigue sin ver la excepción.

## Fecha

2026-09-22

## Contexto

Un servicio de Nova llama a otros, y lo primero que alguien necesita saber cuando una llamada
falla es **de quién es el problema**. No es lo mismo un puerto cerrado, que se arregla con
configuración, que un upstream lento, que es del equipo que lo mantiene, ni que una respuesta que
llegó cortada, que suele ser la red. Cada uno tiene un responsable distinto, y confundirlos manda
el incidente a la bandeja equivocada.

### La información existe y el cliente la tira

Se provocó cada fallo contra servidores locales con el `fetch` de undici 8.10.2, que es el que usa
`HttpClientService`, y se anotó qué expone:

| Fallo provocado | Qué expone undici | Qué contesta Nova hoy |
|---|---|---|
| Nadie escucha en el puerto | `cause.code = ECONNREFUSED` | 502 |
| El nombre no resuelve | `cause.code = ENOTFOUND` | 502 |
| La conexión no se establece a tiempo | `UND_ERR_CONNECT_TIMEOUT` | 502 |
| Las cabeceras no llegan a tiempo | `UND_ERR_HEADERS_TIMEOUT` | 502 |
| Vence el plazo propio de la llamada | `TimeoutError`, sin envolver | 504 |
| Cortan la conexión antes de responder | `UND_ERR_SOCKET`, «other side closed» | 502 |
| Cortan la respuesta a mitad del cuerpo | `TypeError: terminated` sobre `UND_ERR_SOCKET` | **500** |
| Lo que contesta no es HTTP | `HTTPParserError` | 502 |
| El certificado no es válido | `cause.code = DEPTH_ZERO_SELF_SIGNED_CERT` | 502 |
| Contesta 2xx con HTML donde se esperaba JSON | `SyntaxError` al parsear | **200, con el HTML como resultado** |

**Cada fallo deja un código distinto, y el cliente convierte ocho de ellos en el mismo 502** con
el mensaje «Upstream service error». La diferencia sólo sobrevive en el stack de la línea de log,
que nadie agrega ni alerta.

Las dos filas en negrita son defectos, no pérdidas de información:

- **El cuerpo se lee fuera de la traducción de errores.** Un upstream que corta la respuesta a
  mitad produce un `TypeError` sin traducir, el filtro lo trata como un fallo propio y contesta
  500. El tablero cuenta un defecto nuestro donde hubo un problema de red.
- **Un 2xx que no es JSON se devuelve como texto.** El método promete un `T` y entrega un string;
  el error aparece más adelante, en el código que usó el resultado, lejos de la causa.

### En una cadena de servicios el origen se pierde en cada salto

La organización que motivó este análisis encadena cinco capas antes de llegar a un sistema externo,
en dos stacks. Se relevaron todos sus servicios de backend, y el recorrido de un solo timeout lo resume: el
servicio de negocio que lo sufre contesta 504, el orquestador que lo llama lo convierte en 503, el
siguiente orquestador en otro 503, y el BFF se lo entrega al cliente como 502. **Cuatro saltos,
tres status distintos, y en ninguno queda dicho que fue un timeout ni dónde.**

El resto del relevamiento repite el patrón:

- **Cada capa colapsa a su manera.** Los servicios Node juntan DNS, conexión rechazada, reset, TLS y
  JSON inválido en un 502; los Java juntan todo en un 503 con un código genérico. El código del
  sistema -`ENOTFOUND`, `ECONNREFUSED`- no se registra en ninguno.
- **Hay timeouts que salen como 500**, o sea como defecto propio: en varios servicios Java la
  excepción del timeout se lanza fuera del `try` que la traducía. Es el mismo defecto que el cuerpo
  cortado de la tabla anterior, en otro stack.
- **Ninguna respuesta dice qué salto falló**, y seguir el identificador de correlación tampoco
  alcanza: en la mitad de los servicios no llega a la línea de log.
- **Las cuatro variantes del catálogo de códigos** que conviven en el stack Java no coinciden ni en
  qué status corresponde a «no disponible».

### Ya existe un estándar para esto

**RFC 9209** (*The Proxy-Status HTTP Response Header Field*, 2022) define un registro de tipos de
error para un intermediario que no pudo obtener una respuesta del siguiente salto, cada uno con el
status que recomienda, y una cabecera para que cada intermediario de una cadena agregue el suyo. Un
BFF y un ACL son intermediarios en exactamente ese sentido. Adoptarlo evita inventar una taxonomía
propia, que es lo que haría cada organización por su cuenta.

## Decisión

**Todo fallo de una llamada saliente se clasifica con un tipo del registro de RFC 9209, se agrupa
en una categoría que dice a quién le toca, y viaja como campo -no dentro del mensaje- en el log y
en la excepción.**

### Tipos, categorías y status

La categoría es de Nova y es lo que responde «de quién es el problema». El tipo es del RFC y es lo
que se agrega en un tablero.

| Categoría | Qué significa | Tipos de RFC 9209 | Status |
|---|---|---|---|
| `connectivity` | no se llegó a hablar con el upstream | `dns_error`, `dns_timeout`, `destination_ip_unroutable`, `connection_refused`, `connection_timeout`, `tls_certificate_error`, `tls_protocol_error` | 502; 504 los dos timeouts |
| `timeout` | se llegó, y no contestó a tiempo | `http_response_timeout`, `connection_read_timeout` | 504 |
| `network` | contestaba, y la conexión se cortó o la respuesta llegó rota | `connection_terminated`, `http_response_incomplete`, `http_protocol_error` | 502 |
| `response` | contestó, con un status de error | ninguno: es el `received-status` del RFC | 502; 504 si recibió 504 o 408 |
| `contract` | contestó 2xx con un cuerpo que no se puede usar | extensión de Nova: `http_response_content_invalid` | 502 |
| `internal` | el fallo es nuestro, antes de salir | `proxy_internal_error`, `proxy_configuration_error` | 500 |

**`connection_timeout` es conectividad y no lentitud, y es a propósito.** Que la conexión no se
establezca casi nunca es un upstream lento: en una red con grupos de seguridad es un paquete que
alguien descarta, y se arregla con configuración de red, no pidiéndole al otro equipo que sea más
rápido. Mezclarlo con `http_response_timeout` es el error de triage más caro de esta familia.

El status sigue la recomendación del RFC. Cambia respecto de hoy en los timeouts de conexión y de
DNS, que pasan de 502 a 504.

### El log lleva la clasificación como campos

**Cada fallo deja una sola línea de error, la del filtro de errores.** El cliente no registra:
lanza, y la excepción lleva los campos. `upstream` trae el nombre del upstream, el `type`, la
`category`, la fase -`connect`, `response` o `body`- y la duración; `outbound`, el método, la URL
sin query y el plazo. El filtro los agrega a su línea junto al `traceId`. Un tablero cuenta fallos
por categoría sin parsear texto, y una alerta sobre `connectivity` no se dispara por un 404 de
negocio.

`upstream` nombra al upstream sólo por su host porque es lo que se agrupa. La ruta puede llevar
identificadores de la persona sobre la que era la petición: va aparte, en `outbound`, para leer
una línea y no para contar.

La primera versión de este ADR registraba el fallo en el cliente y en el filtro. Eran dos líneas
de error con los mismos campos, así que todo conteo por categoría daba el doble; y con
`forwardError` había una tercera, falsa, cuando el llamador traducía el error a propósito.

Los nombres del objeto son de Nova y neutros a propósito. Cómo se llaman esos campos en el índice
de una organización es convención y se ajusta desde su perfil (ADR-036).

### Lo relanzado de `forwardError` es un fallo del upstream

`UpstreamHttpError` es una `UpstreamException`, con la misma clasificación que tendría sin la
opción. El llamador traduce el status que entiende y relanza el resto, y el resto sale como 502 o
504, clasificado. Cuando era un `Error` suelto, lo relanzado llegaba al filtro como un fallo propio
y salía 500: el mismo defecto que este ADR corrige en la lectura del cuerpo, del lado equivocado
del tablero.

### El cuerpo no cambia

El 5xx sigue saliendo con el mensaje genérico (ADR-034). **El estándar no recibe el tipo ni el
nombre del upstream**: los dos describen la topología, y el RFC mismo advierte que exponerlos le
dice a un atacante dónde está cada servicio por detrás. Si el estándar debe recibir la categoría
para nombrar el código es la pregunta abierta 1.

### Los dos defectos se corrigen

- La lectura del cuerpo entra en la clasificación: un corte a mitad es `http_response_incomplete`,
  un 502, y no un 500.
- Un 2xx que no se puede parsear es `http_response_content_invalid`, un 502 con su tipo en el log,
  y no un string disfrazado de `T`.

### La cadena de saltos: `Proxy-Status`

Cada servicio que falle por un upstream agrega su miembro a `Proxy-Status`, conservando los que
trajo la respuesta de abajo, como pide el RFC:

```
Proxy-Status: acl-inventory; error=connection_timeout; next-hop="erp", orders; received-status=504
```

Leída desde el primer servicio de la cadena, esa cabecera dice qué salto falló y por qué sin
entrar a los logs de nadie. **Se emite entre servicios internos y se quita en el borde**: el RFC
recomienda no mostrarle la topología a un cliente que no la necesita. Qué servicio es el borde lo
declara el servicio, no lo adivina la plataforma.

Esta parte sólo sirve si la implementan todos los stacks de la cadena, así que se entrega después de
la clasificación y junto con su equivalente en Java.

## Alternativas descartadas

**Una taxonomía propia** -conectividad, red, timeout, ejecución- sin estándar debajo. Es lo que
pidió el primer caso de uso y es lo que haría cada organización. Se descarta por eso: las
categorías de arriba son esa misma idea, pero agrupan tipos que ya tienen nombre y status fijados
por un RFC, y que un proxy de terceros entiende.

**Usar como tipo el nombre de la excepción o el código del sistema** (`ECONNREFUSED`,
`java.net.ConnectException`). Es lo que queda en el log hoy. Tiene alta cardinalidad y **cambia
según el stack**: el mismo puerto cerrado se ve distinto desde Node y desde Java, y el invariante 5
pide que los tres stacks digan lo mismo. El código crudo se conserva en el log como dato, no como
clasificación.

**Reintentar según el tipo**, por ejemplo ante `connection_refused`. Fuera de alcance: ADR-029
decide que el cliente no reintenta, y este ADR clasifica sin cambiar el comportamiento ante el
fallo.

**Un paquete aparte para los errores.** La prueba de ADR-033 lo rechaza: la clasificación no
agrega ninguna dependencia, así que se queda en el núcleo.

**Exponer el tipo en el cuerpo de la respuesta.** Es lo más cómodo para depurar desde el cliente y
es justamente lo que el RFC desaconseja hacia afuera. Hacia adentro ya lo resuelve `Proxy-Status`.

**Registrar el fallo en el cliente en `warn` y en el filtro en `error`.** Conserva un rastro de lo
que el llamador atrapa, pero sigue siendo el mismo fallo en dos líneas con los mismos campos: un
conteo por `upstream.category` que no filtre por `context` da el doble, y esa condición no la
recuerda nadie a las tres de la mañana.

## Preguntas abiertas

**1. Si el estándar recibe la categoría.** Con ella, una organización podría contestar
`UPSTREAM_TIMEOUT` en vez de un código genérico, sin revelar qué upstream ni qué tipo. Sin ella, el
cuerpo de un 5xx sigue siendo igual para todo fallo, que es la regla de hoy. La categoría revela
menos que el tipo pero no nada: dice que hay un upstream.

**2. El nombre de la extensión.** `http_response_content_invalid` no está en el registro del RFC.
Se puede registrar ante IANA o marcarla como propia; un nombre sin marcar puede chocar con uno que
el registro agregue después.

**3. De dónde sale el nombre del servicio** en `Proxy-Status`. El nombre del servicio en el
orquestador no siempre coincide con el del repositorio, y derivarlo es una fuente conocida de
errores. Probablemente tenga que ser una opción explícita.

**4. Qué es un 4xx del upstream.** Hoy se traduce a 502 salvo que el llamador pida `forwardError`.
Un 404 del upstream puede ser «no existe» -dominio- o «la ruta está mal» -configuración-, y sólo el
llamador sabe cuál. Este ADR no cambia esa regla, pero la categoría `response` los junta.

## Consecuencias

### Positivas

- «¿De quién es el problema?» se contesta leyendo un campo, y se puede contar y alertar.
- Los timeouts de conexión dejan de confundirse con lentitud del upstream.
- La taxonomía no es de Nova ni de una organización: es un RFC, y por eso Java puede decir lo mismo.
- Se corrigen dos defectos que hoy producen un 500 falso y un resultado con el tipo equivocado.

### Negativas

- **Cambia el status de algunos fallos**: los timeouts de conexión y de DNS pasan de 502 a 504. Un
  tablero o una alerta escrita sobre el 502 deja de contarlos.
- **Un 2xx con un cuerpo inválido pasa de devolverse a fallar.** Quien dependía de recibir el texto
  tiene que enterarse por el changelog.
- **El clasificador depende de los códigos de undici**, que pueden cambiar entre versiones
  mayores. Necesita una prueba por tipo contra servidores reales, no sólo pruebas unitarias.
- `Proxy-Status` es una cabecera que, mal configurada en el borde, expone la topología que el resto
  de la plataforma protege.
- **Un fallo que el llamador atrapa para degradar la respuesta no deja línea** si el llamador no la
  escribe. Es el costo de registrar una sola vez: el log es de quien decide qué hacer con el fallo,
  y la excepción le trae los campos en `logFields`.

## Referencias

- [ADR-029: Sin Reintentos ni Corte de Circuito en el Cliente HTTP](../nest/ADR-029-sin-reintentos-en-el-cliente-http.md)
- [ADR-031: Módulo Base de Errores por Capas, con Trazabilidad](ADR-031-modulo-de-errores-por-capas-con-trazabilidad.md)
- [ADR-033: Qué es Núcleo, qué es Común Opcional y qué es Plugin](ADR-033-nucleo-comun-y-plugins.md)
- [ADR-034: Lo Duro y lo Reemplazable](ADR-034-puertos-con-implementacion-por-defecto.md)
- [ADR-036: Perfiles de Organización](ADR-036-perfiles-de-organizacion.md)
- RFC 9209, *The Proxy-Status HTTP Response Header Field*, sección 2.3
- `nova-nestjs`: `packages/core/src/http/http-client.service.ts`
