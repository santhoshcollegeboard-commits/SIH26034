@echo off
title PackCheck - Milestone 5

echo ==========================================
echo          PACKCHECK - MILESTONE 5
echo ==========================================
echo.

cd /d "%~dp0"

echo [1/2] Starting FastAPI backend...
start "PackCheck Backend" cmd /k "python -m uvicorn backend.app.main:app --reload"

timeout /t 3 /nobreak >nul

echo [2/2] Starting React frontend...
start "PackCheck Frontend" cmd /k "cd frontend && npm run dev"

echo Waiting for frontend to initialize...
timeout /t 4 /nobreak >nul

echo [3/3] Opening Google Chrome...
start chrome http://localhost:5173

echo.
echo ==========================================
echo PackCheck services are starting...
echo.
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:5173
echo ==========================================
echo.
pause