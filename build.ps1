$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

& $python -m pip install -r requirements.txt pyinstaller
& $python -m PyInstaller ChatViewer.spec --clean

$version = (& $python -c 'from version import __version__; print(__version__)').Trim()
$exePath = "dist\ChatViewer-$version.exe"
if (Test-Path $exePath) {
    Write-Output "Сборка завершена: $exePath"
} else {
    Write-Output "Сборка завершена. Проверьте каталог dist\"
}
