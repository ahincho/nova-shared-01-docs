# ADR-041: Un Repositorio por Capacidad, con su Contrato y sus Implementaciones Adentro

## Estado

Propuesta (2026-09-28). La planteó Angel al empezar la capacidad de secretos: «cada feature o
flavour sea un repo», con un contrato único y, por debajo, las implementaciones para cada
proveedor. Queda a su confirmación.
**Scope:** `java`
**Enmienda:** ADR-005, solo para las capacidades nuevas, y la regla 3 de ADR-039, a la que agrega
el tipo «adaptador de un proveedor».
**Primer caso:** [ADR-042](../shared/ADR-042-secretos-detras-de-un-contrato.md), la capacidad de
secretos.

## Fecha

2026-09-28

## Contexto

ADR-005 eligió varios repositorios con un BOM que los coordina, y en la práctica el corte quedó
**por artefacto**: cada librería y cada conector tienen su propio repositorio. Una capacidad queda
repartida entre varios.

| Capacidad | Repositorios | Artefactos |
|---|---|---|
| estándar de API | `nova-java-01`, `nova-java-08`, `nova-java-10` | la librería, el starter de Spring Boot y la extensión de Quarkus |
| enmascarado | `nova-java-04`, `nova-java-08` | la librería y el starter |
| observabilidad | `nova-java-05`, `nova-java-09` | la librería y el starter |

### Lo que cuesta, medido

Un patch en `nova-api-standard` pasa hoy por tres repositorios antes de salir de la propia
capacidad: el cambio y su release en `nova-java-01`, y en `nova-java-08` y `nova-java-10` un PR
que sube la versión y otro de release. Son seis PR para que la capacidad esté completa, y recién
ahí empieza la cadena del BOM, el meta-starter y el parent. En un solo repositorio serían dos: el
cambio y su release.

### Lo que viene tiene más piezas

Las capacidades que siguen —secretos, auditoría, mensajería, CQRS— tienen todas la misma forma
desde el primer día, porque así se decidió en ADR-034: un contrato, la implementación de Nova por
defecto, un adaptador por proveedor y un conector por framework. Secretos sola, con el corte de
hoy, serían cinco repositorios: el contrato, Vault, AWS Secrets Manager, Spring Boot y Quarkus.

### La prueba del invariante 3

Una frontera de paquete se justifica por otro consumidor o por otro ciclo de vida. Las dos
preguntas dan respuestas distintas en una capacidad, y eso es lo que este ADR separa:

- **Consumidores: distintos.** Un servicio que lee sus secretos de Vault no debe arrastrar el SDK
  de AWS. Cada proveedor es un artefacto aparte.
- **Ciclo de vida: el mismo.** Un cambio en el contrato obliga a cambiar cada adaptador, y un
  adaptador no tiene sentido sin el contrato que implementa. Van juntos.

## Decisión

**Cada capacidad nueva de Nova en Java vive en un repositorio propio. Adentro están su contrato,
la implementación de Nova por defecto, un módulo por proveedor y un módulo por framework, y el
repositorio publica todo con una sola versión.**

### La forma de un repositorio de capacidad

| Módulo | Nivel (ADR-001) | `groupId` (ADR-004) | `artifactId` (ADR-039) |
|---|---|---|---|
| el contrato, con la implementación de Nova si no arrastra un proveedor | 1 | `pe.edu.nova.java.libs` | `nova-<capacidad>` |
| un adaptador por proveedor | 1 | `pe.edu.nova.java.libs` | `nova-<capacidad>-<proveedor>` |
| el conector de Spring Boot | 2 | `pe.edu.nova.java.starters` | `nova-<capacidad>-spring-boot-starter` |
| el conector de Quarkus, cuando haga falta | 2 | `pe.edu.nova.java.starters` | `nova-<capacidad>-quarkus-extension` |

La implementación por defecto va dentro del contrato por la misma prueba de ADR-034: si no
arrastra ninguna dependencia de proveedor, separarla solo agrega un artefacto. Si la arrastra, es
un adaptador más.

### Las reglas

1. **El nombre sale de ADR-038 y ADR-039.** El repositorio es `nova-java-<NN>-<capacidad>`, y la
   familia (regla 4 de ADR-039) es `nova-<capacidad>`: con ese nombre van el componente de
   release-please y la clave de SonarCloud. La raíz del build solo agrega módulos y no se publica.
2. **Una sola versión por repositorio.** Un solo componente de release-please, y todos los
   módulos salen con la misma versión. Un adaptador que no cambió se vuelve a publicar con el
   número nuevo, y es más barato que llevar una tabla de qué versión del contrato acepta cada
   adaptador.
3. **Cada proveedor es su propio artefacto.** Un servicio declara el adaptador que usa y nada más.
   Es la regla de que un proveedor va detrás de un puerto, en un paquete opcional.
