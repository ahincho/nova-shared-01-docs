# ADR-044: El Toolchain de Java: Plugins de Convención de Gradle

## Estado

Aceptada (2026-09-29). Angel pidió para Java algo equivalente al toolchain de NestJS, con Spotless,
Checkstyle y las mejores prácticas, y que el toolchain valide también los mensajes de commit.
**Scope:** `java`. NestJS ya tiene el suyo, `@ahincho/nova-nestjs-toolchain`.
**Aplica:** [ADR-041](ADR-041-un-repositorio-por-capacidad.md) para la forma del repositorio y
[ADR-006](../shared/ADR-006-conventional-commits-y-semantic-versioning.md) para la convención de
commits.
**Reemplaza, cuando se complete la migración:** el repositorio `nova-java-16-spring-boot-gradle-plugin`.

## Fecha

2026-09-29

## Contexto

Cada repositorio Java arma su propio tooling, y ya se desvió. Medido sobre los 17 repositorios con
`build.gradle.kts`:

- **Checkstyle está copiado en 15 repositorios, en 4 versiones distintas.** Las reglas de estilo están
  en `warning`, así que nunca rompen el build.
- **El bloque de OWASP está copiado en 11.** El filtro del archivo de supresiones tiene un defecto en
  Java 25 (`File("").exists()` es verdadero), y hay que arreglarlo en cada copia.
- **JaCoCo está en 7 de los 17,** y ninguno exige un mínimo.
- **Ningún repositorio formatea el código.**
- **Los mensajes de commit se validan con Node:** 18 repositorios llevan `package.json`,
  `commitlint.config.js` y `lefthook.yml`. Un repositorio Java necesita Node para aceptar un commit,
  y la validación depende de que cada persona haya corrido `npm install`. **El CI no la repite en
  ningún repositorio.** Con merges que conservan cada commit, cada uno llega a `main` y release-please
  lo lee, así que un commit mal escrito termina en el changelog.

NestJS resolvió lo mismo con un paquete que trae las herramientas, sus configuraciones y un comando
`nova`. Sus decisiones se sostienen en Java; su forma no, porque Gradle y su wrapper ya son el comando
que existe en cada repositorio.

## Decisión

**Un repositorio de capacidad, `nova-java-24-gradle-toolchain`, publica plugins de convención de
Gradle que traen las herramientas en versiones fijas, sus configuraciones y un contrato de tareas.
Un repositorio no nombra ninguna herramienta ni declara su versión.**

### Los plugins

| Plugin | Para quién | Qué aplica |
|---|---|---|
| `pe.edu.nova.java.quality` | todo proyecto Java | compilación, formato, Checkstyle, pruebas, cobertura, validación de commits y hooks de git |
| `pe.edu.nova.java.library` | librerías y starters de la plataforma | `quality`, más `java-library`, jars de fuentes y javadoc, publicación, POM, OWASP y SBOM |
| `pe.edu.nova.java.spring-boot` | servicios Spring Boot | `quality`, más Spring Boot, los starters de Nova, OWASP, SBOM y la imagen |
| `pe.edu.nova.java.quarkus` | servicios Quarkus | `quality`, más Quarkus, la extensión de Nova, OWASP, SBOM y la imagen |

`pe.edu.nova.java.spring-boot` **conserva su id**, así que el consumidor del plugin del repo 16 solo
sube la versión. Los plugins se publican con el grupo `pe.edu.nova.java`, como el repo 16.

### Las tareas

| Tarea | Qué corre |
|---|---|
| `novaFormat` | aplica el formato |
| `novaVerify` | formato, Checkstyle, pruebas, cobertura y reglas de arquitectura; es lo que corre el CI |
| `novaCommitLint` | valida los mensajes de commit de un rango o de un archivo |
| `novaInstallGitHooks` | instala el hook `commit-msg` |
| `novaSecurity` | OWASP y el SBOM; va aparte porque tarda |
| `novaDocker` | construye la imagen con el Dockerfile de la plataforma |
| `novaDockerEject` | escribe ese Dockerfile en el repositorio, para un pipeline que lo exige |

`check` depende de `novaVerify`, así que `./gradlew build` verifica lo mismo que el CI.

### Una herramienta, un papel

- **Spotless formatea** con `palantir-java-format`: 4 espacios y 120 columnas, como ya está escrito el
  código de Nova. También formatea los `*.gradle.kts` y quita espacios al final de línea en los demás
  archivos de texto.
- **Checkstyle queda solo para defectos**, en `error` y con `maxWarnings = 0`. Lo que es estilo lo
  resuelve el formateador, que además lo corrige.
- **javac compila con `-Xlint:all -Werror`,** `-parameters` y `--release 25`.
- **ArchUnit cuida las capas**, como una prueba más, con `nova-architecture-rules`.
- **JaCoCo exige el 80 % de líneas**, el mismo número que el preset de Vitest en NestJS, para que la
  cifra signifique lo mismo en los dos stacks. Una clase `main` y las generadas quedan fuera.

### Lo que no se puede perder sin darse cuenta

Es la razón de fondo, igual que `--type-aware` en NestJS: una bandera que falta no avisa, deja el
análisis a medias y en verde.

- `maxWarnings = 0` en Checkstyle y `-Werror` en javac.
- La verificación de cobertura cuelga de `check`, no de una tarea que haya que acordarse de llamar.
- Las pruebas usan JUnit Platform, y Gradle falla si no encuentra ninguna.
- Los archivos generados son reproducibles: sin fechas y en orden fijo.

### Todo se puede extender

