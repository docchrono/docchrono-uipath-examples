# Production and Orchestrator deployment

## Production principle

Treat Python, the UiPath package, runtime request/data assets, source corpus, and generated case files as separate governed assets. The repository enforces this physically: only `UiPath/DocChronoUiPathExamples/` is the UiPath project. A working developer `.venv` is not a deployment artifact.

## Reference topology

```text
Orchestrator process + trigger
  -> Windows unattended robot image
     |-- immutable UiPath package
     |-- C:\Program Files\DocChronoBridge\venv\Scripts\python.exe
     |-- D:\DocChronoJobs\<job-id>\
         |-- input\      (staged source documents)
         |-- requests\   (versioned request)
         |-- output\     (case + responses)
         `-- temp\       (job-scoped temporary files)
  -> governed evidence storage / review queue
```

Paths are illustrative. Use your organization's approved software and data locations.

## 1. Build an immutable Python artifact

On a controlled build agent with a supported CPython version:

```powershell
py -3.13 -m venv .build-venv
.\.build-venv\Scripts\python.exe -m pip install --upgrade pip build
.\.build-venv\Scripts\python.exe -m build
```

Record hashes for the bridge wheel and all dependency wheels. Mirror them into an internal repository and scan them under your software-supply-chain policy. The runtime pins include `docchrono==0.1.0`; do not let the robot resolve unbounded versions from the public internet.

Provision each robot image from the same wheel set, for example:

```powershell
py -3.13 -m venv C:\ProgramData\DocChronoBridge\venv
C:\ProgramData\DocChronoBridge\venv\Scripts\python.exe -m pip install `
  --no-index `
  --find-links C:\ApprovedWheels `
  docchrono_uipath_bridge_examples-0.1.0-py3-none-any.whl
```

Use the actual wheel filename produced by the build. A robot service identity must have read/execute access but not permission to replace the interpreter or installed packages.

## 2. Validate the robot image

Run a synthetic smoke test as the same identity and session type used by the Robot:

```powershell
$pythonExe = 'C:\ProgramData\DocChronoBridge\venv\Scripts\python.exe'
& $pythonExe -c "import sys, docchrono, docchrono_uipath_bridge; print(sys.version); print(docchrono.__version__)"
```

Then run the five synthetic requests in an isolated staging copy. Confirm counts, evidence polarity, path direction, and review candidate. Native dependencies can behave differently across desktop and server images, so a simple import is necessary but not sufficient.

## 3. Package the UiPath process

The UiPath publish root is `UiPath\DocChronoUiPathExamples`, not the repository root. Root `src`, `.venv`, `Examples`, tests, docs, scripts, and `artifacts` are intentionally outside the process project and must not be swept into its package. Deploy the built Python bridge and authorized runtime request/data assets separately.

Before publishing:

- restore `UiPath.System.Activities 26.6.1` from an approved feed;
- run Workflow Analyzer under the production governance policy;
- run all Python tests and the UiPath synthetic workflow;
- confirm no `.venv`, real evidence, generated `artifacts`, credentials, or local absolute paths are included;
- increment the project/package version and add release notes;
- sign the package when required by organizational policy.

Publish using Studio or the documented command:

```powershell
$publisher = "$env:LOCALAPPDATA\Programs\UiPath\Studio\UiPath.Studio.CommandLine.exe"
& $publisher publish `
  --project-path (Resolve-Path .\UiPath\DocChronoUiPathExamples\project.json).Path `
  --target OrchestratorTenant `
  --new-version 1.0.0 `
  --notes "DocChrono bridge 1.0 / DocChrono 0.1.0"
```

See UiPath's [publishing guide](https://docs.uipath.com/studio/standalone/latest/user-guide/about-publishing-automation-projects).

## 4. Create the Orchestrator process

1. Add the published package to the appropriate Orchestrator folder.
2. Create a process using `Main.xaml` as its entry point.
3. Keep **user interaction not required**; the bridge is background-capable.
4. Configure `in_PythonExe` as an absolute provisioned interpreter path.
5. Configure `in_WorkingDirectory` as a per-job external workspace containing its `Examples\requests`, `Examples\data`, and writable `artifacts`; it is not the installed UiPath package directory. Do not use one shared writable folder for concurrent jobs.
6. Apply folder, machine, runtime, and identity assignments according to least privilege.

