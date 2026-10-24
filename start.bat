@echo off
title College Faculty Attendance & Session Monitoring System
echo ============================================================
echo   Starting Faculty Attendance & Session Monitoring System
echo ============================================================
echo.

echo [1/2] Starting FastAPI Backend Server on port 8000...
start "FAMS - Backend Server (Port 8000)" cmd /k "cd /d "%~dp0backend" && .\venv\Scripts\activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/2] Starting React Frontend Dev Server...
start "FAMS - Frontend Server" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ============================================================
echo   Servers are starting up!
echo   - Backend API:  http://localhost:8000/api
echo   - Swagger Docs: http://localhost:8000/docs
echo   - Frontend App: http://localhost:5173
echo ============================================================
echo.
