@echo off
setlocal
chcp 65001 >nul
echo Starting Kiri Uninstallation...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"
pause
endlocal
