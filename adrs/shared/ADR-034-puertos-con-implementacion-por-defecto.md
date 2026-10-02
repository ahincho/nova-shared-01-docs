# ADR-034: Lo Duro y lo Reemplazable: Reglas en el Núcleo, Convenciones Detrás de un Puerto

## Estado

Aceptada (2026-09-22). Implementada en NestJS para el estándar de API, entrada y salida; Spring y
Quarkus pendientes. Desde el 2026-10-01 la extensión de Quarkus 3.0.0 envuelve el éxito como
Spring, con `ApiResponseFilter`
([ADR-050](../java/ADR-050-errores-por-capas-en-quarkus.md)); el puerto `ApiStandard` sigue
pendiente en los dos stacks de Java.
**Scope:** `shared` (Java + NestJS)
**Enmienda:** ADR-033, nivel 1. **Generaliza:** el punto de extensión de serialización de ADR-031.
**Afecta:** ADR-030, que pasa a describir un contrato por estándar.

## Fecha

2026-09-22

## Contexto

Nova hace dos clases de cosas y el código no las distingue.

**Reglas.** Un 5xx no le dice al cliente qué falló por dentro. Una respuesta que no es HTTP no se
envuelve. Una cabecera `authorization` no llega a un log. Un secreto malformado corta el arranque
sin citarse. Son la razón para usar la plataforma: un servicio que las apaga deja de estar
protegido por ella, y ninguna organización tiene una buena razón para querer otra cosa.

**Convenciones.** La forma del cuerpo de respuesta, el catálogo de códigos de error, el nombre de
la cabecera de correlación, de dónde salen los secretos. Nova toma una decisión razonable en cada
una, pero una organización puede tener la suya con el mismo derecho. Y como la tesis de Nova es
servir a varias organizaciones con perfiles propios, poder traer la suya no es un caso borde: es
el producto.

El caso más visible es el estándar de API, y es el que este ADR mide.

### Hoy reemplazar solo existe como apagar

| Stack | Cómo se cambia el estándar hoy | Qué tiene que reescribir el servicio |
|---|---|---|
| NestJS | `apiStandard: { wrapResponses: false, catchExceptions: false }` | el interceptor y el filtro enteros, reglas incluidas |
| Spring Boot | `nova.api-standard.enabled=false`: los dos beans se registran con `@Bean` plano, sin `@ConditionalOnMissingBean` | lo mismo |
| Quarkus | un `@ServerExceptionMapper` más específico | solo el error: la extensión no registra envoltorio de éxito |

Apagar el estándar se lleva las reglas con él. Un servicio que quiere otra forma de cuerpo termina
reescribiendo el saneado del 5xx, el caso no HTTP, `@SkipResponseWrapper` y la detección del doble
sobre, y cualquiera de esas cuatro cosas se puede olvidar. Es la definición de defecto del
invariante 2: para cambiar algo, el servicio tiene que salirse de la plataforma. En Spring, además,
contradice el invariante tal como está escrito.

### Apagado, el estándar se sigue filtrando

Aun con las dos opciones en `false`, en NestJS la forma de Nova sigue saliendo por tres lugares que
ninguna opción cubre:

- `validationExceptionFactory` produce `ApiErrorItem` de Nova, así que el filtro propio del
  servicio recibe errores con la forma del estándar que acaba de apagar.
- `@ApiEnvelope` y `@ApiErrors` documentan el sobre y el catálogo de Nova. Con otro estándar activo
  **el documento OpenAPI describe un cuerpo que ya no sale por el cable**, y un cliente generado a
  partir de él falla en el primer parseo.
- El generador emite los dos decoradores en cada controlador y una prueba e2e que exige
  `ApiEnvelopeSchema` en el documento. Todo servicio nuevo nace atado al estándar por defecto.

### Lo que la primera organización usa, medido

En los diez servicios NestJS de la primera organización, sincronizados el 2026-09-22, **el sobre es
el de Nova campo por campo**: `success`, `status`, `data` y `errors` con `code`, `message` y
`field`. No es casualidad: el estándar de Nova salió de ahí.

Las diferencias no están en la forma sino en la política del 5xx, y no son uniformes ni dentro de
la organización. Revisarlas separa dos tipos de diferencia que parecen iguales y no lo son, y ese
es el criterio de este ADR.

**Cómo se nombra un 5xx es forma.** El status ya viaja en la línea de estado, así que contestar
`BAD_GATEWAY` en vez de `INTERNAL_SERVER_ERROR` no le cuenta al cliente nada que no sepa. Una
organización lo puede elegir.

**Qué se le dice en un 5xx es contenido.** El mensaje de una excepción interna puede llevar un host,
una consulta o el cuerpo de un upstream. Eso no lo elige nadie.

