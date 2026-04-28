param(
  [string]$BaseUrl = "http://127.0.0.1:8016"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$db = Join-Path $root "codex_perf_preflight.db"
if (Test-Path $db) { Remove-Item -LiteralPath $db -Force }

$env:DATABASE_URL = "sqlite:///$($db -replace '\\','/')"
$env:DB_FALLBACK_URL = $env:DATABASE_URL
$env:APP_ENV = "development"
$env:JWT_SECRET = "dev-secret-key"
$env:METRICS_ENABLED = "true"
$env:METRICS_REQUIRE_PROMETHEUS_CLIENT = "false"
$env:RATE_LIMIT_ENABLED = "true"
$env:RATE_LIMIT_STORAGE = "memory"

Push-Location (Join-Path $root "backend")
$server = $null
try {
  Write-Host "[preflight] Running migrations..."
  & .\.venv\Scripts\alembic -c alembic.ini upgrade head | Out-Null

  Write-Host "[preflight] Starting API..."
  $server = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8016" -PassThru -WindowStyle Hidden
  Start-Sleep -Seconds 3

  Write-Host "[preflight] Checking /health and /ready..."
  & .\.venv\Scripts\python.exe -c "import urllib.request; h=urllib.request.urlopen('$BaseUrl/health',timeout=10); r=urllib.request.urlopen('$BaseUrl/ready',timeout=10); print('health',h.status); print('ready',r.status)" | Out-Host

  Write-Host "[preflight] Validating seed contract (register/login/create/list)..."
  & .\.venv\Scripts\python.exe -c "import json,urllib.request; b='$BaseUrl';
def post(path,payload,token=None):
  headers={'Content-Type':'application/json'}
  if token: headers['Authorization']='Bearer '+token
  req=urllib.request.Request(b+path,data=json.dumps(payload).encode(),headers=headers)
  return json.loads(urllib.request.urlopen(req,timeout=15).read().decode())
post('/auth/register',{'full_name':'Perf Farmer','phone':'+2127111000','password':'secret1234','role':'farmer','terms_accepted':True,'data_consent_accepted':True})
post('/auth/register',{'full_name':'Perf Worker','phone':'+2127112000','password':'secret1234','role':'worker','terms_accepted':True,'data_consent_accepted':True})
token=post('/auth/login',{'phone':'+2127112000','password':'secret1234','legal_acknowledged':True})['access_token']
post('/workers',{'name':'Perf Worker','phone':'+2127112000','village':'Sfax','men_count':1,'women_count':1,'rate_type':'day','men_rate_value':120,'women_rate_value':120,'overtime_open':False,'available_dates':['2026-05-01'],'available':True},token)
rows_req=urllib.request.Request(b+'/workers',headers={'Authorization':'Bearer '+token})
rows=json.loads(urllib.request.urlopen(rows_req,timeout=15).read().decode())
assert isinstance(rows,list) and len(rows)>=1
print('seed_ok',len(rows))" | Out-Host

  Write-Host "[preflight] PASS"
}
finally {
  if ($server -and !$server.HasExited) { Stop-Process -Id $server.Id -Force }
  Pop-Location
}
