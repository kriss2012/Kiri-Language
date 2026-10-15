@echo off
setlocal
chcp 65001 >nul
echo Starting Kiri Setup...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\windows\install.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Setup encountered an error.
    pause
    exit /b %ERRORLEVEL%
)
echo.
pause
endlocal
