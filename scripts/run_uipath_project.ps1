[CmdletBinding()]
param(
    [string]$PythonExecutable = ".venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$projectRoot = Join-Path $repoRoot "UiPath\DocChronoUiPathExamples"
$pythonPath = if ([System.IO.Path]::IsPathRooted($PythonExecutable)) {
    $PythonExecutable
}
else {
    [System.IO.Path]::GetFullPath((Join-Path $repoRoot $PythonExecutable))
}
$auditRoot = Join-Path $env:TEMP ("docchrono-uipath-run-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $auditRoot | Out-Null
$argumentsPath = Join-Path $auditRoot "main.arguments.json"
$logPath = Join-Path $auditRoot "main.uip.log"
$arguments = [ordered]@{
    in_PythonExe = $pythonPath
    in_WorkingDirectory = $repoRoot
}
$arguments | ConvertTo-Json | Set-Content -LiteralPath $argumentsPath -Encoding utf8

$rawResult = & uip rpa run `
    --file-path "Main.xaml" `
    --project-dir $projectRoot `
    --skip-build `
    --input-arguments-file $argumentsPath `
    --output json `
    --log-file $logPath
$toolExit = $LASTEXITCODE
if ($toolExit -ne 0) {
    throw "UiPath CLI failed to execute Main.xaml (exit $toolExit). Inspect $logPath."
}
$serializedResult = $rawResult | Out-String
$jsonMatch = [regex]::Match($serializedResult, '(?s)\{\s*"Result".*\}\s*$')
if (-not $jsonMatch.Success) {
    throw "UiPath CLI did not return a parseable result envelope. Inspect $logPath."
}
$result = $jsonMatch.Value | ConvertFrom-Json
if ($result.Result -ne "Success" -or $result.Data.hasErrors) {
    throw "Main.xaml failed: $($result.Data.errorMessage)"
}

Write-Host "UiPath Main.xaml completed all five DocChrono examples without errors."
