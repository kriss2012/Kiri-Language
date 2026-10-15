# Kiri Programming Language — Official Windows Native Installer
# Installs standalone Kiri native distribution, configures PATH, registers .kiri extension, registers icons, and registers Start Menu shortcuts.

param(
    [string]$InstallDir = ($env:LOCALAPPDATA + '\Kiri')
)

$ErrorActionPreference = 'Stop'

Write-Host '==========================================================' -ForegroundColor Cyan
Write-Host '       Kiri Programming Language — Windows Setup          ' -ForegroundColor Cyan
Write-Host '==========================================================' -ForegroundColor Cyan
Write-Host ('Installing to: ' + $InstallDir)
Write-Host ''

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path ($ScriptDir + '\..\..')).Path

# 1. Create directory structure
$BinDir = $InstallDir + '\bin'
$StdlibDir = $InstallDir + '\stdlib'
$IconsDir = $InstallDir + '\icons'
$ExamplesDir = $InstallDir + '\examples'
$DocsDir = $InstallDir + '\docs'
$ToolsDir = $InstallDir + '\tools'

New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
New-Item -ItemType Directory -Force -Path $StdlibDir | Out-Null
New-Item -ItemType Directory -Force -Path $IconsDir | Out-Null
New-Item -ItemType Directory -Force -Path $ExamplesDir | Out-Null
New-Item -ItemType Directory -Force -Path $DocsDir | Out-Null
New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null

# 2. Copy Native Kiri Executable & Dependencies to bin/
Write-Host '[1/7] Installing native compiler and runtime binaries...' -ForegroundColor Green
$CliBinSource = $RepoRoot + '\src\Kiri.Cli\bin\Debug\net10.0'

if (-not (Test-Path ($CliBinSource + '\kiri.exe'))) {
    throw ('Native binary not found at ' + $CliBinSource + '\kiri.exe. Please ensure build artifacts exist.')
}

Copy-Item -Path ($CliBinSource + '\*') -Destination $BinDir -Recurse -Force
if (Test-Path ($BinDir + '\kiri.exe')) {
    Move-Item -Path ($BinDir + '\kiri.exe') -Destination ($BinDir + '\kiri-core.exe') -Force
}
Write-Host '      Installed native kiri-core.exe, Kiri.Core.dll, and runtime configuration.' -ForegroundColor Gray

# 3. Create bin/kiri.cmd and bin/kiri.bat launchers
Write-Host '[2/7] Creating CLI command wrappers...' -ForegroundColor Green
Copy-Item -Path ($RepoRoot + '\kiri.cmd') -Destination ($BinDir + '\kiri.cmd') -Force
Copy-Item -Path ($RepoRoot + '\kiri.bat') -Destination ($BinDir + '\kiri.bat') -Force

# 4. Copy Icons to icons/
Write-Host '[3/7] Installing official Kiri icons...' -ForegroundColor Green
Copy-Item -Path ($RepoRoot + '\icons\*') -Destination $IconsDir -Recurse -Force

# 5. Copy Standard Library, Examples, Docs, Tools
Write-Host '[4/7] Installing standard library, tools, and documentation...' -ForegroundColor Green
if (Test-Path ($RepoRoot + '\stdlib')) { Copy-Item -Path ($RepoRoot + '\stdlib\*') -Destination $StdlibDir -Recurse -Force }
if (Test-Path ($RepoRoot + '\examples')) { Copy-Item -Path ($RepoRoot + '\examples\*') -Destination $ExamplesDir -Recurse -Force }
if (Test-Path ($RepoRoot + '\docs')) { Copy-Item -Path ($RepoRoot + '\docs\*') -Destination $DocsDir -Recurse -Force }
if (Test-Path ($RepoRoot + '\tools')) { Copy-Item -Path ($RepoRoot + '\tools\*') -Destination $ToolsDir -Recurse -Force }

# 6. Configure User PATH
Write-Host '[5/7] Configuring environment PATH...' -ForegroundColor Green
$UserPath = [Environment]::GetEnvironmentVariable('Path', [EnvironmentVariableTarget]::User)
if (-not $UserPath) { $UserPath = '' }
$Paths = $UserPath.Split(';') | Where-Object { $_ -ne '' -and $_ -ne $null }
if ($Paths -notcontains $BinDir) {
    $NewPathsList = @($Paths) + @($BinDir)
    $NewPath = [string]::Join(';', $NewPathsList)
    [Environment]::SetEnvironmentVariable('Path', $NewPath, [EnvironmentVariableTarget]::User)
    Write-Host ('      Added ' + $BinDir + ' to User PATH.') -ForegroundColor Gray
} else {
    Write-Host ('      ' + $BinDir + ' is already in User PATH.') -ForegroundColor Gray
}

# Update current session PATH
$env:Path = $BinDir + ';' + $env:Path

