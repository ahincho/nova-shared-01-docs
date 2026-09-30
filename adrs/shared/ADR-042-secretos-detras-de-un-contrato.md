# ADR-042: Secretos detrás de un Contrato: el Entorno, Vault y AWS Secrets Manager

## Estado

Aceptada (2026-09-28). Angel eligió secretos como la primera capacidad nueva y pidió un contrato
único con implementaciones para Vault y AWS Secrets Manager. Al confirmarlo pidió dejar explícito
que un secreto de AWS llega como un JSON que hay que abrir para inyectarlo: es la sección
«El JSON de AWS».
**Scope:** `shared` (Java + NestJS). Java lo implementa en `nova-java-23-secrets`; NestJS ya tiene
la fuente del entorno, en la rama `feat/platform-next` de `nova-nestjs-01-platform`.
**Aplica:** la fila de secretos de [ADR-034](ADR-034-puertos-con-implementacion-por-defecto.md),
el reparto de [ADR-036](ADR-036-perfiles-de-organizacion.md) y la forma de repositorio de
[ADR-041](../java/ADR-041-un-repositorio-por-capacidad.md).

## Fecha

2026-09-28

## Contexto

ADR-034 dejó la regla y el puerto de esta capacidad escritos en una línea: el núcleo decide que
los secretos se resuelvan antes de que exista la aplicación y que uno roto corte el arranque sin
citarse; de dónde salen es un puerto, porque el JSON que inyecta ECS es una fuente y no la única.
Este ADR la desarrolla.

### Por dónde llega un secreto a un servicio

1. **El orquestador lo pone en el entorno.** ECS inyecta un secreto de Secrets Manager entero, como
   un JSON, en una sola variable, y Kubernetes puede hacer lo mismo si el `Secret` guarda el JSON
   en una sola clave. La aplicación no llama a nadie: parsea.
2. **La aplicación lo lee de un almacén al arrancar**: Vault, AWS Secrets Manager. Hay una llamada
   de red antes de que exista la aplicación.
3. **El almacén lo genera en el momento**, con un plazo de vida: los secretos dinámicos de Vault.
   Queda fuera de este ADR.

### Lo que hay hoy, medido

- **En Java no hay nada.** Nova no trae ninguna forma de cargar un secreto.
- **En la primera organización, uno de sus dieciséis repositorios Java desdobla el JSON que
  inyecta ECS**, con un `ConfigSource` propio que lee una sola variable escrita en el código y se
  ubica por encima de las variables de entorno (ordinal 350).
- **En NestJS la fuente del entorno ya existe**, sin publicar, en la rama `feat/platform-next`:
  `unfoldSecrets()` desdobla las variables que se nombran, las que empiezan con un prefijo y las
  que lista `NOVA_SECRETS`. El prefijo no tiene valor por defecto porque es de la organización.
  Una variable ausente no falla y una malformada corta el arranque.

### Lo que ofrece Spring, y por qué no alcanza solo

Spring Cloud Vault y Spring Cloud AWS resuelven el caso 2 para Spring, y lo resuelven bien:
métodos de autenticación, renovación, `spring.config.import`. Pero cada uno tiene su propia
configuración (`spring.cloud.vault.*`, `spring.cloud.aws.*`), su propia respuesta a qué pasa cuando
un secreto falta, y ninguno sirve en Quarkus. Un servicio que cambia de almacén cambia sus
dependencias, su configuración y el comportamiento ante un error, y un equipo con servicios en los
dos frameworks aprende dos mecanismos para lo mismo.

## Decisión

**Un servicio de Nova lee sus secretos como propiedades de configuración y nunca sabe de dónde
salen. De dónde salen es un puerto, `SecretSource`. La implementación por defecto de Nova lee el
entorno del proceso, y hay un adaptador por almacén: Vault y AWS Secrets Manager.**

El servicio escribe `${DB_PASSWORD}` y nada más. Pasar de Vault a AWS Secrets Manager es cambiar una
dependencia y una línea de configuración, sin tocar código.

### Lo que decide el núcleo, siempre

