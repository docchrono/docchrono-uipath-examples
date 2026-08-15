[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$projectRoot = Join-Path $repoRoot "UiPath\DocChronoUiPathExamples"
$auditRoot = Join-Path $env:TEMP ("docchrono-uipath-package-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $auditRoot | Out-Null
$logPath = Join-Path $auditRoot "pack.log"

& uip rpa pack $projectRoot $auditRoot `
    --package-id DocChronoUiPathExamples `
    --package-version 1.0.0 `
    --package-author DocChrono `
    --package-description "DocChrono UiPath integration examples" `
    --output json `
    --log-file $logPath | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "UiPath package creation failed. Inspect $logPath."
}

$packages = @(Get-ChildItem -LiteralPath $auditRoot -Filter *.nupkg -File)
if ($packages.Count -ne 1) {
    throw "Expected one UiPath package, found $($packages.Count)."
}
$package = $packages[0]
if ($package.Length -gt 10MB) {
    throw "UiPath package is unexpectedly large ($($package.Length) bytes)."
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead($package.FullName)
try {
    $entries = @($archive.Entries | ForEach-Object { $_.FullName.Replace("\", "/") })
    $forbiddenPrefixes = @(
        "content/.claude/",
        "content/.github/",
        "content/.local/",
        "content/.pytest_cache/",
        "content/.ruff_cache/",
        "content/.venv/",
        "content/artifacts/",
        "content/docs/",
        "content/Examples/data/",
        "content/Examples/expected/",
        "content/Examples/requests/",
        "content/scripts/",
        "content/src/",
        "content/tests/"
    )
    foreach ($prefix in $forbiddenPrefixes) {
        if ($entries.Where({ $_.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) }).Count -gt 0) {
            throw "UiPath package contains forbidden content under $prefix."
        }
    }
    $requiredEntries = @(
        "content/project.json",
        "content/entry-points.json"
    )
    foreach ($entry in $requiredEntries) {
        if ($entries -cnotcontains $entry) {
            throw "UiPath package is missing required entry $entry."
        }
    }
    if ($entries.Where({ $_ -like "lib/*/DocChronoUiPathExamples.dll" }).Count -ne 1) {
        throw "UiPath package must contain exactly one compiled process assembly."
    }
}
finally {
    $archive.Dispose()
}

Write-Host "UiPath package content verified: $($package.Name) ($($package.Length) bytes)"
