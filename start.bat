@echo off
echo ========================================
echo   BookRead - Starting Backend Server
echo ========================================
cd /d %~dp0backend
start "BookRead Backend" python start.py
echo Backend started on http://localhost:5000
echo.
echo ========================================
echo   BookRead - Starting Frontend Dev Server
echo ========================================
cd /d %~dp0frontend
start "BookRead Frontend" cmd /c "node_modules\.bin\vite --host"
echo Frontend started on http://localhost:5173
echo.
echo Press any key to open browser...
pause >nul
start http://localhost:5173
