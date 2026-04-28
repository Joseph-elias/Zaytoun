param(
  [Parameter(Mandatory = $true)][string]$BaseUrl,
  [string]$FarmerPhone = "+2127441000",
  [string]$FarmerPassword = "Phase1Pass123!",
  [string]$WorkerPhone = "+2127442000",
  [string]$WorkerPassword = "Phase1Pass123!",
  [string]$MetricsBearerToken = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $root "backend\.venv\Scripts\python.exe"
if (!(Test-Path $python)) {
  throw "Python venv not found at $python"
}

Write-Host "[phase1] Seeding/validating users and worker profile..."
$workerId = (& $python (Join-Path $root "deploy\perf\seed_phase1_users.py") `
  --base-url $BaseUrl `
  --farmer-phone $FarmerPhone `
  --farmer-password $FarmerPassword `
  --worker-phone $WorkerPhone `
  --worker-password $WorkerPassword).Trim()

if (-not $workerId) {
  throw "Could not resolve worker id from seed step."
}
Write-Host "[phase1] Worker id: $workerId"

Write-Host "[phase1] Running staging load + gates..."
powershell -ExecutionPolicy Bypass -File (Join-Path $root "deploy\perf\run_phase0_staging.ps1") `
  -BaseUrl $BaseUrl `
  -FarmerPhone $FarmerPhone `
  -FarmerPassword $FarmerPassword `
  -WorkerPhone $WorkerPhone `
  -WorkerPassword $WorkerPassword `
  -WorkerId $workerId `
  -MetricsBearerToken $MetricsBearerToken
