# ADR-037: El Borde: Cómo Entra la Correlación y Quién Escribe la Identidad

## Estado

Aceptada (2026-09-23), con la pregunta abierta 1 sin decidir.
**Scope:** `shared` (Java + NestJS)
**Completa:** ADR-036, cuyo primer perfil no pudo declarar dos convenciones de su organización.
**No decide por ADR-032:** este ADR fija cómo entra el id por el borde y quién escribe la
identidad; con qué formato viaja el contexto entre servicios sigue siendo decisión de ADR-032.

## Fecha

2026-09-23

## Contexto

Al escribir el perfil de la primera organización (ADR-036) quedaron dos convenciones que Nova no
puede expresar. Al revisarlas apareció una tercera cosa, que no es una convención sino un defecto.

### El id de correlación entra con otro nombre

Nova usa una sola cabecera para tres cosas: lee el id de la primera de `correlationHeaders`, lo
devuelve en la respuesta con ese nombre y lo reenvía a los upstreams con ese mismo nombre. Si falta,
lo genera. En la primera organización el borde funciona distinto:

| | Nova hoy | La primera organización |
|---|---|---|
| El frontend lo manda como | `x-request-id` | `transaction-id` |
| Si falta o no es un UUID | se genera uno | 400 `VALIDATION_ERROR` |
| Se devuelve como | `x-request-id` | `transaction-id` |
| Viaja hacia adentro como | `x-request-id` | `x-request-id` |

Entrada, respuesta y propagación son tres decisiones, y una sola cabecera no alcanza para las tres.
Hay un detalle que lo agrava: la política de CORS de Nova sólo permite `x-request-id`, así que un
navegador ni siquiera puede mandar `transaction-id`.

### El rol no viaja

La primera organización pasa a sus capas internas el usuario en `user-id` y su rol en `user-role`.
Nova escribe el usuario con `auth.userIdHeader` y no tiene nada para el rol.

### La identidad que manda el cliente se reenvía

Nova copia de la petición que llega cada cabecera de `correlationHeaders`, y por defecto esa lista
incluye `x-user-id`, que es también la cabecera con la que la autenticación manda el usuario. En una
ruta protegida el guard la reescribe con lo que dice el token. **En una ruta `@Public()` el guard
termina antes, y lo que escribió el cliente viaja hacia adentro como si fuera el usuario.** No es
la convención de nadie: es un defecto, y está en los defaults.

## Decisión

**Cómo entra el id por el borde es una opción de observabilidad, separada de cómo viaja. Y cuando un
servicio declara autenticación, la identidad que viaja hacia adentro la escribe sólo la
autenticación.**

### La entrada del id se separa de su propagación

```ts
NovaModule.forRoot({
  observability: {
    // Cómo viaja hacia adentro: sin cambios.
    correlationHeaders: ['x-request-id', 'user-id', 'user-role'],
    // Cómo entra y cómo se devuelve.
    requestId: { accept: ['transaction-id', 'x-request-id'] },
  },
  auth: { userIdHeader: 'user-id', roleHeader: 'user-role' },
});
```

- **`accept`**: de qué cabeceras se toma el id que manda el llamador, en orden. Gana la primera que
  traiga un valor. Por defecto, la cabecera de propagación: lo mismo que hoy.
- **`echo`**: con qué nombre se devuelve en la respuesta. Por defecto, la primera de `accept`.

Hacia adentro el id viaja con la primera de `correlationHeaders`, y **es el mismo valor en todas
partes**: el que se devuelve, el que viaja, el `traceId` de cada línea de log y el del cuerpo de un
error. El logger lee la misma lista en el mismo orden, así que no importa si pino o el contexto de
la plataforma lo resuelven primero.

La política de CORS permite las cabeceras de `accept` y expone la de `echo` sin que haya que
declararlas otra vez. Con eso el servicio de la primera organización lee `transaction-id` y la
reenvía como `x-request-id` a sus servicios internos, que siguen leyendo lo de siempre. El perfil
declara `accept: ['transaction-id', 'x-request-id']` y sirve igual al BFF y a los servicios de
adentro.

**Si falta, se genera**, como hoy. Rechazar es la pregunta abierta 1.

### La autenticación escribe la identidad, y sólo ella

- **`auth.roleHeader`**: con qué cabecera viaja el rol hacia los upstreams. No tiene default: Nova no
  propaga el rol si nadie lo pide.
- **Regla del núcleo, no una opción:** cuando el servicio declara `auth`, las cabeceras que escribe
  la autenticación -la del usuario y, si se declara, la del rol- **nunca se copian de la petición
  que llega**, en ninguna ruta, tampoco en una `@Public()`. En una ruta protegida salen del token;
  en una pública no viajan.

