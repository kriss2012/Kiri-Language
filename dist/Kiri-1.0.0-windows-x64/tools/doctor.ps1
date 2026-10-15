# Kiri Doctor — Diagnostics and Environment Health Check
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "                       Kiri Doctor                        " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$kiriHome = if ($env:KIRI_HOME) { $env:KIRI_HOME } else { "$env:LOCALAPPDATA\Kiri" }
$binDir = "$kiriHome\bin"
$kiriCoreExe = "$binDir\kiri-core.exe"
$kiriExe = "$binDir\kiri.exe"
$fallbackExe = (Resolve-Path "$PSScriptRoot\..\src\Kiri.Cli\bin\Debug\net10.0\kiri.exe" -ErrorAction SilentlyContinue).Path

# 1. Executable check
if (Test-Path $kiriCoreExe) {
    Write-Host "[OK]   Kiri Executable:       $kiriCoreExe" -ForegroundColor Green
    $resolvedExe = $kiriCoreExe
} elseif (Test-Path $kiriExe) {
    Write-Host "[OK]   Kiri Executable:       $kiriExe" -ForegroundColor Green
    $resolvedExe = $kiriExe
} elseif ($fallbackExe -and (Test-Path $fallbackExe)) {
    Write-Host "[OK]   Kiri Executable (Dev): $fallbackExe" -ForegroundColor Green
    $resolvedExe = $fallbackExe
} else {
    Write-Host "[FAIL] Kiri Executable:       Not found!" -ForegroundColor Red
    $resolvedExe = $null
}

# 2. Version check
if ($resolvedExe) {
    $ver = & $resolvedExe --version
    Write-Host "[OK]   Kiri Version:          $ver" -ForegroundColor Green
}

# 3. .NET Runtime check
$runtimes = dotnet --list-runtimes 2>&1
$net10 = $runtimes | Where-Object { $_ -like "Microsoft.NETCore.App 10.*" }
if ($net10) {
    Write-Host "[OK]   Native Runtime:        $($net10.Trim())" -ForegroundColor Green
} else {
    $anyNet = $runtimes | Where-Object { $_ -like "Microsoft.NETCore.App*" }
    if ($anyNet) {
        Write-Host "[WARN] Native Runtime:        $($anyNet[0].Trim()) (Recommend .NET 10)" -ForegroundColor Yellow
    } else {
        Write-Host "[FAIL] Native Runtime:        No .NET Core runtime found!" -ForegroundColor Red
    }
}

# 4. PATH integration
$userPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
$inUserPath = $userPath -and ($userPath -split ";" -contains $binDir)
$inCurrentPath = ($env:Path -split ";" -contains $binDir)
if ($inUserPath -or $inCurrentPath) {
    Write-Host "[OK]   Terminal Integration:   '$binDir' is in PATH" -ForegroundColor Green
} else {
    Write-Host "[WARN] Terminal Integration:   '$binDir' is NOT in PATH" -ForegroundColor Yellow
    Write-Host "       Suggestion: Run 'installer\windows\install.cmd' to register Kiri in PATH." -ForegroundColor Gray
}

# 5. File association (.kiri)
$extReg = Get-ItemProperty -Path "HKCU:\Software\Classes\.kiri" -ErrorAction SilentlyContinue
if ($extReg -and $extReg.'(default)' -eq "Kiri.SourceFile") {
    Write-Host "[OK]   File Association:      .kiri -> Kiri.SourceFile" -ForegroundColor Green
} else {
    Write-Host "[WARN] File Association:      .kiri not registered in HKCU" -ForegroundColor Yellow
}

# 6. File icon (.ico)
$iconReg = Get-ItemProperty -Path "HKCU:\Software\Classes\Kiri.SourceFile\DefaultIcon" -ErrorAction SilentlyContinue
if ($iconReg) {
    $iconPath = ($iconReg.'(default)' -split ",")[0].Trim('"')
    if (Test-Path $iconPath) {
        Write-Host "[OK]   Official File Icon:    $iconPath" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Official File Icon:    Path not found ($iconPath)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[WARN] Official File Icon:    Icon not associated with .kiri" -ForegroundColor Yellow
}

# 7. Architecture
$arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
$osDesc = [System.Runtime.InteropServices.RuntimeInformation]::OSDescription
Write-Host "[OK]   System Architecture:   $osDesc ($arch)" -ForegroundColor Green

Write-Host "----------------------------------------------------------" -ForegroundColor Cyan
Write-Host "Diagnostics complete." -ForegroundColor Cyan
Write-Host ""
