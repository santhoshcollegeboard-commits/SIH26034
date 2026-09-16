@echo off
setlocal enabledelayedexpansion

title PackCheck Launcher

:: -------------------------------------------------------------
:: Determine project root directory dynamically from .bat location
:: -------------------------------------------------------------
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

echo ==========================================================
echo               PackCheck Launcher - SIH26034
echo ==========================================================
echo Project Directory: %ROOT%
echo.

:: -------------------------------------------------------------
:: 1. Detect Python Executable
:: -------------------------------------------------------------
set "PYTHON_EXE="
if exist "%ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT%\.venv\Scripts\python.exe"
) else (
    where python.exe >nul 2>nul
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=python"
    ) else if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" (
        set "PYTHON_EXE=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python executable could not be found.
    echo Please install Python 3.10+ or set up a virtual environment in .venv.
    echo.
    pause
    exit /b 1
)

:: -------------------------------------------------------------
:: 2. Detect Node.js and npm
:: -------------------------------------------------------------
where npm.cmd >nul 2>nul
if !errorlevel! neq 0 (
    if exist "%USERPROFILE%\AppData\Local\Programs\nodejs\npm.cmd" (
        set "PATH=%USERPROFILE%\AppData\Local\Programs\nodejs;%PATH%"
    ) else if exist "%USERPROFILE%\.gemini\antigravity-ide\bin\npm.cmd" (
        set "PATH=%USERPROFILE%\.gemini\antigravity-ide\bin;%PATH%"
    )
)

where npm.cmd >nul 2>nul
if !errorlevel! neq 0 (
    echo [ERROR] Node.js / npm could not be found.
    echo Please install Node.js v20 or later to run the PackCheck frontend.
    echo.
    pause
    exit /b 1
)

set "PYTHONPATH=%ROOT%;%PYTHONPATH%"

:: -------------------------------------------------------------
:: 3. Start or Verify Backend Server
:: -------------------------------------------------------------
curl.exe -s -f http://127.0.0.1:8000/health >nul 2>nul
if !errorlevel! equ 0 (
    echo PackCheck Backend is already running on http://127.0.0.1:8000.
) else (
    echo Starting PackCheck Backend...
    start "PackCheck Backend" cmd /k "cd /d "%ROOT%" && set "PYTHONPATH=%ROOT%;%%PYTHONPATH%%" && "%PYTHON_EXE%" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"
)

:: -------------------------------------------------------------
:: 4. Start or Verify Frontend Server
:: -------------------------------------------------------------
curl.exe -s -f http://127.0.0.1:5173/ >nul 2>nul
if !errorlevel! equ 0 (
    echo PackCheck Frontend is already running on http://127.0.0.1:5173.
) else (
    echo Starting PackCheck Frontend...
    start "PackCheck Frontend" cmd /k "cd /d "%ROOT%\frontend" && npm.cmd run dev -- --host 127.0.0.1 --port 5173"
)

:: -------------------------------------------------------------
:: 5. Wait for PackCheck Frontend to be responsive
:: -------------------------------------------------------------
echo Waiting for PackCheck...
set ATTEMPTS=0

:WAIT_LOOP
set /a ATTEMPTS+=1
ping 127.0.0.1 -n 2 >nul
curl.exe -s -f http://127.0.0.1:5173/ >nul 2>nul
if !errorlevel! equ 0 goto LAUNCH_BROWSER

if !ATTEMPTS! geq 30 (
    echo.
    echo [ERROR] PackCheck frontend did not become available within 30 seconds.
    echo Please check the PackCheck Backend and PackCheck Frontend command windows for details.
    echo.
    pause
    exit /b 1
)
goto WAIT_LOOP

:: -------------------------------------------------------------
:: 6. Open Default Browser
:: -------------------------------------------------------------
:LAUNCH_BROWSER
echo Opening PackCheck...
start http://127.0.0.1:5173
echo.
echo ==========================================================
echo PackCheck is running successfully.
echo - Backend:  http://127.0.0.1:8000
echo - Frontend: http://127.0.0.1:5173
echo.
echo Keep the backend and frontend command windows open.
echo You can close this launcher window at any time.
echo ==========================================================
echo.
ping 127.0.0.1 -n 4 >nul
exit /b 0
