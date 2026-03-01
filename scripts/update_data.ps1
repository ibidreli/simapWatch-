Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found at $pythonExe"
}

$argsList = @("-m", "simapwatch.update_cli") + $args

Push-Location (Join-Path $repoRoot "src")
try {
    & $pythonExe @argsList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
