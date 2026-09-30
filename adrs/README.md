# Architecture Decision Records (ADRs) — Nova Platform

Registro de decisiones arquitectonicas y tecnicas del meta-framework **Nova**.

## Estructura

```
docs/adrs/
  shared/      Decisiones cross-stack (Java + NestJS)
  java/        Decisiones especificas del stack Java
  nest/        Decisiones especificas del stack NestJS
  versioning/  Decisiones de politica de versionado (cross-stack)
```

## Convenciones

- **Aceptada:** Decision tomada y en vigor.
- **Aceptada (con concern):** Vigente pero con un punto debil documentado.
- **Propuesta:** Documentada, pendiente de ejecucion o aprobacion.
- **Pendiente:** Placeholder, no desarrollada todavia.
- **Deprecada:** Ya no aplica.
- **Reemplazada por ADR-XXX:** Sustituida por otra decision.

## ADRs Compartidos (`shared/`)

Decisiones aplicables a Java y NestJS.

| # | ADR | Estado | Tema |
|---|---|---|---|
| 001 | [Arquitectura del Meta-Framework en 5 Niveles](shared/ADR-001-arquitectura-meta-framework-cinco-niveles.md) | Aceptada | Arquitectura |
| 004 | [Namespace `pe.edu.nova`](shared/ADR-004-namespace-pe-edu-nova.md) | Aceptada | Estructura |
| 006 | [Conventional Commits y Semantic Versioning](shared/ADR-006-conventional-commits-y-semantic-versioning.md) | Aceptada | Versioning |
| 007 | [release-please para Automatizacion de Releases](shared/ADR-007-release-please-para-automatizacion.md) | Aceptada (solo Java, ver ADR-028) | Versioning |
| 008 | [GitHub Packages como Registry Principal](shared/ADR-008-github-packages-como-registry-principal.md) | Aceptada | Publishing |
| 009 | [Estrategia Multi-Registry](shared/ADR-009-estrategia-multi-registry.md) | Aceptada | Publishing |
| 010 | [GitHub Actions Cache para Build Performance](shared/ADR-010-github-actions-cache-para-build.md) | Aceptada | Performance |
| 011 | [Composite Actions y Reusable Workflows](shared/ADR-011-composite-actions-y-reusable-workflows.md) | Aceptada | CI/CD |
| 012 | [Estandares de Calidad y Testing](shared/ADR-012-estandares-de-calidad-testing.md) | Aceptada | Calidad |
| 014 | [Observabilidad: Four Golden Signals](shared/ADR-014-observabilidad-four-golden-signals.md) | Aceptada | Observabilidad |
| 030 | [Contrato de Plataforma Versionado](shared/ADR-030-contrato-de-plataforma-versionado.md) | Propuesta | Arquitectura |
| 031 | [El Módulo de Errores por Capas, con Trazabilidad](shared/ADR-031-modulo-de-errores-por-capas-con-trazabilidad.md) | Aceptada | Arquitectura |
| 032 | [Observabilidad como Puerto Conectable](shared/ADR-032-observabilidad-como-puerto-conectable.md) | Propuesta | Observabilidad |
| 033 | [Que es Nucleo, que es Comun Opcional y que es Plugin](shared/ADR-033-nucleo-comun-y-plugins.md) | Propuesta | Arquitectura |
| 034 | [Lo Duro y lo Reemplazable: Reglas en el Núcleo, Convenciones Detrás de un Puerto](shared/ADR-034-puertos-con-implementacion-por-defecto.md) | Aceptada | Arquitectura |
| 035 | [Fallos de Upstream Clasificados con el Registro de RFC 9209](shared/ADR-035-fallos-de-upstream-rfc-9209.md) | Aceptada | Errores |
| 036 | [Perfiles de Organización: Cómo una Organización Adapta Nova sin Forkearla](shared/ADR-036-perfiles-de-organizacion.md) | Aceptada | Arquitectura |
| 037 | [El Borde: Cómo Entra la Correlación y Quién Escribe la Identidad](shared/ADR-037-borde-correlacion-e-identidad.md) | Aceptada | Observabilidad |
| 038 | [Nombres de Repositorio por Tecnología y Número](shared/ADR-038-nombres-de-repositorio-por-tecnologia.md) | Aceptada | Estructura |
| 039 | [Nombres de Artefacto Derivados del Repositorio](shared/ADR-039-nombres-de-artefacto-derivados-del-repositorio.md) | Aceptada | Estructura |
| 042 | [Secretos detrás de un Contrato](shared/ADR-042-secretos-detras-de-un-contrato.md) | Aceptada | Arquitectura |
| 043 | [Plaza, la Plataforma de Compras que Demuestra Nova](shared/ADR-043-plaza-la-plataforma-de-compras.md) | Aceptada | Producto |
| 047 | [La Idempotencia de las Operaciones, detrás de un Contrato](shared/ADR-047-idempotencia-detras-de-un-contrato.md) | Aceptada | Arquitectura |

