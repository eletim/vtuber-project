param([int]$Port = 8766, [string]$Python = $env:PYTHON)
$ErrorActionPreference = 'Stop'
if (-not $Python) {
    $Python = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
}
if (-not (Test-Path -LiteralPath $Python)) { throw 'Python was not found. Pass -Python with your existing Python executable.' }
$localDependencies = Join-Path (Split-Path $PSScriptRoot -Parent) '.local-python'
if (Test-Path -LiteralPath $localDependencies) {
    $env:PYTHONPATH = $localDependencies + [IO.Path]::PathSeparator + $env:PYTHONPATH
}
Write-Host "Koma: http://127.0.0.1:$Port (Ctrl+C to stop; browser is not opened automatically)"
& $Python (Join-Path $PSScriptRoot 'runtime\server.py') --port $Port
exit $LASTEXITCODE
