# ADR-032: Observabilidad como Puerto Conectable, no como Dependencia del Nucleo

## Estado

Propuesta
**Scope:** `shared` (Java + NestJS)
**Enmienda a:** ADR-014, que fija el stack de observabilidad como un conjunto cerrado de
herramientas. Este ADR no descarta ese stack; lo convierte en la implementacion por defecto de un
puerto, y el stack sigue siendo el que ADR-014 eligio.

## Fecha

2026-09-20

## Contexto

### Los dos stacks no observan lo mismo, ni de lejos

| | Java (Spring Boot) | NestJS |
|---|---|---|
| Metricas | Micrometer, con `GoldenSignalsFilter` y `GoldenSignalsMetrics` | ninguna |
| Trazas distribuidas | OpenTelemetry via `micrometer-tracing-bridge-otel`, exportador OTLP | **ninguna** |
| Correlacion de logs | MDC con `traceId` y `spanId` | pino, con un id propio |
| Salud del collector | `CollectorHealthIndicator` | no aplica |

El nucleo NestJS **no tiene una sola referencia a OpenTelemetry**. Sus dependencias de
observabilidad son `pino`, `pino-http` y `nestjs-pino`, y nada mas.

### La consecuencia es que una traza no cruza entre stacks

NestJS propaga tres cabeceras propias -`x-request-id`, `x-user-id`, `x-tenant-id`- y genera el
identificador cuando el llamador no lo manda. Java propaga **W3C `traceparent`**, que es lo que
Micrometer Tracing pone y lee.

La busqueda de `traceparent` en todo el monorepo NestJS devuelve cero resultados.

Entonces una peticion que va del navegador a un BFF NestJS y de ahi a un microservicio Quarkus
produce **dos correlaciones que no se juntan**: el BFF registra su `x-request-id` y el
microservicio abre una traza OTel nueva, sin padre. Se puede encontrar cada mitad por separado en
OpenSearch; no se puede seguir la peticion de punta a punta, que es exactamente para lo que existe
una traza distribuida.

Esto no es un defecto de configuracion. Son dos mecanismos distintos que nadie unio.

### Y la observabilidad no se puede quitar

En Java, `nova.observability.enabled=false` apaga el comportamiento, pero el arbol de dependencias
sigue trayendo el BOM de OpenTelemetry, el bridge de Micrometer y el exportador OTLP. Un servicio
que no quiere nada de esto igual los compila, los empaqueta y los carga.

ADR-014 lo anota en sus consecuencias negativas -«dependencia en OpenTelemetry BOM agrega
complejidad al arbol de dependencias»- y lo acepta. Lo que no previo es que hoy esa dependencia es
obligatoria y no hay forma de no tenerla.

## Decision

**La observabilidad pasa a ser un puerto que la plataforma define y una implementacion separada
que el servicio conecta, o no.**

Tres piezas:

**El nucleo define la interfaz y no depende de ningun proveedor.** Lo que `core` conoce es el
puerto: abrir y cerrar un tramo, registrar una medicion, exponer el identificador de correlacion
vigente. Ni OpenTelemetry, ni Micrometer, ni Prometheus entran en sus dependencias.

**La implementacion viaja en un paquete aparte** -`@ahincho/nova-nestjs-otel` del lado NestJS, un
starter propio del lado Java- que el servicio agrega cuando la quiere. Cambiar de solucion es
cambiar ese paquete, sin tocar el nucleo ni el codigo del servicio.

**Cuando no hay implementacion conectada, el puerto no desaparece: queda en una version que no
exporta nada pero sigue correlacionando.** Es la parte que evita el peor resultado posible de
hacerlo opcional, y esta explicada abajo.

### El formato de propagacion no es una eleccion del plugin

Es la restriccion que hace que esto no rompa el invariante 5.

**La cabecera de propagacion es parte del contrato de plataforma -ADR-030-, no de la
implementacion.** Un adaptador puede cambiar a donde se exportan las trazas; no puede cambiar como
viaja el contexto entre servicios, porque de eso depende que los dos stacks se enlacen.

El contrato debe fijar **W3C `traceparent`**, que es lo que Java ya emite y lo que cualquier
proveedor entiende. Las tres cabeceras `x-*` de NestJS se conservan, porque llevan cosas que
`traceparent` no lleva -el usuario, el tenant- pero dejan de ser el mecanismo de correlacion.

Eso implica trabajo real en NestJS: leer `traceparent` entrante, continuar la traza y emitirlo
hacia los upstreams. Hoy no lo hace.

### El puerto vacio sigue correlacionando

Un servicio sin adaptador conectado no exporta trazas ni metricas, pero **sigue generando y
propagando el identificador de correlacion, y sigue poniendolo en cada linea de log**.

La razon es que sin esto, hacer la observabilidad opcional produce el peor caso: un servicio que
llega a produccion sin telemetria y sin que nada lo avise. Un `no-op` total es indistinguible de
un despliegue correcto hasta el dia del incidente. Con el puerto vacio, lo que se pierde al no
conectar un adaptador son las trazas y las metricas agregadas; lo que nunca se pierde es poder
seguir una peticion por los logs.

## Sobre el sidecar

La peticion original dice «tipo sidecar», y conviene separar dos cosas que suenan igual y no lo
son, porque **una de las dos ya esta decidida**.

**El sidecar de verdad ya existe en ADR-014:** el OpenTelemetry Collector. La aplicacion habla
OTLP contra un collector local y el collector enruta a donde sea -Grafana, Datadog, Jaeger,
OpenSearch-. Eso es lo que hace que cambiar de backend no exija recompilar ni redesplegar el
servicio, y es la razon por la que ADR-014 eligio el Collector «no Jaeger directo».