La conclusión práctica: **hoy esa organización no necesita un estándar distinto, necesita elegir
su catálogo de códigos.** El segundo estándar real, el que probaría que la costura sirve para algo,
es RFC 7807, que ADR-030 dejó abierto porque adoptarlo en todos lados rompía el sobre.

## Decisión

**Cada capacidad de Nova se parte en una regla, que el núcleo aplica siempre, y una convención, que
vive detrás de un puerto de la plataforma. Nova registra por defecto su propia implementación de
cada puerto, y un servicio o un perfil de organización la reemplaza entera sin tocar la regla.**

Aplicado al estándar de API, el reparto cabe en una frase: **el estándar decide la forma; el núcleo
decide qué se puede decir.**

### Reemplazar no es apagar

ADR-033 dice que lo que se puede apagar no puede ser contrato, y eso se mantiene. El puerto del
estándar de API **no tiene apagado**: toda respuesta HTTP pasa por el estándar activo, siempre. Lo
que se vuelve configurable es cuál está activo.

Por eso `wrapResponses` y `catchExceptions` se deprecan. Son el camino de apagar, y dejan de hacer
falta cuando existe el de reemplazar.

### El reparto, en el estándar de API

| El núcleo decide, siempre | El estándar decide, reemplazable |
|---|---|
| qué respuestas pasan por el estándar: las HTTP, menos las marcadas con `@SkipResponseWrapper` | la forma del cuerpo de éxito |
| que un cuerpo ya formateado no se formatee dos veces, preguntándole al estándar si es suyo | la forma del cuerpo de error y su `Content-Type` |
| qué status corresponde a cada excepción | el catálogo: qué código lleva cada status |
| **que un 5xx no lleve detalle**: el mensaje llega saneado y sin código de dominio | cómo se describe todo lo anterior en OpenAPI |
| qué campo falló en una validación | cómo se escribe ese desglose |

La fila en negrita es la que justifica la tabla entera. Si el estándar recibiera la excepción
cruda, uno mal escrito filtraría el cuerpo de un upstream al cliente y el núcleo no tendría cómo
impedirlo. El estándar recibe un fallo **ya clasificado y ya saneado**: puede escribirlo como
quiera, pero no tiene de dónde sacar lo que el núcleo le quitó.

La línea de log del error no está en ninguna de las dos columnas: es de observabilidad. Cambiar el
estándar de API no cambia el log, y los nombres de sus campos se reemplazan desde el puerto de ese
módulo, no desde este.

### El puerto

Los nombres son provisionales; la forma es la decisión.

```ts
/** Un fallo ya clasificado y saneado por el núcleo. Es todo lo que el estándar ve. */
export type ApiFailure = {
  readonly status: number;
  readonly traceId: string | undefined;
  readonly errors: readonly {
    /** El código que puso quien lanzó. Nunca llega en un 5xx: el núcleo lo quita. */
    readonly code: string | undefined;
    /** Ya saneado: en un 5xx es el mensaje genérico, nunca el de la excepción. */
    readonly message: string;
    /** El campo que falló, o null cuando el error no es de validación. */
    readonly field: string | null;
  }[];
};

/** Lo que sale por el cable. */
export type ApiWire = {
  readonly body: unknown;
  /** Por defecto application/json. RFC 7807 contesta application/problem+json. */
  readonly contentType?: string;
};

export interface ApiStandard {
  success(payload: unknown, status: number): ApiWire;
  failure(failure: ApiFailure): ApiWire;
  /** Si el handler ya devolvió un cuerpo de este estándar, para no envolverlo otra vez. */
  owns(payload: unknown): boolean;
  /** Los esquemas del cuerpo, para que el documento describa el cable y no el método. */
  readonly openapi: ApiStandardSchemas;
}
```

`ApiFailure` es también donde entra ADR-031: la capa y el `traceId` capturado al nacer son campos
de este modelo, así que el módulo de errores por capas no necesita otro punto de extensión.

**Se registra en cada stack con el mecanismo que el invariante 2 ya nombra:**

| NestJS | Spring Boot | Quarkus |
|---|---|---|
| `NovaModule.forRoot({ apiStandard: { standard } })`, con una clase inyectable o una instancia | un bean `ApiStandard`; el de Nova, con `@ConditionalOnMissingBean` | un bean `ApiStandard`; el de Nova, con `@DefaultBean` |

**La implementación por defecto es el sobre de hoy, sin cambios en el cable.** `ApiResponses` pasa
a ser su implementación y deja de ser la única forma posible. Acepta el catálogo como parámetro,
porque es la necesidad real de la primera organización y es una variación del mismo sobre, no otro
estándar.

### OpenAPI: el decorador dice qué se devuelve, el estándar dice cómo viaja

Es la única parte donde reemplazar no se reduce a cambiar un proveedor. `@ApiEnvelope` y
`@ApiErrors` se evalúan cuando se importa la clase, **antes de que exista el contenedor de
inyección**, así que no pueden preguntarle al estándar activo cuál es.

