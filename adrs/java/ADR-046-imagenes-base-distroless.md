# ADR-046: Las Imágenes Base: Distroless por Defecto, Docker Hardened como Opción

## Estado

Aceptada (2026-09-29). Angel pidió sumar Docker Hardened Images o distroless a las imágenes de la
plataforma, y aprobó la propuesta: distroless por defecto, Docker Hardened Images como opción y los
CVE como una métrica más. También pidió que las decisiones queden documentadas con sus fuentes, que
están al final.
**Scope:** `java`.
**Enmienda:** la imagen de [ADR-044](ADR-044-toolchain-de-java.md), que pasa de Ubuntu a distroless, y
la base nativa de [ADR-045](ADR-045-imagen-nativa-junto-a-la-jvm.md).
**Suma a:** las métricas de ADR-045, que agregan los CVE de cada imagen.

## Fecha

2026-09-29

## Contexto

Hasta hoy, la imagen de la JVM salía de `eclipse-temurin:25-jre`, sobre Ubuntu, con shell y gestor de
paquetes. La nativa ya usaba `gcr.io/distroless/base-debian12`.

Una imagen de ejecución solo tiene que ejecutar el proceso. La shell y el gestor de paquetes no los
usa la aplicación, pero sí le sirven a quien logra entrar al contenedor, y suman paquetes que hay que
mantener al día.

Hay tres familias de imágenes mínimas:

- **Distroless**, de Google: basada en Debian, sin shell ni gestor de paquetes, y se descarga sin
  cuenta. Publica `java25-debian13` con Temurin 25.
- **Docker Hardened Images**, de Docker: gratis bajo Apache 2.0, con la promesa de cero CVE conocidos,
  SBOM firmado, procedencia SLSA nivel 3 y un usuario sin privilegios por defecto. Pide `docker login
  dhi.io` con una cuenta de Docker.
- **Chainguard:** su plan gratis solo publica la etiqueta `latest`. Fijar una versión pide suscripción,
  aunque se puede fijar por digest.

Un escáner cuenta CVE según lo que declara cada distribución, así que contar no alcanza: importa cuáles
tienen arreglo y cuáles vienen de las librerías de la aplicación. Por eso esta decisión viene con una
medición.

## Decisión

### La imagen final es distroless

| Modo | Etapa de build | Imagen final, por defecto | Opción con Docker Hardened |
|---|---|---|---|
| JVM | `eclipse-temurin:25-jre` | `gcr.io/distroless/java25-debian13` | la variante JRE 25 de `dhi.io/eclipse-temurin` |
| Nativo | `ghcr.io/graalvm/native-image-community:25` | `gcr.io/distroless/base-nossl-debian13` | la variante `glibc-debian13` de `dhi.io/static` |

Solo cambia la imagen final. Las etapas de build conservan una imagen completa, porque corren un `RUN`
que necesita shell, y no llegan a la imagen final. Cada imagen es un argumento del Dockerfile, para
fijarla por digest:

| Argumento | Dockerfile | Qué es |
|---|---|---|
| `JAVA_IMAGE` | JVM | la imagen final, con el JRE |
| `BUILD_IMAGE` | JVM | la etapa que abre el jar por capas; es nuevo |
| `RUNTIME_IMAGE` | nativo | la imagen final, sin JVM |
| `GRAALVM_IMAGE` | nativo | la etapa que compila el ejecutable |

**Por qué distroless por defecto:** quita la shell y el gestor de paquetes, se descarga sin cuenta ni
secretos en el CI, trae el mismo Temurin 25 y reduce la imagen de la JVM de 359 a 250 MB.

**Por qué la base nativa no trae OpenSSL:** con `--static-nolibc`, el ejecutable solo necesita glibc.
El TLS de Java no usa el OpenSSL del sistema, y `native-image` guarda dentro del ejecutable los
certificados raíz del JDK con el que compila. `base-nossl-debian13` solo trae glibc, los certificados,
las zonas horarias y los archivos base de Debian.

### Docker Hardened Images es una opción

Se usa con el mismo `--build-arg`, sin cambiar el Dockerfile. No es el valor por defecto porque pide
`docker login dhi.io` en cada máquina y un secreto con esas credenciales en el CI de cada repositorio.
La etiqueta exacta se toma del catálogo, que también pide la cuenta. Para el ejecutable nativo sirve
la variante de Debian con glibc, no la de Alpine, que trae musl.