1. **Se resuelven antes de que exista la aplicación**, para que un `DataSource` ya los encuentre.
   En Spring Boot, con un `EnvironmentPostProcessor` y con la API de `ConfigData`, la misma que
   usa `spring.config.import`; en Quarkus, con un `ConfigSource`.
2. **Ausente y malformado son casos distintos.**
   - Una variable de entorno ausente no falla: es lo que permite que una corrida local y los tests
     usen sus propias variables. Es lo mismo que hace NestJS.
   - Una referencia a un almacén que no existe **sí falla**, salvo que el servicio la marque
     `optional:`, que es la convención de `spring.config.import`. Si el servicio escribió la
     referencia, prometió que existe; dejarla pasar solo cambia el error por uno peor, cuando el
     `DataSource` no pueda conectarse.
   - Un secreto que no es un objeto JSON, o un almacén que contesta con un error, **corta el
     arranque**.
3. **El error nombra la referencia y nunca el contenido.** El mensaje del parser de JSON no se
   encadena, porque cita el texto que no pudo leer, y ese texto es el secreto.
4. **El valor nunca llega a un log.** `Secret.toString()` no muestra valores, y las propiedades
   que salen de un secreto se sanean en `/actuator/env` aunque el servicio active
   `show-values=always`.
5. **Toda llamada a un almacén lleva timeout.** Un Vault que no contesta corta el arranque con un
   error claro en vez de dejarlo colgado. Es la misma regla que ADR-029 puso al cliente HTTP.
6. **Un secreto pisa a una propiedad suelta con el mismo nombre** (`nova.secrets.override`, por
   defecto `true`). Es lo que hacen NestJS y el `ConfigSource` de la primera organización, y lo que
   quiere producción: si una variable vieja quedó en la task definition, el almacén manda.
7. **Solo cuentan los valores escalares.** Una clave cuyo valor es un objeto, una lista o `null` se
   ignora, en lugar de convertirse en un texto que pasaría cualquier validación llevando basura.
   También es lo que hace NestJS.

### El contrato

Los nombres son provisionales; la forma es la decisión.

```java
/** Un almacén de secretos: el entorno del proceso, Vault, AWS Secrets Manager. */
public interface SecretSource {
    /** El secreto que nombra la referencia, ya aplanado en clave → valor; vacío si no existe. */
    Optional<Secret> find(String reference);
}

/** Crea una fuente con su configuración. Se descubre con ServiceLoader. */
public interface SecretSourceProvider {
    /** El nombre con que se elige: "env", "vault", "aws-secrets-manager". */
    String name();
    SecretSource create(SecretSettings settings);
}

/** Lectura de configuración que no depende del framework: la dan Spring, Quarkus o el entorno. */
@FunctionalInterface
public interface SecretSettings {
    Optional<String> get(String key);
}
```

El contrato no importa nada de Spring ni de Quarkus (ADR-015). `SecretSettings` es lo que permite
que un adaptador lea su dirección o su región sin saber qué framework lo llama.

### Las implementaciones

| Nombre | Artefacto | De dónde lee | Su configuración |
|---|---|---|---|
| `env`, por defecto | `nova-secrets` | variables de entorno que traen un objeto JSON | `nova.secrets.env.variables`, `nova.secrets.env.prefix` (sin valor por defecto) y la variable `NOVA_SECRETS` |
| `vault` | `nova-secrets-vault` | Vault, motor KV versión 2 | `address`, `token` o AppRole (`role-id`, `secret-id`), `mount` (por defecto `secret`), `timeout` |
| `aws-secrets-manager` | `nova-secrets-aws-secrets-manager` | AWS Secrets Manager, `GetSecretValue` | `region`, `endpoint` (para un emulador), `timeout` |

Las claves van bajo `nova.secrets.<nombre>.*`. **Donde el proveedor tiene su convención, Nova la
respeta como valor por defecto**: `VAULT_ADDR` y `VAULT_TOKEN` para Vault, y la cadena por defecto
de AWS para la región y las credenciales, que dentro de ECS toma el rol de la tarea.

