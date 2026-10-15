@echo off
setlocal
chcp 65001 >nul

if /i "%~1"=="doctor" (
    if exist "%~dp0..\tools\doctor.ps1" (
        powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\tools\doctor.ps1"
    ) else (
        powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\doctor.ps1"
    )
    exit /b %ERRORLEVEL%
)

if exist "%~dp0kiri-core.exe" (
    "%~dp0kiri-core.exe" %*
) else (
    "%~dp0src\Kiri.Cli\bin\Debug\net10.0\kiri.exe" %*
)
endlocal


