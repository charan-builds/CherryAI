param(
    [switch]$NoGui
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
} else {
    $PythonExe = "python"
}

$ArgsList = @((Join-Path $ProjectRoot "main.py"))
if ($NoGui) {
    $ArgsList += "--no-gui"
}

& $PythonExe @ArgsList
exit $LASTEXITCODE
