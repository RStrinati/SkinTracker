# run_dev.ps1 — Start FastAPI on 127.0.0.1:8081, start ngrok, set Telegram webhook automatically

$ErrorActionPreference = "Stop"

# --- Config ---
$PORT     = 8081
$APP_HOST = "127.0.0.1"
$BOT_ENV  = "TELEGRAM_BOT_TOKEN"   # expects token in .env or environment
$WEBHOOK_PATH = "/webhook"
# --------------

Write-Host "[INFO] Killing any process using ports $PORT or 8000..."

function Kill-Port {
    param([int]$Port)
    # Prefer modern cmdlet if available
    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        foreach ($c in $conns) {
            try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue } catch {}
        }
    } else {
        # Fallback to netstat parsing on older systems
        $lines = netstat -ano | Select-String ":$Port\s"
        foreach ($line in $lines) {
            $parts = ($line.ToString() -split "\s+") | Where-Object { $_ -ne "" }
            $procId = $parts[-1]
            if ($procId -match '^\d+$') {
                try { taskkill /PID $procId /F | Out-Null } catch {}
            }
        }
    }
}

Kill-Port -Port 8000
Kill-Port -Port $PORT

# Load .env into current session (best-effort)
if (Test-Path ".env") {
    Write-Host "[INFO] Loading .env into session..."
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*#') { return }
        if ($_ -match '^\s*$') { return }
        $kv = $_ -split '=', 2
        if ($kv.Length -eq 2) {
            $k = $kv[0].Trim()
            $v = $kv[1].Trim()
            [System.Environment]::SetEnvironmentVariable($k, $v, "Process")
        }
    }
}

# Sanity check for bot token
$BOT_TOKEN = [System.Environment]::GetEnvironmentVariable($BOT_ENV, "Process")
if (-not $BOT_TOKEN) {
    throw "[ERROR] $BOT_ENV is not set. Put TELEGRAM_BOT_TOKEN=... in your .env or set it in the environment."
}

# Activate venv if present
if (Test-Path "venv/Scripts/Activate.ps1") {
    Write-Host "[INFO] Activating Python venv..."
    . "venv/Scripts/Activate.ps1"
}

# Start FastAPI
Write-Host "[INFO] Starting FastAPI on http://$APP_HOST`:$PORT ..."
Start-Process -NoNewWindow -FilePath python -ArgumentList "-m uvicorn server:app --host $APP_HOST --port $PORT --reload"

Start-Sleep -Seconds 2

# Start ngrok
Write-Host "[INFO] Starting ngrok tunnel -> http://$APP_HOST`:$PORT ..."
Start-Process -NoNewWindow -FilePath ngrok -ArgumentList "http $PORT"

# Wait for ngrok to come up and fetch https public_url
Write-Host "[INFO] Waiting for ngrok public URL..."
$publicUrl = $null
for ($i=0; $i -lt 30; $i++) {
    try {
        $tunnels = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -Method GET -TimeoutSec 2
        $publicUrl = ($tunnels.tunnels | Where-Object {$_.public_url -like "https*"} | Select-Object -First 1).public_url
        if ($publicUrl) { break }
    } catch {}
    Start-Sleep -Seconds 1
}
if (-not $publicUrl) { throw "[ERROR] Could not get ngrok public URL from 127.0.0.1:4040" }

Write-Host "[INFO] ngrok public URL: $publicUrl"

# Set Telegram webhook
$webhookUrl = "$publicUrl$WEBHOOK_PATH"
Write-Host "[INFO] Setting Telegram webhook -> $webhookUrl"
Invoke-RestMethod -Uri "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" -Method POST -Body @{ url = $webhookUrl } | Out-Null

# Show webhook info
$info = Invoke-RestMethod -Uri "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo" -Method GET
Write-Host "[INFO] Current Telegram Webhook Info:"
$info | ConvertTo-Json -Depth 5

# Health check (local & public)
Write-Host "[INFO] Hitting /health locally and via ngrok..."
try { Invoke-RestMethod -Uri "http://$APP_HOST`:$PORT/health" -Method GET -TimeoutSec 5 | Out-Null } catch {}
try { Invoke-RestMethod -Uri "$publicUrl/health" -Method GET -TimeoutSec 5 | Out-Null } catch {}

# Send a test fake Telegram update to your webhook (verifies 200 OK from your handler)
Write-Host "[INFO] Sending test POST to $WEBHOOK_PATH ..."
$dummy = @{ update_id = 1; message = @{ message_id = 1; date = 0; chat = @{ id = 123; type = "private" }; text = "/start" } } | ConvertTo-Json
try {
    Invoke-RestMethod -Uri $webhookUrl -Method POST -ContentType "application/json" -Body $dummy -TimeoutSec 5 | Out-Null
    Write-Host "[INFO] Test POST sent (check uvicorn logs and ngrok inspector)."
} catch {
    Write-Host "[WARN] Test POST failed: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "[READY] Dev server is live."
Write-Host "        Local:     http://$APP_HOST`:$PORT"
Write-Host "        Public:    $publicUrl"
Write-Host "        Inspector: http://127.0.0.1:4040"