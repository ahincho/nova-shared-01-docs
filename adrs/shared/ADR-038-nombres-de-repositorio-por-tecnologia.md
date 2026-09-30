# ADR-038: Nombres de Repositorio por Tecnología y Número

## Estado

Aceptada (2026-09-27), con una enmienda del mismo día: los ejemplos tienen su propia categoría.
La migración se ejecuta repositorio por repositorio.
**Scope:** `shared` (Java + NestJS)
**Receta de migración:** [`ops/rename-repos.py`](../../ops/rename-repos.py), con el mapa de
nombres en [`ops/repo-renames.json`](../../ops/repo-renames.json).

## Fecha

2026-09-27

## Contexto

Nova tiene 29 repositorios activos bajo `ahincho`, en una cuenta que tiene unos 170. El nombre
agrupa por tecnología solo a medias: `nova-java-*` y `nova-nestjs-*` se ordenan juntos, pero
`nova-bom`, `nova-devops`, `nova-docs`, `nova-infrastructure`, `nova-profile-utp` y
`ms-course-quarkus` no dicen a qué tecnología pertenecen, y ningún nombre da un orden de lectura.

El workspace de A303 numera sus repositorios, y el número funciona como nombre corto: se habla
de «el 36» sin decir el resto. Pero ahí el número llevaba además la categoría (`01–12` frontend,
`13–39` backend), y cuando los rangos se llenaron llegaron `40` frontend, `41` backend, `42` una
librería y `43` una herramienta. Hoy el número de A303 dice el orden de llegada, no la capa.

Reservar bloques en Nova tendría el mismo destino, porque la plataforma va a seguir sumando
componentes: el BOM y el parent separados de Spring Boot, la plataforma de Quarkus, el adaptador
de observabilidad de ADR-032, el generador de servicios. Ningún rango sabe de antemano cuántos
va a recibir.

### Lo que un renombrado rompe, medido

Se contaron las referencias en los 29 clones antes de decidir.

| Referencia | Cantidad | Después de renombrar |
|---|---|---|
| `uses:` a actions y workflows de `nova-devops` | 147, en 20 repos | **se rompe en el acto** |
| URLs `maven.pkg.github.com/ahincho/<repo>` | 51 | no se rompe |
| enlaces web y remotos de git | el resto | redirigen solos |

**El único corte real es `nova-devops`.** La documentación de GitHub dice que no redirige las
llamadas a una action de un repositorio renombrado: el workflow falla con `repository not found`.
Esos 147 `uses:` son todo el CI de Java.

**GitHub Packages no valida el segmento del repositorio al leer.** Se verificó pidiendo el
`maven-metadata.xml` de `nova-date-utils` con el nombre real, con el nombre nuevo, con un
repositorio que no existe y con `*`: las cuatro respuestas fueron 200. Un consumidor Maven con
la URL vieja sigue resolviendo.

Los enlaces web y los remotos de git redirigen mientras nadie cree un repositorio con el nombre
viejo. Si alguien lo hace, las redirecciones de ese nombre dejan de funcionar.

## Decisión

**Los repositorios se llaman `nova-<tecnología>-<NN>-<nombre>`.**

```
nova-shared-01-docs
nova-java-01-api-standard
nova-java-10-api-standard-quarkus-extension
nova-nestjs-01-platform
```

Cuatro reglas lo sostienen.

**1. La categoría vive en una palabra, no en el número.** La palabra es la tecnología: `shared`,
`java`, `nestjs`. Una palabra no se llena, así que crear componentes no obliga a reservar nada.
`shared` es la misma palabra que usan los scopes de los ADR.

La tecnología es `java` y no `spring-boot` o `quarkus`, porque las librerías puras del nivel 1
de ADR-001 sirven a los dos frameworks y separar por framework obligaría a elegirles un lado. El
framework sigue en el nombre, como hoy: `nova-java-10-api-standard-quarkus-extension`.

