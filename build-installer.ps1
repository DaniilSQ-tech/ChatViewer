param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

if (-not $SkipBuild) {
    Write-Output "Building executable..."
    & $python -m pip install -r requirements.txt pyinstaller -q
    & $python -m PyInstaller ChatViewer.spec --clean
}

$version = (& $python -c 'from version import __version__; print(__version__)').Trim()
$exeName = "ChatViewer-$version.exe"
$exePath = Join-Path $root "dist\$exeName"

if (-not (Test-Path $exePath)) {
    throw "Missing $exePath. Run .\build.ps1 first or omit -SkipBuild."
}

$isccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)

$iscc = $null
foreach ($candidate in $isccCandidates) {
    if (Test-Path $candidate) {
        $iscc = $candidate
        break
    }
}

if (-not $iscc) {
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        $iscc = $cmd.Source
    }
}

if (-not $iscc) {
    throw "Inno Setup 6 not found. Install: winget install --id JRSoftware.InnoSetup"
}

Write-Output "Compiling installer..."
& $iscc "/DMyAppVersion=$version" "/DMyAppExeName=$exeName" (Join-Path $root "installer\ChatViewer.iss")

$setupPath = Join-Path $root "dist\ChatViewer-Setup-$version.exe"
if (Test-Path $setupPath) {
    Write-Output "Installer ready: $setupPath"
} else {
    Write-Output "Done. Check dist\ folder."
}