## ADRs Java (`java/`)

Decisiones especificas del stack Java (Spring Boot, Quarkus, Micronaut).

| # | ADR | Estado | Tema |
|---|---|---|---|
| 002 | [Gradle 9.x como Build System Principal](java/ADR-002-gradle-como-build-system-principal.md) | Aceptada | Build System |
| 003 | [Java 25 como Version Objetivo](java/ADR-003-java-25-como-version-objetivo.md) | Aceptada* | Build System |
| 005 | [Multi-Repo con BOM Coordinador](java/ADR-005-multi-repo-con-bom-coordinador.md) | Aceptada | Estructura |
| 013 | [Firma GPG Preparada pero Diferida](java/ADR-013-firma-gpg-preparada-diferida.md) | Propuesta | Seguridad |
| 015 | [Librerias Puras sin Dependencias de Framework](java/ADR-015-librerias-puras-sin-dependencias-framework.md) | Aceptada | Arquitectura |
| 041 | [Un Repositorio por Capacidad](java/ADR-041-un-repositorio-por-capacidad.md) | Aceptada | Estructura |
| 044 | [El Toolchain de Java: Plugins de Convención de Gradle](java/ADR-044-toolchain-de-java.md) | Aceptada | Build System |
| 045 | [La Imagen Nativa de GraalVM, junto a la JVM](java/ADR-045-imagen-nativa-junto-a-la-jvm.md) | Aceptada | Build System |
| 046 | [Las Imágenes Base: Distroless por Defecto, Docker Hardened como Opción](java/ADR-046-imagenes-base-distroless.md) | Aceptada | Build System |

*ADR-003 tiene un concern abierto sobre soportar Java 21 LTS como minimo.

## ADRs de Versioning (`versioning/`)

Decisiones sobre politica de versionado y bump. Exclusivo del stack Java: el ADR propio de NestJS que ADR-018 anunciaba es [ADR-028](nest/ADR-028-changesets-y-versionado-cero-x.md), escrito el 2026-09-07.

| # | ADR | Estado | Tema |
|---|---|---|---|
| 018 | [Politica de Versioning y Bump para Nova Platform](versioning/ADR-018-politica-de-versioning-y-bump.md) | Aceptada (implementada) | Versioning |

## ADRs NestJS (`nest/`)

Decisiones especificas del stack NestJS. **El stack entro en alcance el 2026-09-05**, con tres
paquetes publicados en `ahincho/nova-nestjs`. **Ya no queda ningun placeholder sin redactar.**