Una extensión `nova { }` permite sumar reglas de Checkstyle, excluir clases de la cobertura o subir el
mínimo, sin perder lo de la plataforma. Bajar el mínimo o apagar una verificación también se puede,
pero queda escrito en el `build.gradle.kts` del repositorio, a la vista de quien revisa.

### Las versiones

El plugin fija las versiones de Spotless, `palantir-java-format`, Checkstyle, JaCoCo, OWASP y
CycloneDX, y trae como plataforma las de JUnit, AssertJ, Testcontainers, ArchUnit y
`nova-architecture-rules`. Un servicio escribe
`testImplementation("org.testcontainers:testcontainers-postgresql")`, sin versión.

Las restricciones por CVE que hoy repite cada repositorio también viven en el plugin.

### Los commits

`novaCommitLint` valida la especificación de Conventional Commits con las mismas reglas que
`@commitlint/config-conventional`, que es lo que usan hoy los 18 repositorios:

- el tipo es uno de `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`,
  `style` y `test`, en minúscula;
- el alcance es opcional, entre paréntesis;
- `!` o un pie `BREAKING CHANGE:` marcan un cambio que rompe;
- la descripción no va vacía ni termina en punto, y el encabezado no pasa de 100 caracteres;
- entre el encabezado y el cuerpo va una línea en blanco.

Se saltan los commits de merge que genera GitHub, porque no son de nadie.

**Corre en dos lugares, con el mismo código:**

- **Al hacer el commit,** por el hook `commit-msg`. El hook no llama a Gradle, que tarda segundos en
  arrancar: ejecuta con `java` un jar chico que `novaInstallGitHooks` copia en `.git/hooks`. El hook se
  instala solo en el primer build local, y nunca en CI.
- **En el CI,** sobre todos los commits del PR: `./gradlew novaCommitLint --from=<base>`. Es la parte
  que hoy no existe, y la que importa, porque el hook se puede saltar con `--no-verify`.

Con eso, **un repositorio Java deja de necesitar Node**: `package.json`, `commitlint.config.js` y
`lefthook.yml` se borran en la migración.

### La imagen

El Dockerfile vive en el plugin, igual que en NestJS
([ADR-027](../nest/ADR-027-imagen-de-contenedor-compartida.md)): JRE 25, un usuario sin privilegios y
el jar por capas, para que una imagen nueva reuse las dependencias de la anterior. **No se copia a
cada repositorio**, porque una copia envejece sin fallar. `novaDockerEject` lo escribe con un
encabezado que dice de dónde salió.

En Java, el build corre fuera de Docker y la imagen solo copia el jar, así que el build de la imagen
no necesita el token del registro.

### El repositorio

Por ADR-041, un repositorio con un módulo por plugin, una sola versión y release-please.
El `.git-blame-ignore-revs` va en cada repositorio que adopta el formato, con el commit `style:` que
lo aplicó, para que `git blame` siga mostrando al autor de cada línea.

## La migración

Un PR por repositorio, en este orden:

1. **Pedidos de Plaza,** con `quality` y `spring-boot`. Es nuevo y no tiene nada que migrar.
2. **`nova-java-23-secrets`**, el primer repositorio de plataforma con `library`.
3. **Los demás repositorios de plataforma,** uno por PR. El primer commit de cada uno es el `style:`
   que aplica el formato, separado del resto para que el diff se pueda revisar.
4. **El catálogo de Plaza,** con `quarkus`.
5. **El repo 16 se archiva** cuando ningún consumidor lo use, con una receta de migración: cambiar la
   versión del plugin y borrar la configuración que el plugin ya trae.

El CI compartido pasa a llamar a `./gradlew novaVerify` y `novaCommitLint`.

## Preguntas abiertas

1. **Error Prone.** Encuentra defectos al compilar, pero hay que medir en Java 25 que no rompa con
   Spring ni con Quarkus, y cuánto alarga el build. Entra solo si la medición lo justifica, como oxlint
   en NestJS.
2. **La validación de commits en NestJS.** Hoy no existe en ningún lado del stack. Lo parejo es un
   `nova commitlint` en el toolchain de NestJS con las mismas reglas.
3. **El nombre de la rama.** Se podría validar también la forma `<tipo>/<descripción>`. Queda fuera
   hasta que haga falta.

## Alternativas descartadas

- **Un comando `nova` aparte para Java.** Sumaría una herramienta que instalar sin quitar ninguna:
  `./gradlew` ya existe en cada repositorio y funciona igual en local y en CI.
- **`google-java-format`.** Usa 2 espacios, y reformatearía cada línea de todos los repositorios.
- **Seguir con commitlint y lefthook sobre Node.** Obliga a instalar Node en un repositorio Java y no
  valida nada en CI.
- **Un hook que llame a Gradle.** Tarda varios segundos en cada commit, y un hook lento se termina
  saltando.
- **Copiar un `build.gradle.kts` base a cada repositorio.** Es lo que hay hoy, y es lo que se desvió.

## Consecuencias

### Positivas

- Un cambio de herramienta o de versión se hace en un lugar y llega con una versión del plugin.
- Los mensajes de commit se validan en CI por primera vez, y con eso el changelog de release-please.
- Los repositorios Java dejan de necesitar Node.
- El mismo número de cobertura y el mismo modelo de imagen en los dos stacks.

### Negativas

- El primer formateo toca casi todas las líneas de cada repositorio. Se mitiga con el commit `style:`
  aparte y `.git-blame-ignore-revs`.
- Checkstyle en `error` puede romper builds que hoy pasan. Cada migración arregla lo que aparezca en el
  mismo PR.
- Es un repositorio más, y todos los demás dependen de él.