Es una regla y no una opción por lo que dice ADR-034: la regla es lo que el núcleo garantiza, y una
opción para apagarla sería una opción para que un cliente se haga pasar por otro usuario ante las
capas de adentro. **Un servicio que confía en una identidad escrita antes que él** -un gateway que
ya validó el token y la inyecta- **no declara `auth`**, y entonces la copia como cualquier otra
cabecera de `correlationHeaders`.

Para la primera organización esto simplifica el perfil: declara `user-id` y `user-role` para todos
sus servicios. En un BFF salen del token; en un servicio interno, que no declara `auth`, se copian
de lo que puso la capa de arriba.

### El consumidor es el perfil, no el ejemplo

El servicio de ejemplo no declara `auth`, así que no tiene cómo usar `roleHeader`, y no tiene un
borde con una cabecera propia que justifique `accept`. El consumidor real de estas opciones es el
perfil de la primera organización, que las prueba levantando un servicio de verdad. Agregarle al
ejemplo una autenticación sólo para ejercitar la opción lo volvería menos parecido a un servicio
real, que es para lo que existe.

### Con los otros stacks y con ADR-032

El contrato vale igual para Java (invariante 5): tres decisiones separadas sobre la cabecera de
correlación -entrada, respuesta y propagación- y la identidad escrita sólo por la autenticación.
Los starters de Java todavía no tienen capa HTTP; lo implementan cuando la tengan.

Si ADR-032 lleva la propagación a `traceparent`, `accept` y `echo` no cambian: siguen describiendo el
borde, que es otra cosa. Y un UUID ocupa 16 bytes, lo mismo que el trace-id de `traceparent`, así
que el id que manda el frontend puede ser el de toda la traza. Cómo se hace esa conversión es de
ADR-032.

## Alternativas descartadas

**Llamar `transaction-id` a la cabecera de correlación en toda la cadena.** Alcanza con la opción
que ya existe, pero obliga a cambiar a la vez todos los servicios internos, que hoy leen
`x-request-id`, incluidos los de Java. Resuelve el borde moviendo el problema hacia adentro.

**Un middleware propio en cada BFF.** Es lo de hoy: cada servicio lo resuelve a su manera, y la
deriva entre esas copias es el problema que Nova existe para cerrar.

**Una función `auth.propagate(principal)` que devuelva todas las cabeceras.** Es más flexible, pero
la regla necesita saber qué cabeceras son de la autenticación para no copiarlas de la petición, y
una función no lo dice hasta que se ejecuta.

**Dejar la regla como opción.** Convierte un defecto de seguridad en una configuración, y el
default de hoy es justo el caso que falla.

## Preguntas abiertas

**1. Si el borde rechaza un id que falta.** La primera organización responde 400 cuando el frontend
no manda `transaction-id` o no es un UUID. Rechazar garantiza que el id del frontend sea el de la
traza; generar no rompe a un cliente que no lo manda. Si se rechaza, hay que decidir además dónde:
las sondas de salud nunca traen el id, y rechazarlas saca la tarea del balanceador. Mientras no se
decida, Nova genera, y un BFF de la primera organización sobre Nova es más permisivo que el de hoy.

**2. Si `x-tenant-id` sigue entre las cabeceras por defecto.** ADR-036 dejó esa fila esperando a
ADR-032. La regla de este ADR cierra el caso del usuario, pero el tenant no lo escribe la
autenticación: sigue copiándose de lo que mande quien llama, también en el borde.

## Consecuencias

### Positivas

- La primera organización declara en su perfil el borde y el rol, y sus BFF dejan de resolverlos
  cada uno con su propio código.
- Una ruta pública deja de reenviar la identidad que escriba el cliente.
- Entrada, respuesta y propagación quedan como tres decisiones con nombre, que es lo que ADR-032
  necesita para cambiar la propagación sin tocar el borde.

### Negativas

- **Cambia el comportamiento de las rutas públicas** en los servicios que declaran `auth`: lo que
  antes viajaba deja de viajar. Es el arreglo, pero quien dependía de eso lo va a notar. No lleva
  codemod porque no cambia ninguna firma; va en el changelog como corrección de seguridad.
- Dos opciones más en observabilidad y una en autenticación, y hay que explicar por qué la cabecera
  de correlación tiene dos nombres.
- Hasta que se decida la pregunta 1, un BFF de la primera organización sobre Nova genera el id en
  vez de rechazar.

## Referencias

- [ADR-032: Observabilidad como Puerto Conectable](ADR-032-observabilidad-como-puerto-conectable.md)
- [ADR-034: Lo Duro y lo Reemplazable](ADR-034-puertos-con-implementacion-por-defecto.md)
- [ADR-036: Perfiles de Organización](ADR-036-perfiles-de-organizacion.md)
- `nova-nestjs`: `packages/core/src/observability/request-context.ts`,
  `packages/core/src/observability/request-context.middleware.ts`,
  `packages/core/src/observability/logger.ts`, `packages/core/src/auth/auth.guard.ts`,
  `packages/core/src/config/cors.ts`
- `nova-profile-utp`: `src/profile.ts`