El adaptador de Vault habla con la API HTTP de Vault usando el cliente HTTP del JDK, sin un
cliente de terceros. El de AWS usa el módulo `secretsmanager` del SDK v2.

### El JSON de AWS

Un secreto de AWS Secrets Manager es un texto, y por convención ese texto es un objeto JSON con
varias claves:

```json
{ "username": "course", "password": "…", "host": "db.internal", "port": 5432 }
```

No llega como una variable por clave, así que el servicio no puede usarlo tal cual: hay que abrir
el JSON y convertir cada clave en una propiedad. Ese es el truco que hoy escribe a mano cada
servicio que lo necesita, y **Nova lo hace en un solo lugar, `Secret.fromJson()` del contrato**.

Lo usan las dos rutas por las que llega un secreto de AWS:

| Ruta | Quién trae el JSON | Quién lo abre |
|---|---|---|
| ECS lo inyecta entero en una variable, como `SECRET_DB` | la task definition | la fuente `env` |
| el servicio lo pide al arrancar | `GetSecretValue`, en su campo `SecretString` | la fuente `aws-secrets-manager` |

Como las dos pasan por el mismo código, **producen exactamente las mismas propiedades**, y un
servicio puede pasar de una ruta a la otra sin cambiar nada más que de dónde sale el secreto. Un
secreto guardado como binario (`SecretBinary`) no se abre: corta el arranque con un error que lo
dice.

### Cómo se usa en Spring Boot

La fuente del entorno se aplica sola cuando hay algo que desdoblar, igual que en NestJS. Los
almacenes se piden con `spring.config.import`:

```yaml
spring:
  config:
    import: nova-secrets:vault:ms-course        # o nova-secrets:aws-secrets-manager:prod/ms-course/db
  datasource:
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}
```

**Lo que es de una organización va en su starter, no en Nova.** El prefijo `SECRET_` de la primera
organización lo pone su propio starter, que en Java es lo que ADR-036 llama perfil y dejó sin
nombre en su pregunta abierta 3. Nova no trae ningún valor de ninguna organización.

### Quarkus

Los mismos adaptadores, a través de un `ConfigSource` que arma `nova-secrets-quarkus-extension`,
más adelante. Reemplazaría el `ConfigSource` propio que hoy escribe un servicio cuando lo necesita.

### Fuera de alcance

- **Cifrar campos con Vault Transit** es otra capacidad, la de protección de datos.
- **Secretos dinámicos, plazos de vida y rotación sin reiniciar.** En la primera versión los
  secretos se leen al arrancar, y rotar uno es reiniciar el servicio.
- **Otros almacenes** —Parameter Store, GCP Secret Manager, Azure Key Vault— entran como un
  adaptador cada uno cuando un consumidor los pida.

### Cómo se prueba

- Las reglas, con pruebas unitarias sobre fuentes falsas.
- Los adaptadores, contra un Vault real y un emulador de AWS (LocalStack o Moto) levantados con
  Testcontainers.
- El starter, con `ApplicationContextRunner`: cuándo se activa, qué pisa a qué y qué se sanea.
- **El consumidor real todavía no existe, y se dice.** Hoy ningún ejemplo de Spring necesita un
  secreto: ninguno tiene base de datos ni llama a un servicio con credenciales. Lo será el servicio
  de pedidos que se agrega como ejemplo, con su base de datos tomando las credenciales de Vault, así
  que la capacidad no se da por terminada hasta que ese ejemplo la use.
  `nova-shared-03-infrastructure` suma un Vault en modo desarrollo y el emulador de AWS para
  correrlo en local.

## Alternativas descartadas

**Usar Spring Cloud Vault y Spring Cloud AWS directamente.** Funciona hoy en Spring. Se descarta
por lo que dice el contexto: dos configuraciones para una misma cosa, reglas distintas según la
librería y nada para Quarkus. El costo aceptado es escribir el cliente de Vault, con su
autenticación, en vez de heredarlo.

