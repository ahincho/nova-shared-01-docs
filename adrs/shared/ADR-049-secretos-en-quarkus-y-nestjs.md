# ADR-049: Los Secretos en Quarkus y NestJS, con las Mismas Reglas que en Spring Boot

## Estado

Propuesta (2026-10-01). Angel pidió que la capacidad de secretos también se desarrolle para Quarkus
y NestJS.
**Scope:** `shared` (Java y NestJS).
**Completa:** [ADR-042](ADR-042-secretos-detras-de-un-contrato.md). Responde sus preguntas abiertas
4 (Vault y AWS Secrets Manager en NestJS), 5 (Quarkus en imagen nativa) y 6 (con qué se lee el JSON),
y la pregunta 3 de [ADR-041](../java/ADR-041-un-repositorio-por-capacidad.md) (dónde viven los
adaptadores de NestJS).
**Aplica:** la forma de repositorio de ADR-041, las reglas del núcleo de ADR-042 y la imagen nativa
de [ADR-045](../java/ADR-045-imagen-nativa-junto-a-la-jvm.md).
**Primeros consumidores:** `plaza-catalog` en Quarkus y `plaza-bff` en NestJS
([ADR-043](ADR-043-plaza-la-plataforma-de-compras.md)), con la salvedad de la pregunta abierta 1.

## Fecha

2026-10-01

## Contexto

ADR-042 decidió un contrato, `SecretSource`, con la fuente del entorno por defecto y un adaptador por
almacén. Hoy cada stack lo tiene en un punto distinto:

| | Spring Boot | Quarkus | NestJS |
|---|---|---|---|
| Fuente del entorno (el JSON que inyecta ECS) | sí, `nova-secrets` 1.0.1 | **no** | sí, `unfoldSecrets()` en `@ahincho/nova-nestjs` |
| Vault | sí, `nova-secrets-vault` | **no** | **no** |
| AWS Secrets Manager | sí, `nova-secrets-aws-secrets-manager` | **no** | **no** |
| Cómo se piden | `spring.config.import` | — | — |
| Consumidor real | pedidos de Plaza, con Postgres desde Vault | — | — |

Lo que falta en Quarkus es el conector: los adaptadores de Java ya son librerías puras (ADR-015) y se
descubren con `ServiceLoader`, así que sirven sin cambios. En NestJS falta todo lo que no es el
entorno.

Dos hechos fijan el diseño:

- **La primera organización escribe a mano un `ConfigSource` de Quarkus** que desdobla una sola
  variable, con ordinal 350. Es lo que el conector de Nova reemplaza.
- **En NestJS el arranque ya es asíncrono.** `bootstrap()` desdobla el entorno antes de
  `NestFactory.create`, así que leer un almacén por la red cabe en el mismo lugar sin cambiar cómo un
  servicio arranca.

## Decisión

**Los tres stacks aplican las siete reglas de ADR-042 con la misma configuración: las mismas
variables de entorno, la misma forma de pedir un almacén y los mismos mensajes de error. Quarkus
reusa los adaptadores de Java con un conector propio dentro de `nova-java-23-secrets`, y NestJS suma
los dos almacenes como dos paquetes nuevos de su monorepo.**

### Lo mismo en los tres

| Qué | Spring Boot | Quarkus | NestJS |
|---|---|---|---|
| Pedir un almacén | `spring.config.import: nova-secrets:vault:ms-course` | `nova.secrets.import=vault:ms-course` | opción `imports` de `bootstrap()` |
| Pedirlo desde operaciones | `NOVA_SECRETS_IMPORT` | `NOVA_SECRETS_IMPORT` | `NOVA_SECRETS_IMPORT` |
| Un secreto que puede faltar | `optional:` delante | `optional:` delante | `optional:` delante |
| Dirección y credenciales de Vault | `NOVA_SECRETS_VAULT_ADDRESS`, por defecto `VAULT_ADDR`; `VAULT_TOKEN` o AppRole | igual | igual |
| Región de AWS | `NOVA_SECRETS_AWS_SECRETS_MANAGER_REGION`, por defecto `AWS_REGION` y la cadena del SDK | igual | igual |
| Timeout de cada llamada | `5s` | `5s` | `5s` |
| Un secreto pisa a una variable suelta | sí (`nova.secrets.override`) | sí, con ordinal 350 | sí (`override`) |

