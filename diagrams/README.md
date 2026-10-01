# Diagramas de Nova Platform

El estado del desarrollo de Nova en seis diagramas: la plataforma entera, cada stack, Plaza y una
matriz de capacidades. Están dibujados con [Excalidraw](https://excalidraw.com) y reflejan las
versiones publicadas al 2026-10-01.

| Diagrama | Qué muestra |
|---|---|
| [Panorama](#panorama) | los repositorios por stack y por nivel de [ADR-001](../adrs/shared/ADR-001-arquitectura-meta-framework-cinco-niveles.md) |
| [Spring Boot](#spring-boot) | qué recibe un servicio Spring Boot y de dónde sale |
| [Quarkus](#quarkus) | lo mismo en Quarkus, con lo que propone [ADR-050](../adrs/java/ADR-050-errores-por-capas-en-quarkus.md) |
| [NestJS](#nestjs) | el monorepo, sus cinco paquetes y el perfil de UTP |
| [Plaza](#plaza) | los servicios de [ADR-043](../adrs/shared/ADR-043-plaza-la-plataforma-de-compras.md), lo que existe y lo planeado |
| [Capacidades](#capacidades) | cada capacidad transversal en los tres stacks: hecha, parcial, pendiente o propuesta |

En todos, **un borde sólido es algo que existe hoy y un borde punteado es algo planeado o sin
código**.

## Panorama

![Panorama de Nova por stack y nivel](00-panorama.svg)

## Spring Boot

![Nova en Spring Boot](01-spring-boot.svg)

## Quarkus

![Nova en Quarkus](02-quarkus.svg)

## NestJS

![Nova en NestJS](03-nestjs.svg)

## Plaza

![Plaza, la plataforma de compras](04-plaza.svg)

## Capacidades

![Capacidades de Nova por stack](05-capacidades.svg)

## Cómo se actualizan

Cada diagrama tiene tres archivos:

| Archivo | Para qué |
|---|---|
| `NN-nombre.excalidraw` | la escena editable: se abre en excalidraw.com con *Open* |
| `NN-nombre.svg` | lo que muestra este README, con la fuente incrustada |
| `src/NN-nombre.json` | la fuente: los elementos en el formato de esqueleto de Excalidraw, con las etiquetas dentro de cada figura |

**Un cambio chico se hace en excalidraw.com.** Se abre el `.excalidraw`, se edita, se guarda encima
y se exporta el SVG con *Export image* → *SVG*, con *Embed scene* apagado. En ese caso `src/` queda
atrás: conviene corregir también el JSON, o el próximo regenerado deshace el cambio.

**Un cambio de contenido se hace en `src/`** y se regenera. `tools/export.mjs` corre la propia
librería de Excalidraw en un Edge sin ventana: convierte el esqueleto, escribe el `.excalidraw` y el
`.svg`, y deja una vista previa en PNG para revisar el resultado antes de subirlo.

```bash
cd diagrams
node tools/gen-matrix.mjs
node tools/export.mjs src/05-capacidades.json 05-capacidades
```

La matriz se genera con `tools/gen-matrix.mjs`, porque son 56 celdas y a mano es fácil
desalinearlas: el estado de cada capacidad se cambia ahí. El script de exportación pide Node 24 y
Microsoft Edge, y descarga Excalidraw 0.18.0 de esm.sh. Los `*.preview.png` no se versionan.

**Cuándo.** Un diagrama se actualiza en el mismo PR que cambia lo que muestra: una versión
publicada, una capacidad que se completa o un repositorio nuevo. Así no se queda atrás.
