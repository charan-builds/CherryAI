param(
    [string]$Python = "python",
    [switch]$SkipPipUpgrade,
    [switch]$TrustPypiHost
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPath = Join-Path $ProjectRoot ".venv"

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $Arguments"
    }
}

if (-not (Test-Path $VenvPath)) {
    Invoke-NativeCommand -FilePath $Python -Arguments @("-m", "venv", $VenvPath)
}

$PythonExe = Join-Path $VenvPath "Scripts\python.exe"
$PipInstallArgs = @("-m", "pip", "install")
if ($TrustPypiHost) {
    $PipInstallArgs += @("--trusted-host", "pypi.org", "--trusted-host", "files.pythonhosted.org")
}

if (-not $SkipPipUpgrade) {
    Invoke-NativeCommand -FilePath $PythonExe -Arguments ($PipInstallArgs + @("--upgrade", "pip"))
}

Invoke-NativeCommand -FilePath $PythonExe -Arguments ($PipInstallArgs + @("-r", (Join-Path $ProjectRoot "requirements.txt")))

Write-Host "Cherry AI environment is ready: $VenvPath"
