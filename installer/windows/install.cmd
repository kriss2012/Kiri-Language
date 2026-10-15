@echo off
setlocal
chcp 65001 >nul
echo ==========================================================
echo       Kiri Programming Language — Windows Installer       
echo ==========================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Installation encountered an error.
    pause
    exit /b %ERRORLEVEL%
)
echo.
pause
endlocal
