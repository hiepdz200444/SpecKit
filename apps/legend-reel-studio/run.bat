@echo off
rem Legends Reel Studio - Windows launcher (double-click duoc)
setlocal
cd /d "%~dp0"

set "PYEXE=python"
set "PYARGS="
where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo.
    echo Chua co Python. Cai bang:  winget install --id Python.Python.3.12 -e --source winget
    echo Sau do mo lai cua so nay va chay lai run.bat
    echo.
    pause
    exit /b 1
  )
  set "PYEXE=py"
  set "PYARGS=-3"
)

if not exist ".venv" (
  echo -^> Tao virtualenv .venv
  %PYEXE% %PYARGS% -m venv .venv
  if errorlevel 1 (
    echo Tao .venv that bai. Thu cai Python 3.11+ tu python.org
    pause
    exit /b 1
  )
)

rem Goi bat buoc (thieu la khong chay duoc)
".venv\Scripts\python.exe" -c "import fastapi, PIL, edge_tts, multipart" >nul 2>nul
if errorlevel 1 (
  echo -^> Cai dependencies ^(lan dau co the mat 1-2 phut^)
  ".venv\Scripts\python.exe" -m pip install -q --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
  if errorlevel 1 (
    echo Cai dependencies that bai. Kiem tra ket noi mang roi chay lai.
    pause
    exit /b 1
  )
)

rem Goi phu tro: giup Facebook khong tra HTTP 400 khi doc page doi thu.
rem Thieu cung KHONG chan khoi dong - chi mat duong "dan link la xong".
".venv\Scripts\python.exe" -c "import curl_cffi, httpx, h2" >nul 2>nul
if errorlevel 1 (
  echo -^> Cai them curl_cffi + httpx ^(de doc page Facebook tu may chu^)
  ".venv\Scripts\python.exe" -m pip install -q curl_cffi "httpx[http2]"
  if errorlevel 1 (
    echo    ^! Khong cai duoc curl_cffi. Studio van chay; khi doc page hay dung
    echo      "Tai trang HTML len" hoac nut bookmark trong tab Reels doi thu.
  )
)

if "%PORT%"=="" set PORT=8000
if not exist "data" mkdir data

echo.
echo   Legends Reel Studio dang chay:  http://localhost:%PORT%
echo   Nhan Ctrl + C de tat server.
echo.
".venv\Scripts\python.exe" -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port %PORT%
pause
