# Canonical metadata for 16 Nova Platform repositories
# Used by apply-metadata.ps1 to fix descriptions, topics, homepage, and labels
# Last updated: 2026-09-28

$repos = @(
    # === Multi-stack (CI/CD, IaC, BOM, Docs) ===
    @{
        name = "nova-shared-01-docs"
        description = "Documentacion del meta-framework Nova Platform: ADRs (shared, java, nest), guias tecnicas (semantic versioning, evaluacion de madurez, comparativa de archetypes) y scripts de automatizacion operativa."
        topics = @("adrs", "docs", "documentation", "guides", "meta-framework", "nova-platform")
    },
    @{
        name = "nova-java-13-bom"
        description = "Bill of Materials (BOM) del stack Java de Nova Platform: nova-bom para las libs puras y un BOM por framework (Spring Boot, Quarkus y Micronaut)."
        topics = @("bom", "dependency-management", "java", "meta-framework", "micronaut", "nova-platform", "quarkus", "spring-boot")
    },
    @{
        name = "nova-shared-02-pipelines"
        description = "Workflows reutilizables de GitHub Actions para CI/CD del meta-framework Nova Platform (build, quality, publish para Maven y Gradle)."
        topics = @("build-automation", "ci-cd", "github-actions", "gradle", "maven", "nova-platform", "reusable-workflows")
    },
    @{
        name = "nova-shared-03-infrastructure"
        description = "Infraestructura como codigo (Docker Compose) del stack de observabilidad Nova Platform: OpenTelemetry Collector, Tempo, Loki, Mimir, Pyroscope y Grafana."
        topics = @("docker-compose", "grafana", "infrastructure-as-code", "loki", "mimir", "nova-platform", "observability", "opentelemetry", "pyroscope", "tempo")
    },

    # === Java: Libs puras (framework-agnostic) ===
    @{
        name = "nova-java-01-api-standard"
        description = "Libreria pura Java de estandares API: ApiResponse/ApiError, HATEOAS links, PageInfo, FilterCriteria, RateLimitInfo, HttpStatusCode y UserAgentParser."
        topics = @("api", "framework-agnostic", "java", "library", "nova-platform")
    },
    @{
        name = "nova-java-02-date-utils"
        description = "Libreria pura Java de utilidades de fechas: formateo, parseo, calculo relativo y helpers de zona horaria. Sin dependencias de Spring."
        topics = @("date", "framework-agnostic", "java", "library", "nova-platform", "utils")
    },
    @{
        name = "nova-java-03-mapper-utils"
        description = "Libreria pura Java de mapeo entre objetos (MapStruct-like) y helpers de conversion. Sin dependencias de Spring."
        topics = @("framework-agnostic", "java", "library", "mapper", "nova-platform", "utils")
    },
    @{
        name = "nova-java-04-mask-utils"
        description = "Libreria pura Java de enmascaramiento de datos sensibles (tarjetas de credito, emails, telefonos). Sin dependencias de Spring."
        topics = @("framework-agnostic", "java", "library", "masking", "nova-platform", "pii", "utils")
    },
    @{
        name = "nova-java-05-observability-utils"
        description = "Libreria pura Java de utilidades de observabilidad: metricas, trazas y logs sin acoplamiento a Spring. Helpers para OpenTelemetry SDK."
        topics = @("framework-agnostic", "java", "library", "nova-platform", "observability", "opentelemetry", "utils")
    },

    # === Java: Starters / meta-starters (Spring Boot-coupled) ===
    @{
        name = "nova-java-08-commons-spring-boot-starter"
        description = "Starter Spring Boot que re-exporta las libs puras de Nova (api-standard, mask-utils) como dependencias auto-configuradas para una aplicacion Spring Boot."
        topics = @("java", "nova-platform", "spring-boot", "starter")
    },
    @{
        name = "nova-java-09-observability-spring-boot-starter"
        description = "Starter Spring Boot de observabilidad: Four Golden Signals (latency, traffic, errors, saturation), trazas distribuidas con OpenTelemetry y auto-configuracion para Spring Boot Actuator."
        topics = @("java", "nova-platform", "observability", "opentelemetry", "spring-boot", "starter")
    },
    @{
        name = "nova-java-12-spring-boot-starter"
        description = "Meta-starter Spring Boot de Nova Platform: incluye todos los starters Nova (commons, observability) y configura la aplicacion para usar el meta-framework."
        topics = @("java", "nova-platform", "spring-boot", "starter", "meta-framework")
    },

    # === Java: Maven-only (parent, archetype) y Gradle plugin ===
    @{
        name = "nova-java-17-spring-boot-archetype"
        description = "Maven archetype para generar un nuevo proyecto Spring Boot con las convenciones y dependencias del meta-framework Nova Platform."
        topics = @("archetype", "java", "maven", "nova-platform", "spring-boot")
    },
    @{
        name = "nova-java-16-spring-boot-gradle-plugin"
        description = "Plugin Gradle de Nova Platform para proyectos Spring Boot: aplica convenciones de build, configura Java toolchain y Spring Boot plugin automaticamente."
        topics = @("gradle", "java", "nova-platform", "plugin", "spring-boot")
    },
    @{
        name = "nova-java-14-spring-boot-parent"
        description = "Parent POM de Maven para proyectos Spring Boot del meta-framework Nova Platform: dependencias gestionadas, plugins y propiedades centralizadas."
        topics = @("java", "maven", "nova-platform", "parent-pom", "spring-boot")
    },

    # === Java: Instance / demo ===
    @{
        name = "nova-example-01-spring-boot-reference"
        description = "Instancia/demo del meta-framework Nova Java. Muestra uso real de las libs puras + starters de Nova."
        topics = @("demo", "example", "java", "nova-platform", "spring-boot")
    }
)

