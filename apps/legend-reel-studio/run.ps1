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

$pythonArgs = @()
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonExe = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonExe = "py"
    $pythonArgs = @("-3")
} else {
    Fail "Chua co Python. Cai bang:  winget install --id Python.Python.3.12 -e --source winget   (roi mo lai PowerShell)"
}

& $pythonExe @pythonArgs -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) { Fail "Can Python 3.11 tro len. Tai ban moi tai python.org (nho tick 'Add python.exe to PATH')." }

if (-not (Test-Path ".venv")) {
    Write-Host "-> Tao virtualenv .venv" -ForegroundColor Cyan
    & $pythonExe @pythonArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) { Fail "Tao .venv that bai. Thu cai Python 3.11+ tu python.org." }
}

$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Fail "Khong tim thay $py. Xoa thu muc .venv roi chay lai." }

& $py -c "import fastapi, PIL, edge_tts, multipart" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "-> Cai dependencies (lan dau co the mat 1-2 phut)" -ForegroundColor Cyan
    & $py -m pip install -q --upgrade pip
    & $py -m pip install -q -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Fail "Cai dependencies that bai. Kiem tra ket noi mang roi chay lai." }
}

# Goi phu tro: giup Facebook khong tra HTTP 400 khi doc page doi thu.
# Thieu cung khong chan khoi dong - chi mat duong "dan link la xong".
& $py -c "import curl_cffi, httpx, h2" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "-> Cai them curl_cffi + httpx (de doc page Facebook tu may chu)" -ForegroundColor Cyan
    & $py -m pip install -q curl_cffi "httpx[http2]"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ! Khong cai duoc curl_cffi. Studio van chay; khi doc page hay dung 'Tai trang HTML len' hoac nut bookmark." -ForegroundColor Yellow
    }
}

New-Item -ItemType Directory -Force -Path "data" | Out-Null
$port = if ($env:PORT) { $env:PORT } else { "8000" }

Write-Host ""
Write-Host "  Legends Reel Studio dang chay:  http://localhost:$port" -ForegroundColor Green
Write-Host "  Nhan Ctrl + C de tat server." -ForegroundColor DarkGray
Write-Host ""

& $py -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port $port
