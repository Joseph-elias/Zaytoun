param(
  [Parameter(Mandatory = $true)][string]$BaseUrl,
  [Parameter(Mandatory = $true)][string]$FarmerPhone,
  [Parameter(Mandatory = $true)][string]$FarmerPassword,
  [Parameter(Mandatory = $true)][string]$WorkerPhone,
  [Parameter(Mandatory = $true)][string]$WorkerPassword,
  [Parameter(Mandatory = $true)][string]$WorkerId,
  [string]$MetricsBearerToken = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$resultsDir = Join-Path $root ".perf-results\staging"
New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null
$k6 = Join-Path $root ".tools\k6-v0.52.0-windows-amd64\k6.exe"

if (!(Test-Path $k6)) {
  throw "k6 not found at $k6"
}

Write-Host "[staging] Running health scenario..."
& $k6 run (Join-Path $root "deploy\perf\health-smoke.js") -e BASE_URL=$BaseUrl --summary-export (Join-Path $resultsDir "health.json")

Write-Host "[staging] Running workers scenario..."
& $k6 run (Join-Path $root "deploy\perf\workers-list.js") -e BASE_URL=$BaseUrl --summary-export (Join-Path $resultsDir "workers.json")

Write-Host "[staging] Running auth scenario..."
& $k6 run (Join-Path $root "deploy\perf\auth-login.js") -e BASE_URL=$BaseUrl -e LOGIN_PHONE=$FarmerPhone -e LOGIN_PASSWORD=$FarmerPassword --summary-export (Join-Path $resultsDir "auth.json")

Write-Host "[staging] Running booking scenario..."
& $k6 run (Join-Path $root "deploy\perf\bookings-flow.js") -e BASE_URL=$BaseUrl -e FARMER_PHONE=$FarmerPhone -e FARMER_PASSWORD=$FarmerPassword -e WORKER_PHONE=$WorkerPhone -e WORKER_PASSWORD=$WorkerPassword -e WORKER_ID=$WorkerId --summary-export (Join-Path $resultsDir "booking.json")

Write-Host "[staging] Evaluating pass/fail gates..."
& (Join-Path $root "backend\.venv\Scripts\python.exe") (Join-Path $root "backend\scripts\evaluate_phase0_gates.py") `
  --health (Join-Path $resultsDir "health.json") `
  --workers (Join-Path $resultsDir "workers.json") `
  --auth (Join-Path $resultsDir "auth.json") `
  --booking (Join-Path $resultsDir "booking.json") `
  --base-url $BaseUrl `
  --metrics-bearer-token $MetricsBearerToken
