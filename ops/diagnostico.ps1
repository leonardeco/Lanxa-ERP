# Diagnostico rapido Super Ozono ERP (LAN) - no imprime secretos.
#   powershell -ExecutionPolicy Bypass -File ops\diagnostico.ps1

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$script:fail = 0

function Ok {
  param([string]$m)
  Write-Host ("  [OK] " + $m) -ForegroundColor Green
}
function Warn {
  param([string]$m)
  Write-Host ("  [!!] " + $m) -ForegroundColor Yellow
}
function Bad {
  param([string]$m)
  Write-Host ("  [X]  " + $m) -ForegroundColor Red
  $script:fail++
}

Write-Host ""
Write-Host "=== Super Ozono ERP - Diagnostico ===" -ForegroundColor Cyan
Write-Host ("Carpeta: " + $Root)
Write-Host ""

# --- 1 Red ---
Write-Host "--- 1 Red ---"
$ip = $null
try {
  $addrs = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
      $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*"
    } |
    Sort-Object InterfaceMetric
  if ($addrs) { $ip = $addrs[0].IPAddress }
} catch {}
if ($ip) { Ok ("IP LAN: " + $ip) } else { Warn "No se detecto IP LAN" }

# --- 2 Archivos ---
Write-Host ""
Write-Host "--- 2 Archivos ---"
$need = @(
  "backend\venv\Scripts\python.exe",
  "backend\.env",
  "frontend\.env",
  "frontend\node_modules\vite\bin\vite.js",
  "certs\server.crt",
  "certs\server.key",
  "start.bat"
)
foreach ($rel in $need) {
  $full = Join-Path $Root $rel
  if (Test-Path $full) { Ok $rel } else { Bad ("Falta " + $rel) }
}

# --- 3 UTF-8 .env ---
Write-Host ""
Write-Host "--- 3 Encoding backend.env ---"
$be = Join-Path $Root "backend\.env"
try {
  $bytes = [System.IO.File]::ReadAllBytes($be)
  $utf8Strict = New-Object System.Text.UTF8Encoding $false, $true
  [void]$utf8Strict.GetString($bytes)
  Ok "UTF-8 valido"
} catch {
  Bad "backend.env NO es UTF-8 - ejecuta ops\sync-lan-ip.ps1"
}

# --- 4 frontend ---
Write-Host ""
Write-Host "--- 4 frontend.env ---"
$fe = Join-Path $Root "frontend\.env"
if (Test-Path $fe) {
  $line = Get-Content $fe | Where-Object { $_ -match "^VITE_API_URL=" } | Select-Object -First 1
  if ($line) {
    Ok $line
    $localOk = $line -match "127\.0\.0\.1|localhost"
    $ipOk = $false
    if ($ip) { $ipOk = $line -match [regex]::Escape($ip) }
    if ($ip -and (-not $ipOk) -and (-not $localOk)) {
      Warn ("VITE_API_URL no usa IP actual " + $ip + " - start.bat o sync-lan-ip.ps1")
    }
  } else {
    Bad "Sin VITE_API_URL"
  }
}

# --- 5 CORS ---
Write-Host ""
Write-Host "--- 5 CORS ---"
try {
  $cors = Get-Content $be -Encoding UTF8 | Where-Object { $_ -match "^CORS_ORIGINS=" } | Select-Object -First 1
  if ($cors) {
    $corsHasIp = $false
    if ($ip) { $corsHasIp = $cors -match [regex]::Escape($ip) }
    if ($corsHasIp) {
      Ok ("CORS incluye " + $ip)
    } elseif ($cors -match "localhost|127\.0\.0\.1") {
      Ok "CORS tiene localhost"
    } else {
      Warn "Revisa CORS_ORIGINS"
    }
  } else {
    Warn "CORS_ORIGINS no encontrado"
  }
} catch {
  Warn "No se pudo leer CORS"
}

# --- 6 Puertos ---
Write-Host ""
Write-Host "--- 6 Puertos ---"
foreach ($port in @(8000, 5173)) {
  $pattern = ":" + $port + "\s"
  $listen = netstat -ano 2>$null | Select-String $pattern | Select-String "LISTENING"
  if ($listen) {
    Ok ("Puerto " + $port + " LISTENING")
  } else {
    Bad ("Puerto " + $port + " NO escucha (ejecuta start.bat)")
  }
}

# --- 7 Health ---
Write-Host ""
Write-Host "--- 7 Health API ---"
$py = Join-Path $Root "backend\venv\Scripts\python.exe"
$healthScript = Join-Path $PSScriptRoot "_diag_health.py"
if ((Test-Path $py) -and (Test-Path $healthScript)) {
  $out = & $py $healthScript 2>&1 | Out-String
  if ($LASTEXITCODE -eq 0) {
    Ok $out.Trim()
  } else {
    Bad ("health: " + $out.Trim())
  }
} else {
  Bad "Sin python venv o ops\_diag_health.py"
}

# --- 8 Cert ---
Write-Host ""
Write-Host "--- 8 Certificado ---"
$certScript = Join-Path $PSScriptRoot "_diag_cert.py"
$certPath = Join-Path $Root "certs\server.crt"
if ((Test-Path $py) -and (Test-Path $certScript)) {
  $cout = & $py $certScript $certPath 2>&1 | Out-String
  if ($cout -match "FAIL") {
    Bad $cout.Trim()
  } else {
    Ok $cout.Trim()
    if ($ip -and ($cout -notmatch [regex]::Escape($ip))) {
      Warn ("Cert no incluye IP " + $ip + " - ejecuta ops\sync-lan-ip.ps1")
    }
  }
} else {
  Warn "No se pudo verificar certificado"
}

# --- 9 Alegra ---
Write-Host ""
Write-Host "--- 9 Alegra ---"
try {
  $lines = Get-Content $be -Encoding UTF8
  foreach ($k in @("ALEGRA_EMAIL", "ALEGRA_TOKEN")) {
    $aline = $lines | Where-Object { $_ -match ("^" + $k + "=") } | Select-Object -First 1
    if (-not $aline) {
      Warn ($k + " ausente")
    } else {
      $parts = $aline -split "=", 2
      $v = ""
      if ($parts.Count -gt 1) {
        $v = $parts[1].Trim().Trim([char]34)
      }
      if ($v) {
        Ok ($k + " configurado len=" + $v.Length)
      } else {
        Warn ($k + " vacio (normal sin FE)")
      }
    }
  }
} catch {
  Warn "No se pudo leer Alegra"
}

# --- 10 Postgres tests ---
Write-Host ""
Write-Host "--- 10 Postgres tests ---"
$svc = Get-Service postgresql-x64-17 -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -eq "Running") {
  Ok "postgresql-x64-17 Running"
} elseif ($svc) {
  Warn ("postgresql-x64-17: " + $svc.Status)
} else {
  Warn "Postgres servicio no instalado (ok si no usas pytest local)"
}

Write-Host ""
if ($script:fail -eq 0) {
  Write-Host "RESULTADO: sin errores criticos" -ForegroundColor Green
  Write-Host "Smoke: ops\smoke-diario.bat"
  if ($ip) { Write-Host ("URL: https://" + $ip + ":5173") }
  exit 0
} else {
  Write-Host ("RESULTADO: " + $script:fail + " problema(s)") -ForegroundColor Red
  Write-Host "Tip: stop.bat -> powershell -File ops\sync-lan-ip.ps1 -> start.bat"
  exit 1
}
