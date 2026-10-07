# ADR-057: FastAPI como Stack de Nova, con un Conector que Instala el Estándar de API

## Estado

Propuesta (2026-10-07). Angel pidió crear el primer adaptador de Nova para FastAPI, empezando por el
manejo de errores, para usarlo en sus productos en Python; el primero es el backend de Busco Chamba.
La implementación está en
[`nova-fastapi-01-platform`](https://github.com/ahincho/nova-fastapi-01-platform), PR #1.
**Scope:** `python` (stack nuevo).
**Aplica:** el módulo de errores de [ADR-031](../shared/ADR-031-modulo-de-errores-por-capas-con-trazabilidad.md),
los puertos de [ADR-034](../shared/ADR-034-puertos-con-implementacion-por-defecto.md), los perfiles de
[ADR-036](../shared/ADR-036-perfiles-de-organizacion.md), la correlación de
[ADR-037](../shared/ADR-037-borde-correlacion-e-identidad.md) y los nombres de
[ADR-038](../shared/ADR-038-nombres-de-repositorio-por-tecnologia.md) y
[ADR-039](../shared/ADR-039-nombres-de-artefacto-derivados-del-repositorio.md).
**Primer consumidor:** `busco-chamba-01-backend` (FastAPI 0.141, Python 3.14), de la organización
`nxtep-peru`.

## Fecha

2026-10-07

## Contexto

Nova tiene tres stacks, Spring Boot, Quarkus y NestJS, y los tres responden igual desde ADR-031: el
mismo sobre, los mismos códigos y los mismos textos. Python no tiene nada. Lo único que existe es lo
de CI en `nova-shared-02-pipelines`: la acción `nova-setup-python` y el workflow
`reusable-build-python.yml`, agregados el 2026-09-23 para un servicio de FastAPI que ya los usa.

Ese servicio es el backend de Busco Chamba, y muestra lo que pasa sin la plataforma. Medido el
2026-10-07:

- Los errores salen en tres formas: `{"detail": "texto"}` en los propios, `{"detail": [ ... ]}` en
  inglés en la validación de FastAPI y texto plano en un 500 no previsto.
- El cliente distingue los casos por el status, que ya comparten causas distintas: un 403 por un
  consentimiento que falta y otro por un origen no autorizado.
- Dos respuestas de la búsqueda devolvían el motivo técnico: nombres de variables de entorno y lo que
  contestaba cada portal.
- Un primer intento de corregirlo dentro del servicio fue hacia RFC 9457, que ADR-031 descartó como
  formato por defecto. Es el riesgo de que cada servicio resuelva lo suyo.

## Decisión

**Python entra a Nova como un stack más, con FastAPI como framework. Su primer repositorio,
`nova-fastapi-01-platform`, publica un solo paquete, `nova-fastapi`, que trae el estándar de API de
ADR-031 y se instala en un servicio con `install_nova(app)`.**

### El nombre

La tecnología del repositorio es el framework, `fastapi`, como `nestjs` en NestJS y no como `java`
en Java: un servicio de Python sin FastAPI no tiene qué usar de este paquete. El paquete sigue la
regla 1 de ADR-039 sin el número, y su import es el mismo nombre con guion bajo.

| Repositorio | Paquete | Import |
|---|---|---|
| `nova-fastapi-01-platform` | `nova-fastapi` | `nova_fastapi` |

Es la forma de `nova-nestjs-01-platform` → `@ahincho/nova-nestjs`. Python no tiene scope, así que el
dueño no va en el nombre.

### Dónde vive cada cosa

La misma separación que ADR-031 pide en los otros stacks, dentro de un paquete:

| Subpaquete | Qué tiene | Importa FastAPI |
|---|---|---|
| `nova_fastapi.errors` | el modelo por capas, los tres puertos con la implementación de Nova, el catálogo | no |
| `nova_fastapi.api_standard` | el sobre `ApiResponse[T]`, el estándar de Nova y su serializador | no |
| `nova_fastapi.observability` | el id de la petición: la variable de contexto y su middleware | solo el middleware |
| `nova_fastapi.api` | `install_nova`, `NovaRoute`, los manejadores de excepciones, la documentación | sí |

Un paquete y no dos, como ADR-025 decidió para NestJS: el núcleo y el conector se versionan juntos, y
un servicio declara una sola dependencia. Que el núcleo no importe el framework lo vigila un contrato
de import-linter en el CI, igual que la regla de oxlint sobre `@ahincho/nova-nestjs/errors`, y el
paquete carga el conector solo cuando se pide.

### Lo mismo que los otros stacks

- **El sobre:** `{ success, status, data, errors }`, con `metadata.traceId` en los errores. Es la forma
  de NestJS, la intersección de los dos sobres de hoy (pregunta abierta 1 de ADR-030).
- **Los errores:** las cuatro capas con sus tipos, las mismas fábricas (`DomainError.not_found`, en
  snake_case), la tabla de status, el catálogo con sus textos en español, la regla de que un 5xx no
  muestra ni su código ni su mensaje ni su proveedor, y `Retry-After`.
- **El reparto de ADR-034:** se clasifica la excepción, se escribe una línea de log con todo, y los
  puertos reciben el fallo saneado.
- **El log:** el nivel lo decide la capa, y los campos `statusCode`, `traceId`, `layer`, `type`,
  `code` y `upstream` llevan los mismos nombres que el índice de los otros stacks.
- **La suite de contrato:** los nueve casos de ADR-031, en `tests/test_contract.py`.
- **Los perfiles:** lo de Nova, encima el perfil, encima el servicio.

### Cómo se instala en FastAPI

`install_nova(app)` reemplaza los manejadores de FastAPI para sus excepciones y la validación, agrega
uno para las de Nova y un middleware para lo que nadie atrapó, abre el contexto de cada petición y
ajusta el esquema de `/docs`. Tres decisiones son propias de FastAPI:

- **Lo no previsto se responde en un middleware y no en el manejador de `Exception`.** El de Starlette
  corre por fuera de todos los middlewares, y su respuesta sale sin las cabeceras de CORS: el navegador
  recibe el 500 y no puede leer su cuerpo.
- **El éxito se envuelve en una clase de ruta, `NovaRoute`**, y no en un middleware. Así FastAPI
  valida y documenta `ApiResponse[T]` con el modelo del endpoint, que es lo que hace el interceptor de
  NestJS con su documentación propia. El status del sobre es el que declara la ruta.
- **La validación responde 400 con `BAD_REQUEST`**, como pide ADR-031 y como Spring Boot y Quarkus, y
  no el 422 de FastAPI.

### La distribución

GitHub Packages, el registro de ADR-008, no tiene registro de Python. El paquete se instala desde el
repositorio, fijado a un tag que publica release-please con `release-type: python`:

```toml
dependencies = ["nova-fastapi @ git+https://github.com/ahincho/nova-fastapi-01-platform@v0.1.0"]
```

El repositorio es público, como el resto de Nova, así que no hace falta un token para instalarlo.

## Alternativas descartadas

- **RFC 9457 como formato de Python.** Dejaría a Python respondiendo distinto que los otros tres
  stacks. ADR-031 ya lo descartó como formato por defecto; queda como un `ErrorSerializer` propio.
- **Dos paquetes, `nova-api-standard` y `nova-api-standard-fastapi`, como en Java.** En Java la
  coordinación de versiones la hace el BOM; en Python, como en npm, la tiene que hacer el productor.
- **Un middleware para envolver el éxito.** Tendría que leer y reescribir el cuerpo ya serializado, y
  `/docs` seguiría mostrando el modelo sin el sobre.
- **PyPI.** Sería la forma natural en Python, pero publicaría Nova fuera del registro de la plataforma
  sin que nadie lo haya decidido.

## Preguntas abiertas

1. **¿Se acepta `fastapi` como tecnología en los nombres de ADR-038?** Es la primera fuera de `java`,
   `nestjs` y `shared`. La recomendación es sí, por la razón de NestJS: el paquete solo sirve con ese
   framework.
2. **¿Se registra el tipo de artefacto en la tabla de ADR-039?** La regla 3 pide que un tipo nuevo
   entre con el ADR que lo introduce. La recomendación es sumar la fila «paquete de Python de un
   framework, `nova-<framework>`».
3. **¿La validación de NestJS pasa a `BAD_REQUEST`?** Hoy es el único stack que responde
   `VALIDATION_ERROR`, distinto de lo que pide ADR-031.
4. **¿El contador `nova.errors{layer,code}`?** Python no tiene todavía observabilidad. La
   recomendación es sumarlo con el puerto de observabilidad de ADR-032 y no antes.

## Consecuencias

### Positivas

- Un servicio de FastAPI responde igual que uno de Spring Boot, Quarkus o NestJS, con una línea.
- Busco Chamba no mantiene su propio formato de errores, y sus clientes leen lo mismo que leerían de
  cualquier otro servicio de Nova.
- La suite de contrato corre en un cuarto stack, que es lo que ADR-031 pedía para saber que los
  stacks no se separan.

### Negativas

- **Un cuarto stack que mantener**, con su propio toolchain: uv, ruff, pytest e import-linter.
- **Sin registro de paquetes.** Instalar desde git no resuelve rangos de versiones: un servicio fija
  un tag y lo sube a mano.
- **El status del sobre de un éxito es el que declara la ruta.** Un endpoint que contesta otro status
  arma su propia respuesta.

## Referencias

- [ADR-008: GitHub Packages como Registry Principal](../shared/ADR-008-github-packages-como-registry-principal.md)
- [ADR-025: Tres Paquetes NestJS en Lugar de Once](../nest/ADR-025-tres-paquetes-en-lugar-de-once.md)
- [ADR-030: Contrato de Plataforma Versionado](../shared/ADR-030-contrato-de-plataforma-versionado.md)
- [ADR-031: El Módulo de Errores por Capas, con Trazabilidad](../shared/ADR-031-modulo-de-errores-por-capas-con-trazabilidad.md)
- [ADR-034: Lo Duro y lo Reemplazable](../shared/ADR-034-puertos-con-implementacion-por-defecto.md)
- [ADR-036: Perfiles de Organización](../shared/ADR-036-perfiles-de-organizacion.md)
- [ADR-037: El Borde: Cómo Entra la Correlación y Quién Escribe la Identidad](../shared/ADR-037-borde-correlacion-e-identidad.md)
- [ADR-038: Nombres de Repositorio por Tecnología y Número](../shared/ADR-038-nombres-de-repositorio-por-tecnologia.md)
- [ADR-039: Nombres de Artefacto Derivados del Repositorio](../shared/ADR-039-nombres-de-artefacto-derivados-del-repositorio.md)
- FastAPI, *Custom Request and APIRoute class*
- Starlette, *Exceptions*: `ServerErrorMiddleware` y `ExceptionMiddleware`