| # | ADR | Estado | Tema |
|---|---|---|---|
| 016 | [Node.js 24 como Version Objetivo](nest/ADR-016-node-version-objetivo.md) | Aceptada | Build System |
| 017 | [pnpm como Package Manager](nest/ADR-017-pnpm-package-manager.md) | Aceptada (implementada) | Build System |
| 019 | [TypeScript en Modo Estricto](nest/ADR-019-typescript-estricto.md) | Aceptada (implementada) | Lenguaje |
| 020 | [ORM para Persistencia](nest/ADR-020-orm-persistencia.md) | No aplica | Persistencia |
| 021 | [Framework de Testing](nest/ADR-021-jest-testing.md) | Aceptada (implementada) | Testing |
| 022 | [Linter y Formateador](nest/ADR-022-eslint-prettier-husky.md) | Parcialmente aceptada | Calidad |
| 023 | [Swagger/OpenAPI](nest/ADR-023-swagger-openapi.md) | Aceptada (implementada) | Documentacion |
| 024 | [NestJS 12 como Framework Backend](nest/ADR-024-nestjs-framework.md) | Aceptada (implementada) | Framework |
| 025 | [Tres Paquetes NestJS en Lugar de Once](nest/ADR-025-tres-paquetes-en-lugar-de-once.md) | Aceptada | Arquitectura |
| 026 | [Generador de Servicio y Reglas de Arquitectura](nest/ADR-026-generador-de-servicio-y-reglas-de-arquitectura.md) | Aceptada (implementada) | Arquitectura |
| 027 | [Una Imagen de Contenedor para Todos los Servicios](nest/ADR-027-imagen-de-contenedor-compartida.md) | Aceptada (implementada) | Despliegue |
| 028 | [Changesets y Versionado `0.x` para NestJS](nest/ADR-028-changesets-y-versionado-cero-x.md) | Aceptada (implementada) | Versioning |
| 029 | [Sin Reintentos ni Corte de Circuito en el Cliente HTTP](nest/ADR-029-sin-reintentos-en-el-cliente-http.md) | Aceptada | Resiliencia |

ADR-021 se cerró el 2026-09-06 en Vitest y está publicado en `@ahincho/nova-nestjs` 0.6.0.
Con eso ADR-016 dejó de depender de él: la bandera `--experimental-vm-modules` desapareció y el
piso de Node bajó de `>=24.9` a `>=24`.

ADR-022 está aceptada por mitades, pero **ya no queda nada que ejecutar**. El linter se cerró
el 2026-09-06 en oxlint y está publicado en 0.7.0; el formateador se queda en Prettier, con el
disparador de revisión atado a que oxfmt publique su 1.0.

ADR-024 se redactó el 2026-09-06 al subir a NestJS 12, publicado en 0.8.1. El placeholder decía
«NestJS 10.x» y llevaba dos versiones mayores de atraso.

El 2026-09-07 se cerraron los cuatro placeholders que quedaban. ADR-017 y ADR-019 documentan
decisiones que ya estaban implementadas desde el primer commit y nunca se habían escrito; se
redactan ahora porque sus consecuencias dejaron de ser teóricas -la 0.8.0 salió publicada rota
por una de ellas-. ADR-023 se implementó el mismo día, publicado en 0.12.0.

**ADR-020 se cierra sin elegir.** La pregunta asumía que un servicio NestJS de este stack tiene
base de datos, y ninguno la tiene por diseño: los BFF y los ACL son sin estado, y la persistencia
vive en la capa Quarkus. Se reabre si alguna vez un servicio NestJS es dueño de datos.

ADR-028 se escribió el 2026-09-07 al revisar el estado del stack antes de publicar la 0.14.0.
No documenta una decisión nueva: Changesets y `0.x` estaban vivos desde el primer commit y no
los había escrito nadie. Lo que sí corrige es que ADR-007 reclamaba alcance sobre NestJS y
ADR-018 anunciaba un ADR que nunca llegó, así que los dos describían el stack de una forma que
no coincidía con el código. **Un ADR aceptado que dice algo falso se lee como norma**, y ese es
el motivo de cerrarlo antes de una publicación y no después.

ADR-029 documenta una **ausencia**, que es el tipo de ADR que más falta hace y menos se escribe.
El cliente HTTP no reintenta ni abre circuitos, y eso nunca se decidió: no se escribió. Un
revisor que abriera el módulo no podía saber si faltaba o si se había descartado. Se cierra en
«no», con las tres razones y con el disparador que obliga a revisarlo. Mismo espíritu que
ADR-020, que se cerró sin elegir porque la pregunta no aplicaba.

ADR-026 se agrega el mismo día para el generador de servicio y sus reglas de arquitectura
ejecutables, que hasta entonces sólo estaban documentadas en el README del paquete.

## Formato

Cada ADR sigue el template:

```
# ADR-NNN: Titulo

## Estado
## Fecha
## Contexto
## Decision
## Consecuencias (Positivas / Negativas)
## Referencias
```
