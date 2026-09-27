# Apply Nova Platform metadata to all 19 repos
# - Sets description, homepage, topics for each repo
# - Creates Nova-specific labels in each repo
# Idempotent: safe to re-run (gh label create --force)
# Usage: pwsh apply-nova-metadata.ps1
# NO COMMITS, NO PUSHES: this script only mutates GitHub remote properties.

$ErrorActionPreference = "Continue"
$metadataPath = Join-Path $PSScriptRoot "nova-platform-metadata.json"
if (-not (Test-Path -LiteralPath $metadataPath)) {
    Write-Error "Metadata file not found: $metadataPath. Run nova-repos-metadata.ps1 first."
    exit 1
}

$payload = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
$repos = $payload.repos
$labels = $payload.labels
$homepage = $payload.homepage

$totalSteps = $repos.Count * 2 + $labels.Count * $repos.Count
$currentStep = 0

function Step-Progress {
    param($msg)
    $script:currentStep++
    Write-Host "[$currentStep/$totalSteps] $msg" -ForegroundColor Cyan
}

# === Phase 1: Set description + homepage + topics for each repo ===
Write-Host ""
Write-Host "=== Phase 1: Set description, homepage, topics ===" -ForegroundColor Yellow
foreach ($r in $repos) {
    $name = $r.name
    $fullName = "ahincho/$name"

    Step-Progress "Setting description + homepage for $name"
    $descEscaped = $r.description -replace '"', '\"'
    gh repo edit $fullName --description $r.description --homepage $homepage 2>&1 | ForEach-Object { Write-Host "  $_" }

    # Get current topics to avoid duplicates
    $currentTopics = (gh repo view $fullName --json repositoryTopics 2>$null | ConvertFrom-Json).repositoryTopics | ForEach-Object { $_.name }

    # Add each desired topic if not present
    foreach ($t in $r.topics) {
        Step-Progress "  Adding topic '$t' to $name"
        if ($currentTopics -contains $t) {
            Write-Host "    (already present)" -ForegroundColor DarkGray
        } else {
            gh repo edit $fullName --add-topic $t 2>&1 | ForEach-Object { Write-Host "    $_" }
        }
    }
}

# === Phase 2: Create Nova-specific labels in each repo ===
Write-Host ""
Write-Host "=== Phase 2: Create Nova labels in all 19 repos ===" -ForegroundColor Yellow
foreach ($r in $repos) {
    $name = $r.name
    $fullName = "ahincho/$name"
    Write-Host ""
    Write-Host "  Repo: $name" -ForegroundColor Magenta
    foreach ($l in $labels) {
        Step-Progress "    Label '$($l.name)'"
        $descEscaped = $l.description -replace '"', '\"'
        # --force overwrites if exists
        gh label create $l.name --repo $fullName --color $l.color --description $l.description --force 2>&1 | ForEach-Object { Write-Host "      $_" }
    }
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "Total API calls: $currentStep / $totalSteps"
