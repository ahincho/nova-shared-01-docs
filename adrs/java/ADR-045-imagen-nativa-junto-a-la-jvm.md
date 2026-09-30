# ADR-045: La Imagen Nativa de GraalVM, junto a la JVM

## Estado

Aceptada (2026-09-29). Angel pidió que los servicios se puedan compilar en nativo con GraalVM sin
dejar la JVM, para comparar los dos modos y sacar métricas, y aprobó el plan con las respuestas
recomendadas a las preguntas abiertas. Sigue abierta la fecha de la presentación.
**Scope:** `java`. NestJS no tiene un equivalente.
**Extiende:** [ADR-044](ADR-044-toolchain-de-java.md), que define los plugins de servicio y la imagen
de la JVM.
**Se mide en:** [ADR-043](../shared/ADR-043-plaza-la-plataforma-de-compras.md), Plaza.

## Fecha

2026-09-29

## Contexto

Hoy un servicio sale en una sola forma: el jar sobre una JRE 25, en la imagen que construye
`novaDocker`. Es la forma correcta por defecto: compila en alrededor de un minuto, rinde al máximo
cuando el JIT se calienta y no le pone condiciones al código.

Una imagen nativa invierte ese equilibrio. `native-image` analiza la aplicación entera al compilar y
genera un ejecutable que arranca en milisegundos y ocupa menos memoria. A cambio:

- **el build tarda minutos y pide varios GB de RAM**;
- **el mundo es cerrado:** lo que el análisis no ve al compilar no existe en ejecución. La reflexión,
  los proxies y los recursos que no descubre hay que declararlos, y cuando faltan no siempre hay un
  error;
- **en Spring, el grafo de beans queda fijo:** el procesamiento AOT decide los perfiles y las
  condiciones al compilar;
- **no hay JIT:** el rendimiento sostenido suele ser menor que el de una JVM caliente.

El ejecutable es de la plataforma donde se compila. En Linux no hay `.exe`, y un binario hecho en
Windows no corre en un contenedor Linux: no hay compilación cruzada.

Ninguno de los repositorios del curso usa GraalVM, así que no es un requisito sino un diferenciador.
Y la comparación solo vale con números medidos en las mismas condiciones, no con los publicados para
otra aplicación.

## Decisión

### La JVM sigue siendo el modo por defecto

Un servicio se construye en los dos modos desde el mismo commit, con el mismo contrato de tareas:

| Tarea | Imagen | Etiqueta |
|---|---|---|
| `novaDocker` | la de hoy: JRE 25 y el jar por capas | `<servicio>:<versión>` |
| `novaDockerNative` | el ejecutable nativo sobre una base mínima | `<servicio>:<versión>-native` |

Hacia afuera, las dos imágenes se comportan igual: puerto 8080, usuario 10001, el ambiente por
variables de entorno y el proceso como PID 1. La regla de una sola imagen para todos los ambientes
([ADR-027](../nest/ADR-027-imagen-de-contenedor-compartida.md)) vale para cada modo.

### El nativo es opcional, por servicio

El servicio lo activa con una línea en `gradle.properties`:

```properties
nova.native=true
```

Con esa propiedad, `spring-boot-service` aplica GraalVM Native Build Tools, que activa el
procesamiento AOT de Spring, y registra `novaDockerNative`. Sin ella no cambia nada: el build no paga
el AOT ni sus restricciones. La versión de Native Build Tools sale del catálogo del toolchain, como
las demás.

`quarkus-service` ofrece la misma tarea con la compilación nativa de Quarkus, que usa Mandrel.

### El ejecutable se compila dentro de Docker, a partir del jar

El Dockerfile nativo vive en el plugin, como el de la JVM, y tiene dos etapas:

1. **La compilación:** una imagen de GraalVM 25 abre el jar que ya construyó Gradle y corre
   `native-image` con los argumentos que el procesamiento AOT deja dentro del jar.