# === Nova-specific labels (added on top of GitHub defaults) ===
$labels = @(
    @{ name = "nova:semver"; color = "0e8a16"; description = "Cambios relacionados con versioning, release automation o SemVer policy" },
    @{ name = "nova:workflow"; color = "1d76db"; description = "Cambios en reusable workflows o composite actions de nova-shared-02-pipelines" },
    @{ name = "nova:docs"; color = "0075ca"; description = "Cambios en documentacion del meta-framework (doc 06, ADRs)" },
    @{ name = "breaking-change"; color = "b60205"; description = "API breaking change (fuerza bump major en release-please)" },
    @{ name = "priority:high"; color = "b60205"; description = "Prioridad alta - bloquea release o sprint" },
    @{ name = "priority:medium"; color = "fbca04"; description = "Prioridad media - debe resolverse en el sprint actual" },
    @{ name = "priority:low"; color = "0e8a16"; description = "Prioridad baja - puede diferirse" },
    @{ name = "sprint-0"; color = "5319e7"; description = "Actividad NOVA-SEMVER-01 a 04 (fundamentos versioning)" },
    @{ name = "sprint-1"; color = "5319e7"; description = "Actividad NOVA-SEMVER-05 a 08 (reusable workflows faltantes)" },
    @{ name = "sprint-2"; color = "5319e7"; description = "Actividad NOVA-SEMVER-09 a 12 (multi-registry publishing)" },
    @{ name = "sprint-3"; color = "5319e7"; description = "Actividad NOVA-SEMVER-13 a 16 (release-please + primer release)" },
    @{ name = "sprint-4"; color = "5319e7"; description = "Actividad NOVA-SEMVER-17 a 22 (Maven Central + calidad)" },
    @{ name = "sprint-5"; color = "5319e7"; description = "Actividad NOVA-SEMVER-23 a 28 (build cache + composite actions)" },
    @{ name = "needs-triage"; color = "ededed"; description = "Issue nuevo sin revisar por el maintainer" }
)

# === Homepage (raiz del meta-framework) ===
$homepage = "https://github.com/ahincho/nova-java-13-bom"

# === Export to JSON for use by apply script ===
$payload = @{
    repos = $repos
    labels = $labels
    homepage = $homepage
}
$metadataPath = Join-Path $PSScriptRoot "nova-platform-metadata.json"
$payload | ConvertTo-Json -Depth 5 | Out-File -FilePath $metadataPath -Encoding UTF8
Write-Host "Metadata written to $metadataPath"
Write-Host "Repos: $($repos.Count), Labels: $($labels.Count)"
