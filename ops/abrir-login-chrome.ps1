# Arranca ERP si hace falta y abre Chrome con login Superusuario (Playwright).
# Uso: powershell -ExecutionPolicy Bypass -File ops\abrir-login-chrome.ps1

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Test-Port([int]$Port) {
  return [bool](netstat -ano 2>$null | Select-String (":" + $Port + "\s") | Select-String "LISTENING")
}

Write-Host "=== Super Ozono - Abrir login Chrome ===" -ForegroundColor Cyan

# Backend
if (-not (Test-Port 8000)) {
  Write-Host "Arrancando backend :8000 ..."
  # Certs relativos (evita split por espacios en "MI PC")
  Start-Process cmd.exe -ArgumentList @(
    "/c",
    "start `"Backend-FastAPI`" /D `"$Root\backend`" cmd /k venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile ..\certs\server.key --ssl-certfile ..\certs\server.crt"
  )
} else {
  Write-Host "Backend ya en :8000"
}

# Frontend
if (-not (Test-Port 5173)) {
  Write-Host "Arrancando frontend :5173 ..."
  Start-Process cmd.exe -ArgumentList @(
    "/c",
    "start `"Frontend-Vite`" /D `"$Root\frontend`" cmd /k node node_modules\vite\bin\vite.js --host 0.0.0.0 --port 5173"
  )
} else {
  Write-Host "Frontend ya en :5173"
}

$py = Join-Path $Root "backend\venv\Scripts\python.exe"
$ready = $false
for ($i = 1; $i -le 50; $i++) {
  Start-Sleep -Seconds 2
  & $py (Join-Path $Root "ops\_diag_health.py") 2>$null | Out-Null
  $hOk = ($LASTEXITCODE -eq 0)
  $fOk = Test-Port 5173
  if ($hOk -and $fOk) { $ready = $true; Write-Host "Listo (try $i)"; break }
  Write-Host "Esperando servicios try $i health=$hOk fe=$fOk"
}

if (-not $ready) {
  Write-Host "ERROR: backend/frontend no listos." -ForegroundColor Red
  exit 1
}

$email = "admin@superozonoglobal.com"
$password = ""
Get-Content (Join-Path $Root "backend\.env") -Encoding UTF8 | ForEach-Object {
  if ($_ -match "^SEED_ADMIN_EMAIL=(.*)$") { $email = $Matches[1].Trim().Trim([char]34) }
  if ($_ -match "^SEED_ADMIN_PASSWORD=(.*)$") { $password = $Matches[1].Trim().Trim([char]34) }
}

if (-not $password) {
  Write-Host "ERROR: SEED_ADMIN_PASSWORD vacia" -ForegroundColor Red
  exit 1
}

# Verificar API
$env:ERP_EMAIL = $email
$env:ERP_PASSWORD = $password
& $py -c "import os,ssl,json; from urllib.request import Request,urlopen; from urllib.parse import urlencode; ctx=ssl._create_unverified_context(); body=urlencode({'username':os.environ['ERP_EMAIL'],'password':os.environ['ERP_PASSWORD']}).encode(); req=Request('https://127.0.0.1:8000/api/login/access-token',data=body,method='POST'); req.add_header('Content-Type','application/x-www-form-urlencoded'); r=urlopen(req,context=ctx,timeout=10); d=json.loads(r.read().decode()); assert d.get('access_token'); print('API_LOGIN_OK')"
if ($LASTEXITCODE -ne 0) {
  Write-Host "ERROR: login API fallo" -ForegroundColor Red
  exit 1
}

# Cred file (evita caracteres especiales en cmd)
$shots = Join-Path $Root "ops\smoke-screens"
New-Item -ItemType Directory -Force -Path $shots | Out-Null
$credPath = Join-Path $shots "_login_cred.json"
$cred = @{
  email = $email
  password = $password
  url = "https://127.0.0.1:5173"
  keepMs = 1200000
} | ConvertTo-Json
[System.IO.File]::WriteAllText($credPath, $cred, [System.Text.UTF8Encoding]::new($false))

$scriptSrc = Join-Path $Root "ops\_login_chrome.cjs"
$localScript = Join-Path $Root "frontend\_login_chrome.cjs"
Copy-Item $scriptSrc $localScript -Force

$env:ERP_CRED_FILE = $credPath
$env:ERP_EMAIL = $email
$env:ERP_PASSWORD = $password
$env:ERP_URL = "https://127.0.0.1:5173"
$env:ERP_KEEP_MS = "1200000"

Write-Host "Abriendo Chrome con sesion Superusuario..." -ForegroundColor Green
Write-Host "Usuario: $email"
Start-Process -FilePath "node" -ArgumentList @("_login_chrome.cjs") -WorkingDirectory (Join-Path $Root "frontend") -WindowStyle Normal

Write-Host "Revisa Chrome / barra de tareas."
Write-Host "Estado: ops\smoke-screens\login-status.txt"
exit 0
