# ADR-036: Perfiles de Organización: Cómo una Organización Adapta Nova sin Forkearla

## Estado

Aceptada (2026-09-22). El perfil de la primera organización vive en un repositorio público propio,
fuera del monorepo de Nova; ver «Dónde vive un perfil».
**Scope:** `shared` (Java + NestJS)
**Completa:** ADR-034, que separa la regla de la convención en cada módulo pero no dice cómo se
entregan juntas las convenciones de una organización. **Cubre el eje que ADR-025 no consideró:**
ADR-025 ordenó los paquetes por consumidor técnico -runtime contra herramientas-, no por
organización.

## Fecha

2026-09-22

## Contexto

La tesis de Nova tiene dos mitades: una forma correcta y genérica de construir servicios, y
extensiones para que cada organización la adapte a como trabaja. ADR-034 resolvió la primera
mitad módulo por módulo: la regla queda en el núcleo y la convención detrás de un puerto. **La
segunda mitad no tiene mecanismo**, y el núcleo lo compensa llevando las convenciones de la primera
organización como si fueran de todos.

### Lo que hoy es de una organización y está en el núcleo, medido

| Valor | Dónde vive hoy | Qué haría el genérico |
|---|---|---|
| El puerto sale primero de `APP_PORT` | `bootstrap.ts`, `DEFAULT_PORT_VARIABLES` | `PORT`, que es la convención de Node y de casi todo orquestador |
| Los ambientes son `development`, `qa` y `production` | `config/app-environment.ts`, `APP_ENVIRONMENTS` | la lista de la organización; `qa` no es universal |
| Viajan `x-user-id` y `x-tenant-id` a todo upstream | `observability/request-context.ts` | sólo el id de correlación |
| El log de error usa `traceId` y `statusCode` | `api/filters/all-exceptions.filter.ts` | lo que decida ADR-032 |
| Los roles salen de `realm_access.roles` | `auth/tokens.ts` | `roles`, el claim de RFC 9068; `realm_access` es de Keycloak |
| El id del usuario se pasa a mayúsculas y pierde la `@` | `auth/tokens.ts`, `normalizeUserId` | sin normalizar |
| Los roles `offline_access`, `uma_authorization` y `default-roles-*` se descartan | `auth/tokens.ts` | nada que descartar: son de Keycloak |
| `secrets: true` descubre las variables `SECRET_*` | `config/secrets.ts` | el mecanismo sí es genérico; el prefijo no |
| El generador emite `.env.example` con `qa` y un CI para `dev`, `qa` y `master` | `schematics` | las ramas y ambientes de la organización |

Ninguno está mal para esa organización. El problema es que **para cualquier otra son defaults
equivocados que tiene que deshacer**, opción por opción y servicio por servicio, sin saber cuáles
son: nada en el código distingue «esto es Nova» de «esto es de alguien». El de los roles es el más
caro: un token de cualquier proveedor que no sea Keycloak no trae `realm_access`, y sale 401.

Hay uno que parece de un proveedor y no lo es: el usuario sale de `preferred_username`, que es un
claim estándar de OpenID Connect. Se queda como default.

### Pasar las opciones servicio por servicio no alcanza

Todo lo de la tabla ya se puede cambiar con una opción, así que técnicamente nadie está bloqueado.
Pero una organización con veinte servicios escribiría las mismas nueve opciones veinte veces, y la
deriva entre esas copias es exactamente el problema que Nova existe para cerrar. Lo que falta no es
configurabilidad, es **un lugar donde una organización declare sus convenciones una sola vez**.

## Decisión

**Un perfil de organización es un paquete con las convenciones de una organización, que se
declara una vez y ajusta las implementaciones por defecto de Nova. Nova no publica ningún perfil;
cada organización publica el suyo.**

### El orden en que se aplica

```
defaults de Nova  <  perfil de la organización  <  opciones del servicio
```

