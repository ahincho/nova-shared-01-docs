#requires -Version 5.1
<#
.SYNOPSIS
  Agrega NOVA_PACKAGES_READ_TOKEN al repo nova-java-14-spring-boot-parent para que
  la fase propagate-read del script maestro pueda ejecutarse. Pide el valor por
  Read-Host (no expone el token en el historial de comandos).
#>
param([switch]$Force, [switch]$DryRun)

$ErrorActionPreference = 'Stop'
$Owner = 'ahincho'
$Targets = @('nova-java-14-spring-boot-parent')

function Confirm-Continue([string]$Message) {
  if ($Force) { return }
  $resp = Read-Host "$Message [y/N]"
  if ($resp -ne 'y') {
    Write-Host "[!] Cancelado." -ForegroundColor Yellow
    exit 0
  }
}

Write-Host ''
Write-Host 'A continuacion se te pedira el valor de NOVA_PACKAGES_READ_TOKEN.' -ForegroundColor Cyan
Write-Host 'Obtenlo de https://github.com/settings/tokens (classic) o fine-grained con scope read:packages.' -ForegroundColor Cyan
Write-Host 'Repos semilla (donde ya esta configurado): nova-java-12-spring-boot-starter, nova-java-08-commons-spring-boot-starter' -ForegroundColor Cyan
Write-Host ''

$secure = Read-Host 'NOVA_PACKAGES_READ_TOKEN' -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$value = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

if ($value.Length -lt 10) {
  throw "El valor parece muy corto (length=$($value.Length)). Abortando."
}

Write-Host "[i] Token length: $($value.Length) chars" -ForegroundColor Cyan
Confirm-Continue "Setear NOVA_PACKAGES_READ_TOKEN en $($Targets.Count) repo(s)?"

foreach ($r in $Targets) {
  $target = "$Owner/$r"
  Write-Host "  -> $target : NOVA_PACKAGES_READ_TOKEN = ***" -ForegroundColor Green
  if (-not $DryRun) {
    $value | gh secret set NOVA_PACKAGES_READ_TOKEN --repo $target 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
      Write-Host "  [x] FALLO en $target" -ForegroundColor Red
    } else {
      Write-Host "  [v] OK en $target" -ForegroundColor Green
    }
  }
}

Write-Host ''
Write-Host "[+] Listo. Puedes volver a triggear publish.yml en $Owner/$($Targets[0])" -ForegroundColor Green
