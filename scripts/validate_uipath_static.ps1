[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$projectRoot = Join-Path $repoRoot "UiPath\DocChronoUiPathExamples"
$projectPath = Join-Path $projectRoot "project.json"

$project = Get-Content -LiteralPath $projectPath -Raw | ConvertFrom-Json
if ($project.name -ne "DocChronoUiPathExamples") {
    throw "Unexpected UiPath project name."
}
if ($project.main -ne "Main.xaml" -or $project.targetFramework -ne "Windows") {
    throw "UiPath entry point or target framework changed unexpectedly."
}
if ($project.expressionLanguage -ne "VisualBasic") {
    throw "The UiPath project must keep Visual Basic expressions."
}
if ($project.dependencies.'UiPath.System.Activities' -ne '[26.6.1]') {
    throw "UiPath.System.Activities must remain exactly pinned to [26.6.1]."
}

$xamlFiles = @(Get-ChildItem -LiteralPath $projectRoot -Recurse -Filter *.xaml -File)
if ($xamlFiles.Count -ne 7) {
    throw "Expected exactly seven UiPath XAML workflows, found $($xamlFiles.Count)."
}
foreach ($xamlFile in $xamlFiles) {
    try {
        [xml](Get-Content -LiteralPath $xamlFile.FullName -Raw) | Out-Null
    }
    catch {
        throw "Invalid XAML/XML in $($xamlFile.FullName): $($_.Exception.Message)"
    }
}

$forbiddenProjectPaths = @(
    ".github",
    ".venv",
    "artifacts",
    "docs",
    "Examples\data",
    "Examples\expected",
    "Examples\requests",
    "src",
    "tests"
)
foreach ($relativePath in $forbiddenProjectPaths) {
    if (Test-Path -LiteralPath (Join-Path $projectRoot $relativePath)) {
        throw "UiPath publish root contains forbidden path: $relativePath"
    }
}

$cliPolicy = Get-Content -LiteralPath (Join-Path $repoRoot ".uipath\config.json") -Raw | ConvertFrom-Json
if ($cliPolicy.core.autoVersionSync -ne "false" -or $cliPolicy.core.version -ne "1.197") {
    throw "UiPath CLI policy must disable auto sync and pin the 1.197 tool line."
}

Write-Host "UiPath static contract verified: 7 XAML files, pinned activities, isolated publish root."
