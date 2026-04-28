param(
  [string]$BaseUrl = "http://127.0.0.1:8012"
)

$ErrorActionPreference = "Stop"

Write-Host "[phase0-safe] Running preflight..."
powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "perf_preflight.ps1") -BaseUrl $BaseUrl
if ($LASTEXITCODE -ne 0) {
  Write-Error "[phase0-safe] Preflight failed. Blocking load run."
  exit $LASTEXITCODE
}

Write-Host "[phase0-safe] Preflight passed. Running Phase 0 load suite..."
powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "run_phase0_e2e.ps1") -BaseUrl $BaseUrl
exit $LASTEXITCODE
