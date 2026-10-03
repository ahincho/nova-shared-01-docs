# ADR-051: Las Plantillas de Servicio, un Nivel entre el Build y los Generadores

## Estado

Aceptada (2026-10-01), con las recomendaciones de sus preguntas abiertas. Angel pidió un nivel de plantillas, como el que se planteó en el curso
entre el BOM y las herramientas, con repositorios que se llamen como
`nova-template-01-spring-boot-service`.
**Scope:** `shared` (Java y NestJS).
**Enmienda:** [ADR-001](ADR-001-arquitectura-meta-framework-cinco-niveles.md), que pasa de cinco
niveles a seis; [ADR-038](ADR-038-nombres-de-repositorio-por-tecnologia.md), con la categoría
`template`; y [ADR-039](ADR-039-nombres-de-artefacto-derivados-del-repositorio.md), con las
coordenadas de una plantilla.
**Primeros consumidores:** `plaza-payments`, `plaza-catalog` y `plaza-bff`
([ADR-043](ADR-043-plaza-la-plataforma-de-compras.md)), los tres servicios de Plaza que todavía no
existen.

## Fecha

2026-10-01

## Contexto

### Lo que enseña el curso

El curso tiene una plantilla de servicio, `oms-service-template`: un servicio Spring Boot completo,
con un CRUD de ejemplo, su Dockerfile y su docker-compose. Cada servicio posterior nace como una copia
a mano de esa carpeta, con las clases renombradas. La plantilla viene después del parent y los
starters, y antes de las aplicaciones. Es la respuesta del curso a cómo empieza un servicio.

### Lo que hace Nova hoy

ADR-001 pone en el nivel 5 todo lo que no es una API: el plugin de convención y el arquetipo. Ahí
conviven dos cosas distintas:

- **Qué forma tiene un servicio.** Su estructura, su configuración, el Dockerfile, el CI, las pruebas
  y las reglas de arquitectura.
- **Cómo se crea.** El arquetipo de Maven, los schematics de NestJS, el botón *Use this template* de
  GitHub y su tarea `rename`.

Como el nivel no los separa, la forma de un servicio está copiada dentro de cada generador, en cuatro
lugares que nadie compara:

| Dónde | Qué genera | Estado |
|---|---|---|
| `nova-java-17-spring-boot-archetype`, `archetype-resources` | un servicio Maven sobre `nova-spring-boot-parent` | nunca se publicó |
| `nova-java-18-quarkus-archetype` | un proyecto Maven de tres módulos | 1.0.1 |
| `nova-java-19-quarkus-template`, `src-styles` | un servicio Gradle, con marcadores `__PACKAGE__` | la plantilla misma no compila |
| `nova-nestjs-01-platform`, los archivos de los schematics | un servicio NestJS: base, BFF o ACL | su CI genera un servicio y le pasa la compuerta entera |

ADR-043 ya registró la consecuencia: los generadores 17, 18 y 19 producen proyectos que no compilan.
NestJS es la excepción, y por una razón concreta: su CI genera un servicio y lo construye en cada
pull request, y `nova-example-08-nestjs-generated` es esa salida.

**El nivel 5 tiene además una dependencia hacia arriba.** Un servicio aplica el plugin de convención
de Gradle (`nova-java-24-gradle-toolchain`) igual que en Maven hereda el parent: es cómo se
construye, no cómo se crea. Ponerlo en el nivel 5, junto al arquetipo que genera ese mismo servicio,
mezcla lo que el servicio usa con lo que lo fabrica.

## Decisión

**Nova tiene seis niveles. Las plantillas de servicio son el nivel 5: un servicio real por stack y
tipo, que compila y pasa su CI. Los generadores pasan al nivel 6 y producen exactamente lo que dice
la plantilla, y el CI lo comprueba.**

### Los seis niveles

| Nivel | Qué es | En Nova |
|---|---|---|
| 1 | Librerías puras | `nova-java-01` a `07`, y los contratos de `23` y `25` |
| 2 | Starters y extensiones | `nova-java-08` a `11`, y los conectores de `23` y `25` |
| 3 | Meta-starter | `nova-java-12` |
| 4 | **BOM, parent y plugins de convención**: qué versiones y cómo se construye | `nova-java-13` a `16` y **`24`**, que sube desde el nivel 5; en NestJS, `nova-nestjs-toolchain` |
| **5** | **Plantillas de servicio**: la forma canónica de un servicio | `nova-template-*`, nuevo |
| 6 | **Generadores**: lo que crea un servicio a partir de una plantilla | `nova-java-17` y `18`; en NestJS, `nova-nestjs-schematics` |

