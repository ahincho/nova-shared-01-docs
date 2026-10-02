# ADR-052: La Meta-Extensión de Quarkus, el Nivel 3 que le Faltaba

## Estado

Aceptada (2026-10-01), con las recomendaciones de sus preguntas abiertas. Enmendada el mismo día con lo que entra en el meta-starter de Spring Boot. Angel preguntó por qué Quarkus no tenía un meta-starter, y pidió este ADR
para agregarlo.
**Scope:** `java`, Quarkus. Fija además una regla para el meta-starter de Spring Boot.
**Completa:** el nivel 3 de [ADR-001](../shared/ADR-001-arquitectura-meta-framework-cinco-niveles.md),
que hasta hoy solo nombra a `nova-spring-boot-starter`.
**Enmienda:** la tabla de tipos de
[ADR-039](../shared/ADR-039-nombres-de-artefacto-derivados-del-repositorio.md), con el tipo «nivel 3
en Quarkus».
**Depende de:** [ADR-050](ADR-050-errores-por-capas-en-quarkus.md), la extensión 10 en su 3.0.0.
**Primer consumidor:** `plaza-catalog` ([ADR-043](../shared/ADR-043-plaza-la-plataforma-de-compras.md)),
creado desde `nova-template-02-quarkus-service` ([ADR-051](../shared/ADR-051-plantillas-de-servicio.md)).

## Fecha

2026-10-01

## Contexto

El nivel 3 de ADR-001 es una dependencia que trae a todas las del nivel 2: un servicio agrega una
línea en vez de cinco. Spring Boot lo tiene en `nova-java-12-spring-boot-starter`, y NestJS lo cubre
con su núcleo, que reúne los niveles 1 a 3 en un paquete. Quarkus no tiene nada en ese nivel, y el
panorama de `diagrams/` lo mostraba como «no aplica».

**Sí aplica.** En Quarkus una extensión puede depender de otras, y es como el propio Quarkus arma las
extensiones que agrupan a otras. La única condición es la pareja: el runtime depende de los runtime y
el deployment depende de los deployment. Quarkus valida esa correspondencia al construir.

**Hasta hace poco no valía la pena.** Con una sola extensión, agruparla no ahorraba nada. Hoy hay dos
que un servicio quiere siempre:

| Extensión | Versión | Qué trae |
|---|---|---|
| `nova-api-standard-quarkus-extension` (`nova-java-10`) | 2.0.1; 3.0.0 con ADR-050 | el sobre y los errores por capas |
| `nova-secrets-quarkus-extension` (`nova-java-23`) | 1.2.0 | los secretos del entorno y de los almacenes |

### El meta-starter de Spring, medido

Es la única referencia que tiene Nova, y tiene dos defectos que esta extensión no puede heredar:

- **Falta un starter.** ADR-001 dice que el meta-starter agrega todos los del nivel 2. La 1.0.4 no
  trae `nova-observability-spring-boot-starter`, y nada lo detectó.
- **Se queda atrás por construcción.** Su build importa `nova-spring-boot-bom` 2.0.0 como
  `platform`, y ese mismo BOM es el que gestiona al meta-starter. Cada versión del BOM necesita un
  meta-starter nuevo, y cada meta-starter nuevo apunta a un BOM viejo. Hoy un servicio que usa solo
  el meta-starter, sin el BOM 3.x, recibe los starters 2.x, con los errores de antes de ADR-031.

## Decisión

**Quarkus tiene su nivel 3: `nova-quarkus-extension`, una meta-extensión sin código que trae las
extensiones de Nova. Declara sus versiones sin importar el BOM, y el CI del BOM comprueba que no se
le escape ninguna extensión.**

### Qué es

| Módulo | `artifactId` | Qué tiene |
|---|---|---|
| runtime | `nova-quarkus-extension` | ningún código; depende del runtime de cada extensión de Nova |
| deployment | `nova-quarkus-extension-deployment` | ningún paso de build; depende del deployment de cada una |

El `groupId` es `pe.edu.nova.java.starters`, el de las extensiones que agrega. Un servicio declara
una dependencia de Nova y recibe el estándar de API y los secretos:

```kotlin
implementation(platform("pe.edu.nova.java:nova-quarkus-bom:4.0.0"))
implementation("pe.edu.nova.java.starters:nova-quarkus-extension")
```

**Vive en un repositorio propio, `nova-java-26-quarkus-extension`**, como el meta-starter de Spring
vive en el 12. No es una capacidad, así que ADR-041 no la pone junto a ninguna, y su ciclo de
versiones no es el de ninguna de las extensiones que agrega.

### Qué entra

**Entra cada extensión de Quarkus de Nova que, sin configuración, no cambia el comportamiento del
servicio.** Es la condición que hace seguro agregar una línea:

- El estándar de API entra: es lo que todo servicio de Nova responde.
- Los secretos entran: sin `nova.secrets.import` no leen ningún almacén, y el entorno se desdobla
  con las mismas reglas de ADR-042 en los tres stacks.
