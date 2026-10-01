# Nova Docs

The written record behind the Nova Platform: why each decision was taken,
what was rejected, and what is still open. If you want to understand the
platform rather than use it, start here.

The ADRs are written in Spanish; this index is in English so the
structure is readable either way.

## Where things are

```
adrs/
  shared/      cross-stack decisions (Java + NestJS)
  java/        Java-specific
  nest/        NestJS-specific
  versioning/  versioning policy
diagrams/      Excalidraw diagrams of the platform, each stack and Plaza
java/          technical guides for the Java stack
nest/          technical guides for the NestJS stack
ops/           metadata automation scripts
```

## Start with these four

| ADR | Decision |
|---|---|
| [ADR-001](adrs/shared/ADR-001-arquitectura-meta-framework-cinco-niveles.md) | The five-level meta-framework architecture — the shape everything else follows |
| [ADR-015](adrs/java/ADR-015-librerias-puras-sin-dependencias-framework.md) | Core libraries carry no framework dependency; adapters do the wiring |
| [ADR-005](adrs/java/ADR-005-multi-repo-con-bom-coordinador.md) | Multi-repo coordinated by a BOM, rather than a monorepo |
| [ADR-014](adrs/shared/ADR-014-observabilidad-four-golden-signals.md) | The Four Golden Signals as the observability contract |

## All decisions

**Cross-stack** — architecture (001), namespace `pe.edu.nova` (004),
multi-repo with a coordinating BOM (005), conventional commits and
semantic versioning (006), release-please (007), GitHub Packages as the
primary registry (008), multi-registry strategy (009), Actions cache
(010), composite actions and reusable workflows (011), quality and
testing standards (012), Four Golden Signals (014).

**Java** — Gradle as the primary build system (002), Java 25 as the
target (003), deferred GPG signing (013), framework-free libraries (015).

**NestJS** — target Node version (016), pnpm (017), strict TypeScript
(019), ORM and persistence (020), Jest (021), ESLint, Prettier and Husky
(022), Swagger and OpenAPI (023), NestJS itself (024).

**Versioning** — versioning and bump policy (018).

The [ADR index](adrs/README.md) carries the status of each one: accepted,
accepted with a concern, proposed, pending, deprecated or superseded.

## Diagrams

[`diagrams/`](diagrams/README.md) draws the current state: the repositories by
stack and level, what a service receives in Spring Boot, Quarkus and NestJS,
the Plaza services, and a capability matrix across the three stacks. Each one
is an editable `.excalidraw` file with its SVG next to it.

![Nova Platform capabilities by stack](diagrams/05-capacidades.svg)

## Guides

Longer pieces that are not decisions:

- `java/01` — what a meta-framework is, technically
- `java/02` and `nest/02` — maturity assessment per stack
- `java/04` and `java/05` — archetype comparison and adoption
- `java/06` — semantic versioning in Java
- `java/07` — the Quarkus adoption analysis
- `java/08` — DDD utilities and a multi-framework bus
- `java/11` — pipeline cleanup and token hardening
- `java/32` — repository metadata standardisation

## Ops

`ops/` holds the PowerShell that keeps the 28 repositories' GitHub
metadata — description, topics, homepage — consistent, driven by
`nova-platform-metadata.json`.

## The rest of the platform

Every repository is at
[github.com/ahincho?q=nova](https://github.com/ahincho?tab=repositories&q=nova).

## License

Eclipse Public License 2.0 — see [LICENSE](LICENSE).

Copyright © 2026 Angel Hincho.
