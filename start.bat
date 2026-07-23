@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo  Palcord - Palworld Discord Integration
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python が見つかりません。Python 3.11+ をインストールし、PATH に追加してください。
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [.venv] 仮想環境を作成しています...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] venv の作成に失敗しました。
    pause
    exit /b 1
  )
)

echo [deps] 依存パッケージをインストール / 更新しています...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] pip の更新に失敗しました。
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] 依存パッケージのインストールに失敗しました。
  pause
  exit /b 1
)

echo.
echo [run] Palcord を起動します...
echo.
".venv\Scripts\python.exe" -m palcord
set "EXITCODE=%ERRORLEVEL%"

echo.
if not "%EXITCODE%"=="0" (
  echo [Palcord] 終了コード: %EXITCODE%
)
pause
exit /b %EXITCODE%