- Una extensión que exige configuración para arrancar, o que cambia las respuestas solo por estar,
  queda fuera y el servicio la declara aparte. Es el caso que hay que mirar con la extensión de
  Keycloak (11): si exigiera un servidor OIDC configurado, entrar la volvería obligatoria para todos.

La misma condición vale para el meta-starter de Spring, cuyos starters ya son condicionales.

### Cómo no se queda atrás

**1. Declara sus versiones, no importa el BOM.** Cada dependencia lleva su versión explícita en el
build de la meta-extensión. Así se rompe el ciclo: el BOM gestiona a la meta-extensión, y la
meta-extensión no conoce al BOM.

**2. El BOM comprueba que la meta-extensión está completa y al día.** Antes de publicarse, el CI de
`nova-java-13-bom` mira cada `*-quarkus-extension` que gestiona `nova-quarkus-bom` y exige que la
meta-extensión la traiga, en la misma versión. El BOM es el único lugar que conoce todas las
extensiones, así que es donde vive la prueba.

**3. El orden de publicación queda fijo:** sale la extensión, después la meta-extensión que la trae,
y por último el BOM que gestiona a las dos. Si alguien publica el BOM antes, la prueba del punto 2 lo
frena.

**La misma prueba se aplica al meta-starter de Spring**, y va a fallar el primer día: le falta el
starter de observabilidad y arrastra el BOM 2.0.0. Arreglarlo es su propio PR en `nova-java-12`, con
la regla 1, y no bloquea este ADR.

### Imagen nativa

Cada extensión suma pasos de build y peso a la imagen nativa, aunque el servicio no la use. Hoy el
costo es bajo: las dos extensiones que entran se usan en todo servicio. La condición de «qué entra»
es la que lo mantiene bajo. Un servicio que necesite recortar excluye la dependencia transitiva en su
build; Quarkus resuelve el deployment desde el runtime, así que basta excluir el runtime.

### Versión

Sale en la **0.1.0**, como la idempotencia de ADR-047, y pasa a la **1.0.0** cuando `plaza-catalog`
la use. No tiene API propia, pero su lista de dependencias es un contrato: sacar una extensión de ahí
rompe a un servicio que contaba con ella, y eso es una versión mayor.

### El orden

Cada paso es su propio PR:

1. La extensión 10 en su 3.0.0, por ADR-050. Agregar ahora la 2.0.1 publicaría una meta-extensión que
   responde los errores a la antigua.
2. `nova-java-26-quarkus-extension` 0.1.0, con sus dos módulos y una `@QuarkusTest` que arranca con
   solo esa dependencia y responde un error de ADR-031 con su `traceId`.
3. `nova-quarkus-bom` la gestiona, con la prueba de completitud.
4. `nova-template-02-quarkus-service` declara solo la meta-extensión.
5. La enmienda a ADR-001, la tabla de ADR-039 y el panorama de `diagrams/`.

### Enmienda (2026-10-01): qué entra en el meta-starter de Spring Boot

Al aplicar la condición de «qué entra» a `nova-java-12`, dos de los starters que el meta-starter no
traía resultaron no cumplirla, y el que se daba por faltante tampoco la cumplía todavía:

| Starter | Sin configuración | Decisión |
|---|---|---|
| `nova-api-standard-spring-boot-starter` 3.0.1 | el sobre y los errores de ADR-031, que todo servicio responde | entra |
| `nova-mask-spring-boot-starter` 3.0.1 | enmascara lo que se anota, y también lo que infiere por el nombre del campo | entra **desde la 4.0.0** |
| `nova-secrets-spring-boot-starter` 1.2.0 | sin `nova.secrets.import` no lee ningún almacén | entra |
| `nova-observability-spring-boot-starter` 2.0.2 | exporta por OTLP a `http://localhost:4318` fijo, y su indicador de salud deja `/actuator/health` en DOWN sin collector | entra **desde la 3.0.0** |
| `nova-idempotency-spring-boot-starter` 0.1.1 | se enciende sola y exige la tabla de su almacén JDBC; además es 0.x | queda fuera |

**La observabilidad sale en la 3.0.0 apagando la exportación sin endpoint.** Angel lo decidió el
2026-10-01 en vez de dejarla fuera: un servicio que solo use el meta-starter tiene que tener los Four
Golden Signals de ADR-014. Desde la 3.0.0:

- `nova.observability.otlp.endpoint` no tiene valor por defecto. El localhost fijo era además un valor
  de consumidor escrito en la plataforma.
- Las métricas, las trazas y la correlación de logs siguen encendidas. Los `traceId` se siguen
  generando, así que ADR-031 los encuentra.
- La exportación OTLP arranca solo si hay un endpoint: el de Nova, o el estándar
  `OTEL_EXPORTER_OTLP_ENDPOINT` si quien opera ya lo usa. Sin endpoint no se exporta nada.
- El indicador de salud del collector se registra solo cuando hay un endpoint.

La receta de migración va en su README: quien dependía del localhost implícito lo declara.

