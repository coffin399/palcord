@echo off
setlocal EnableExtensions
cd /d "%~dp0"

REM Avoid mojibake: use UTF-8 for this console and for Python I/O
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ========================================
echo  Palcord - Palworld Discord Integration
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found. Install Python 3.11+ and add it to PATH.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [.venv] Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create .venv
    pause
    exit /b 1
  )
)

echo [deps] Installing / updating dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] Failed to upgrade pip
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Failed to install requirements
  pause
  exit /b 1
)

echo.
echo [run] Starting Palcord...
echo.
".venv\Scripts\python.exe" -m palcord
set "EXITCODE=%ERRORLEVEL%"

echo.
if not "%EXITCODE%"=="0" (
  echo [Palcord] Exit code: %EXITCODE%
)
pause
exit /b %EXITCODE%
