# ADR-020: ORM para Persistencia (Prisma vs TypeORM)

## Estado

**No aplica.** Cerrada sin elegir.
**Scope:** `nest`
Se reabre si alguna vez un servicio NestJS es dueño de datos.
**Reabierta (2026-10-02)** por [ADR-056](../shared/ADR-056-plaza-fase-1-catalogo-y-pagos-en-nestjs.md): los pagos de
Plaza son el primer servicio NestJS dueño de datos, y usan TypeORM como dependencia propia. La
plataforma sigue sin capa de persistencia hasta que haya un segundo.

## Fecha

2026-09-07.

## Contexto

El placeholder planteaba elegir entre Prisma y TypeORM para los servicios NestJS. La pregunta
venía de asumir que un servicio NestJS de este stack tiene base de datos.

**Ninguno la tiene, y no por ahora: por diseño.** Los once servicios NestJS de A303 son de dos
tipos, y los dos son sin estado:

- **BFF** -siete-: compone respuestas para una pantalla llamando a servicios de aguas arriba.
- **ACL** -cuatro-: traduce el modelo de un sistema externo al modelo propio.

La persistencia vive en la capa de microservicios, que son dieciséis repositorios **Quarkus sobre
Java**. Sus decisiones de datos son las de `adrs/java/`, y un ORM de Node no tiene nada que decir
ahí.

## Decisión

**No se elige ORM, y la plataforma no ofrece capa de persistencia.**

Elegir uno ahora significaría publicarlo -o al menos documentarlo- sin un solo consumidor que lo
ejercite. Un módulo de la plataforma que nadie usa no es neutro: envejece, se copia por
imitación, y decide por adelantado una discusión que corresponde tener con el caso real delante.

## Consecuencias

### El chequeo de disponibilidad no mira ninguna base

`NovaHealthModule` recibe `readinessChecks: []` y ahí se queda. Un servicio que sí tenga datos
algún día le pasará el suyo; el mecanismo ya existe y no hace falta decidir el ORM para tenerlo.

### Si esto se reabre, la pregunta cambia

No será «Prisma o TypeORM» en abstracto, sino qué necesita **ese** servicio: si es lectura de un
esquema que no controla -que es lo típico de un ACL- puede que la respuesta no sea un ORM sino un
cliente SQL a secas.

### Los secretos ya están resueltos, y no por acá

Cuando llegue el caso, las credenciales no se inventan: en esta cuenta el task definition inyecta
el JSON entero de Secrets Manager en una variable (`SECRET_DB`), y la aplicación lo parsea. Está
documentado del lado de infraestructura.

## Referencias

- `adrs/java/`, donde vive la persistencia de verdad
- ADR-014, sobre las señales que sí observa la plataforma