**La máscara entra desde la 4.0.0, que enmascara solo lo anotado.** La 3.0.1 se dio por segura y no
lo era: infería el tipo por el nombre del campo en todo JSON que escribía Spring, así que un `name`
salía como `T***` en una respuesta de la API. Lo destapó `nova-template-01-spring-boot-service`, y
Angel decidió el 2026-10-01 que se enmascare solo con `@Masked` o `@MaskedClass`. La inferencia queda
detrás de `nova.mask.infer-by-field-name`, apagada por defecto. El meta-starter que la trae es la
3.0.0.

**La idempotencia queda fuera mientras sea 0.x y exija su almacén.** Entra cuando cumpla la
condición, por ejemplo apagada hasta que un servicio la declare, y en una versión 1.x.

**El meta-starter pasa a la 2.0.0**, con la regla 1. Deja de importar `nova-spring-boot-bom` y
declara la versión de cada starter. Spring Boot llega con su propio BOM, y el meta-starter lleva los
mismos parches de seguridad que el BOM de Nova, como el de Tomcat. Es mayor porque cambia lo que
recibe un servicio que lo usa sin el BOM: los starters 3.x en lugar de los 2.x, con los errores de
ADR-031. La receta remite a la del starter de API.

## Alternativas descartadas

**Dejar Quarkus sin nivel 3.** El BOM ya alinea las versiones, y un servicio puede declarar dos
extensiones. Pero cada servicio repite la misma lista, y una extensión nueva de Nova no le llega a
nadie hasta que alguien la agregue a mano en cada uno.

**Llamarla `nova-quarkus-starter`**, como diría hoy la tabla de ADR-039 para el nivel 3. En Quarkus
todo lo que se agrega es una extensión, y el término *starter* es de Spring: un equipo de Quarkus lo
buscaría con otro nombre.

**Importar el BOM dentro de la meta-extensión**, como hace el meta-starter de Spring. Es justo lo que
deja al meta-starter atrás.

**Ponerla dentro de un repositorio existente**, como el BOM o la extensión 10. El BOM no publica
código, y la extensión 10 es una capacidad con su propio ritmo de versiones.

**Un *codestart* de Quarkus**, la plantilla de `code.quarkus.io`. Resuelve cómo nace un proyecto, que
es el nivel 5 de ADR-051, no qué dependencia lo mantiene al día.

## Preguntas resueltas

Angel aprobó las recomendaciones el 2026-10-01.

**1. Si entra la extensión de Keycloak cuando exista.** Depende de si arranca sin configuración.
Resuelta: **diseñarla para que no haga nada sin `nova.auth.*`**, como el `auth` de NestJS, que
está apagado si el servicio no lo declara. Así entra en la meta-extensión y la paridad se mantiene.

**2. Si la prueba de completitud también exige el orden de publicación en el workflow.**
Resuelta: **no por ahora**. La prueba del BOM ya frena una publicación fuera de orden, y
automatizar la cadena es trabajo del pipeline compartido.

## Consecuencias

### Positivas

- El nivel 3 existe en los tres stacks, y el panorama deja de tener un hueco.
- Un servicio Quarkus declara una dependencia de Nova, como uno de Spring Boot.
- Las extensiones nuevas les llegan a los servicios con subir una versión.
- La regla de versiones corrige también al meta-starter de Spring, que hoy reparte starters viejos.

### Negativas

- **Un repositorio más**, con su CI y sus releases.
- **Una publicación más en cada cambio de extensión**, en un orden fijo.
- **La imagen nativa carga lo que el servicio no use**, mientras la condición de «qué entra» no se
  cumpla de verdad en cada extensión nueva.

## Referencias

- [ADR-001: Arquitectura de Meta-Framework en Cinco Niveles](../shared/ADR-001-arquitectura-meta-framework-cinco-niveles.md)
- [ADR-039: Nombres de Artefacto Derivados del Repositorio](../shared/ADR-039-nombres-de-artefacto-derivados-del-repositorio.md)
- [ADR-041: Un Repositorio por Capacidad](ADR-041-un-repositorio-por-capacidad.md)
- [ADR-045: La Imagen Nativa de GraalVM, junto a la JVM](ADR-045-imagen-nativa-junto-a-la-jvm.md)
- [ADR-047: La Idempotencia de las Operaciones, detrás de un Contrato](../shared/ADR-047-idempotencia-detras-de-un-contrato.md)
- [ADR-049: Los Secretos en Quarkus y NestJS](../shared/ADR-049-secretos-en-quarkus-y-nestjs.md)
- [ADR-050: Los Errores por Capas en Quarkus](ADR-050-errores-por-capas-en-quarkus.md)
- [ADR-051: Las Plantillas de Servicio](../shared/ADR-051-plantillas-de-servicio.md)
- `nova-java-12-spring-boot-starter`: `build.gradle.kts`, el `platform` del BOM 2.0.0
- Quarkus, *Writing Your Own Extension*: dependencias entre extensiones