### El SBOM viaja dentro de la imagen nativa

En la imagen nativa, las librerías quedan compiladas dentro del ejecutable y un escáner no las ve. Sin
más, la imagen nativa aparentaría no tener dependencias vulnerables, aunque lleva las mismas que el
jar. El Dockerfile nativo copia el SBOM del jar a `/application/sbom`, y con él Trivy reporta las mismas
dependencias en los dos modos.

### Los CVE son una métrica de ADR-045

La medición de Plaza suma el escaneo de cada imagen con Trivy, un escáner de código abierto de Aqua
Security que cruza los paquetes del sistema y las librerías de una imagen con las bases públicas de
vulnerabilidades. Se reporta el total de CVE únicos, cuántos son HIGH o CRITICAL y **cuántos tienen
arreglo**, separando los del sistema de los de las librerías.

Trivy se usa con tres cuidados, por el ataque a su cadena de suministro de marzo de 2026 (CVE-2026-33634):
ese mes se publicaron binarios e imágenes maliciosos, y casi todas las etiquetas de `trivy-action`
apuntaron a código que robaba secretos del CI.

- La imagen se fija por digest, no por etiqueta.
- El job que escanea no recibe secretos.
- La imagen a escanear se le pasa como archivo, con `docker save`, sin darle el socket de Docker.

### La medición inicial

Trivy 0.74.0 (`aquasec/trivy@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969`),
con la base de vulnerabilidades del 2026-09-30. Se cuentan CVE únicos.

| Imagen base | Sistema | CVE | HIGH o CRITICAL | Con arreglo |
|---|---|---|---|---|
| `eclipse-temurin:25-jre` | Ubuntu 26.04 | 36 | 0 | 0 |
| `gcr.io/distroless/java25-debian13` | Debian 13.7 | 40 | 8 | 0 |
| `gcr.io/distroless/base-debian12` | Debian 12.15 | 37 | 1 | 7 |
| `gcr.io/distroless/base-nossl-debian13` | Debian 13.7 | 21 | 0 | 0 |

La misma aplicación de ejemplo, un servicio web con Spring Boot 4.0.8, en los tres modos:

| Imagen | Tamaño | CVE del sistema | CVE de las librerías |
|---|---|---|---|
| JVM sobre Temurin y Ubuntu | 359 MB | 36 | 6: 3 CRITICAL y 1 HIGH, todos con arreglo |
| JVM sobre distroless | 250 MB | 40 | los mismos 6 |
| Nativo sobre distroless, con el SBOM | 100 MB | 21 | los mismos 6 |

Con el mismo JDK, 25.0.4.1, y cinco corridas alternadas, la JVM sobre distroless arranca igual que
sobre Temurin: 4.39 y 4.44 s de mediana hasta el primer 200 del endpoint de salud.

Lo que dicen los números:

1. **En la JVM, distroless no baja la cuenta de CVE: la sube de 36 a 40.** Los 8 HIGH están en
   `libexpat1` y `libuuid1`, que llegan con `fontconfig`, la dependencia del JRE para las fuentes.
   Ninguno de los CVE del sistema tiene arreglo en ninguna de las dos bases, y Ubuntu y Debian no
   declaran lo mismo. Lo que gana distroless es superficie y tamaño, no la cuenta.
2. **La base nativa sí la baja:** 21 CVE en un solo paquete, `libc6`, contra 37 y 7 arreglables en
   `base-debian12`.
3. **Pesan más las librerías que la base.** Los únicos CVE con arreglo y los únicos CRITICAL están en
   las librerías de la aplicación, `tomcat-embed-core` 11.0.24 y `jackson-databind` 3.1.5, y son los
   mismos en los tres modos.
4. **Sin el SBOM, la imagen nativa aparentaba cero CVE en sus librerías.** Era falso.

## Preguntas abiertas

1. **Docker Hardened Images como valor por defecto.** Se decide midiéndola con la misma herramienta,
   frente a distroless. Pide una cuenta de Docker y el secreto en el CI.
2. **El escaneo como compuerta del CI.** Hoy es una métrica. Si pasa a compuerta, fallaría solo por lo
   que se puede arreglar (`--ignore-unfixed`), para que una base sin arreglo publicado no bloquee todo.
