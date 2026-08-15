# UiPath setup

## 1. Prerequisites

- Windows x64 machine supported by your UiPath release.
- UiPath Studio with the **Windows** project compatibility.
- Access to an approved feed containing `UiPath.System.Activities 26.6.1`.
- Git.
- 64-bit CPython 3.11, 3.12, or 3.13. Do not use 3.14 for DocChrono 0.1.0.
- Permission for the Robot identity to start the configured Python executable.

The sample uses Visual Basic expressions in XAML. It is not a Windows-Legacy or cross-platform project.

## 2. Clone and create the environment

Run PowerShell:

```powershell
git clone https://github.com/docchrono/docchrono-uipath-examples.git
Set-Location .\docchrono-uipath-examples

# Choose any supported minor installed on the machine.
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install .

.\.venv\Scripts\python.exe -c `
  "import sys, docchrono, docchrono_uipath_bridge; print(sys.version); print(docchrono.__version__)"
```

Expected DocChrono version: `0.1.0`.

For a clean reproducibility check, `requirements.txt` contains the same exact runtime pins. `pip install .` builds and installs the bridge with its pinned runtime dependencies. Contributors can instead run `pip install -r requirements-dev.txt`, which installs the local project plus test/audit tools. Production should install an immutable built artifact.

## 3. Smoke-test the bridge

```powershell
.\.venv\Scripts\python.exe -m docchrono_uipath_bridge `
  --request .\Examples\requests\01_build_case.json `
  --response .\artifacts\responses\01_build_case.response.json

