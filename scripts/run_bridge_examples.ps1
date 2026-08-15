[CmdletBinding()]
param(
    [string]$PythonExecutable = ".venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = if ([System.IO.Path]::IsPathRooted($PythonExecutable)) {
    $PythonExecutable
}
else {
    [System.IO.Path]::GetFullPath((Join-Path $repoRoot $PythonExecutable))
}
$requests = @(
    "01_build_case",
    "02_export_timeline",
    "03_export_evidence",
    "04_find_path",
    "05_export_review_queue"
)

Push-Location $repoRoot
try {
    foreach ($name in $requests) {
        $requestPath = Join-Path $repoRoot "Examples\requests\$name.json"
        $responsePath = Join-Path $repoRoot "artifacts\responses\$name.response.json"
        & $pythonPath -m docchrono_uipath_bridge --request $requestPath --response $responsePath
        if ($LASTEXITCODE -notin @(0, 2)) {
            throw "Bridge request $name failed with exit code $LASTEXITCODE."
        }
        Write-Host "Created $responsePath"
    }
}
finally {
    Pop-Location
}