3. **VEX.** Docker Hardened Images publica declaraciones de explotabilidad, y Trivy las puede leer con
   `--vex` para descartar lo que no aplica. Se evalúa junto con la pregunta 1.
4. **Las librerías de la aplicación.** Spring Boot 4.0.8 trae `tomcat-embed-core` 11.0.24 y
   `jackson-databind` 3.1.5, y ya existen 11.0.26 y 3.2.3. Ninguna versión de Spring Boot las trae
   todavía, ni siquiera la 4.1.1. Que el toolchain las fije queda para un PR aparte.

## Alternativas descartadas

- **Seguir con `eclipse-temurin` en la imagen final.** Trae shell y gestor de paquetes, y pesa 109 MB
  más. Hoy Trivy le cuenta menos CVE, pero ninguno de los de una u otra base tiene arreglo.
- **Chainguard.** El plan gratis solo publica `latest`: fijar una versión pide suscripción.
- **Alpine.** El ejecutable nativo se enlaza con glibc, y Alpine trae musl.
- **Un ejecutable totalmente estático sobre `scratch`.** Pide musl y sus herramientas en la etapa de
  build, y el asignador de memoria de musl es más lento, lo que sesgaría la comparación de ADR-045.

## Consecuencias

### Positivas

- La imagen final no trae shell ni gestor de paquetes, en los dos modos.
- Los dos modos salen de la misma familia de base, así que la comparación de tamaño mide el runtime y no
  el sistema operativo.
- La imagen nativa se puede escanear como la de la JVM.
- La métrica de CVE separa lo que se puede arreglar de lo que no, y lo del sistema de lo de la aplicación.

### Negativas

- Sin shell no hay `docker exec ... sh`. Se depura con `docker debug` o con la variante `:debug` de
  distroless.
- En la JVM, un escáner reporta más CVE sin arreglo que con la base de Ubuntu. Queda documentado arriba.
- Docker Hardened Images suma una cuenta y un secreto por repositorio para quien la use.

### La receta para volver atrás

La imagen de la JVM sobre Ubuntu se recupera con `--build-arg=JAVA_IMAGE=eclipse-temurin:25-jre`, y la
base nativa anterior con `--build-arg=RUNTIME_IMAGE=gcr.io/distroless/base-debian12`.

## Fuentes

Consultadas el 2026-09-29.

- [Docker Hardened Images: documentación](https://docs.docker.com/dhi/)
- [Docker Hardened Images: Eclipse Temurin en el catálogo](https://hub.docker.com/hardened-images/catalog/dhi/eclipse-temurin)
- [Docker Hardened Images: la imagen `static`](https://hub.docker.com/hardened-images/catalog/dhi/static/guides)
- [Docker Hardened Images: glibc y musl](https://docs.docker.com/dhi/explore/security-concepts/glibc-musl/)
- [Docker Hardened Images: migrar una aplicación Java](https://docs.docker.com/dhi/migration/examples/java)
- [Distroless: el repositorio](https://github.com/GoogleContainerTools/distroless)
- [Distroless: las imágenes de Java](https://github.com/GoogleContainerTools/distroless/blob/main/java/README.md)
- [GraalVM: ejecutables estáticos y mayormente estáticos](https://www.graalvm.org/latest/reference-manual/native-image/guides/build-static-executables/)
- [GraalVM: los certificados en Native Image](https://www.graalvm.org/latest/reference-manual/native-image/dynamic-features/CertificateManagement/)
- [Chainguard: cambios en el plan gratis](https://support.chainguard.dev/hc/en-us/articles/40405733238299-Customer-Notice-Free-Image-Tier-Changes)
- [Trivy: el aviso del ataque a su cadena de suministro](https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23)
- [Aqua Security: qué pasó y cómo se remedió](https://www.aquasec.com/blog/trivy-supply-chain-attack-what-you-need-to-know/)
- [Microsoft: cómo detectar y defenderse del ataque a Trivy](https://www.microsoft.com/en-us/security/blog/2026/03/24/detecting-investigating-defending-against-trivy-supply-chain-compromise/)
- [Trivy 0.74.0](https://github.com/aquasecurity/trivy/releases/tag/v0.74.0)