$exit = $LASTEXITCODE
$response = Get-Content .\artifacts\responses\01_build_case.response.json -Raw | ConvertFrom-Json
$response.status
$response.result.counts
if ($exit -notin 0, 2) { throw "Bridge failed with exit $exit" }
```

Expected: `complete`, 6 documents, 12 entities, 5 events, 16 relationships, 10 claims, and 1 review item.

## 4. Open the project

```powershell
Invoke-Item .\UiPath\DocChronoUiPathExamples\project.json
```

If Windows has no UiPath file association:

1. Start UiPath Studio.
2. Select **Home > Open > Browse Local**.
3. Select `UiPath\DocChronoUiPathExamples\project.json`.
4. Wait for dependency restore.

Do not open a copy from a read-only network share. UiPath recommends source control for collaboration and requires writable project metadata.

## 5. Validate project settings

In Studio, verify:

- project compatibility: **Windows**;
- expression language: **Visual Basic**;
- process main file: `Main.xaml`;
- `UiPath.System.Activities`: `26.6.1`;
- background process: no UI interaction required;
- excluded logged data includes private/password patterns.

Open `UiPath\DocChronoUiPathExamples\Framework\RunDocChronoBridge.xaml` and run **Analyze File**, then analyze the whole nested project under the organization's Workflow Analyzer policy.

Public GitHub-hosted pull-request jobs intentionally run only secret-free static XAML/project-contract checks. The `uip rpa` tool bridges to Studio, and a fresh headless runner requires UiPath authentication/entitlement for Analyzer, compiler, runtime, and package operations. Run the repository's full UiPath scripts on a signed-in Studio/Robot machine or configure an approved external application in governed CI; never expose those credentials to public pull requests. See UiPath's [CLI authentication guide](https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/authentication).

## 6. Configure arguments

For a local repository run:

| Argument | Value |
|---|---|
| `in_PythonExe` | Absolute path returned for root `.venv\Scripts\python.exe` |
| `in_WorkingDirectory` | Absolute repository root containing root `Examples` and `artifacts` |

Resolve both values from the repository root before opening/running Studio:

```powershell
(Resolve-Path .\.venv\Scripts\python.exe).Path
(Resolve-Path .).Path
```

Paste those values into the Main arguments. Do not use the nested `UiPath\DocChronoUiPathExamples` directory as `in_WorkingDirectory`; requests and data intentionally remain under the repository root `Examples`. For unattended jobs, always use absolute paths supplied through governed configuration.

## 7. Run

To run everything, open the nested `Main.xaml`, set the absolute arguments above, and select **Run File** (`F6`). To run one example, open the individual XAML and select **Run File**. Examples 2-5 require root `artifacts\case.docchrono.json`, so run example 1 first.

For the repository's automated UiPath CLI run, use:

```powershell
.\scripts\run_uipath_project.ps1 -PythonExecutable .venv\Scripts\python.exe
```

The framework validates response schema/correlation and a 64 MiB maximum. It preserves but throws on validated partial exit `2`; only complete exit `0` reaches normal example completion. Captured stdout/stderr are discarded by the five examples.

The result files are:

```text
artifacts/responses/01_build_case.response.json
artifacts/responses/02_export_timeline.response.json
artifacts/responses/03_export_evidence.response.json
artifacts/responses/04_find_path.response.json
artifacts/responses/05_export_review_queue.response.json
```

Generated artifacts are sensitive in real cases and should not be committed.

## 8. Reuse from an existing UiPath project

Choose one of two supported shapes.

### Import the reusable workflow

1. Copy `UiPath\DocChronoUiPathExamples\Framework\RunDocChronoBridge.xaml` into your Windows/VB project.
2. Add `UiPath.System.Activities` through the approved feed.
3. Add **Invoke Workflow File** and select the copied framework XAML.
4. Pass absolute Python, working, request, and response paths plus a bounded timeout.
5. Capture exit code and response path.
6. Parse and validate the JSON envelope before business processing.

### Invoke this project as a child workflow

Copy an example and its request into your solution, or publish a governed library/process wrapper. Keep request creation in your application layer; do not edit shared request files in place when jobs can overlap.

UiPath's [Invoke Workflow File documentation](https://docs.uipath.com/activities/other/latest/workflow/invoke-workflow-file) explains argument passing and isolation behavior.

## 9. Build request JSON safely

Prefer a typed object and a JSON serializer over string concatenation. Write to a job-specific request path in UTF-8. Keep it under 1 MiB. The request contains paths, not source document contents.

Use a unique `request_id` that is safe to expose in logs, such as a UUID or an existing non-sensitive job/case correlation ID. Do not place a person's name, document quote, access token, or secret in it.

## 10. Parse response JSON

In the consuming workflow:

1. Capture the child process exit code.
2. Require a non-empty response file no larger than the approved limit (64 MiB in this runner).
3. Use **Read Text File** with UTF-8.
4. Deserialize with an approved JSON library/activity.
5. Require `schema_version = "1.0"`.
6. Match `request_id` to the outgoing request.
7. Handle `errors` before `result`.
8. Route exit `2`/`status: partial` to an explicit review policy. The supplied sample validates it and then throws to fail closed.
9. Keep warnings and provenance with downstream records.

## 11. Publish only after local validation

Use Studio's **Publish** wizard, or the official command-line publisher. For a per-user Studio installation:

```powershell
$publisher = "$env:LOCALAPPDATA\Programs\UiPath\Studio\UiPath.Studio.CommandLine.exe"
& $publisher publish `
  --project-path (Resolve-Path .\UiPath\DocChronoUiPathExamples\project.json).Path `
  --target OrchestratorTenant `
  --notes "Validated DocChrono UiPath bridge release"
```

For a per-machine installation, the executable is normally under `C:\Program Files\UiPath\Studio`. Publishing requires an already configured Studio/Orchestrator connection and suitable permissions.

Publish only `UiPath\DocChronoUiPathExamples`. The root Python bridge, `.venv`, fixtures/requests, expected snapshots, tests, and generated cases are not part of that UiPath project. Provision the Python bridge and authorized runtime assets separately on the robot, then configure their absolute paths.

Do not use `UiRobot.exe execute --file project.json` as a development shortcut for this Windows project. UiPath's current Robot CLI documentation says direct JSON/XAML file execution is not supported for Windows or cross-platform projects. Publish/install the package, then run the registered process, or run from Studio.

## Official UiPath references

- [Studio project types and compatibility](https://docs.uipath.com/studio/standalone/latest/user-guide/about-automation-projects)
- [Studio project open flow](https://docs.uipath.com/studio/standalone/latest/user-guide/the-user-interface)
- [Invoke Code](https://docs.uipath.com/activities/other/latest/workflow/invoke-code)
- [Invoke Workflow File](https://docs.uipath.com/activities/other/latest/workflow/invoke-workflow-file)
- [Publishing automation projects](https://docs.uipath.com/studio/standalone/latest/user-guide/about-publishing-automation-projects)
- [Robot command-line interface](https://docs.uipath.com/robot/standalone/latest/admin-guide/command-line-interface)
