@echo off
setlocal

REM 支持环境变量自定义端口
if not defined BACKEND_PORT set BACKEND_PORT=5000
if not defined VITE_PORT set VITE_PORT=5173

echo ========================================
echo   BookRead - Starting Backend Server
echo ========================================
cd /d %~dp0backend
start "BookRead Backend" python start.py
echo Backend started on http://localhost:%BACKEND_PORT%
echo.
echo ========================================
echo   BookRead - Starting Frontend Dev Server
echo ========================================
cd /d %~dp0frontend
start "BookRead Frontend" cmd /c "node_modules\.bin\vite --host"
echo Frontend started on http://localhost:%VITE_PORT%
echo.
echo Press any key to open browser...
pause >nul
start http://localhost:%VITE_PORT%
