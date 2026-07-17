# Sincroniza IP LAN actual en frontend\.env, CORS del backend\.env y certificado TLS.
# Uso: powershell -ExecutionPolicy Bypass -File ops\sync-lan-ip.ps1
param(
    [string]$Ip = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

function Get-LanIPv4 {
    $candidates = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike '127.*' -and
            $_.IPAddress -notlike '169.254.*' -and
            $_.PrefixOrigin -ne 'WellKnown'
        } |
        Sort-Object -Property InterfaceMetric
    if ($candidates) { return $candidates[0].IPAddress }
    # fallback ipconfig
    $m = ipconfig | Select-String -Pattern 'IPv4.*:\s*([\d.]+)' | ForEach-Object {
        if ($_.Matches.Groups[1].Value -notmatch '^(127\.|169\.254\.)') { $_.Matches.Groups[1].Value }
    } | Select-Object -First 1
    return $m
}

if (-not $Ip) { $Ip = Get-LanIPv4 }
if (-not $Ip) { Write-Error "No se pudo detectar IP LAN. Pasa -Ip 192.168.x.x" }

Write-Host "IP LAN: $Ip"

# --- frontend\.env ---
$fe = Join-Path $Root "frontend\.env"
$feContent = "VITE_API_URL=https://${Ip}:8000/api`r`n"
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($fe, $feContent, $utf8)
Write-Host "frontend\.env -> VITE_API_URL=https://${Ip}:8000/api"

# --- backend\.env CORS (reescribir UTF-8 limpio) ---
$be = Join-Path $Root "backend\.env"
if (Test-Path $be) {
    $raw = [System.IO.File]::ReadAllBytes($be)
    try {
        $text = [System.Text.Encoding]::UTF8.GetString($raw)
        if ($text.Contains([char]0xFFFD)) { throw "bad utf8" }
    } catch {
        $text = [System.Text.Encoding]::GetEncoding(1252).GetString($raw)
    }
    $text = $text -replace [char]0x2014, '-' -replace [char]0x2013, '-' -replace [char]0x97, '-'
    # Reemplazar IPs 192.168.x.x viejas en CORS y texto
    $text = [regex]::Replace($text, 'https://192\.168\.\d+\.\d+:5173', "https://${Ip}:5173")
    $text = [regex]::Replace($text, 'https://192\.168\.\d+\.\d+:8000', "https://${Ip}:8000")
    if ($text -notmatch [regex]::Escape("https://${Ip}:5173")) {
        $text = $text -replace '(?m)^(CORS_ORIGINS=)(.*)$', "`$1https://${Ip}:5173,`$2"
    }
    [System.IO.File]::WriteAllText($be, $text, $utf8)
    Write-Host "backend\.env CORS/IPs actualizados (UTF-8)"
}

# --- Certificado ---
$py = Join-Path $Root "backend\venv\Scripts\python.exe"
$gen = Join-Path $Root "backend\scripts\generate_tls_cert.py"
& $py $gen $Ip localhost 127.0.0.1
Write-Host "Certificado regenerado para $Ip + localhost"
Write-Host "Listo. Ejecuta start.bat"