**2. El número es un contador por tecnología, y no promete nada más que orden.** La primera
numeración sigue los niveles de ADR-001 para que la lista se lea de las librerías a las
herramientas, con los ejemplos al final. A partir de ahí cada repositorio nuevo toma el siguiente
número de su tecnología, y la posición deja de indicar el nivel. Si se intentara conservar el
nivel en la posición, se volvería a reservar sin decirlo. Con dos dígitos caben 99 por tecnología.

**3. Un número se asigna una sola vez**: no se reutiliza ni se renumera, igual que el número de
un ADR. Los huecos no molestan. Un nombre viejo tampoco se vuelve a usar nunca, por lo dicho
arriba sobre las redirecciones.

**4. El número va solo en el nombre del repositorio.** No cambian el `groupId`, el `artifactId`,
el paquete npm, el paquete Java, el componente de release-please ni la clave de SonarCloud.
Cambiar las coordenadas sería incompatible para cada consumidor, y cambiar el componente le
haría perder a release-please el historial de tags.

### La tabla

| Tecnología | # | Hoy | Nuevo | Nivel ADR-001 o rol |
|---|---|---|---|---|
| shared | 01 | `nova-docs` | `nova-shared-01-docs` | contrato y decisiones |
| shared | 02 | `nova-devops` | `nova-shared-02-pipelines` | pipelines reutilizables |
| shared | 03 | `nova-infrastructure` | `nova-shared-03-infrastructure` | stack de observabilidad |
| java | 01 | `nova-java-api-standard` | `nova-java-01-api-standard` | 1, librería pura |
| java | 02 | `nova-java-date-utils` | `nova-java-02-date-utils` | 1 |
| java | 03 | `nova-java-mapper-utils` | `nova-java-03-mapper-utils` | 1 |
| java | 04 | `nova-java-mask-utils` | `nova-java-04-mask-utils` | 1 |
| java | 05 | `nova-java-observability-utils` | `nova-java-05-observability-utils` | 1 |
| java | 06 | `nova-java-keycloak` | `nova-java-06-keycloak` | 1 |
| java | 07 | `nova-java-architecture-rules` | `nova-java-07-architecture-rules` | 1, reglas de ArchUnit |
| java | 08 | `nova-java-commons-spring-boot-starter` | `nova-java-08-commons-spring-boot-starter` | 2, conector |
| java | 09 | `nova-java-observability-spring-boot-starter` | `nova-java-09-observability-spring-boot-starter` | 2 |
| java | 10 | `nova-java-api-standard-quarkus-extension` | `nova-java-10-api-standard-quarkus-extension` | 2 |
| java | 11 | `nova-java-keycloak-quarkus-extension` | `nova-java-11-keycloak-quarkus-extension` | 2 |
| java | 12 | `nova-java-spring-boot-starter` | `nova-java-12-spring-boot-starter` | 3, meta-starter |
| java | 13 | `nova-bom` | `nova-java-13-bom` | 4, BOM |
| java | 14 | `nova-java-spring-boot-parent` | `nova-java-14-spring-boot-parent` | 4, parent |
| java | 15 | `nova-java-quarkus-parent` | `nova-java-15-quarkus-parent` | 4, parent |
| java | 16 | `nova-java-spring-boot-gradle-plugin` | `nova-java-16-spring-boot-gradle-plugin` | 5, tooling |
| java | 17 | `nova-java-spring-boot-archetype` | `nova-java-17-spring-boot-archetype` | 5 |
| java | 18 | `nova-java-quarkus-archetype` | `nova-java-18-quarkus-archetype` | 5 |
| java | 19 | `nova-java-quarkus-template` | `nova-java-19-quarkus-template` | 5 |
| java | 20 | `nova-java-example` | `nova-java-20-example` | ejemplo, Spring Boot |
| java | 21 | `nova-java-quarkus-example` | `nova-java-21-quarkus-example` | ejemplo, Quarkus |
| java | 22 | `ms-course-quarkus` | `nova-java-22-ms-course-quarkus` | instancia |
| nestjs | 01 | `nova-nestjs` | `nova-nestjs-01-platform` | los tres paquetes de ADR-025 |
| nestjs | 02 | `nova-profile-utp` | `nova-nestjs-02-profile-utp` | perfil de organización |
| nestjs | 03 | `nova-nestjs-example` | `nova-nestjs-03-example` | ejemplo |
| nestjs | 04 | `nova-nestjs-generated` | `nova-nestjs-04-generated` | ejemplo generado |

