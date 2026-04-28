param(
  [string]$BaseUrl = 'http://127.0.0.1:8012'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$db = Join-Path $root 'codex_phase0_e2e.db'
if (Test-Path $db) { Remove-Item -LiteralPath $db -Force }

$env:DATABASE_URL = "sqlite:///$($db -replace '\\','/')"
$env:DB_FALLBACK_URL = $env:DATABASE_URL
$env:APP_ENV = 'development'
$env:JWT_SECRET = 'dev-secret-key'
$env:METRICS_ENABLED = 'true'
$env:METRICS_REQUIRE_PROMETHEUS_CLIENT = 'false'
$env:RATE_LIMIT_ENABLED = 'true'
$env:RATE_LIMIT_STORAGE = 'memory'
$env:RATE_LIMIT_GLOBAL_REQUESTS = '250'
$env:RATE_LIMIT_GLOBAL_WINDOW_SECONDS = '60'
$env:RATE_LIMIT_GLOBAL_AUTHENTICATED_REQUESTS = '2000'
$env:RATE_LIMIT_GLOBAL_AUTHENTICATED_WINDOW_SECONDS = '60'
$env:RATE_LIMIT_AUTH_LOGIN_REQUESTS = '25'
$env:RATE_LIMIT_AUTH_LOGIN_WINDOW_SECONDS = '60'
$env:RATE_LIMIT_WORKER_WRITE_REQUESTS = '120'
$env:RATE_LIMIT_WORKER_WRITE_WINDOW_SECONDS = '60'

Push-Location (Join-Path $root 'backend')
$server = $null
try {
  & .\.venv\Scripts\alembic -c alembic.ini upgrade head

  $server = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8012" -PassThru -RedirectStandardOutput (Join-Path $root '.perf-results\uvicorn.out.log') -RedirectStandardError (Join-Path $root '.perf-results\uvicorn.err.log') -WindowStyle Hidden
  Start-Sleep -Seconds 4

  & .\.venv\Scripts\python.exe -c "import urllib.request;print(urllib.request.urlopen('$BaseUrl/health',timeout=10).status)"

  & .\.venv\Scripts\python.exe -c "import json, urllib.request; b='$BaseUrl';
import urllib.error
def post(path,payload,token=None):
  r=urllib.request.Request(b+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json', **({'Authorization':'Bearer '+token} if token else {})})
  try:
    return json.loads(urllib.request.urlopen(r,timeout=15).read().decode())
  except urllib.error.HTTPError as e:
    print(path, e.code, e.read().decode())
    raise
post('/auth/register',{'full_name':'Farmer Perf','phone':'+2127001000','password':'secret1234','role':'farmer','terms_accepted':True,'data_consent_accepted':True})
post('/auth/register',{'full_name':'Worker Perf','phone':'+2127002000','password':'secret1234','role':'worker','terms_accepted':True,'data_consent_accepted':True})
wt=post('/auth/login',{'phone':'+2127002000','password':'secret1234','legal_acknowledged':True})['access_token']
post('/workers',{'name':'Worker Perf','phone':'+2127002000','village':'Sfax','men_count':1,'women_count':1,'rate_type':'day','men_rate_value':120,'women_rate_value':120,'overtime_open':False,'available_dates':['2026-05-01'],'available':True},wt)"
}
finally {
  Pop-Location
}

$k6 = Join-Path $root '.tools\k6-v0.52.0-windows-amd64\k6.exe'
& $k6 run (Join-Path $root 'deploy\perf\health-smoke.js') -e BASE_URL=$BaseUrl --summary-export (Join-Path $root '.perf-results\phase0-health-rerun.json')
& $k6 run (Join-Path $root 'deploy\perf\workers-list.js') -e BASE_URL=$BaseUrl --summary-export (Join-Path $root '.perf-results\phase0-workers-rerun.json')
& $k6 run (Join-Path $root 'deploy\perf\auth-login.js') -e BASE_URL=$BaseUrl -e LOGIN_PHONE=+2127001000 -e LOGIN_PASSWORD=secret1234 --summary-export (Join-Path $root '.perf-results\phase0-auth-rerun.json')

Push-Location (Join-Path $root 'backend')
try {
  $wid = (& .\.venv\Scripts\python.exe -c "import json, urllib.request; b='$BaseUrl'; req=urllib.request.Request(b+'/auth/login',data=json.dumps({'phone':'+2127002000','password':'secret1234','legal_acknowledged':True}).encode(),headers={'Content-Type':'application/json'}); t=json.loads(urllib.request.urlopen(req,timeout=10).read().decode())['access_token']; req2=urllib.request.Request(b+'/workers',headers={'Authorization':'Bearer '+t}); rows=json.loads(urllib.request.urlopen(req2,timeout=10).read().decode()); print(rows[0]['id'])").Trim()
}
finally {
  Pop-Location
}

& $k6 run (Join-Path $root 'deploy\perf\bookings-flow.js') -e BASE_URL=$BaseUrl -e FARMER_PHONE=+2127001000 -e FARMER_PASSWORD=secret1234 -e WORKER_PHONE=+2127002000 -e WORKER_PASSWORD=secret1234 -e WORKER_ID=$wid --summary-export (Join-Path $root '.perf-results\phase0-booking-rerun.json')

if ($server -and !$server.HasExited) {
  Stop-Process -Id $server.Id -Force
}