Only arguments on the main entry point are exposed by Orchestrator. UiPath documents this and the 1 MiB input/output argument storage limit in [About Input and Output Arguments](https://docs.uipath.com/orchestrator/automation-cloud/latest/user-guide/about-input-and-output-arguments). This design passes paths through arguments and keeps evidence in controlled files.

## 5. Stage a job workspace

The demonstration uses fixed repository request files. A production dispatcher should create a unique job workspace and write a new request per case:

```text
D:\DocChronoJobs\<job-id>\input
D:\DocChronoJobs\<job-id>\requests\build.json
D:\DocChronoJobs\<job-id>\output\case.docchrono.json
D:\DocChronoJobs\<job-id>\output\build.response.json
```

Use a UUID or Orchestrator job key for directory isolation. Reject path traversal at the business boundary and resolve allowed roots before launching the bridge. Never build paths directly from an untrusted filename without canonicalization.

The example bridge resolves parameter paths relative to the request file. A generated request can therefore use `../input` and `../output/case.docchrono.json`, keeping the workspace relocatable.

## 6. Trigger and run

UiPath supports input values at process, job, and trigger levels. Use the narrowest stable scope:

- machine-wide Python path: process-level or asset-derived configuration;
- job-specific working directory/case correlation: job input;
- schedule: trigger-level only when it is truly constant for that trigger.

Unattended jobs are launched from Orchestrator jobs, processes, or triggers. See [About Jobs](https://docs.uipath.com/orchestrator/automation-cloud/latest/user-guide/about-jobs) and [About Processes](https://docs.uipath.com/orchestrator/automation-cloud/latest/user-guide/about-processes).

## 7. Handle completion idempotently

Treat the combination of business case ID, bridge request ID, command, and bridge schema version as an idempotency key. Before adding queue items or copying evidence outputs, check whether that key has already completed.

| Condition | Action |
|---|---|
| Exit `0`, `status=complete`, no errors | Continue with reviewed business routing. |
| Exit `2`, `status=partial` | The sample validates and preserves the response, then throws to fail closed; catch at a surrounding boundary only to create an explicit exception/review route. |
| Exit `1`, structured error | Route using stable error code; retry only transient storage conditions. |
| Exit `70` or missing response | Quarantine workspace and escalate. The runner deletes stale output before launch, so a missing new response is expected on some failures. |
| UiPath timeout | Kill is attempted, but inspect/quarantine output before retry; the child may have reached a write boundary. |

The review export itself is read-only. If a downstream workflow creates Queue items or Action Center tasks, that workflow owns deduplication, assignment, deadlines, and reviewer authorization.

## 8. Observability

Safe operational fields include:

- Orchestrator job ID and a non-sensitive request ID;
- bridge schema and pinned software versions;
- command name, exit code, status, duration, timeout flag;
- counts and count drift thresholds;
- generic failure codes/stages;
- response checksum and governed storage reference.

Do not log:

- source text or evidence quotations;
- response JSON bodies;
- source directory paths or sensitive filenames;
- entity/person names;
- stdout/stderr by default;
- tokens, credentials, or Orchestrator secrets.

The XAML captures stdout/stderr to prevent pipe deadlock; the five examples discard both streams. Preserve more detailed diagnostics only in a restricted incident channel with an explicit retention period.

## 9. Storage and retention

The normal full DocChrono save retains raw document text, evidence quotes, and local source paths. This bridge's save removes raw text and local paths, but quotes and source filenames remain. Store case and response artifacts at the same or higher classification as the source corpus.

Recommended lifecycle:

1. Stage immutable originals from an authoritative source.
2. Build in an encrypted job workspace.
3. Hash originals and outputs if chain-of-custody is required.
4. Transfer approved artifacts to governed evidence storage.
5. Record disposition outcome.
6. Delete local workspace through an approved, auditable cleanup process only after transfer validation and retention checks.

This repository does not implement cleanup because deletion policy is organization- and case-specific.

## 10. Capacity and concurrency

Benchmark on representative document sizes and formats. Track peak memory, build time, document failure rate, event/entity count drift, and output size. Set timeouts from measured percentiles plus a bounded margin, not the 60/120-second demonstration defaults.

Never let concurrent jobs write the same case or response path. Python response replacement is atomic per destination where supported, but the UiPath runner deletes stale output before launch, and atomic replacement does not make competing writers semantically safe. The runner also rejects response envelopes larger than 64 MiB; capacity-test well below that ceiling.

## 11. Upgrade and rollback

Upgrade DocChrono, the bridge, Python, and UiPath activities independently in a compatibility matrix. For every candidate upgrade:

1. Build a new immutable image/artifact.
2. Run the fixed synthetic corpus and representative approved regression corpora.
3. Review count and evidence changes; do not assume drift is a defect or improvement.
4. Validate XAML in the target Studio/Robot version.
5. Canary on isolated non-production jobs.
6. Keep the previous UiPath package and Python environment addressable for rollback.

Bridge schema `1.0` and DocChrono saved-case schemas are separate compatibility concerns. Do not load a case across versions unless DocChrono documents that path and tests prove it.