**Un contrato de Nova con adaptadores que delegan en Spring Cloud.** Conserva la autenticación y
la renovación que Spring Cloud ya tiene. Pero los adaptadores quedan atados a Spring, no se reusan
en Quarkus, y su configuración se filtra hacia el servicio: dos juegos de propiedades para una
sola decisión.

**Solo el entorno, y que el orquestador inyecte todo.** Alcanza para la primera organización. Se
descarta porque deja afuera a cualquier organización que lee Vault al arrancar, y a la corrida
local sin orquestador. Es, además, convertir la topología de una organización en la única, que es
lo que ADR-036 rechaza.

**Una variable por clave**, con la selección `:CLAVE::` que permite ECS. La aplicación no parsea
nada, pero la lista de claves se muda a la infraestructura: cada clave nueva es un cambio en la
task definition. Sigue siendo posible, porque una variable suelta es una propiedad más; lo que se
descarta es que sea el único mecanismo.

## Preguntas abiertas

**1. Rotación sin reiniciar y secretos dinámicos.** En Spring la herramienta habitual es
`@RefreshScope`, que es de Spring Cloud. Se decide cuando un consumidor lo pida.

**2. Otros métodos de autenticación de Vault**, como Kubernetes o IAM de AWS. La primera versión
trae token y AppRole.

**3. El valor por defecto de `override`.** `true` da paridad con NestJS y con lo que ya corre en
producción, pero va contra la costumbre de Spring, donde una variable de entorno gana. Si
sorprende en la práctica, se revisa.

**4. Vault y AWS Secrets Manager en NestJS.** La fuente del entorno ya existe allá. Los almacenes
se agregan con el mismo contrato cuando un servicio NestJS los necesite.

**5. Quarkus en imagen nativa**, donde `ServiceLoader` necesita que los adaptadores se registren
en tiempo de build.

**6. Con qué lee el JSON el contrato.** Spring Boot 4 trae Jackson 3 y Quarkus sigue en Jackson 2,
así que depender de `jackson-databind` ata el contrato a uno de los dos. `jackson-core` 2, que es
solo el parser de streaming, convive con los dos porque Jackson 3 cambió de paquete. Se decide al
implementar, con una prueba en cada framework.

## Consecuencias

### Positivas

- El servicio no importa nada de Vault ni de AWS, y cambiar de almacén no toca su código.
- Las mismas reglas valen para todo almacén y para los dos frameworks.
- Operaciones configura igual un servicio NestJS y uno Java: las mismas variables, el mismo
  prefijo, la misma salida de emergencia.
- Son las primeras pruebas de Nova contra servicios reales, en contenedores.

### Negativas

- **Nova mantiene un cliente de Vault**, con su autenticación, sus errores y su TLS.
- **El orden por defecto no es el que espera quien viene de Spring**, y hay que decirlo en la
  documentación del starter.
- **Es un contrato público más.** Cambiar `SecretSource` rompe a quien haya escrito su propio
  adaptador.
- **El arranque depende del almacén.** Es a propósito: sin sus secretos el servicio no debe
  arrancar.

## Referencias

- [ADR-015: Librerías Puras sin Dependencias de Framework](../java/ADR-015-librerias-puras-sin-dependencias-framework.md)
- [ADR-029: Sin Reintentos ni Corte de Circuito en el Cliente HTTP](../nest/ADR-029-sin-reintentos-en-el-cliente-http.md)
- [ADR-034: Lo Duro y lo Reemplazable](ADR-034-puertos-con-implementacion-por-defecto.md)
- [ADR-036: Perfiles de Organización](ADR-036-perfiles-de-organizacion.md)
- [ADR-041: Un Repositorio por Capacidad](../java/ADR-041-un-repositorio-por-capacidad.md)
- `nova-nestjs-01-platform`, rama `feat/platform-next`: `packages/core/src/config/secrets.ts`
- Spring Boot, *Importing Additional Data* (`spring.config.import`) y la API de `ConfigData`
- Vault, API del motor KV versión 2 y del método de autenticación AppRole
- AWS Secrets Manager, `GetSecretValue`
