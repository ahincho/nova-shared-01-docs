# ADR-039: Nombres de Artefacto Derivados del Repositorio

## Estado

Aceptada (2026-09-27). Angel confirmó las tres preguntas que quedaban:

1. Con «eliminar el prefijo de `quarkus-api-rest`» se refería a `nova-quarkus-api-ext`, que pasa
   a `nova-api-standard-quarkus-extension`.
2. La fase 2 va enseguida de la fase 1; la fase 3, a medida que se toque cada repositorio.
3. La extensión se publica como 2.0.1.

**Scope:** `shared` (Java + NestJS)
**Receta de migración:** [`ops/rename-artifacts.py`](../../ops/rename-artifacts.py), con el mapa
de coordenadas en [`ops/artifact-renames.json`](../../ops/artifact-renames.json).
**Guía práctica:** [`java/12-guia-crear-un-artefacto.md`](../../java/12-guia-crear-un-artefacto.md)

## Fecha

2026-09-27

## Contexto

ADR-038 fijó cómo se llama un repositorio y dejó las coordenadas quietas a propósito: su regla 4
dice que el número no entra en el `groupId`, en el `artifactId` ni en el paquete npm. Lo que
ningún ADR fijó es cómo se elige el `artifactId`, y sin una regla cada repositorio lo resolvió a
su manera.

### Lo que hay, medido

Se revisaron los 20 artefactos que definen los 19 repositorios Java, y se compararon con lo que
GitHub Packages tiene publicado de verdad.

| Repositorio | `artifactId` | Forma |
|---|---|---|
| `nova-java-01` a `05` y `07` | `nova-api-standard`, `nova-date-utils`, ... | `nova-` + nombre del repositorio |
| `nova-java-08-commons-spring-boot-starter` | `nova-api-standard-starter`, `nova-mask-starter` | calla el framework |
| `nova-java-09-observability-spring-boot-starter` | `nova-observability-starter` | calla el framework |
| `nova-java-10-api-standard-quarkus-extension` | `nova-quarkus-api-ext` | framework delante, tipo abreviado |
| `nova-java-12` a `18` | `nova-spring-boot-starter`, `nova-bom`, ... | `nova-` + nombre del repositorio |

**Dieciséis de los veinte ya se llaman `nova-` más el nombre del repositorio**, sin la
tecnología y sin el número. Los cuatro que no lo cumplen son los conectores del nivel 2 de
ADR-001, y lo incumplen de dos maneras distintas: los starters de Spring Boot no dicen para qué
framework son, y la extensión de Quarkus pone el framework delante y abrevia el tipo.

Los nombres derivados tampoco coinciden siempre. El componente de release-please es
`nova-starter` en `nova-java-12` y `nova-java-spring-boot-gradle-plugin` en `nova-java-16`, y
la clave de SonarCloud se aparta del `artifactId` en `nova-java-08`, `09`, `12`, `16` y en el
ejemplo 04.

**SonarCloud, además, no tiene hoy ningún proyecto de Nova.** La organización `ahincho` solo
tiene los seis proyectos de Spark Match, y ninguno de los 29 repositorios Java, NestJS y de
ejemplos tiene el secreto `NOVA_SONAR_TOKEN`, así que el workflow reutilizable se salta el análisis con una
advertencia. Las claves de los `ci.yml` todavía no apuntan a nada, y corregirlas no pierde
historial.

### La extensión de Quarkus no se puede consumir

El build de `nova-java-10` publica `nova-quarkus-api-ext`, y **ese paquete ya no existe** en el
registro: su `maven-metadata.xml` responde 404. Lo que sí está es
`nova-api-standard-quarkus-extension`, con las versiones 1.0.0 y 2.0.0 del 2026-07-15, iguales
entre sí y sin el índice Jandex que agregó la 1.0.1. `nova-quarkus-bom` y los ejemplos 04 y 06
piden `nova-quarkus-api-ext:1.0.1`, así que hoy ninguno resuelve. Las versiones tampoco
coinciden: `gradle.properties` dice 1.0.0, el manifest de release-please 1.1.1 y el tag más alto
es `v1.1.4`.

