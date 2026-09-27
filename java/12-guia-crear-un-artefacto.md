# Guía para crear un artefacto Java

> Aplica [ADR-039](../adrs/shared/ADR-039-nombres-de-artefacto-derivados-del-repositorio.md),
> aceptado el 2026-09-27. Si el ADR cambia, esta guía cambia con él.

Sirve para crear un repositorio que publica un artefacto, o para agregarle un módulo publicable a
uno que ya existe. Para renombrar un artefacto que ya se publicó, la receta y el orden están en la
sección *Migración* de ADR-039.

## 1. Antes de crear nada

Tres preguntas, en orden. Si alguna responde que no, el código va dentro de un artefacto que ya
existe.

1. **¿Tiene un consumidor real hoy?** Nova no agrega superficie de API sin alguien que la use.
2. **¿Tiene otro consumidor u otro ciclo de vida que el artefacto más cercano?** Es la única razón
   para abrir una frontera de paquete. ADR-025 la aplicó en NestJS, y once paquetes quedaron en
   tres.
3. **¿En qué nivel de ADR-001 cae?** De ahí salen el `groupId` y el tipo del nombre.

## 2. Los nombres

Se deciden juntos y antes del primer commit, porque cada uno sale del anterior.

| Qué | Regla | Ejemplo: un conector de observabilidad para Quarkus |
|---|---|---|
| Repositorio | `nova-java-<NN>-<nombre>`, con el siguiente número sin usar de `java` (ADR-038) | `nova-java-23-observability-quarkus-extension` |
| `groupId` | según el nivel (ADR-004) | `pe.edu.nova.java.starters` |
| `artifactId` | `nova-<nombre>` (ADR-039, reglas 1 a 3) | `nova-observability-quarkus-extension` |
| Paquete Java | el `groupId` seguido de la capacidad | `pe.edu.nova.java.starters.observability.quarkus`, como `nova-java-10` |
| Componente de release-please | el `artifactId` | `nova-observability-quarkus-extension` |
| Clave de SonarCloud | `ahincho_<artifactId>` | `ahincho_nova-observability-quarkus-extension` |

Los números 20 a 22 de `java` quedaron retirados cuando los ejemplos pasaron a su propia categoría,
y no se reutilizan. Un número se asigna una sola vez.

| Nivel (ADR-001) | `groupId` | Forma del `artifactId` |
|---|---|---|
| 1, librería pura | `pe.edu.nova.java.libs` | `nova-<capacidad>` |
| 2, conector de Spring Boot | `pe.edu.nova.java.starters` | `nova-<capacidad>-spring-boot-starter` |
| 2, conector de Quarkus | `pe.edu.nova.java.starters` | `nova-<capacidad>-quarkus-extension` |
| 3, starter del meta-framework | `pe.edu.nova.java.starters` | `nova-<framework>-starter` |
| 4, BOM y parent | `pe.edu.nova.java` | `nova-[<framework>-]bom`, `nova-<framework>-parent` |
| 5, plugin y arquetipo | `pe.edu.nova.java` | `nova-<framework>-<herramienta>-plugin`, `nova-<framework>-archetype` |
| ejemplo, no se publica | `pe.edu.nova.java.examples` | `nova-example-<tecnología>-<nombre>` |

Antes de seguir, el nombre pasa estas cuatro comprobaciones:

- no lleva `java` ni el número;
- el framework va después de la capacidad;
- el tipo sale de la tabla de ADR-039 y está escrito completo, sin abreviar;
- `nova-<nombre>` coincide con el nombre del repositorio sin la tecnología y el número.

## 3. El build

Gradle es el build por defecto (ADR-002). Maven queda para los BOM, los parents y los arquetipos.
Conviene copiar de un repositorio del mismo nivel:

| Para | Copiar de |
|---|---|
| una librería pura | `nova-java-01-api-standard` |
| un conector de Spring Boot | `nova-java-09-observability-spring-boot-starter` |
| un conector de Quarkus | `nova-java-10-api-standard-quarkus-extension` |
| un BOM | `nova-java-13-bom` |

`settings.gradle.kts`:

```kotlin
rootProject.name = "nova-observability-quarkus-extension"
```

`gradle.properties`:

```properties
version=0.1.0-SNAPSHOT
group=pe.edu.nova.java.starters
```

**La versión de `gradle.properties` es un marcador.** El workflow de publicación escribe ahí la
versión del tag antes de compilar, en el paso *Sync version from tag to gradle.properties*. La
versión real vive en el manifest de release-please y en el tag.

`build.gradle.kts`, el bloque de publicación:

```kotlin
publishing {
    publications {
        create<MavenPublication>("mavenJava") {
            from(components["java"])
        }
    }
    repositories {
        maven {
            name = "GitHubPackages"
            url = uri("https://maven.pkg.github.com/ahincho/nova-java-23-observability-quarkus-extension")
            credentials {
                username = System.getenv("GITHUB_ACTOR")
                password = System.getenv("GITHUB_TOKEN")
            }
        }
    }
}
```

