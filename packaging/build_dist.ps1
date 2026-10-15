# Kiri Programming Language — Distribution Packaging Script
param(
    [string]$Version = "1.0.0",
    [string]$Architecture = "windows-x64"
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$DistRoot = "$RepoRoot\dist"
$BundleName = "Kiri-$Version-$Architecture"
$BundleDir = "$DistRoot\$BundleName"
$ZipPath = "$DistRoot\$BundleName.zip"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       Building Kiri Distribution Package: $BundleName     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Clean previous bundle
if (Test-Path $BundleDir) { Remove-Item -Path $BundleDir -Recurse -Force }
if (Test-Path $ZipPath) { Remove-Item -Path $ZipPath -Force }
New-Item -ItemType Directory -Force -Path $BundleDir | Out-Null

$BinDir = "$BundleDir\bin"
$IconsDir = "$BundleDir\icons"
$ExamplesDir = "$BundleDir\examples"
$DocsDir = "$BundleDir\docs"
$ToolsDir = "$BundleDir\tools"
$InstallerDir = "$BundleDir\installer\windows"

New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
New-Item -ItemType Directory -Force -Path $IconsDir | Out-Null
New-Item -ItemType Directory -Force -Path $ExamplesDir | Out-Null
New-Item -ItemType Directory -Force -Path $DocsDir | Out-Null
New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null
New-Item -ItemType Directory -Force -Path $InstallerDir | Out-Null

# 2. Copy Native Binaries
Write-Host "[1/6] Copying native binaries..." -ForegroundColor Green
$CliSource = "$RepoRoot\src\Kiri.Cli\bin\Debug\net10.0"
Copy-Item -Path "$CliSource\*" -Destination $BinDir -Recurse -Force
if (Test-Path "$BinDir\kiri.exe") {
    Move-Item -Path "$BinDir\kiri.exe" -Destination "$BinDir\kiri-core.exe" -Force
}
Copy-Item -Path "$RepoRoot\kiri.cmd" -Destination "$BinDir\kiri.cmd" -Force
Copy-Item -Path "$RepoRoot\kiri.bat" -Destination "$BinDir\kiri.bat" -Force

# 3. Copy Icons
Write-Host "[2/6] Copying icons..." -ForegroundColor Green
Copy-Item -Path "$RepoRoot\icons\*" -Destination $IconsDir -Recurse -Force

# 4. Copy Documentation, Examples, Tools
Write-Host "[3/6] Copying standard documentation, examples, and tools..." -ForegroundColor Green
if (Test-Path "$RepoRoot\examples") { Copy-Item -Path "$RepoRoot\examples\*" -Destination $ExamplesDir -Recurse -Force }
if (Test-Path "$RepoRoot\docs") { Copy-Item -Path "$RepoRoot\docs\*" -Destination $DocsDir -Recurse -Force }
if (Test-Path "$RepoRoot\tools") { Copy-Item -Path "$RepoRoot\tools\*" -Destination $ToolsDir -Recurse -Force }

# 5. Copy Installer scripts & root Setup.cmd
Write-Host "[4/6] Copying installer scripts..." -ForegroundColor Green
Copy-Item -Path "$RepoRoot\installer\windows\*" -Destination $InstallerDir -Recurse -Force
Copy-Item -Path "$RepoRoot\Setup.cmd" -Destination "$BundleDir\Setup.cmd" -Force
if (Test-Path "$RepoRoot\README.md") { Copy-Item -Path "$RepoRoot\README.md" -Destination "$BundleDir\README.md" -Force }
if (Test-Path "$RepoRoot\LICENSE") { Copy-Item -Path "$RepoRoot\LICENSE" -Destination "$BundleDir\LICENSE" -Force }

# 6. Generate SHA256 Checksum
Write-Host "[5/6] Creating ZIP archive..." -ForegroundColor Green
Compress-Archive -Path "$BundleDir\*" -DestinationPath $ZipPath -CompressionLevel Optimal

Write-Host "[6/6] Generating SHA256 checksums..." -ForegroundColor Green
$sha256 = (Get-FileHash -Path $ZipPath -Algorithm SHA256).Hash
Set-Content -Path "$DistRoot\$BundleName.zip.sha256" -Value "$sha256 *$BundleName.zip" -Encoding utf8

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "         Distribution Package Created!                    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Archive:  $ZipPath" -ForegroundColor Green
Write-Host "SHA256:   $sha256" -ForegroundColor Yellow
Write-Host ""