2. **La ejecución:** el ejecutable solo, sin JVM, sobre una base mínima con glibc. La base es un
   `ARG`, para fijarla por digest como en la imagen de la JVM.

Compilar dentro de un contenedor Linux resuelve la plataforma: el mismo comando funciona en Windows y
en el CI, y no hace falta instalar GraalVM. Como el jar llega hecho, el build de la imagen tampoco
necesita el token del registro.

**La memoria del compilador se acota:** el Dockerfile fija un tope de heap para `native-image`, que se
puede subir con `--build-arg`. Un build nativo nunca corre dentro de `./gradlew build`.

### En la máquina, para ensayar

Native Build Tools trae además `nativeCompile` y `nativeRun`, que compilan con el GraalVM instalado en la
máquina. En Windows piden también las herramientas de C++ de Visual Studio, y generan un `.exe` que
corre en la propia estación: sirve para ensayar rápido o para medir en la máquina de la presentación.
El toolchain les pone el mismo tope de heap que al Dockerfile.

**No reemplazan a la imagen.** Un `.exe` de Windows no corre en un contenedor Linux, así que la imagen
nativa se construye siempre en Docker, y los números del informe salen siempre de las imágenes.

### Cada librería de Nova responde por su modo nativo

Si una librería usa reflexión o recursos, ella declara sus metadatos y prueba el modo nativo en su CI.
El servicio no los repite. Leyendo el código aparecen tres casos concretos:

- **`nova-mask` busca los campos `@Masked` por reflexión.** En nativo, una clase no registrada no
  muestra sus campos, así que **el dato sale sin enmascarar y sin error**. Es el riesgo más serio: la
  librería tiene que registrar las clases que enmascara, y una prueba nativa tiene que comprobarlo.
- **El procesamiento AOT de Spring prepara el `Environment` al compilar,** así que el import
  `nova-secrets:` intentaría leer el almacén durante el build. El starter tiene que saltarse la carga
  cuando detecta el procesamiento AOT. A verificar.
- **`nova-observability` usa el starter de OpenTelemetry para Spring Boot,** no el agente de Java.
  Es la variante que funciona en nativo. A verificar.

### Las métricas

La medición vive en Plaza, no en el toolchain: el toolchain construye los dos modos, y Plaza los
compara sobre su propia infraestructura. `nova-plaza-01-shared-platform` suma un workflow manual que:

1. construye las dos imágenes de un servicio desde el mismo commit;
2. levanta Postgres y Vault con el compose;
3. **comprueba que los dos modos responden lo mismo** a las mismas peticiones, antes de medir nada. Una
   diferencia es un defecto del modo nativo, como un dato sin enmascarar;
4. corre cada modo cinco veces con los mismos límites de CPU y de memoria, y publica la mediana en el
   resumen del job y en un JSON.

| Métrica | Cómo se mide |
|---|---|
| Tiempo de build | el de `novaDocker` y el de `novaDockerNative`, con la caché vacía |
| Tamaño de la imagen | el que reporta Docker |
| Tiempo hasta estar listo | desde que arranca el contenedor hasta el primer 200 del endpoint de salud |
| Primera petición | la latencia de la primera llamada de negocio, en frío |
| Memoria | la del proceso en reposo, y el máximo bajo carga |
| Latencia y rendimiento | p50, p95, p99 y peticiones por segundo con k6 a una tasa fija, separando el calentamiento del régimen estable |
| CPU | el promedio bajo carga |
| CVE | los de cada imagen con Trivy, del sistema y de las librerías, y cuántos tienen arreglo ([ADR-046](ADR-046-imagenes-base-distroless.md)) |

Para que la comparación sea justa: la misma infraestructura, los mismos endpoints y el mismo tope de
heap relativo a la memoria del contenedor. Cada informe registra las versiones (JDK, GraalVM y el
digest de cada base) y el recolector de basura de cada modo. Y suma un escenario con poca memoria, por
ejemplo 256 MB, que es donde se ve la diferencia.

