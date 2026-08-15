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
$fakeRoot = Join-Path $repoRoot "tests\uipath_fakes"
$auditRoot = Join-Path $env:TEMP ("docchrono-uipath-envelope-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $auditRoot | Out-Null

$scenarios = @(
    @{
        Name = "mismatched_request_id"
        ErrorText = "Validate correlated response envelope"
    },
    @{
        Name = "partial"
        ErrorText = "validated partial result"
    },
    @{
        Name = "malformed_result"
        ErrorText = "Validate response value shapes"
    },
    @{
        Name = "malformed_warning"
        ErrorText = "Validate response value shapes"
    },
    @{
        Name = "malformed_error"
        ErrorText = "Validate response value shapes"
    },
    @{
        Name = "mismatched_exit_status"
        ErrorText = "Validate correlated response envelope"
    }
)

foreach ($scenario in $scenarios) {
    $name = $scenario.Name
    $argumentsPath = Join-Path $auditRoot "$name.arguments.json"
    $responsePath = Join-Path $auditRoot "$name.response.json"
    $logPath = Join-Path $auditRoot "$name.uip.log"
    $requestPath = Join-Path $fakeRoot "$name.json"
    $arguments = [ordered]@{
        in_PythonExe = $pythonPath
        in_WorkingDirectory = $fakeRoot
        in_RequestPath = $requestPath
        in_ResponsePath = $responsePath
        in_TimeoutMs = 30000
    }
    $arguments | ConvertTo-Json | Set-Content -LiteralPath $argumentsPath -Encoding utf8

    $rawResult = & uip rpa run `
        --file-path "Framework\RunDocChronoBridge.xaml" `
        --project-dir $projectRoot `
        --skip-build `
        --input-arguments-file $argumentsPath `
        --output json `
        --log-file $logPath
    $toolExit = $LASTEXITCODE
    if ($toolExit -ne 0) {
        throw "UiPath CLI failed to execute the $name envelope test (exit $toolExit)."
    }
    $serializedResult = $rawResult | Out-String
    $jsonMatch = [regex]::Match($serializedResult, '(?s)\{\s*"Result".*\}\s*$')
    if (-not $jsonMatch.Success) {
        throw "UiPath CLI did not return a parseable $name result envelope. Inspect $logPath."
    }
    $result = $jsonMatch.Value | ConvertFrom-Json
    if (-not $result.Data.hasErrors) {
        throw "UiPath accepted the unsafe $name response envelope."
    }
    if ($result.Data.errorMessage -notlike "*$($scenario.ErrorText)*") {
        throw "UiPath rejected $name for an unexpected reason: $($result.Data.errorMessage)"
    }
    Write-Host "Rejected unsafe envelope: $name"
}