Tres nombres cambian más que el prefijo, y cada uno por una razón:

- **`nova-devops` pasa a `pipelines`.** El repositorio tiene workflows reutilizables y también
  actions compuestas (la más usada, `nova-setup-java`, es una action), así que `workflows`
  nombraría solo la mitad. Va en `shared` aunque hoy solo lo llama Java, porque el ítem 7 del plan
  lo convierte en un producto para los tres stacks.
- **`nova-nestjs` pasa a `platform`.** El monorepo se llama igual que su tecnología, así que
  necesita un nombre después del número.
- **`nova-bom` va en `java`.** Sus tres BOM son de Maven (Spring Boot, Quarkus y Micronaut),
  aunque su descripción en GitHub dice que también cubre NestJS.

Quedan fuera los cuatro repositorios NestJS archivados por ADR-025. Son historia, conservan su
nombre, y ese nombre tampoco se reutiliza.

Los cinco ejemplos de esta tabla (`java` 20 a 22, `nestjs` 03 y 04) se renombraron otra vez el
mismo día, por la enmienda que sigue.

### Enmienda (2026-09-27): los ejemplos tienen su propia categoría

Angel pidió que los ejemplos lleven la palabra `example` en el nombre, para distinguirlos a
primera vista de los componentes de la plataforma. Un ejemplo no se publica ni lo consume nadie:
existe para mostrar cómo se usa lo que sí se publica, y mezclarlo en el contador de su tecnología
lo hacía parecer un componente más.

**Los ejemplos se llaman `nova-example-<NN>-<tecnología>-<nombre>`.** La categoría es `example`,
con un contador propio para todos los stacks, y la tecnología pasa después del número porque ya
no es la categoría. Las cuatro reglas de arriba se aplican igual: el número solo da orden, se
asigna una vez y no va en ninguna coordenada.

| # | Antes | Ahora |
|---|---|---|
| 01 | `nova-java-20-example` | `nova-example-01-spring-boot-reference` |
| 02 | `instances/ms-course` (sin repositorio) | `nova-example-02-spring-boot-ms-course` |
| 03 | `instances/ms-forum` (sin repositorio) | `nova-example-03-spring-boot-ms-forum` |
| 04 | `nova-java-21-quarkus-example` | `nova-example-04-quarkus-reference` |
| 05 | `nova-java-22-ms-course-quarkus` | `nova-example-05-quarkus-ms-course` |
| 06 | `examples/code-with-nova` (sin repositorio) | `nova-example-06-quarkus-code-with-nova` |
| 07 | `nova-nestjs-03-example` | `nova-example-07-nestjs-reference` |
| 08 | `nova-nestjs-04-generated` | `nova-example-08-nestjs-generated` |

Dentro de cada tecnología va primero el ejemplo de referencia, el que muestra el uso completo, y
después los demás por antigüedad. Los tres sin repositorio existían solo como carpetas locales y
se publican con esta enmienda.

**Los números `java` 20, 21 y 22 y `nestjs` 03 y 04 quedan retirados.** No se reutilizan, así que
el próximo componente Java es el 23 y el próximo NestJS es el 05, aunque haya un hueco. La
tecnología usa `nestjs`, igual que los repositorios de la plataforma.

### Enmienda (2026-09-29): un producto lleva su nombre

Un producto construido sobre Nova, con varios servicios que se entienden entre sí, no es un
ejemplo. Angel pidió que sus repositorios lleven el nombre del producto en el lugar de `example`:
**`nova-<producto>-<NN>-<tecnología>-<nombre>`**, con un contador propio por producto. El primero
es Plaza, en [ADR-043](ADR-043-plaza-la-plataforma-de-compras.md): `nova-plaza-01-shared-platform`,
`nova-plaza-02-nestjs-bff` y los que siguen.

## Migración

### La receta automatizada

`ops/rename-repos.py` recorre un repositorio o una carpeta con varios. Por defecto simula, con
`--apply` escribe, y con `--remotes` actualiza además el `origin` de cada clon. Es idempotente:
correrla dos veces no cambia nada la segunda.

