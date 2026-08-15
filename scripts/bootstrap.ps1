[CmdletBinding()]
param(
    [string]$PythonVersion = "3.13"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

Push-Location $repoRoot
try {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        & py "-$PythonVersion" -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            throw "Could not create .venv with Python $PythonVersion. Install CPython 3.11-3.13 or pass another supported version."
        }
    }

    & $venvPython -m pip install -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }

    & $venvPython scripts/generate_synthetic_data.py --check
    if ($LASTEXITCODE -ne 0) {
        throw "Committed synthetic fixtures do not match the generator."
    }

    Write-Host "Environment ready: $venvPython"
}
finally {
    Pop-Location
}
