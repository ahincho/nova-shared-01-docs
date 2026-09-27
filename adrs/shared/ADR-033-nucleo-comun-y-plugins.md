# ADR-033: Que es Nucleo, que es Comun Opcional y que es Plugin

## Estado

Propuesta
**Scope:** `shared` (Java + NestJS)
**Relacionada con:** ADR-025, que colapso once paquetes NestJS en tres. Este ADR define la regla
que evita deshacer aquello por accidente.

## Fecha

2026-09-20

## Contexto

La plataforma tiene piezas que todo servicio debe llevar y piezas que solo algunos necesitan, pero
**esa distincion no esta escrita en ningun lado**. Se manifiesta de tres formas distintas segun el
modulo, y ninguna de las tres esta justificada por una regla.

En NestJS hoy conviven tres mecanismos:

| Mecanismo | Modulos | Como se activa |
|---|---|---|
| Siempre, sin apagado | `api-standard`, `api`, `observability`, `http`, `health` | `NovaModule.forRoot()` los importa incondicionalmente |
| Opcional en tiempo de ejecucion | `config`, `auth` | solo si la aplicacion declara la clave |
| Opcional fuera del modulo | `openapi` | por `bootstrap({ openapi })` |

Los tres significan cosas distintas y ninguno quita nada del arbol de dependencias. **Un modulo
«opcional» hoy se instala, se compila y se empaqueta igual**; lo unico que cambia es si se activa.

### Que arrastra cada modulo, medido

| Modulo | Lineas | Dependencias externas propias |
|---|---|---|
| `api-standard` | 177 | **ninguna** |
| `api` | 447 | `rxjs` (ya viene con NestJS) |
| `auth` | 480 | **ninguna** |
| `config` | 630 | `@nestjs/config` |
| `health` | 365 | `@nestjs/terminus` |
| `http` | 548 | `undici` |
| `observability` | 545 | `nestjs-pino`, `pino`, `undici` |
| `openapi` | 277 | `@nestjs/swagger` |

Dos cosas saltan de esta tabla, y las dos son contraintuitivas.

**`auth` es el modulo mas grande despues de `config` y no arrastra nada.** Son 480 lineas que hoy
ya son opcionales en ejecucion. Sacarlas a un paquete aparte no le quitaria una sola dependencia a
nadie: solo agregaria un paquete que publicar.

**`openapi` es de los mas chicos y es el que mas arrastra**: `@nestjs/swagger` viaja en todo
servicio, exponga documentacion o no.

La conclusion es que **el tamano del modulo no predice nada**, y que tampoco lo hace la sensacion
de que algo sea accesorio. Sin una regla, «esto deberia ser un plugin» se decide por intuicion, y
la intuicion se equivoca en los dos casos anteriores.

### El riesgo de equivocarse tiene precedente

ADR-025 colapso once paquetes NestJS en tres, porque nadie instalaba las piezas sueltas y cada
cambio en una arrastraba bumps en cascada. **«Hagamoslo un plugin» aplicado sin criterio reconstruye
exactamente esos once paquetes.** Este ADR existe tanto para permitir los plugins que hacen falta
como para impedir esa regresion.

## Decision

**Tres niveles, y una prueba que decide a cual pertenece cada modulo.**

### La prueba

> Un modulo sale del nucleo y se convierte en paquete **solo si al quitarlo desaparece una
> dependencia que el servicio no tendria de otro modo, o si su ciclo de vida es distinto al de la
> plataforma.**

Que algo sea opcional **no basta**. `auth` es opcional y no arrastra nada: se queda. La
opcionalidad se expresa con una opcion, no con un paquete.

Es la misma prueba del invariante de fronteras -distinto consumidor o distinto ciclo de vida-
aplicada a esta pregunta concreta, y es lo que hace que la respuesta sea verificable en vez de
opinable: se mira el arbol de dependencias, no el criterio de quien pregunta.

### Nivel 1 — Nucleo

Viaja siempre y **no tiene apagado**. Un servicio sin esto no es un servicio Nova, y ofrecer una
bandera para desactivarlo seria ofrecer la opcion de salirse del contrato.

- El sobre de respuesta y el catalogo de errores (`api-standard`).
- El filtro global de excepciones y la validacion (`api`).
- La correlacion de peticion: generar, propagar y loguear el identificador (`observability`, su
  parte de contexto).
- El arranque (`bootstrap`).

Es deliberadamente corto. Todo lo que esta aca es lo que ADR-030 va a declarar como contrato:
**si se puede apagar, no puede ser contrato.**

### Nivel 2 — Comun opcional

Viaja en el mismo paquete que el nucleo y **se activa declarandolo**. No sale a un paquete propio
porque no quitaria dependencias relevantes, y la frontera ya es visible en el objeto de opciones.

`config`, `http`, `health`, `auth`.

`health` y `http` hoy se activan siempre; pasan a declararse. Es el unico cambio de comportamiento
que este nivel introduce, y es pequeno: un servicio que no llama a nadie no necesita cliente HTTP.

### Nivel 3 — Plugin

Paquete aparte, se instala o no. **Solo entra aca lo que pasa la prueba.**

