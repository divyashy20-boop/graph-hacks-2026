param(
  [switch]$RunLive,
  [string]$Dataset = "showcase-b-incident",
  [string]$Start = "Checkout",
  [string]$End = "Cache",
  [string]$Target = "Cache",
  [string]$Python = "python"
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.\ugi\__init__.py')) {
    Write-Error "Extract the ZIP into the CURRENT UGI repository root (the directory containing ugi\, not inside ugi\)."
    exit 1
}
$env:UGI_ALLOW_PAID_CALLS = 'false'
Write-Host '1/3 - Checking read-only bridge unit tests...'
& $Python -m unittest discover -s ugi_integration_lab/tests -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host '2/3 - Running offline synthetic comparison...'
& $Python -m ugi_integration_lab.run --mode offline
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($RunLive) {
    Write-Host '3/3 - Read-only live UGI/FalkorDB comparison...'
    & $Python -m ugi_integration_lab.run --mode live --dataset $Dataset --start $Start --end $End --target $Target --output ugi_integration_lab/results/live.json
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host '3/3 - Live comparison SKIPPED (pass -RunLive to enable). No graph write performed.'
}
Write-Host 'Results are in ugi_integration_lab/results/'