Nova trae el valor genérico, el perfil lo ajusta para la organización y el servicio sigue pudiendo
cambiar cualquier cosa (invariante 2). Un perfil **no puede tocar una regla del núcleo**: sólo ve
las mismas opciones y los mismos puertos que ve un servicio, así que lo que ADR-034 dejó fijo sigue
fijo.

### La forma

```ts
export const acme = defineProfile({
  name: 'acme',
  // Lo que se decide antes de que exista la aplicación o fuera de los módulos.
  bootstrap: {
    portVariables: ['APP_PORT', 'PORT'],
    secrets: { prefix: 'SECRET_' },
    globalPrefix: 'api/v1',
  },
  // Una clave por módulo, con las mismas opciones que recibe su forRoot().
  health: { legacyPath: 'api/v1/health' },
  auth: { rolesClaim: 'realm_access.roles' },
  apiStandard: { standard: new NovaEnvelopeStandard({ codes: acmeCodes }) },
});

// app.module.ts
NovaModule.forRoot({ profile: acme, config: { load: [academic] } });

// main.ts
void bootstrap(AppModule, { profile: acme });
```

**Se declara en dos lugares, y es a propósito.** Los secretos se desdoblan antes de que exista la
aplicación, así que `bootstrap()` necesita el perfil antes de poder leer el módulo; y el módulo se
configura cuando se importa, antes de que `bootstrap()` corra. Para que las dos declaraciones no
se separen, `NovaModule` registra el nombre del perfil y **`bootstrap()` corta el arranque si no
coincide** con el suyo.

### Los defaults del núcleo pasan a ser genéricos

Cada fila de la tabla vuelve al valor genérico, y el valor de la primera organización se muda a su
perfil. Tres filas esperan: las dos de observabilidad dependen de ADR-032 y se mueven cuando ese ADR
se decida, porque este no elige por él los nombres de los campos ni la cabecera de correlación; y
la lista de ambientes espera a la pregunta abierta 1. La del generador espera a que el generador
sepa recibir un perfil, que es trabajo propio.

Es un cambio incompatible para quien dependía de esos defaults sin saberlo. Lleva el codemod que
pide el invariante 4: `nova migrate profile <paquete>` agrega el perfil en `NovaModule.forRoot()` y
en `bootstrap()`, y un servicio que lo corre queda contestando igual que antes.

### Dónde vive un perfil

**Fuera de Nova, en un repositorio de la organización.** Pasa las dos pruebas del invariante 3:
tiene otro consumidor -los servicios de esa organización- y otro ciclo de vida -cambia cuando la
organización decide, no cuando Nova publica-. Meterlo en el monorepo de Nova ataría las dos
cadencias y obligaría a publicar Nova para corregir un código de error de una organización.

Tiene además una consecuencia que no es técnica: **un perfil describe cómo trabaja una
organización por dentro** -su proveedor de identidad, cómo inyecta sus secretos, cómo se llaman sus
campos de log-. Publicarlo es una decisión de quien responde por esas convenciones, no de Nova.

**Para la primera organización se decidió un repositorio público propio**, fuera del monorepo de
Nova y con su propio versionado. Se evaluaron otras dos opciones: un repositorio privado de la
organización, que no expone nada pero saca el caso real del portafolio, y un paquete dentro del
monorepo, que es lo más rápido pero ata los dos ciclos de vida. El costo aceptado es el de la
sección anterior: sus convenciones quedan a la vista.

El servicio de ejemplo de Nova demuestra el mecanismo con un perfil ficticio, para que el ejemplo no
dependa del paquete de ninguna organización.

### El primer perfil trae su catálogo de errores

La primera organización necesita, además de las convenciones de la tabla, nombrar a su manera los
fallos que ADR-035 clasifica: qué código ve el cliente ante un timeout del upstream, cómo se llaman
sus capas en los logs, qué salto de su arquitectura es el borde. Eso también es convención, y va en
el mismo perfil: **un solo paquete por organización, no uno por tema.** Un paquete de errores aparte
tendría el mismo consumidor y el mismo ciclo de vida que el perfil, y el invariante 3 no lo
justifica.

