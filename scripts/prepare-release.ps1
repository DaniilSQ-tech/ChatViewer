param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

if (-not $Version) {
    $Version = (& $python -c 'from version import __version__; print(__version__)').Trim()
}

$setupName = "ChatViewer-Setup-$Version.exe"
$portableName = "ChatViewer-$Version.exe"
$setupPath = Join-Path $root "dist\$setupName"
$portablePath = Join-Path $root "dist\$portableName"

foreach ($path in @($setupPath, $portablePath)) {
    if (-not (Test-Path $path)) {
        throw "File not found: $path. Run .\build-installer.ps1 first."
    }
}

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLower()
}

$shaSetup = Get-Sha256 $setupPath
$shaPortable = Get-Sha256 $portablePath
$date = Get-Date -Format "yyyy-MM-dd"

$templatePath = Join-Path $root ".github\RELEASE_NOTES.template.md"
$template = Get-Content $templatePath -Raw -Encoding UTF8

$notes = $template `
    -replace '\{\{VERSION\}\}', $Version `
    -replace '\{\{DATE\}\}', $date `
    -replace '\{\{CHANGE_1\}\}', 'Initial stable release' `
    -replace '\{\{CHANGE_2\}\}', 'OpenRouter multi-model comparison' `
    -replace '\{\{CHANGE_3\}\}', 'AI prompt assistant, export, Windows installer' `
    -replace '\{\{SHA256_SETUP\}\}', $shaSetup `
    -replace '\{\{SHA256_PORTABLE\}\}', $shaPortable

$outPath = Join-Path $root "dist\RELEASE_NOTES-$Version.md"
$notes | Set-Content -Path $outPath -Encoding UTF8

Write-Output "Release notes: $outPath"
Write-Output ""
Write-Output "SHA256 Setup:    $shaSetup"
Write-Output "SHA256 Portable: $shaPortable"
Write-Output ""
Write-Output "Create release:"
Write-Output "  git tag -a v$Version -m `"ChatList $Version`""
Write-Output "  git push origin v$Version"
Write-Output "  gh release create v$Version `"dist\$setupName`" `"dist\$portableName`" --title `"ChatList $Version`" --notes-file `"dist\RELEASE_NOTES-$Version.md`""