**Entonces el puerto en codigo no se justifica por poder cambiar de solucion**, porque esa parte
ya la resuelve el Collector, y la resuelve mejor: a nivel de infraestructura y sin tocar el
artefacto.

Se justifica por otras dos cosas, y conviene ser claro en que son estas y no aquella:

- **Que se pueda no tener.** Un servicio que corre en un test, en local, o en un entorno sin
  collector, no deberia cargar un SDK de telemetria para no usarlo.
- **Que el nucleo no dependa de un proveedor.** Hoy `core` tendria que importar OpenTelemetry para
  instrumentar, y con eso toda decision de version del SDK pasa a ser una publicacion de la
  plataforma.

Hay ademas un caso que el Collector no cubre y el puerto si: un backend que **no** habla OTLP. Si
alguna vez hay que integrar algo asi, el adaptador es el lugar.

## Alternativas descartadas

**Dejar OpenTelemetry directamente en el nucleo y exponer solo una bandera de apagado.** Es lo que
hay hoy en Java. Se descarta porque apagar el comportamiento no quita la dependencia: el costo de
arbol, de arranque y de superficie de seguridad se paga igual. Y ata la version del SDK al ciclo
de publicacion de la plataforma.

**Un puerto sin implementacion por defecto, que falle si no hay adaptador.** Fuerza a decidir, que
es tentador, y rompe el caso de correr un servicio en un test o en local sin infraestructura. El
puerto vacio da lo mismo sin el costo.

**Apoyarse solo en el Collector y no definir puerto alguno.** Es la alternativa mas fuerte y hay
que decirlo: cubre el cambio de backend, que era el motivo declarado. No cubre la opcionalidad ni
la independencia del nucleo respecto del SDK, que son las dos razones que quedan en pie.

**Instrumentacion automatica por agente** -el java agent de OTel, `--require` en Node-. No requiere
ningun codigo y es como se instrumenta una aplicacion que no se puede modificar. Se descarta como
mecanismo principal porque no puede conocer las Four Golden Signals tal como ADR-014 las define, ni
distinguir la capa de un error como propone ADR-031: son semanticas nuestras, y un agente generico
no las ve. Sigue siendo valido como complemento.

## Preguntas abiertas

**1. Si las metricas y las trazas son un puerto o dos.** Se agrupan por costumbre, pero un
servicio puede querer metricas sin trazas, y el costo de cada una es distinto. Dos puertos son mas
honestos y mas piezas que mantener.

**2. Que pasa con las Four Golden Signals si no hay adaptador.** Son el contrato de observabilidad
de ADR-014, y sin exportador no hay donde publicarlas. O dejan de estar garantizadas -y entonces
ADR-014 necesita una enmienda mas profunda que esta-, o el puerto vacio tiene que exponerlas por
algun otro medio.

**3. Si `x-request-id` sobrevive a `traceparent`.** Mantener los dos es tolerante con los
llamadores actuales y es tambien la clase de duplicacion que dentro de un ano nadie sabe explicar.
Retirarlo es un cambio incompatible para quien hoy lo manda.

**4. Que tan atras llega esto en A303.** Los servicios desplegados hoy correlacionan por
`x-request-id` y las consultas de OpenSearch estan escritas contra ese campo. Migrar la
propagacion implica una ventana en que conviven los dos, y eso hay que planificarlo antes de
tocar nada.

## Consecuencias

### Positivas

- Una traza puede cruzar de NestJS a Quarkus, que hoy no puede. Es el beneficio principal y no
  depende del resto.
- El nucleo deja de arrastrar un SDK de telemetria, y la version de ese SDK deja de ser una
  publicacion de la plataforma.
- Un servicio puede correr sin observabilidad sin que eso sea un apagado a medias.
- Integrar un backend que no habla OTLP pasa a ser posible sin tocar el nucleo.

### Negativas

- **Es un cambio incompatible en Java.** La observabilidad deja de llegar por el meta-starter y
  pasa a declararse; todo servicio existente tiene que agregar una dependencia o se queda sin
  telemetria. Necesita receta de migracion, y la receta tiene que ser ruidosa.
- **Instrumentar NestJS con OTel es trabajo nuevo, no una reorganizacion.** Hoy no hay nada: hay
  que leer y emitir `traceparent`, abrir tramos y exportarlos.
- **Un puerto es una abstraccion sobre algo que ya era una abstraccion.** OpenTelemetry existe
  precisamente para ser neutral entre proveedores, y ponerle una interfaz encima puede terminar
  reproduciendo su API con otros nombres. Si el adaptador de OTel resulta ser una traduccion uno a
  uno, la abstraccion no esta ganando nada y conviene revisarla.
- Dos paquetes mas que publicar y versionar por stack.

## Referencias

- [ADR-014: Observabilidad - Four Golden Signals](ADR-014-observabilidad-four-golden-signals.md)
- [ADR-030: Contrato de Plataforma Versionado](ADR-030-contrato-de-plataforma-versionado.md)
- [ADR-031: Modulo Base de Errores por Capas, con Trazabilidad](ADR-031-modulo-de-errores-por-capas-con-trazabilidad.md)
- W3C Trace Context, `traceparent` y `tracestate`
- `nova-java-observability-spring-boot-starter`: `OtlpExporterAutoConfiguration`,
  `TracingAutoConfiguration`, `GoldenSignalsFilter`, `CollectorHealthIndicator`
- `nova-nestjs`: `packages/core/src/observability/request-context.ts` (`DEFAULT_CORRELATION_HEADERS`),
  `packages/core/package.json` (sin dependencias de OpenTelemetry)