Si el artefacto depende de otros paquetes de Nova, declara un repositorio Maven de lectura por cada
uno, con `NOVA_PACKAGES_READ_TOKEN`: el `GITHUB_TOKEN` de un workflow no puede leer los paquetes de
otro repositorio. `nova-java-10` tiene el ejemplo.

## 4. La versión y la publicación

`.release-please-config.json`:

```json
{
  "packages": {
    ".": {
      "component": "nova-observability-quarkus-extension",
      "package-name": "pe.edu.nova.java.starters:nova-observability-quarkus-extension",
      "release-type": "java",
      "include-component-in-tag": false,
      "skip-snapshot": true,
      "bump-minor-pre-major": true,
      "bump-patch-for-minor-pre-major": true,
      "draft": false,
      "prerelease": false
    }
  }
}
```

`include-component-in-tag: false` no es opcional. Deja los tags como `vX.Y.Z`, que es lo que espera
el workflow de publicación, y permite corregir el componente más adelante sin perder el historial
(ADR-039, regla 5).

`.release-please-manifest.json`:

```json
{
  ".": "0.0.0"
}
```

**El manifest de un repositorio nuevo arranca en `0.0.0`**, y así la primera versión es 1.0.0,
como pide ADR-018. release-please toma `0.0.0` como «sin versión previa» y propone su versión
inicial, 1.0.0. Si el manifest arranca en `1.0.0`, lo toma como ya publicado y la primera versión
sale 1.1.0: le pasó a `nova-java-07-architecture-rules`, cuyo primer tag es `v1.1.0`. El ejemplo de
la sección 6 de ADR-018 dice `1.0.0` y conviene corregirlo.

Los workflows se copian del repositorio modelo:

- `ci.yml`, con `sonar-project-key: ahincho_<artifactId>`;
- `release-please.yml`, con `permissions: contents: write` y `pull-requests: write` a nivel de
  workflow;
- `publish-on-tag.yml`, que publica cuando release-please crea el tag y, justo después, llama a
  `nova-verify-publication` (regla 6 de ADR-039):

  ```yaml
      - name: Verify the publication can be downloaded
        if: steps.detect.outputs.should_publish == 'true'
        uses: ahincho/nova-shared-02-pipelines/.github/actions/nova-verify-publication@main
        with:
          group-id: pe.edu.nova.java.starters
          artifact-ids: nova-observability-quarkus-extension
          version: ${{ steps.detect.outputs.tag }}
          token: ${{ github.token }}
  ```

## 5. La configuración del repositorio

Estos pasos son de Angel, porque son configuración de seguridad o secretos:

- **Permitir que Actions abra pull requests.** Sin esto, release-please falla con *GitHub Actions
  is not permitted to create or approve pull requests*. El token por defecto sigue siendo de solo
  lectura:

  ```bash
  GH_TOKEN=$(gh auth token --user ahincho) gh api -X PUT repos/ahincho/<repositorio>/actions/permissions/workflow -f default_workflow_permissions=read -F can_approve_pull_request_reviews=true
  ```

- **`NVD_API_KEY`**, para el análisis de OWASP.
- **`NOVA_PACKAGES_READ_TOKEN`**, si el artefacto lee otros paquetes de Nova.

SonarCloud todavía no analiza ningún repositorio de Nova: el workflow se salta el análisis mientras
no exista el secreto `NOVA_SONAR_TOKEN`. La clave se deja escrita igual, para que el día que se
active ya esté alineada.

## 6. Que otros lo encuentren

- **El BOM.** Una librería pura entra en `nova-bom`; un conector entra en el BOM de su framework,
  `nova-spring-boot-bom` o `nova-quarkus-bom`. Cada uno con una propiedad `<artifactId>.version`
  y su entrada en `dependencyManagement`.
- **El README** abre con la tabla de coordenadas: `groupId`, `artifactId`, versión y registro.
- **La descripción del repositorio en GitHub** dice qué capacidad cubre y para qué framework.

## 7. La primera publicación

1. El primer push a `main` hace que release-please abra el PR de release de 1.0.0.
2. Al mergearlo, release-please crea el tag `v1.0.0` y `publish-on-tag.yml` publica.
3. **Se comprueba que se descarga**, no solo que el run quedó en verde. Lo hace
   `nova-verify-publication` dentro del mismo run: si el paso falla, la versión no quedó
   disponible aunque `publish` haya terminado bien. Para comprobarlo a mano, sin pedir nunca la
   ruta antes de publicar:

   ```bash
   GH_TOKEN=$(gh auth token --user ahincho); curl -s -o /dev/null -w '%{http_code}\n' -L -H "Authorization: Bearer $GH_TOKEN" https://maven.pkg.github.com/ahincho/<repositorio>/pe/edu/nova/java/starters/<artifactId>/1.0.0/<artifactId>-1.0.0.pom
   ```

   Tiene que responder 200, igual que el `.jar`. En julio una extensión se publicó cinco veces con
   el run en verde sin que nadie pudiera descargarla, y así fue como se descubrió.