Pasan a registrar la intención -el DTO, si es una lista, qué estados documenta- y el documento se
completa al construirse en `bootstrap({ openapi })`, que ya es de Nova, pidiéndole los esquemas al
estándar activo. Los controladores no cambian: `@ApiEnvelope(CourseResponse)` se sigue escribiendo
igual y pasa a significar «el cuerpo del estándar activo, con este DTO adentro».

### Lo mismo en el resto de los módulos

Este ADR implementa el reparto solo en el estándar de API. Para los demás deja el mapa, y **cada
puerto se crea cuando aparece un consumidor que lo necesita**, no antes: la regla de no agregar
superficie sin consumidor sigue en pie.

| Módulo | El núcleo decide, siempre | Puerto, con la implementación de Nova por defecto |
|---|---|---|
| observabilidad | que haya un id de correlación, que viaje a los upstreams y que se loguee; que las cabeceras sensibles se redacten | el logger, los nombres de campo del log, la cabecera de correlación |
| secretos | que se resuelvan antes de que exista la aplicación; que uno roto corte el arranque sin citarse | de dónde salen: el JSON por variable que inyecta ECS es una fuente, no la única |
| cliente HTTP | que el timeout esté siempre puesto; sin reintentos (ADR-029); que un fallo de upstream no llegue literal | el transporte y su pool |
| auth | que el guard sea global y niegue por defecto cuando se declara | cómo se valida el token y cómo se leen los claims |
| health | que existan liveness y readiness, y que no lleven sobre | las rutas y los checks |

### Dos ejes, no uno

Este ADR no decide dónde vive el código; eso es de ADR-033. Los dos se componen: **este decide si
algo se puede reemplazar, y ADR-033 decide dónde vive la implementación por defecto.**

El sobre de Nova no arrastra ninguna dependencia, así que su implementación se queda en el núcleo.
El logger es el mismo caso con otra respuesta posible: el puerto es del núcleo, y si la
implementación con pino se queda adentro o sale a un plugin lo decide la prueba de ADR-033, no este
ADR.

### Qué cambia en los borradores

- **ADR-033, nivel 1.** Dice que el sobre y el catálogo son núcleo sin apagado. Pasa a decir que son
  núcleo **el puerto y las reglas**, y que el sobre de Nova es la implementación por defecto. Sigue
  sin apagado; deja de ser irreemplazable.
- **ADR-031.** Ya propone que la serialización del error sea un punto de extensión con una
  implementación por defecto. Este ADR generaliza ese punto a todo el estándar -éxito, error,
  catálogo y documentación-, y ADR-031 queda como el modelo que el núcleo le entrega.
- **ADR-030.** La especificación deja de describir *el* sobre y describe cada estándar que Nova
  publica, y la suite de conformidad corre una vez por estándar. Su pregunta abierta 2 -RFC 7807 o
  el sobre- deja de ser una decisión de una sola vía: los dos pueden existir, y lo que queda por
  decidir es cuál va por defecto.

## Alternativas descartadas

**Seguir con las opciones de apagado.** Es lo que hay. Se descarta porque apagar obliga a reescribir
las reglas, y un servicio que reescribe el saneado del 5xx es un servicio que puede olvidarlo.
Medido: es la única vía en los tres stacks.

**Un estándar configurable por campos** -nombres de campo, incluir o no `success`, dónde va el
`traceId`-. Sirve para variaciones del mismo sobre y no sirve para RFC 7807, que no es una variación
sino otro cuerpo con otro `Content-Type`. Una perilla por cada diferencia posible termina siendo un
lenguaje de plantillas. Las perillas dentro de una implementación, como el catálogo, sí; en lugar
del puerto, no.

**Un paquete por estándar.** Falla la prueba de ADR-033: ni el sobre de Nova ni RFC 7807 arrastran
dependencias. Separarlos reconstruye la fragmentación que ADR-025 deshizo.

**Que el perfil herede la implementación de Nova y sobreescriba métodos.** Ata cada perfil a la
implementación interna del sobre, y un refactor dentro de Nova rompe a todos los perfiles. El
puerto es la interfaz estable; heredar queda disponible para quien quiera reusar, pero no es el
mecanismo.

**Resolverlo solo en NestJS.** Rompe el invariante 5. Un perfil que existe en NestJS y no en Java
hace que el BFF y el microservicio de la misma organización contesten distinto, que es el riesgo
principal del proyecto.

## Preguntas abiertas

**1. Si RFC 7807 se publica como segunda implementación desde el primer día.** A favor: un puerto
con una sola implementación no está probado, y esta resolvería la pregunta 2 de ADR-030 sin elegir
por todos. En contra: el método pide no agregar superficie sin un consumidor real en el servicio de
ejemplo, y hoy nadie la pide. Una salida intermedia es que viva solo en la suite de conformidad del
núcleo hasta que un servicio la pida.