4. **El contrato descubre sus implementaciones con `ServiceLoader`.** El conector de un framework
   no nombra ningún adaptador, así que el mismo JAR sirve en Spring Boot y en Quarkus, y agregar
   un proveedor es agregar una dependencia.
5. **El BOM gestiona una capacidad con una sola propiedad**, porque todos sus artefactos comparten
   la versión.

### El tipo nuevo en ADR-039

La regla 3 de ADR-039 dice que un tipo nuevo entra en su tabla con el ADR que lo introduce. Este
lo introduce:

| Nivel (ADR-001) | Forma | Ejemplo |
|---|---|---|
| 1, adaptador de un proveedor | `nova-<capacidad>-<proveedor>` | `nova-secrets-vault`, `nova-secrets-aws-secrets-manager` |

El proveedor se escribe con palabras completas, como el resto de la tabla: `aws-secrets-manager`,
no `asm` ni `aws` a secas, porque AWS tiene más de un almacén de secretos.

### Alcance

**Solo las capacidades nuevas.** El estándar de API, el enmascarado y la observabilidad siguen
como están hasta una decisión propia, que es la revisión de ADR-005. Moverlos cambia la URL del
registro, el historial de release-please y el componente de SonarCloud de artefactos que ya tienen
consumidores, y eso merece su propio ADR con su receta.

**NestJS queda afuera.** ADR-025 juntó once paquetes en tres dentro de un monorepo, a propósito, y
este ADR no lo revisa.

## Alternativas descartadas

**Un repositorio por artefacto, como hoy.** Es el costo medido arriba, y crece con cada proveedor:
secretos serían cinco repositorios que siempre cambian juntos.

**Un solo repositorio para todo Java**, como hizo ADR-025 en NestJS. Una sola versión para todo
obliga a publicar el estándar de API para corregir un adaptador de Vault, mezcla en un build los
BOM y parents de Maven con los módulos de Gradle, y es una migración de diecinueve repositorios.
Además se pierde la capacidad como unidad: lo que se revisa, se prueba y se presenta junto.

**Un repositorio para el contrato y uno por proveedor.** Separa lo que tiene el mismo ciclo de
vida: un cambio en el contrato vuelve a ser un PR por repositorio.

## Preguntas abiertas

**1. Si se reagrupan las capacidades que ya existen, y cuándo.** Es la revisión de ADR-005, y
también acortaría la cadena de releases entre el BOM, el meta-starter y el parent.

**2. Si el meta-starter trae las capacidades nuevas por defecto.** Los adaptadores no, porque son
opcionales por definición. El conector de Spring Boot sin ningún adaptador es la duda: con la
implementación del entorno ya hace algo útil, pero agrega una dependencia a todo servicio.

**3. Si NestJS adopta la misma forma para sus adaptadores de proveedor**, por ejemplo uno de Vault
fuera del monorepo, o si entran como un paquete más en él.

## Consecuencias

### Positivas

- Un PR publica una capacidad completa, y el contrato y sus adaptadores nunca quedan
  desalineados.
- Un servicio elige un proveedor con una dependencia.
- El BOM tiene una línea por capacidad, no una por artefacto.
- Cada capacidad se prueba y se presenta como una unidad.

### Negativas

- Un adaptador que no cambió se vuelve a publicar con cada release de su capacidad.
- Un repositorio lleva módulos de Java puro, de Spring Boot y más adelante de Quarkus, así que su
  CI es más pesado que el de un repositorio de un artefacto.
- Conviven dos formas en Java hasta que se decida la pregunta 1.
- El nombre de la familia coincide con el del contrato (`nova-secrets`): la raíz del build y el
  módulo del contrato se llaman igual, y solo el segundo se publica.

## Referencias

- [ADR-001: Arquitectura del Meta-Framework en 5 Niveles](../shared/ADR-001-arquitectura-meta-framework-cinco-niveles.md)
- [ADR-004: Namespace `pe.edu.nova`](../shared/ADR-004-namespace-pe-edu-nova.md)
- [ADR-005: Multi-Repo con BOM Coordinador](ADR-005-multi-repo-con-bom-coordinador.md)
- [ADR-025: Tres Paquetes NestJS en Lugar de Once](../nest/ADR-025-tres-paquetes-en-lugar-de-once.md)
- [ADR-034: Lo Duro y lo Reemplazable](../shared/ADR-034-puertos-con-implementacion-por-defecto.md)
- [ADR-038: Nombres de Repositorio por Tecnología y Número](../shared/ADR-038-nombres-de-repositorio-por-tecnologia.md)
- [ADR-039: Nombres de Artefacto Derivados del Repositorio](../shared/ADR-039-nombres-de-artefacto-derivados-del-repositorio.md)
- [ADR-042: Secretos detrás de un Contrato](../shared/ADR-042-secretos-detras-de-un-contrato.md)