Las dependencias siguen bajando: un generador conoce su plantilla, la plantilla usa el BOM, el
plugin y los starters, y nada de abajo sabe que existe una plantilla. En NestJS el núcleo sigue
cubriendo los niveles 1 a 3 en un paquete, como ya dice ADR-025.

### Qué es una plantilla

**Un repositorio con un servicio que compila, pasa sus pruebas y se despliega.** No lleva
marcadores: el código es real, con un nombre de ejemplo, y por eso su propio CI lo prueba como a
cualquier servicio. Es lo que ADR-043 pide para generar un servicio en vivo, y lo que el curso hace
con su carpeta, pero verificado.

Lleva lo que un servicio de Nova trae desde el primer commit:

- el build con el plugin de convención y el BOM;
- los starters del stack;
- una funcionalidad mínima que lanza un error de ADR-031;
- sus pruebas, incluidas las reglas de arquitectura;
- la imagen de contenedor del toolchain;
- el CI con los workflows de `nova-shared-02-pipelines`;
- el `.env.example`, el README y la licencia EPL-2.0.

**Una plantilla por stack y tipo.** El tipo es `service`, y después `bff` y `acl`, que los schematics
de NestJS ya generan. Una plantilla nueva entra cuando un servicio real la necesita.

**Se marca como repositorio plantilla de GitHub**, así que *Use this template* crea un servicio
nuevo con su historia limpia.

### Plantilla y generador no se separan

La regla del nivel: **el CI comprueba que el generador produce la plantilla**. La fuente de verdad
es la que resulte natural en cada stack:

| Stack | Fuente de verdad | Cómo se comprueba |
|---|---|---|
| Spring Boot y Quarkus | la plantilla | el generador se construye desde ella, y el CI genera un servicio y lo compila |
| NestJS | el schematic `service`, que ya tiene opciones | la plantilla es su salida versionada, y el CI regenera y exige cero diferencias |

Así la forma de un servicio vive en un solo lugar por stack, y una copia que se desvía rompe el CI
en vez de esperar a que alguien la use.

### Los nombres

**`nova-template-<NN>-<tecnología>-<tipo>`**, con un contador propio para la categoría, como los
ejemplos de la enmienda de ADR-038. Las cuatro reglas de ADR-038 se aplican igual: el número solo
da orden, se asigna una vez y no va en ninguna coordenada.

| # | Repositorio | Cómo nace |
|---|---|---|
| 01 | `nova-template-01-spring-boot-service` | nuevo |
| 02 | `nova-template-02-quarkus-service` | renombrando `nova-java-19-quarkus-template`, que conserva su historia; el número `java-19` queda retirado |
| 03 | `nova-template-03-nestjs-service` | nuevo, como salida del schematic `service` |

**Las coordenadas siguen la regla 8 de ADR-039**, la de los ejemplos, porque tampoco se publican:

- en Java, `groupId` `pe.edu.nova.java.templates` y `artifactId` `nova-template-<tecnología>-<tipo>`;
- en NestJS, el `name` del `package.json` es `nova-template-nestjs-<tipo>`, privado.

Un servicio creado desde la plantilla cambia esas coordenadas por las suyas al nacer.

**Cambia el sentido de un ejemplo.** La regla 8 de ADR-039 dice que un ejemplo es lo que un equipo
copia para empezar. Desde aquí eso es una plantilla: un ejemplo muestra cómo se usa una capacidad y
no se copia.

### El orden

Cada paso es su propio PR:

1. `nova-template-01-spring-boot-service`, porque todas sus piezas ya existen.
2. `nova-template-03-nestjs-service`, desde el schematic que ya funciona.
3. `nova-template-02-quarkus-service`, después del plugin `quarkus-service` del toolchain, que
   todavía no existe.
4. La enmienda a ADR-001, ADR-038 y ADR-039, el panorama de `diagrams/` y las guías que nombran los
   niveles.

## Alternativas descartadas

**Mantener cinco niveles y aclarar que el 5 son «plantillas y generadores».** No renumera nada, pero
deja juntas las dos cosas que hoy se desvían, y la regla de generar y construir en CI queda sin
lugar.