Es la que se tomó mientras tanto: la segunda implementación existe solo como prueba, en
`packages/core/src/api/api-standard.integration.spec.ts` -éxito en `{ ok, result }`, errores en
`application/problem+json`, catálogo propio- y pasa por `bootstrap()` completo. Prueba el puerto
sin publicarlo; publicarlo sigue abierto.

**2. Cuál es el catálogo de la primera organización.** Sus políticas de 5xx no se pueden unificar
desde Nova. La de contenido la resuelve el núcleo solo, porque con el puerto ya no se puede
expresar; la de forma -nombrar el 5xx por status o colapsarlo- es una decisión de ese equipo, y su
perfil la toma cuando se escriba.

**3. Qué pasa con un cuerpo armado a mano.** Un handler que devuelve `ApiResponses.ok(...)` ata el
servicio al estándar por defecto: con otro activo, ese objeto se trata como carga útil y sale
envuelto. Hoy no hay ningún uso fuera del núcleo -ni en el servicio de ejemplo ni en lo que emite
el generador-, así que deprecarlo es barato. Lo que falta decidir es si se depreca o si se deja
como herramienta del estándar por defecto, con una regla de lint que lo marque.

**4. El lado del que consume.** Un BFF lee el cuerpo de su upstream, y si el upstream habla otro
estándar el cliente HTTP necesita saber cuál. Eso es por upstream, no por servicio. Queda fuera de
este ADR: `HttpClientService` hoy no desenvuelve ningún cuerpo, así que todavía no hay nada que
romper.

## Consecuencias

### Positivas

- Un perfil de organización trae su estándar sin salirse de Nova, y las reglas de seguridad le
  siguen aplicando.
- El documento OpenAPI describe el estándar activo, no el de Nova.
- La pregunta de RFC 7807 deja de ser una decisión de una sola vía.
- Spring deja de contradecir el invariante 2 en este módulo.
- Da una prueba verificable para cualquier módulo: **si reemplazar la convención obliga a reescribir
  una regla, la regla está en el lugar equivocado.**

### Negativas

- **El puerto es un contrato público nuevo, y de un tipo más caro que los de hoy.** Cuando un perfil
  lo implementa, cambiarlo rompe a los perfiles, no solo a los servicios.
- **La paridad se vuelve explícita y se paga por estándar.** Cada estándar que una organización
  quiera en todos sus servicios se implementa tres veces: NestJS, Spring y Quarkus. El puerto no
  reduce ese costo; lo deja a la vista.
- **En Quarkus el puerto necesita un filtro de respuesta para el éxito**, que la extensión hoy no
  registra. Cuánto cambia el cable de un servicio existente depende de si sus recursos ya arman el
  sobre a mano, y hay que medirlo antes de implementar. Se midió en ADR-050: los ejemplos ya
  armaban el sobre, y el filtro de la 3.0.0 no cambia su cable.
- **La documentación OpenAPI deja de ser declarativa.** Se completa al construir el documento, y un
  servicio que lo arme sin `bootstrap({ openapi })` no se entera del estándar activo.
- Retirar `wrapResponses` y `catchExceptions` después de deprecarlos es un cambio incompatible, y
  necesita su codemod por el invariante 4.

## Referencias

- [ADR-025: Tres Paquetes NestJS en Lugar de Once](../nest/ADR-025-tres-paquetes-en-lugar-de-once.md)
- [ADR-029: Sin Reintentos ni Corte de Circuito en el Cliente HTTP](../nest/ADR-029-sin-reintentos-en-el-cliente-http.md)
- [ADR-030: Contrato de Plataforma Versionado](ADR-030-contrato-de-plataforma-versionado.md)
- [ADR-031: Módulo Base de Errores por Capas, con Trazabilidad](ADR-031-modulo-de-errores-por-capas-con-trazabilidad.md)
- [ADR-032: Observabilidad como Puerto Conectable](ADR-032-observabilidad-como-puerto-conectable.md)
- [ADR-033: Qué es Núcleo, qué es Común Opcional y qué es Plugin](ADR-033-nucleo-comun-y-plugins.md)
- `nova-nestjs`: `packages/core/src/api-standard/`, `packages/core/src/api/`,
  `packages/core/src/openapi/envelope.ts`, `packages/schematics/src/service/files/base/test/app.e2e-spec.ts.template`
- `nova-java-commons-spring-boot-starter`: `nova-api-standard-starter/.../autoconfigure/ApiStandardAutoConfiguration.java`
- `nova-java-api-standard-quarkus-extension`: `mapper/ApiExceptionMapper.java`
- RFC 7807, *Problem Details for HTTP APIs*