**Las hipótesis, antes de medir:** el nativo arranca en décimas de segundo contra segundos en la JVM, y
usa una fracción de la memoria; la JVM compila en menos tiempo y rinde más en régimen estable. La
presentación muestra la hipótesis y lo medido, lado a lado.

## La implementación

Un PR por repositorio, en este orden:

1. **El toolchain:** `nova.native`, `novaDockerNative` y el Dockerfile nativo en `spring-boot-service`.
2. **Las librerías:** el modo nativo de `nova-mask`, `nova-secrets` y `nova-observability`, cada una con
   su prueba.
3. **Pedidos de Plaza:** activa `nova.native`, y su imagen nativa arranca y responde.
4. **La medición en Plaza,** con el primer informe de pedidos.
5. **El catálogo,** con `quarkus-service` en los dos modos desde el primer día. Suma otra comparación:
   Spring y Quarkus, cada uno en JVM y en nativo.

## Preguntas abiertas

Las cuatro primeras se resolvieron con la aceptación.

1. **Cuándo compila el CI en nativo.** Resuelta: solo en la medición manual y al publicar una
   versión. Cada PR sigue con la JVM.
2. **La distribución de GraalVM.** Resuelta: GraalVM Community para Spring, que es la que usa la
   documentación de Spring Boot, y Mandrel para Quarkus, que es su valor por defecto. Oracle GraalVM
   trae el recolector G1 y la optimización guiada por perfiles, pero con otra licencia. En la máquina
   de Angel está instalado Oracle GraalVM para ensayar, y eso no cambia la imagen.
3. **Dónde se mide.** Resuelta: en un runner de GitHub, que es siempre el mismo tipo de máquina y no
   ocupa ninguna estación de trabajo durante minutos. El mismo script corre en local para ensayar.
4. **Un tercer modo: la JVM con la caché AOT de Java 25.** Resuelta: se evalúa después del catálogo.
   Es la respuesta de la JVM al nativo, menos tiempo de arranque sin mundo cerrado, pero pide una
   corrida de entrenamiento al construir la imagen, y en pedidos esa corrida necesita la base de datos.
5. **La fecha de la presentación.** Abierta. Marca hasta dónde llega el alcance: los pasos 1 a 4 dan el
   primer informe.

## Alternativas descartadas

- **El nativo en todos los servicios.** Cada build pagaría el AOT y sus restricciones, aunque el
  servicio nunca se compile en nativo.
- **Construir la imagen con el GraalVM de la máquina.** En Windows sale un `.exe` que no corre en el
  contenedor, y la imagen dependería de lo que cada estación tenga instalado. El GraalVM local queda
  para ensayar.
- **Paketo Buildpacks con `bootBuildImage`.** Construye la imagen nativa sin Dockerfile, pero se aparta
  del modelo de ADR-044, en el que la imagen vive en el plugin y se puede leer. Quarkus tampoco lo usa
  por defecto.
- **Comparar con números publicados.** Otra máquina, otra versión y otra aplicación: no dicen nada de
  Plaza.

## Consecuencias

### Positivas

- Un servicio elige su modo sin tocar el código, y los dos modos salen del mismo commit.
- La comparación es reproducible, y la presentación lleva números propios.
- La prueba de equivalencia atrapa los defectos del modo nativo que no avisan.

### Negativas

- Cada librería de Nova suma la responsabilidad de su modo nativo y una prueba más en su CI.
- Un servicio nativo no puede decidir beans por ambiente: los perfiles y las condiciones quedan fijos
  al compilar. Los valores por ambiente siguen funcionando.
- Un build nativo tarda minutos y pide varios GB de RAM. Se acota y corre en el CI.
- GraalVM Community solo trae el recolector Serial, así que bajo carga los dos modos no recolectan
  igual. Se registra en cada medición.