**Plantillas con marcadores**, como `nova-java-19` hoy. Un `__PACKAGE__` no compila, así que la
plantilla no se puede probar; es justo lo que produjo generadores rotos.

**Una carpeta de plantillas dentro de cada generador**, como hace el arquetipo. Es la forma actual, y
es la que reparte la forma de un servicio en cuatro lugares.

**Un solo repositorio con todas las plantillas.** Rompe *Use this template*, que copia un
repositorio entero, y mezcla el CI de tres stacks.

**Usar los ejemplos como plantillas.** Un ejemplo de referencia muestra muchas capacidades a la vez
y crece con ellas; una plantilla lleva solo lo que todo servicio trae desde el primer día.

## Preguntas resueltas

Angel aprobó las recomendaciones el 2026-10-01.

**1. Cómo se genera desde una plantilla Java.** El arquetipo de Maven no sirve para una plantilla
Gradle, porque `archetype:create-from-project` solo lee proyectos Maven. Hay dos caminos:

- **a)** *Use this template* y una tarea `novaRename` del plugin de convención, que cambia el
  `groupId`, el paquete y el nombre. Es lo que hace hoy `nova-java-19`, pero desde el toolchain y no
  copiado en cada servicio.
- **b)** Un generador propio, una CLI como la de NestJS.

Resuelta: **a**. Ya existe la mitad, y no suma otra herramienta que mantener.

**2. Qué pasa con los arquetipos 17 y 18.** Generan servicios Maven, y Nova construye con Gradle
desde ADR-044. Resuelta: **archivar `nova-java-17`**, que nunca se publicó, cuando exista la
plantilla 01, y **dejar `nova-java-18` como generador Maven** mientras haya consumidores de
`nova-quarkus-parent`, construido desde la plantilla 02. Su retiro se decide con su propio ADR.

**3. Si la plantilla 03 reemplaza a `nova-example-08-nestjs-generated`.** Son el mismo archivo: la
salida del schematic `service`. Resuelta: **sí**. El ejemplo 08 se archiva cuando la plantilla
03 exista, y su número queda retirado.

## Consecuencias

### Positivas

- Cada stack tiene un único lugar que dice cómo es un servicio, y un CI que lo prueba.
- Los generadores dejan de producir proyectos que no compilan, porque la regla del nivel lo impide.
- Responde lo que planteó el curso con un nivel propio, y lo mejora: la plantilla del curso se copia
  a mano y nadie la prueba.
- El plugin de convención queda junto al parent, donde un servicio lo usa.
- La fase 5 de Plaza, «el servicio nuevo generado en vivo», tiene de dónde salir.

### Negativas

- **Se renumera un nivel en la documentación**: ADR-001, la columna de nivel de ADR-038, la guía
  `java/01` y el panorama.
- **Tres repositorios nuevos o renombrados**, cada uno con su CI.
- **Una plantilla también envejece**: cuando sale una versión de un starter, hay que subirla en la
  plantilla. Su CI lo detecta, pero alguien tiene que hacerlo.
- Mientras la plantilla 02 espera al plugin `quarkus-service`, Quarkus sigue con el template 19 tal
  como está.

## Referencias

- [ADR-001: Arquitectura de Meta-Framework en Cinco Niveles](ADR-001-arquitectura-meta-framework-cinco-niveles.md)
- [ADR-025: Tres Paquetes NestJS en Lugar de Once](../nest/ADR-025-tres-paquetes-en-lugar-de-once.md)
- [ADR-026: Generador de Servicio y Reglas de Arquitectura](../nest/ADR-026-generador-de-servicio-y-reglas-de-arquitectura.md)
- [ADR-038: Nombres de Repositorio por Tecnología y Número](ADR-038-nombres-de-repositorio-por-tecnologia.md)
- [ADR-039: Nombres de Artefacto Derivados del Repositorio](ADR-039-nombres-de-artefacto-derivados-del-repositorio.md)
- [ADR-043: Plaza, la Plataforma de Compras que Demuestra Nova](ADR-043-plaza-la-plataforma-de-compras.md)
- [ADR-044: El Toolchain de Java](../java/ADR-044-toolchain-de-java.md)
- GitHub Docs, *Creating a template repository*
- Maven Archetype Plugin, `archetype:create-from-project`