**`NOVA_SECRETS_IMPORT` es nueva también en Spring Boot.** El starter de Spring suma la propiedad
`nova.secrets.import` junto a `spring.config.import`, que sigue siendo la forma idiomática. Así quien
opera un servicio pide un almacén con la misma variable en los tres stacks, sin saber en qué
framework está escrito. Es un cambio compatible del starter.

**La referencia es la misma en los tres:** `<fuente>:<referencia>`, con `optional:` delante si puede
faltar, y varias separadas por coma. Un nombre de fuente que no existe corta el arranque y dice qué
dependencia falta.

### Quarkus: `nova-secrets-quarkus-extension`, dentro de `nova-java-23-secrets`

Es la fila «el conector de Quarkus» de la tabla de ADR-041, en el mismo repositorio, con la misma
versión que el resto de la capacidad.

| Módulo | `artifactId` | Qué tiene |
|---|---|---|
| runtime | `nova-secrets-quarkus-extension` | el `ConfigSourceFactory` de SmallRye Config y la lectura de `nova.secrets.*` |
| deployment | `nova-secrets-quarkus-extension-deployment` | los pasos de build: registrar las fuentes y los adaptadores para la imagen nativa |

**Es una extensión de verdad, con su módulo de deployment.** La extensión del estándar de API
(`nova-java-10`) es una librería que se llama extensión. Esta no puede serlo, porque en una imagen
nativa `ServiceLoader` solo encuentra lo que se registró al construirla. El paso de build declara un
`ServiceProviderBuildItem` por cada `SecretSourceProvider` que encuentra en el classpath, y así
agregar un adaptador sigue siendo agregar una dependencia, también en nativo.

**El tipo nuevo en ADR-039.** La regla 3 de ADR-039 pide que un tipo nuevo entre en su tabla con el
ADR que lo introduce. Este introduce el módulo de deployment de una extensión de Quarkus, con la
convención de Quarkus: `nova-<capacidad>-quarkus-extension-deployment`.

**Cómo se resuelven.** Un `ConfigSourceFactory` recibe la configuración que ya existe (las
propiedades y el entorno), la usa como `SecretSettings` para que cada adaptador lea su dirección o su
región, y devuelve una fuente de configuración por referencia. Corre antes de que Quarkus arme el
datasource, que es la regla 1 de ADR-042.

| `nova.secrets.override` | Ordinal | Efecto |
|---|---|---|
| `true`, por defecto | 350 | el secreto gana sobre una variable de entorno (300) |
| `false` | 275 | una variable de entorno gana; el secreto sigue ganando sobre `application.properties` (250) |

**Lo que no se ve.** Quarkus no tiene `/actuator/env`, pero su Dev UI muestra la configuración en
modo desarrollo. Las propiedades que salen de un secreto se marcan como secretas con el mecanismo de
SmallRye Config (`SecretKeys`), así que no aparecen en ningún listado.

**El JSON (pregunta 6 de ADR-042).** Queda como se implementó en Java: el contrato lee con
`jackson-core` 2, solo el parser de streaming, que convive con el Jackson 3 de Spring Boot 4 y con el
Jackson 2 de Quarkus porque Jackson 3 cambió de paquete. La extensión lo prueba en Quarkus.

**Imagen nativa (pregunta 5 de ADR-042).** La fuente del entorno y Vault no usan reflexión: el JSON
se lee en streaming y Vault va por el cliente HTTP del JDK. El adaptador de AWS usa el SDK v2, que
en nativo necesita su configuración. La extensión prueba en nativo el entorno y Vault desde la
primera versión. AWS en nativo entra si la prueba pasa, y si no, se documenta como solo JVM hasta
resolverlo.

