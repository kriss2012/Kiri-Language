# Kiri Programming Language — Official Windows Uninstaller
# Cleans up PATH, file associations, Start Menu shortcuts, and installed files.

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\Kiri"
)

$ErrorActionPreference = "SilentlyContinue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       Kiri Programming Language — Windows Uninstaller    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Uninstalling from: $InstallDir`n"

# 1. Remove from User PATH
Write-Host "[1/5] Removing from environment PATH..." -ForegroundColor Green
$BinDir = "$InstallDir\bin"
$UserPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
if ($UserPath) {
    $Paths = $UserPath -split ";" | Where-Object { $_ -ne "" -and $_ -ne $BinDir }
    $NewPath = $Paths -join ";"
    [Environment]::SetEnvironmentVariable("Path", $NewPath, [EnvironmentVariableTarget]::User)
    Write-Host "      Removed '$BinDir' from User PATH." -ForegroundColor Gray
}

# 2. Remove File Associations and Registry Keys
Write-Host "[2/5] Removing .kiri file associations and icons..." -ForegroundColor Green
Remove-Item -Path "HKCU:\Software\Classes\.kiri" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "HKCU:\Software\Classes\Kiri.SourceFile" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.kiri" -Recurse -Force -ErrorAction SilentlyContinue

# 3. Remove Add/Remove Programs entry
Write-Host "[3/5] Removing Add/Remove Programs entry..." -ForegroundColor Green
Remove-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Kiri" -Recurse -Force -ErrorAction SilentlyContinue

# 4. Remove Start Menu shortcuts
Write-Host "[4/5] Removing Start Menu shortcuts..." -ForegroundColor Green
$StartMenuDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Kiri"
Remove-Item -Path $StartMenuDir -Recurse -Force -ErrorAction SilentlyContinue

# 5. Refresh Windows Shell
try {
    Add-Type -TypeDefinition @'
    using System;
    using System.Runtime.InteropServices;
    public class ShellNotifierUninstall {
        [DllImport("shell32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        public static extern void SHChangeNotify(uint wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
    }
'@ -ErrorAction SilentlyContinue
    [ShellNotifierUninstall]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
} catch {}

# 6. Remove Installation Directory
Write-Host "[5/5] Removing installed files..." -ForegroundColor Green
if (Test-Path $InstallDir) {
    # Remove all except possibly the running uninstaller script if run from there
    Get-ChildItem -Path $InstallDir -Exclude "uninstall.*" -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "      Files removed from $InstallDir" -ForegroundColor Gray
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "         Uninstallation Complete Successfully!            " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Kiri has been cleanly removed from your system." -ForegroundColor Green