**Solo reescribe un nombre cuando va anclado al dueño**, como `ahincho/<repo>` en un `uses:`, en
una URL de GitHub o de GitHub Packages, en un `scm` o en un remoto. Un nombre suelto puede ser
otra cosa: `nova-bom` es a la vez el repositorio y el `artifactId` del BOM. Por eso los nombres
sueltos solo se reescriben en los cinco scripts que enumeran repositorios, listados en
`bareNameFiles`.

**Nunca toca un paquete npm.** Todo lo que empieza con `@ahincho/` es un paquete
(`@ahincho/nova-nestjs` coincide con el nombre de su repositorio). La receta compara los paquetes
de cada archivo antes y después, y si alguno cambiaría, no escribe ese archivo y termina con error.

**No reescribe la historia.** Deja fuera los CHANGELOG, los lockfiles, los ADR y los análisis
fechados de nova-docs (`java/NN-*.md`, `nest/NN-*.md`). Un análisis del 2026-07-09 que dice
«commit `98da16b` en `ahincho/nova-devops`» cuenta lo que pasó con el nombre de entonces;
reescribirlo cambiaría la historia en vez de corregirla. La tabla de este ADR es la clave para
leerlos.

Aplicada sobre los 29 clones: **409 referencias en 136 archivos**, sin tocar ningún `groupId` o
`artifactId`, paquete npm, clave de SonarCloud ni configuración de release-please.

### Lo que queda a mano

- **Unas 170 menciones sueltas** en prosa y comentarios: 87 en `.md`, 48 en comentarios de YAML y
  el resto en comentarios de `.kts`, `.java` y `.xml`. No rompen nada. Cada una la tiene que
  revisar una persona, porque un nombre suelto puede ser el repositorio o el artefacto. Otras 14
  menciones son coordenadas o nombres de proyecto y no se tocan.
- **Las descripciones de los repositorios en GitHub.** La de `nova-bom` está mal (dice que cubre
  NestJS) y la de `nova-nestjs` menciona un scope `@nova-platform` que no existe.
- **Revisar SonarCloud después del renombrado.** Las claves no cambian, pero falta comprobar que
  la decoración de los pull requests sigue enlazada al repositorio.

### Cómo se ejecuta sin perder un commit

La condición de la migración es que no se pierda ningún commit, y se ejecuta repositorio por
repositorio. Antes de tocar el primero:

- **Se rescata lo que solo existía en los clones anteriores.** 18 commits en ramas locales que
  nunca llegaron a GitHub, un stash y los cambios sin commit de 8 repositorios quedaron como ramas
  `rescate/*` en los clones nuevos, verificado commit por commit.
- **Se toma una foto de todas las refs remotas** de los 29 repositorios (ramas, tags y refs de
  pull requests, cada una con su SHA).
- **Los commits salen a nombre de Angel**, con `ahincho@unsa.edu.pe`, fijado en cada clon. Varios
  clones anteriores tenían `Nova Bot <nova@local>`, una identidad que GitHub no enlaza a ninguna
  cuenta.

Después, en cada repositorio:

1. Renombrarlo en GitHub con `gh repo rename`.
2. Subir sus commits a `main` como fast-forward. Nunca un force-push, y nunca un rebase o un squash
   sobre commits que ya existen.
3. Comparar sus refs contra la foto: todas siguen existiendo con el mismo SHA, y la `main` nueva
   desciende de la anterior.
4. Apuntar el clon local al nombre nuevo (`--remotes`).

**Las ramas en curso no se tocan.** `feat/platform-next` en el monorepo NestJS y su ejemplo, y
`docs/adr-034-037` en nova-docs, conservan sus commits. Cuando se integren, se mergea `main` en
ellas en vez de rebasarlas, y la receta, que es idempotente, se corre también sobre esas ramas.

