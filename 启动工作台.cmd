@echo off
setlocal
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo [ERROR] venv not found: %PY%
  pause
  exit /b 1
)

powershell -NoProfile -Command "try{(Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 2)|Out-Null; exit 0}catch{exit 1}"
if errorlevel 1 (
  echo Starting Agent Alex web server on port 8000 ...
  start "Agent Alex web" /D "%~dp0" "%PY%" -m uvicorn app.api:create_app --factory --port 8000
  powershell -NoProfile -Command "1..60 | %% { try{ (Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 2)|Out-Null; exit 0 } catch { Start-Sleep -Milliseconds 500 } }; exit 1"
)

start "" "http://127.0.0.1:8000/"
endlocal