### El «paquete fantasma» de julio, revisado

`nova-quarkus-api-ext` nació como un rodeo. Entre el 14 y el 15 de julio las versiones 1.1.0 a
1.1.4 se publicaron con el run en verde, pero GitHub Packages respondía 404 al pedir el `.pom` y el
`.jar`. El diagnóstico de [`java/07`](../../java/07-quarkus-analisis-adopcion.md) §8 concluyó
que GitHub Packages descarta lo que sube Gradle cuando el `artifactId` pasa de unos 35
caracteres, y acortó el nombre a 20. Tres hechos lo contradicen:

1. **El `artifactId` nunca tuvo 39 caracteres.** `rootProject.name` fue
   `nova-api-standard-quarkus-extension`, de 35, desde el primer commit. El nombre largo era el
   del repositorio de entonces, `nova-java-api-standard-quarkus-extension`, que tiene 40.
2. **La 2.0.0 se descarga hoy.** El diagnóstico la dio por fantasma después de republicarla
   desde cero, y hoy responde 200 con el `.pom` (1586 B), el `.jar` (4462 B) y el `.module`
   (2910 B). El registro anota su creación y su última modificación en el mismo segundo
   (03:59:08 y 03:59:09), así que salió de una sola publicación y nadie la completó después.
3. Los demás artefactos que Nova publica con Gradle tienen hasta 30 caracteres, y nada apunta a
   un límite entre 30 y 35.

El síntoma fue real: la lectura inmediata devolvía 404. La causa no era la longitud. La
explicación más probable, que no está verificada, es que la comprobación leyó un 404 cacheado de
una petición anterior a la subida, y que el cambio de nombre «lo arregló» porque esas rutas
nuevas nunca se habían pedido. Sea cual sea la causa, la lección no es mantener los nombres
cortos: es no dar por buena una publicación en verde. De eso trata la regla 6.

### Por qué no alcanza un POM de relocalización