### NestJS: el contrato en `core` y un paquete por almacén en el monorepo

| Paquete | Qué tiene |
|---|---|
| `@ahincho/nova-nestjs` (core, ya existe) | el contrato (`SecretSource`), la fuente del entorno y la resolución de `imports` |
| `@ahincho/nova-nestjs-secrets-vault`, nuevo | Vault, motor KV versión 2, con `fetch` de Node y sin cliente de terceros |
| `@ahincho/nova-nestjs-secrets-aws-secrets-manager`, nuevo | AWS Secrets Manager, con `@aws-sdk/client-secrets-manager` |

**Por qué en el monorepo y no en un repositorio nuevo (pregunta 3 de ADR-041).** El contrato de
NestJS ya vive en `core`, y ADR-034 deja ahí el puerto con su implementación por defecto. Si los
adaptadores fueran a otro repositorio, el contrato y sus implementaciones quedarían en dos, y un
cambio en el contrato sería un PR en cada uno: es la alternativa que ADR-041 descartó, «un
repositorio para el contrato y uno por proveedor». Dentro del monorepo salen juntos con changesets.
Cada almacén sigue siendo su propio paquete, así que un servicio que usa Vault no instala el SDK de
AWS.

**Cómo se usa.**

```ts
await bootstrap(AppModule, {
  secrets: {
    prefix: 'SECRET_',              // la convención de la organización, desde su perfil
    imports: ['vault:plaza-bff'],   // se suma a NOVA_SECRETS_IMPORT
  },
});
```

**Cómo se encuentra un adaptador.** Node no tiene `ServiceLoader`. La referencia `vault:` hace que
`core` importe `@ahincho/nova-nestjs-secrets-vault` con un `import()` dinámico, y si el paquete no
está instalado, el arranque se corta diciendo cuál instalar. Así cambiar de almacén sigue siendo
cambiar una dependencia y una línea de configuración, sin tocar código, como pide ADR-042. Una
prueba puede pasar las fuentes a mano con la opción `sources`.

**Las reglas son las de ADR-042, sin excepciones.** Un timeout en cada llamada, con
`AbortSignal.timeout`. Sin reintentos, como en el cliente HTTP (ADR-029). Un error que nombra la
referencia y nunca el contenido. Solo valores escalares. Un secreto binario corta el arranque. El
desdoblado del entorno no cambia: `unfoldSecrets()` sigue siendo síncrono y exportado.

### Cómo se prueba

- **Quarkus:** las reglas con `@QuarkusTest`; los adaptadores contra el mismo Vault y el mismo
  emulador de AWS que usa Java, con Testcontainers; y una prueba en imagen nativa en el PR de release,
  como la del toolchain.
- **NestJS:** las reglas con pruebas unitarias sobre fuentes falsas, y cada adaptador contra Vault y
  el emulador de AWS con Testcontainers para Node.
- **Paridad:** una suite que arranca el mismo secreto en los tres stacks y compara las propiedades
  que salen. Es la prueba de que el JSON de AWS se abre igual en todos.

## Alternativas descartadas

**Usar las extensiones de Quarkiverse**, `quarkus-vault` y `quarkus-amazon-secretsmanager`.
Funcionan bien en nativo, pero es el mismo argumento por el que ADR-042 descartó Spring Cloud: otra
configuración, otras reglas ante un secreto que falta, y un servicio que cambia de framework aprende
otro mecanismo.

**Un `ConfigSource` sin módulo de deployment**, como la extensión del estándar de API. Basta en la
JVM, pero en nativo no encuentra los adaptadores, que es justo lo que la capacidad promete.

**Un repositorio nuevo para los adaptadores de NestJS.** Separa el contrato de sus implementaciones,
como se explica arriba.