## Alternativas descartadas

**Dejar las convenciones de la primera organización como defaults.** Es lo de hoy. Contradice la
tesis: para toda organización que no sea la primera, Nova arranca equivocado.

**Opciones servicio por servicio, sin perfil.** Funciona y ya existe. Se descarta por la deriva:
veinte copias de nueve opciones es el problema, no la solución.

**Perfiles dentro del monorepo de Nova.** Ata el ciclo de vida de cada organización al de Nova: un
código de error mal nombrado en un perfil obligaría a publicar una versión de la plataforma.

**Elegir el perfil por variable de entorno** (`NOVA_PROFILE=acme`). El código del perfil tiene que
estar instalado igual, así que la variable no ahorra nada, y cambia un error de compilación -un
perfil mal escrito- por uno de arranque.

**Herencia de configuración, al estilo de un `extends` de tsconfig.** Resuelve los valores pero no
los puertos: un perfil también reemplaza implementaciones, y eso pide código, no un JSON.

## Preguntas abiertas

**1. Qué lista de ambientes es la genérica.** `development`, `test` y `production` es la costumbre
de Node, pero `appEnvironment()` hoy devuelve un tipo cerrado. Abrirlo a cualquier cadena lo hace
genérico y le quita al compilador la validación que hoy tiene.

**2. Cómo se versiona un perfil contra Nova.** Un perfil escrito para una versión puede usar una
opción que la siguiente renombra. Lo natural es que el perfil declare a Nova como `peerDependency`
con rango, pero en 0.x cada minor puede romper.

**3. El nombre, en Java.** En Spring «perfil» ya significa otra cosa, y colisiona. En Spring un
perfil de organización sería un starter con defaults; en Quarkus, una extensión con configuración
por defecto. Puede que convenga otro nombre para los tres stacks.

**4. El orden respecto de ADR-032.** Las filas de observabilidad no se pueden mover hasta que ese
ADR fije los nombres genéricos. Se puede publicar el mecanismo antes y mudarlas después, a costa
de un segundo cambio incompatible.

## Consecuencias

### Positivas

- Una organización adopta Nova declarando un perfil, no nueve opciones por servicio.
- Los defaults de Nova pasan a ser correctos para cualquiera, que es lo que la tesis promete.
- Queda escrito qué es de Nova y qué es de alguien: todo lo que está en un perfil es convención.
- El ejemplo público demuestra la extensión sin exponer a ninguna organización.

### Negativas

- **Es un cambio incompatible** para quien usaba los defaults de la primera organización, y aunque
  el codemod lo cubre, alguien tiene que correrlo.
- **Se declara en dos lugares.** El chequeo de `bootstrap()` convierte el olvido en un error de
  arranque, pero sigue siendo una segunda línea que escribir.
- Cada organización mantiene un paquete más, con su publicación y su versionado.
- La paridad con Java se paga por organización: un perfil que vale para NestJS no sirve en Quarkus.

## Referencias

- [ADR-025: Tres Paquetes NestJS en Lugar de Once](../nest/ADR-025-tres-paquetes-en-lugar-de-once.md)
- [ADR-032: Observabilidad como Puerto Conectable](ADR-032-observabilidad-como-puerto-conectable.md)
- [ADR-034: Lo Duro y lo Reemplazable](ADR-034-puertos-con-implementacion-por-defecto.md)
- [ADR-035: Fallos de Upstream Clasificados con el Registro de RFC 9209](ADR-035-fallos-de-upstream-rfc-9209.md)
- `nova-nestjs`: `packages/core/src/bootstrap.ts`, `packages/core/src/config/app-environment.ts`,
  `packages/core/src/config/secrets.ts`, `packages/core/src/observability/request-context.ts`,
  `packages/core/src/auth/tokens.ts`, `packages/schematics/src/service/files/base/`
