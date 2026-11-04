# Legends Reel Studio - Windows launcher (PowerShell)
# Chay:  .\run.ps1     (neu bi chan: powershell -ExecutionPolicy Bypass -File .\run.ps1)
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Fail($message) {
    Write-Host ""
    Write-Host $message -ForegroundColor Red
    Write-Host ""
    Read-Host "Nhan Enter de thoat"
    exit 1
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Fail "Chua co Python. Cai bang:  winget install --id Python.Python.3.12 -e --source winget   (roi mo lai PowerShell)"
}

if (-not (Test-Path ".venv")) {
    Write-Host "-> Tao virtualenv .venv" -ForegroundColor Cyan
    & python -m venv .venv
    if ($LASTEXITCODE -ne 0) { Fail "Tao .venv that bai. Thu cai Python 3.11+ tu python.org." }
}

$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Fail "Khong tim thay $py. Xoa thu muc .venv roi chay lai." }

& $py -c "import fastapi, PIL, imageio_ffmpeg, numpy" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "-> Cai dependencies (lan dau co the mat 1-2 phut)" -ForegroundColor Cyan
    & $py -m pip install -q --upgrade pip
    & $py -m pip install -q -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Fail "Cai dependencies that bai. Kiem tra ket noi mang roi chay lai." }
}

New-Item -ItemType Directory -Force -Path "data" | Out-Null
$port = if ($env:PORT) { $env:PORT } else { "8000" }

Write-Host ""
Write-Host "  Legends Reel Studio dang chay:  http://localhost:$port" -ForegroundColor Green
Write-Host "  Nhan Ctrl + C de tat server." -ForegroundColor DarkGray
Write-Host ""

& $py -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port $port