**Mover toda la capacidad de NestJS a un repositorio propio**, contrato incluido. Es la forma de
ADR-041 al pie de la letra, pero saca `unfoldSecrets()` de `core`, rompe a quien lo importa y revisa
ADR-025, que juntó los paquetes a propósito.

**Registrar los adaptadores de NestJS a mano en `main.ts`**, sin `import()` dinámico. Es más
explícito, pero cambiar de almacén obliga a tocar código. Queda disponible con la opción `sources`.

## Preguntas abiertas

**1. El consumidor real de NestJS.** `plaza-bff` no tiene datos (ADR-020) y hoy no lee ninguna
credencial: valida el token con las claves públicas de Keycloak. La fuente del entorno sí la usa. Para
los almacenes hay dos caminos:

- **a)** Construirlos ahora con sus pruebas contra Vault y el emulador, y que `plaza-bff` los use
  cuando tenga su primera credencial.
- **b)** Darle al BFF una credencial real que pague una deuda de ADR-043: llamar a los servicios con
  un token de Keycloak propio (*client credentials*), con su secreto en Vault, en vez de que los
  servicios confíen en el BFF sin validar.

Recomendación: **a**, porque **b** es otra capacidad, la autenticación entre servicios, y merece su
propio ADR. Es una excepción a la regla de no agregar superficie sin consumidor, y queda escrita.

**2. AWS Secrets Manager en imagen nativa.** Se decide con la prueba, como se explica arriba.

**3. Si el perfil de UTP en NestJS** (`nova-nestjs-02-profile-utp`) pone el prefijo `SECRET_`, igual
que lo hará el starter de la organización en Java.

## Consecuencias

### Positivas

- Operaciones configura igual un servicio de cualquiera de los tres stacks: las mismas variables, la
  misma forma de pedir un almacén y la misma salida de emergencia.
- Quarkus reusa los adaptadores de Java sin cambiarlos, que es lo que ADR-041 buscaba con
  `ServiceLoader`.
- La primera extensión de Quarkus de Nova con módulo de deployment, y con prueba en nativo.

### Negativas

- **Nova mantiene dos clientes de Vault**, uno en Java y otro en Node, con la misma autenticación y
  los mismos errores.
- **El monorepo de NestJS pasa de tres paquetes a cinco**, y uno arrastra el SDK de AWS a su lockfile.
- **El `import()` dinámico** hace que un paquete que falta se note al arrancar y no al compilar. Por
  eso el error dice qué instalar.

## Referencias

- [ADR-015: Librerías Puras sin Dependencias de Framework](../java/ADR-015-librerias-puras-sin-dependencias-framework.md)
- [ADR-020: ORM para Persistencia](../nest/ADR-020-orm-persistencia.md)
- [ADR-025: Tres Paquetes NestJS en Lugar de Once](../nest/ADR-025-tres-paquetes-en-lugar-de-once.md)
- [ADR-029: Sin Reintentos ni Corte de Circuito en el Cliente HTTP](../nest/ADR-029-sin-reintentos-en-el-cliente-http.md)
- [ADR-034: Lo Duro y lo Reemplazable](ADR-034-puertos-con-implementacion-por-defecto.md)
- [ADR-039: Nombres de Artefacto Derivados del Repositorio](ADR-039-nombres-de-artefacto-derivados-del-repositorio.md)
- [ADR-041: Un Repositorio por Capacidad](../java/ADR-041-un-repositorio-por-capacidad.md)
- [ADR-042: Secretos detrás de un Contrato](ADR-042-secretos-detras-de-un-contrato.md)
- [ADR-043: Plaza, la Plataforma de Compras que Demuestra Nova](ADR-043-plaza-la-plataforma-de-compras.md)
- [ADR-045: La Imagen Nativa de GraalVM, junto a la JVM](../java/ADR-045-imagen-nativa-junto-a-la-jvm.md)
- SmallRye Config, `ConfigSourceFactory` y `SecretKeys`
- Quarkus, *Writing Your Own Extension*: `ServiceProviderBuildItem`