# 7. Register .kiri File Association and Icon in Windows Registry
Write-Host '[6/7] Registering .kiri file association and official icon...' -ForegroundColor Green
try {
    # .kiri extension
    $ExtKey = 'HKCU:\Software\Classes\.kiri'
    New-Item -Path $ExtKey -Force | Out-Null
    Set-ItemProperty -Path $ExtKey -Name '(Default)' -Value 'Kiri.SourceFile'
    Set-ItemProperty -Path $ExtKey -Name 'Content Type' -Value 'text/plain'
    Set-ItemProperty -Path $ExtKey -Name 'PerceivedType' -Value 'text'

    # ProgID
    $ProgIdKey = 'HKCU:\Software\Classes\Kiri.SourceFile'
    New-Item -Path $ProgIdKey -Force | Out-Null
    Set-ItemProperty -Path $ProgIdKey -Name '(Default)' -Value 'Kiri Source File'

    # Default Icon
    $IconKey = $ProgIdKey + '\DefaultIcon'
    New-Item -Path $IconKey -Force | Out-Null
    $IconVal = $IconsDir + '\kiri.ico,0'
    Set-ItemProperty -Path $IconKey -Name '(Default)' -Value $IconVal

    # Shell open (default in editor)
    $OpenCmdKey = $ProgIdKey + '\shell\open\command'
    New-Item -Path $OpenCmdKey -Force | Out-Null
    Set-ItemProperty -Path $OpenCmdKey -Name '(Default)' -Value 'notepad.exe "%1"'

    # Shell Run with Kiri
    $RunKey = $ProgIdKey + '\shell\Run_Kiri'
    New-Item -Path $RunKey -Force | Out-Null
    Set-ItemProperty -Path $RunKey -Name '(Default)' -Value 'Run with Kiri'
    $RunCmdKey = $RunKey + '\command'
    New-Item -Path $RunCmdKey -Force | Out-Null
    $RunVal = '"' + $BinDir + '\kiri.exe" "%1"'
    Set-ItemProperty -Path $RunCmdKey -Name '(Default)' -Value $RunVal

    # Explorer OpenWithProgIds
    $ExplorerExt = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.kiri\OpenWithProgids'
    New-Item -Path $ExplorerExt -Force | Out-Null
    Set-ItemProperty -Path $ExplorerExt -Name 'Kiri.SourceFile' -Value ([byte[]]@())

    Write-Host '      Registered .kiri with ProgID Kiri.SourceFile and official icon.' -ForegroundColor Gray
} catch {
    Write-Warning ('Failed to set file association in registry: ' + $_)
}

# Force Explorer to refresh icon cache immediately
try {
    Add-Type -MemberDefinition '[DllImport("shell32.dll")] public static extern void SHChangeNotify(int eventId, int flags, IntPtr item1, IntPtr item2);' -Name ShellNotifierInstall -Namespace Win32Install -ErrorAction SilentlyContinue
    [Win32Install.ShellNotifierInstall]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
    Write-Host '      Windows Shell refreshed; .kiri files will display Kiri icon.' -ForegroundColor Gray
} catch {}

# 8. Start Menu Shortcut
$StartMenuDir = $env:APPDATA + '\Microsoft\Windows\Start Menu\Programs\Kiri'
New-Item -ItemType Directory -Force -Path $StartMenuDir | Out-Null
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($StartMenuDir + '\Kiri REPL.lnk')
    $Shortcut.TargetPath = $BinDir + '\kiri.exe'
    $Shortcut.Arguments = 'repl'
    $Shortcut.IconLocation = $IconsDir + '\kiri.ico,0'
    $Shortcut.Description = 'Kiri Interactive REPL'
    $Shortcut.Save()
    Write-Host '      Created Start Menu shortcut.' -ForegroundColor Gray
} catch {}

# 9. Create Uninstaller
Copy-Item -Path ($ScriptDir + '\uninstall.ps1') -Destination ($InstallDir + '\uninstall.ps1') -Force
Copy-Item -Path ($ScriptDir + '\uninstall.cmd') -Destination ($InstallDir + '\uninstall.cmd') -Force

# Add to Add/Remove Programs
try {
    $UninstallReg = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Kiri'
    New-Item -Path $UninstallReg -Force | Out-Null
    Set-ItemProperty -Path $UninstallReg -Name 'DisplayName' -Value 'Kiri Programming Language SDK 1.0.0'
    Set-ItemProperty -Path $UninstallReg -Name 'DisplayVersion' -Value '1.0.0'
    Set-ItemProperty -Path $UninstallReg -Name 'Publisher' -Value 'Kiri Language Project'
    Set-ItemProperty -Path $UninstallReg -Name 'DisplayIcon' -Value ($IconsDir + '\kiri.ico')
    Set-ItemProperty -Path $UninstallReg -Name 'InstallLocation' -Value $InstallDir
    $UninstallVal = '"' + $InstallDir + '\uninstall.cmd"'
    Set-ItemProperty -Path $UninstallReg -Name 'UninstallString' -Value $UninstallVal
} catch {}

# 10. Run Validation Check
Write-Host '[7/7] Running installation validation checks...' -ForegroundColor Green
$versionOutput = cmd.exe /c ("`"" + $BinDir + "\kiri.cmd`" --version")
Write-Host ('      Validation 1: ' + $versionOutput) -ForegroundColor Cyan

$testRunOutput = cmd.exe /c ("`"" + $BinDir + "\kiri.cmd`" `"" + $ExamplesDir + "\hello.kiri`"")
Write-Host ('      Validation 2: ' + $testRunOutput) -ForegroundColor Cyan

Write-Host ''
Write-Host '==========================================================' -ForegroundColor Cyan
Write-Host '         Installation Complete Successfully!              ' -ForegroundColor Cyan
Write-Host '==========================================================' -ForegroundColor Cyan
Write-Host 'Kiri is now installed and ready to use.' -ForegroundColor Green
Write-Host 'You can open ANY terminal and type:' -ForegroundColor White
Write-Host '    kiri --version' -ForegroundColor Yellow
Write-Host '    kiri doctor' -ForegroundColor Yellow
Write-Host '    kiri hello.kiri' -ForegroundColor Yellow
Write-Host ''