**El orden entre repositorios importa poco, porque todo redirige salvo los `uses:`.** Primero van
los nueve repositorios que no llaman a pipelines, después `nova-shared-02-pipelines` y enseguida sus
19 llamadores, así el intervalo en que un llamador apunta a un nombre que ya no existe es el más
corto posible. Los `uses:` y lo que falle en CI se revisan al terminar la migración: CI en los 20
repositorios que usan pipelines, una resolución Maven desde un consumidor y la descarga del espejo
de NVD.

## Alternativas descartadas

**Bloques de números reservados por tecnología** (`00–09` transversal, `10–49` Java, `50–59`
NestJS). Fue la primera propuesta. Se descarta porque un bloque se llena y, desde ese momento, el
número deja de decir lo que se le reservó. A303 muestra cómo termina.

**Un contador global en vez de uno por tecnología.** Da un nombre corto único para todo, pero con
dos dígitos se acaba a los 99 repositorios en total, y el número de un repositorio Java pasaría a
depender de cuántos NestJS se crearon antes.

**La tecnología como framework** (`nova-spring-boot-*`, `nova-quarkus-*`). Las librerías puras no
tienen lado, y son siete.

**Numerar solo las carpetas locales.** Cuesta cero y no rompe nada, pero no ordena la vista en
GitHub, que es donde se lee el portafolio.

**Una organización de GitHub propia para Nova.** Separaría la plataforma de los repositorios
académicos, que es un problema real. Pero cambia el dueño, y con él el scope npm `@ahincho`, las
URLs de GitHub Packages y cada `uses:`. Es incompatible para todos los consumidores a la vez, y
un renombrado no lo es.

**Topics.** `nova-platform` ya existe y sirve para filtrar, pero no ordena.

## Preguntas abiertas

**1. Qué pasa con los consumidores de `nova-devops` que no conocemos.** El repositorio es
público, y cualquiera que llame a sus actions queda roto sin aviso. Una opción es dejar un
repositorio `nova-devops` cuyas actions deleguen en el nuevo, para que esos llamadores sigan
funcionando. Pero eso contradice la regla 3: al crear un repositorio con el nombre viejo se
pierden las redirecciones web y de git de ese nombre. Mantener los llamadores externos cuesta
perder las redirecciones, y no hay forma de tener las dos cosas.

**2. `nest` o `nestjs`.** Los repositorios dicen `nestjs` y las carpetas de ADR dicen `nest`. Son
dos palabras para la misma tecnología. Renombrar `adrs/nest` rompe los enlaces relativos entre
ADR, así que por ahora se tolera la diferencia.

**3. Si los ejemplos deberían tener su propio contador.** Resuelta por la enmienda: sí, con la
categoría `example`.

## Consecuencias

### Positivas

- La lista se lee por tecnología y, dentro de cada una, en el orden de los niveles de ADR-001.
- Cada repositorio tiene un nombre corto estable (`java-07`), como el que ya se usa en A303.
- Crear un componente no exige planificar cuántos van a venir.
- La receta sirve también como migración para cualquier consumidor externo (invariante 4).

### Negativas

- **29 renombrados y 136 archivos en un solo movimiento**, con un intervalo en que el CI de Java
  puede fallar.
- **Los consumidores externos de `nova-devops` se rompen sin aviso**, salvo que se resuelva la
  pregunta 1.
- **Unas 170 menciones quedan para revisión manual**, y mientras no se revisen conviven dos
  nombres para el mismo repositorio.
- Los nombres se alargan. `nova-java-09-observability-spring-boot-starter` tiene 46 caracteres.
- Los análisis fechados conservan los nombres viejos a propósito, así que un lector de julio ve
  nombres que ya no existen y tiene que usar la tabla de este ADR para traducirlos.

## Referencias

- [ADR-001: Arquitectura del Meta-Framework en 5 Niveles](ADR-001-arquitectura-meta-framework-cinco-niveles.md)
- [ADR-005: Multi-Repo con BOM Coordinador](../java/ADR-005-multi-repo-con-bom-coordinador.md)
- [ADR-011: Composite Actions y Reusable Workflows](ADR-011-composite-actions-y-reusable-workflows.md)
- [ADR-025: Tres Paquetes NestJS en Lugar de Once](../nest/ADR-025-tres-paquetes-en-lugar-de-once.md)
- GitHub Docs, *Renaming a repository*