Maven permite publicar las coordenadas viejas con un `<relocation>` que apunta a las nuevas.
Gradle no lo trata como una redirección: agrega el artefacto relocalizado como dependencia del
original y los dos terminan en el grafo
([gradle/gradle#1256](https://github.com/gradle/gradle/issues/1256)). Dependabot tampoco lo
entiende ([dependabot-core#1947](https://github.com/dependabot/dependabot-core/issues/1947)).
Casi todo Nova compila con Gradle, así que la migración va por receta, igual que en ADR-038.

## Decisión

**Un repositorio que publica un solo artefacto lo llama `nova-` seguido del `<nombre>` que el
repositorio lleva después del número.**

```
nova-java-01-api-standard                    ->  pe.edu.nova.java.libs:nova-api-standard
nova-java-10-api-standard-quarkus-extension  ->  pe.edu.nova.java.starters:nova-api-standard-quarkus-extension
nova-java-12-spring-boot-starter             ->  pe.edu.nova.java.starters:nova-spring-boot-starter
```

Ocho reglas lo sostienen.

**1. La tecnología va en el `groupId`, y el número en ninguna parte.** El `groupId` ya dice
`java` (ADR-004), así que el `artifactId` no lo repite. El número queda solo en el nombre del
repositorio, como pide la regla 4 de ADR-038, que sigue en pie. Del artefacto se llega al
repositorio agregando la tecnología y el número, y del repositorio al artefacto quitándolos.

**2. El orden es capacidad, framework y tipo.** El framework nunca va delante de la capacidad,
para que los conectores de una capacidad queden junto a su librería:

```
nova-api-standard
nova-api-standard-quarkus-extension
nova-api-standard-spring-boot-starter
```

Es el orden que ya usan los nombres de repositorio, y el que pide Spring Boot para los starters
de terceros (`<nombre>-spring-boot-starter`). Quarkus pone `quarkus-` delante en sus propias
extensiones porque ahí el prefijo es el espacio de nombres; en Nova el espacio de nombres es
`nova-`.

**3. Palabras completas, tomadas de un vocabulario fijo.** Nada de abreviaturas: `extension`, no
`ext`. El tipo sale de esta tabla:

| Nivel (ADR-001) | Forma | Ejemplo |
|---|---|---|
| 1, librería pura | `nova-<capacidad>` | `nova-api-standard`, `nova-date-utils` |
| 2, conector de Spring Boot | `nova-<capacidad>-spring-boot-starter` | `nova-observability-spring-boot-starter` |
| 2, conector de Quarkus | `nova-<capacidad>-quarkus-extension` | `nova-api-standard-quarkus-extension` |
| 2, módulo de build de una extensión | `<artifactId de la extensión>-deployment` | ninguno todavía |
| 3, starter del meta-framework | `nova-<framework>-starter` | `nova-spring-boot-starter` |
| 4, BOM | `nova-[<framework>-]bom` | `nova-bom`, `nova-quarkus-bom` |
| 4, parent | `nova-<framework>-parent` | `nova-quarkus-parent` |
| 5, plugin de build | `nova-<framework>-<herramienta>-plugin` | `nova-spring-boot-gradle-plugin` |
| 5, arquetipo | `nova-<framework>-archetype` | `nova-quarkus-archetype` |

Un tipo nuevo, como un conector de Micronaut, entra en esta tabla con el ADR que lo introduce; no
se inventa en el repositorio. El sufijo `-deployment` es el que exige Quarkus. La extensión de
hoy es una librería con índice Jandex y no tiene módulo de deployment.

**4. Un repositorio con varios artefactos nombra a la familia.** Cada módulo sigue las reglas 2
y 3, y el `<nombre>` del repositorio nombra el conjunto, incluido el proyecto raíz que no se
publica. `nova-java-08-commons-spring-boot-starter` publica `nova-api-standard-spring-boot-starter`
y `nova-mask-spring-boot-starter`, y su raíz se llama `nova-commons-spring-boot-starter`.
`nova-java-13-bom` ya lo hace con sus cuatro BOM.

**5. Lo que se deriva del artefacto lleva su mismo nombre.**

| Dónde | Valor |
|---|---|
| `rootProject.name` en Gradle, o `<artifactId>` en Maven | el `artifactId` |
| `component` de release-please | el `artifactId` |
| `package-name` de release-please | `<groupId>:<artifactId>` |
| clave de SonarCloud | `ahincho_<artifactId>` |
| URL del registro | `https://maven.pkg.github.com/ahincho/<repositorio>` |

La URL del registro lleva el nombre del repositorio, y es el único lugar donde aparece el número:
GitHub Packages no valida ese segmento al leer (ADR-038). En un repositorio con varios
artefactos, el componente y la clave de SonarCloud toman el nombre de la familia.

**Cambiar el componente de release-please no pierde el historial.** Todos los repositorios Java
de Nova tienen `include-component-in-tag: false`, y con esa opción release-please busca la
última versión comparando el manifest con los tags `vX.Y.Z`, sin mirar el componente:
`getComponent()` devuelve vacío en ese caso (`src/strategies/base.ts`, y `buildPullRequests` y
`backfillReleasesFromTags` en `src/manifest.ts`). Lo único que cambia es la rama del PR de
release. El PR abierto con la rama vieja se cierra a mano. Esto corrige la advertencia de la
regla 4 de ADR-038, que suponía que los tags llevaban el componente.

**6. Una publicación no termina en verde si lo publicado no se descarga.** Después de `publish`,
el workflow descarga el `.pom` y el `.jar` de la versión que acaba de subir, reintentando hasta
cinco minutos, y falla si no aparecen. Antes de publicar no pide esas rutas, para no sembrar un
404 en caché. Esta regla reemplaza a «mantener los nombres cortos» como defensa contra el
fantasma: si algún día un nombre lo provoca, el run lo dice ese mismo día, en lugar de que un
consumidor lo descubra semanas después. Se implementa como la acción compuesta
`nova-verify-publication` de `nova-shared-02-pipelines`, y cada workflow de publicación la llama
justo después de publicar.

**7. En npm, la tecnología va en el nombre.** npm no tiene `groupId`, así que el nombre la
lleva: `@ahincho/nova-<tecnología>[-<rol>]`. El monorepo ya lo hace (`@ahincho/nova-nestjs`,
`@ahincho/nova-nestjs-toolchain`, `@ahincho/nova-nestjs-schematics`). Un repositorio que publica
un solo paquete lo llama `nova-<tecnología>-<nombre>`, así que `nova-nestjs-02-profile-utp`
publica `@ahincho/nova-nestjs-profile-utp`. El scope cambia con la organización, en un ADR
aparte; lo que va después del scope no cambia.

**8. Los ejemplos se llaman como su repositorio, sin el número.** No se publican. Su
`artifactId`, o el `name` de su `package.json`, es `nova-example-<tecnología>-<nombre>`, y en
Java su `groupId` es `pe.edu.nova.java.examples`. Un ejemplo es lo que un equipo copia para
empezar, así que también lleva el paquete Java de ADR-004. La única excepción es el ejemplo que
es la salida de un generador (`nova-example-08-nestjs-generated`): conserva el nombre que se le
pasó al generador, `campus-acl`, porque renombrarlo lo haría dejar de ser lo que el generador
produce.

**Fuera de alcance.** Los `groupId` no cambian: ADR-004 sigue vigente, y `starters` nombra los
niveles 2 y 3 de cualquier framework, Quarkus incluido. Los paquetes Java existentes tampoco se
mueven, porque moverlos rompe cada `import` de cada consumidor.

### La tabla

**Fase 1: la extensión de Quarkus**, que hoy está rota.

| Repositorio | Hoy | Estándar | Primera versión | Consumidores |
|---|---|---|---|---|
| `nova-java-10` | `nova-quarkus-api-ext` | `nova-api-standard-quarkus-extension` | 2.0.1 | `nova-quarkus-bom`, ejemplos 04 y 06 |

**Fase 2: los starters de Spring Boot**, que funcionan y solo se alinean.

| Repositorio | Hoy | Estándar | Primera versión | Consumidores |
|---|---|---|---|---|
| `nova-java-08` | `nova-api-standard-starter` | `nova-api-standard-spring-boot-starter` | 2.0.0 | `nova-java-12`, `nova-spring-boot-bom`, `nova-java-16` |
| `nova-java-08` | `nova-mask-starter` | `nova-mask-spring-boot-starter` | 2.0.0 | `nova-java-12`, `nova-spring-boot-bom`, `nova-java-16` |
| `nova-java-08` (raíz, no se publica) | `nova-commons-starter` | `nova-commons-spring-boot-starter` | | |
| `nova-java-09` | `nova-observability-starter` | `nova-observability-spring-boot-starter` | 2.0.0 | `nova-spring-boot-bom`, ejemplos 01, 02 y 03 |

**Fase 3: nombres derivados y ejemplos**, que ningún consumidor usa como dependencia.

| Dónde | Hoy | Estándar |
|---|---|---|
| componente de release-please, `nova-java-12` | `nova-starter` | `nova-spring-boot-starter` |
| componente de release-please, `nova-java-16` | `nova-java-spring-boot-gradle-plugin` | `nova-spring-boot-gradle-plugin` |
| clave de SonarCloud, `nova-java-08` | `ahincho_commons-starter` | `ahincho_nova-commons-spring-boot-starter` |
| clave de SonarCloud, `nova-java-09` | `ahincho_nova-observability-starter` | `ahincho_nova-observability-spring-boot-starter` |
| clave de SonarCloud, `nova-java-12` | `ahincho_nova-starter` | `ahincho_nova-spring-boot-starter` |
| clave de SonarCloud, `nova-java-16` | `ahincho_nova-java-spring-boot-gradle-plugin` | `ahincho_nova-spring-boot-gradle-plugin` |
| clave de SonarCloud, ejemplo 04 | `ahincho_nova-java-quarkus-example` | `ahincho_nova-example-quarkus-reference` |
| paquete npm, `nova-nestjs-02` (no publicado) | `@ahincho/nova-profile-utp` | `@ahincho/nova-nestjs-profile-utp` |
| ejemplo 01 | `pe.edu.nova.java.examples:nova-example` | `pe.edu.nova.java.examples:nova-example-spring-boot-reference` |
| ejemplo 02 | `com.nova.generics:ms-course` | `pe.edu.nova.java.examples:nova-example-spring-boot-ms-course` |
| ejemplo 03 | `com.nova.generics:ms-forum` | `pe.edu.nova.java.examples:nova-example-spring-boot-ms-forum` |
| ejemplo 04 | `pe.edu.nova.java.examples:nova-java-quarkus-example` | `pe.edu.nova.java.examples:nova-example-quarkus-reference` |
| ejemplo 05 | `com.nova.generics:ms-course-quarkus` | `pe.edu.nova.java.examples:nova-example-quarkus-ms-course` |
| ejemplo 06 | `pe.edu.nova:code-with-nova` | `pe.edu.nova.java.examples:nova-example-quarkus-code-with-nova` |
| ejemplo 07 | `nova-nestjs-example` | `nova-example-nestjs-reference` |

Los ejemplos 02, 03 y 05 mueven además su paquete Java de `com.nova.generics` a
`pe.edu.nova.java.examples`, por la regla 8.

## Migración

### La receta automatizada

`ops/rename-artifacts.py` lee `ops/artifact-renames.json`, que lleva por cada artefacto la
coordenada vieja, la nueva y la primera versión con el nombre nuevo, y reescribe un consumidor:

- en Gradle, `"<groupId>:<artifactId viejo>:<versión>"`;
- en Maven, el `<artifactId>` dentro de un bloque cuyo `<groupId>` es de Nova;
- en Quarkus, `quarkus.index-dependency.*.artifact-id`;
- las menciones en los README y en la documentación.

Si la coordenada lleva una versión explícita menor que la primera del nombre nuevo, la sube a
esa versión, porque la vieja no existe con el nombre nuevo. Tiene las mismas guardas que
`rename-repos.py`: no toca los CHANGELOG, los lockfiles, los ADR ni los documentos de historia
fechados; conserva el BOM y los fines de línea; es idempotente, y sin `--apply` solo informa.
`--phase` limita la receta a las filas de una fase, y conviene pasarlo siempre: un consumidor
migra recién cuando el nombre nuevo está publicado. Con `--check` recorre los clones y lista lo
que no cumple las reglas 1 a 5, 7 y 8. Al cerrar cada fase, esa lista queda vacía para las filas
de la fase. El día que se aceptó listaba 33 incumplimientos, los mismos de la tabla.

### El orden, por artefacto

1. **En el repositorio del artefacto**: el nombre en los archivos de la regla 5, un
   `Release-As` con la primera versión de la tabla y la verificación de la regla 6 en su
   workflow de publicación. Va por pull request, para que el CI compile con el nombre nuevo antes
   de que exista una versión que lo lleve.
2. **La publicación**: release-please abre el PR de release. Al mergearlo se crean el tag y la
   publicación, y la verificación confirma que se descarga.
3. **Cada consumidor**: la receta, el CI en verde y el push.
4. **El PR de release viejo**, abierto con la rama del componente anterior, se cierra.

### Las versiones

Cambiar la coordenada es incompatible para el consumidor, así que se sube la versión mayor
(ADR-018). Los starters pasan de 1.0.1 a 2.0.0. La extensión va a 2.0.1 y no a 2.0.0 porque la
2.0.0 ya existe en el registro desde julio, una versión publicada no se sobrescribe, y publicar
por debajo de ella dejaría a la versión vieja como la más reciente.

Los BOM reflejan los nombres nuevos con una versión mayor (ADR-018, sección 5). Como la fase 2 va
enseguida de la fase 1, la familia `nova-bom` publica una sola versión, 2.0.0, que cubre las dos y
se lleva de paso las versiones que se publicaron entretanto.

### Lo que hace Angel

**La limpieza del registro, si la quiere.** Las dos versiones de julio de
`nova-api-standard-quarkus-extension`, el tag `v1.1.4` y los releases en borrador `v1.1.0` y
`v1.1.1` quedaron de la época del fantasma. Nada depende de ellos. Borrarlos es decisión suya y
no cambia la versión elegida.

Las claves de SonarCloud no piden ningún paso en SonarCloud: como no hay proyectos de Nova, el
cambio de la fase 3 es solo texto en los `ci.yml`. Activar el análisis, con sus proyectos y el
secreto `NOVA_SONAR_TOKEN`, es un trabajo aparte; cuando llegue, las claves ya van a estar
alineadas.

## Alternativas descartadas

**Mantener `nova-quarkus-api-ext`.** Su única razón era un límite de longitud que la evidencia
de arriba no sostiene, y rompe las reglas 2 y 3.

**Seguir la convención de Quarkus, `nova-quarkus-<capacidad>`.** Pone el framework delante, que
es justamente lo que se quita, y los conectores de Spring Boot y de Quarkus de una misma
capacidad dejarían de quedar juntos.

**Llevar la tecnología al `artifactId`** (`nova-java-api-standard`). El `groupId` ya la dice, y
era la forma de los nombres viejos de repositorio.

**Callar el framework en los starters**, como hoy (`nova-api-standard-starter`). Funciona
mientras hay un solo framework. Con Quarkus y Micronaut, un `-starter` sin framework no dice para
cuál es, y la sección 11.8.2 de [`java/06`](../../java/06-semantic-versioning-en-java.md) ya tuvo
que devolverles `spring-boot` a los nombres de repositorio por la misma razón.

**Cambiar los `groupId`** por uno neutral al framework. Es incompatible para cada consumidor y
cada paquete Java, sin ganancia: ADR-004 ya usa `starters` para los niveles 2 y 3 de cualquier
framework.

**Un POM de relocalización.** Gradle no lo trata como una redirección, como se explica arriba.

**Borrar las versiones de julio y republicar desde 1.x.** Una versión publicada no se reescribe,
y no se gana nada frente a 2.0.1.

## Preguntas abiertas

1. ~~**¿La fase 2 va enseguida o cuando haga falta?**~~ Resuelta el 2026-09-27: va enseguida de
   la fase 1, y la fase 3 a medida que se toque cada repositorio.
2. **La causa real del fantasma** sigue sin verificar. La regla 6 la hace visible si vuelve. Si
   vuelve, el run, el nombre y su longitud se anotan aquí.

## Consecuencias

### Positivas

- De cualquier artefacto se llega a su repositorio, y al revés, sin consultar una tabla.
- Los conectores de una capacidad quedan juntos y dicen para qué framework son.
- El build, release-please y SonarCloud usan el mismo nombre, así que hay un solo nombre que
  acertar.
- Una publicación fantasma deja de pasar en silencio.

### Negativas

- Cambian cuatro coordenadas publicadas, cada una con su versión mayor, y sus consumidores
  migran con la receta.
- Los nombres se alargan: el más largo es `nova-observability-spring-boot-starter`, con 38
  caracteres.
- Los ejemplos 02, 03 y 05 mueven su paquete Java.

## Referencias

- ADR-001, ADR-004, ADR-018, ADR-025 y ADR-038.
- [`java/07-quarkus-analisis-adopcion.md`](../../java/07-quarkus-analisis-adopcion.md) §8: el
  diagnóstico de julio que este ADR revisa.
- [`java/06-semantic-versioning-en-java.md`](../../java/06-semantic-versioning-en-java.md)
  §11.8.2: `spring-boot` devuelto a los nombres de repositorio.
- Spring Boot, *Creating Your Own Starter*, sección *Naming*.
- [gradle/gradle#1256](https://github.com/gradle/gradle/issues/1256) y
  [dependabot-core#1947](https://github.com/dependabot/dependabot-core/issues/1947).
- release-please: `src/strategies/base.ts` (`getComponent`) y `src/manifest.ts`
  (`buildPullRequests`, `backfillReleasesFromTags`).
