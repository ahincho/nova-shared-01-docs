# ADR-004: Namespace pe.edu.nova

## Estado
Aceptada (implementada)
**Scope:** `shared` (Java + NestJS)

## Fecha
2026-07-08

## Contexto
Todos los repos usaban un namespace heredado del nombre anterior del producto, que reflejaba un contexto educativo. Con el nombre Nova Platform (ahora simplemente "Nova"), los `groupId`, packages Java, y publishing URLs debian alinearse con la identidad del producto.

## Decision
Migrar todo el namespace a `pe.edu.nova`:

| Nivel | GroupId |
|---|---|
| Librerias puras | `pe.edu.nova.java.libs` |
| Starters | `pe.edu.nova.java.starters` |
| Build tools | `pe.edu.nova.java` |
| BOM/Parent | `pe.edu.nova.java` |
| Plugin ID | `pe.edu.nova.java.spring-boot` |

Packages Java renombrados a `pe/edu/nova/` (~200 archivos modificados), y las clases al prefijo `Nova*`.

Nomenclatura del roadmap: `NOVA-SEMVER`.

## Consecuencias
### Positivas
- Identidad consistente en todo el ecosistema de modulos.
- `groupId` alineado con dominio real (`pe.edu.nova`), listo para Maven Central.
- Nomenclatura limpia y profesional en todos los artefactos publicados.

### Negativas
- Breaking change para cualquier consumidor del namespace anterior (mitigado: no hay consumidores en produccion, version era 0.x).
- Esfuerzo de migracion significativo (~200 archivos), aunque se ejecuto una sola vez.

## Referencias
- `docs/java/06-semantic-versioning-en-java.md` Seccion 12 (NOVA-SEMVER-00b, 00d)
- `docs/java/06-semantic-versioning-en-java.md` Seccion 14