- El adaptador de observabilidad con su SDK, segun ADR-032. Pasa la prueba: quitarlo saca el SDK
  de telemetria del arbol.
- `openapi` es el otro candidato claro, porque quitarlo saca `@nestjs/swagger`. Ver preguntas
  abiertas: que casi todo servicio documente su API es un argumento en contra que hay que resolver
  con datos y no con principios.

### El nivel 2 no es un consuelo

Vale la pena decirlo porque es donde va a caer casi todo: que un modulo sea de nivel 2 no lo hace
menos importante ni candidato a ascender. **Es la respuesta correcta para la mayoria**, y el nivel
3 es la excepcion cara que hay que justificar cada vez.

## Alternativas descartadas

**Un paquete por modulo, y que el servicio arme lo suyo.** Es la lectura literal de los cinco
niveles de ADR-001 y es lo que habia antes de ADR-025. Se descarta por lo que ya se midio: nadie
instalaba las piezas sueltas y el costo de publicacion se pagaba igual.

**Todo en el nucleo, sin niveles.** Es practicamente lo de hoy y es defendible por simplicidad. Se
descarta porque no permite lo que ADR-032 necesita: un servicio que no lleve el SDK de telemetria
en su arbol. Sin nivel 3, esa decision no se puede implementar.

**Decidir por peso: lo grande afuera, lo chico adentro.** La tabla de arriba lo refuta sola.
`auth` es grande y no arrastra nada; `openapi` es chico y arrastra swagger.

**Banderas de compilacion en vez de paquetes** -tree shaking, `sideEffects`, compilacion
condicional-. Quitan codigo del artefacto final pero no de `node_modules` ni del lockfile, asi que
no resuelven la auditoria de dependencias ni el tiempo de instalacion, que es la mitad del costo.

## Preguntas abiertas

**1. Si `openapi` sale o se queda.** La prueba dice que sale: quitarlo saca `@nestjs/swagger`. El
argumento en contra es que casi todo servicio expone documentacion, y entonces el paquete extra lo
instalan todos y no se gano nada. **Se resuelve contando** cuantos servicios reales lo desactivan,
no discutiendolo.

**2. Como se ve el nivel 3 en Java.** En NestJS un plugin es un paquete npm que se instala. En
Spring Boot la activacion es por classpath, asi que «no instalarlo» es exactamente la misma
operacion y encaja bien. En Quarkus, en cambio, buena parte de la configuracion ocurre en tiempo
de construccion y una extension no es solo una dependencia. Puede que el nivel 3 no signifique lo
mismo en los tres stacks, y eso afecta al invariante de paridad.

**3. Que pasa con `pino-pretty`.** Es dependencia de produccion y solo se usa en el camino de
desarrollo, cargado por nombre como transporte de pino. Sale en toda imagen de contenedor sin que
nadie lo ejecute ahi. No es un nivel, es un descuido, pero se arregla en el mismo movimiento.

**4. Si el nivel 1 puede crecer.** Hoy queda corto a proposito. Cuando ADR-031 entregue el modulo
de errores por capas, parte de el es contrato y parte no, y habra que decidir donde cae cada mitad.

## Consecuencias

### Positivas

- «Esto deberia ser un plugin» pasa a tener una respuesta verificable mirando el arbol de
  dependencias.
- Protege el resultado de ADR-025: la prueba rechaza la mayoria de las extracciones, que es lo que
  hay que hacer.
- Desbloquea ADR-032, que sin un nivel 3 definido no se puede implementar.
- El nivel 1 queda como la lista de lo que el contrato de ADR-030 puede declarar, y esa
  correspondencia es util en las dos direcciones.

### Negativas

- **Activar `http` y `health` en vez de recibirlos es un cambio incompatible**, chico pero real:
  todo servicio existente tiene que declararlos. Necesita codemod, y es de los que se automatizan
  bien.
- **La prueba es dura con casos legitimos.** Un modulo que no arrastra dependencias pero que solo
  usa un servicio de cada diez se queda en el nucleo igual. Es el precio de tener una regla y no
  un criterio, y se paga a proposito.
- **Tres niveles son tres cosas que explicar** a quien llega. Hoy hay tres mecanismos sin nombre,
  lo cual es peor, pero la comparacion honesta no es contra cero.
- El nivel 3 vuelve a introducir el costo de publicacion que ADR-025 quiso eliminar. Acotado a los
  casos que pasan la prueba, pero existe.

## Referencias

- [ADR-001: Arquitectura del Meta-Framework en 5 Niveles](ADR-001-arquitectura-meta-framework-cinco-niveles.md)
- [ADR-025: Tres Paquetes NestJS en Lugar de Once](../nest/ADR-025-tres-paquetes-en-lugar-de-once.md)
- [ADR-030: Contrato de Plataforma Versionado](ADR-030-contrato-de-plataforma-versionado.md)
- [ADR-032: Observabilidad como Puerto Conectable](ADR-032-observabilidad-como-puerto-conectable.md)
- `nova-nestjs`: `packages/core/src/nova.module.ts`, `packages/core/src/bootstrap.ts`,
  `packages/core/package.json`
