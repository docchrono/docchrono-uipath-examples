[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$projectRoot = Join-Path $repoRoot "UiPath\DocChronoUiPathExamples"
$workflows = @(
    "Framework\RunDocChronoBridge.xaml",
    "Examples\01_BuildCase.xaml",
    "Examples\02_ExportTimeline.xaml",
    "Examples\03_TraceEvidence.xaml",
    "Examples\04_FindGraphPath.xaml",
    "Examples\05_ExportReviewQueue.xaml",
    "Main.xaml"
)

& uip rpa analyzer-rules list --project-dir $projectRoot --scope Workflow --output json
if ($LASTEXITCODE -ne 0) {
    throw "Could not list UiPath Workflow Analyzer rules."
}

& uip rpa analyze $projectRoot `
    --repository-path $repoRoot `
    --default-severity Warning `
    --output json
if ($LASTEXITCODE -ne 0) {
    throw "UiPath project analysis failed."
}

foreach ($workflow in $workflows) {
    & uip rpa validate --file-path $workflow --project-dir $projectRoot --min-severity warning --output json
    if ($LASTEXITCODE -ne 0) {
        throw "UiPath validation failed for $workflow."
    }
}

& uip rpa build $projectRoot --log-level Warn --output json
if ($LASTEXITCODE -ne 0) {
    throw "UiPath project build failed."
}
