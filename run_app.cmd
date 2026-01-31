@echo off
setlocal ENABLEDELAYEDEXPANSION
pushd %~dp0

:: Configure host/port and debug
set HOST=127.0.0.1
set PORT=5050
set DEBUG=True

echo [INFO] Using HOST=%HOST% PORT=%PORT% DEBUG=%DEBUG%

:: Ensure dependencies are installed for the current Python
echo [INFO] Installing dependencies (if needed)...
python -m pip install -r requirements.txt >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo [WARN] Automatic dependency install encountered issues. Please run manually: python -m pip install -r requirements.txt
)

echo [INFO] Starting server. Open http://127.0.0.1:%PORT%/ in your browser.
python app.py

popd
endlocal
