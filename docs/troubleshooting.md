# Troubleshooting

Start with the process exit code and the response envelope. Do not begin by enabling verbose logging of source text.

## Diagnostic checklist

From the repository or deployed working directory:

```powershell
$pythonExe = (Resolve-Path .\.venv\Scripts\python.exe).Path

& $pythonExe -c `
  "import sys, docchrono, docchrono_uipath_bridge; print(sys.executable); print(sys.version); print(docchrono.__version__)"

Test-Path .\Examples\requests\01_build_case.json
Test-Path .\Examples\data

& $pythonExe -m docchrono_uipath_bridge `
  --request .\Examples\requests\01_build_case.json `
  --response .\artifacts\responses\diagnostic.response.json

$LASTEXITCODE
Get-Content .\artifacts\responses\diagnostic.response.json -Raw
```

Run only with synthetic data when output is being shared for support.

## Studio cannot open or restore the project

### Symptoms

- dependency restore fails;
- `Invoke Code` or `Invoke Workflow File` appears unresolved;
- project opens in an unexpected compatibility.

### Checks

1. Confirm Studio supports Windows projects.
2. Confirm `UiPath/DocChronoUiPathExamples/project.json` says `targetFramework: Windows` and `expressionLanguage: VisualBasic`.
3. Confirm the approved feed exposes `UiPath.System.Activities 26.6.1`.
4. Check governance policies and proxy/feed access.
5. Clear/repair package caches only through approved UiPath procedures; do not edit XAML to remove unresolved activities.

If your organization mandates another activity version, make a deliberate branch change and validate XAML and runtime behavior before publishing.

## Python executable not found

### Symptoms

- `The system cannot find the file specified`;
- child process exits before a response;
- local default works in Studio but not Orchestrator.

### Fix

Use the exact absolute executable provisioned on the Robot:

```powershell
Test-Path C:\ProgramData\DocChronoBridge\venv\Scripts\python.exe
& C:\ProgramData\DocChronoBridge\venv\Scripts\python.exe -V
```

Do not assume the Robot service has the developer's `PATH`, profile, mapped drives, or `.venv`.

## Import error

### Symptoms

- `No module named docchrono_uipath_bridge`;
- `No module named docchrono`;
- native dependency import failure.

### Fix

Run installation with the same executable configured in UiPath:

```powershell
& $pythonExe -m pip show docchrono
& $pythonExe -c "import docchrono, docchrono_uipath_bridge; print(docchrono.__version__)"
```

Expected DocChrono version is `0.1.0`. Rebuild the environment from approved exact wheels if the interpreter or pins differ.

## `REQUEST_NOT_FOUND`

The CLI `--request` path is interpreted from Python's working directory. The framework sets that directory from `in_WorkingDirectory`.

Use absolute paths in production. In Studio, open the nested `UiPath\DocChronoUiPathExamples\project.json`, but set `in_WorkingDirectory` to the external repository/job workspace root containing the case-sensitive folder `Examples`.

## `SOURCE_DIRECTORY_NOT_FOUND`

Paths inside request parameters are resolved from the request file's directory. For:

```text
Examples/requests/01_build_case.json
source_directory = ../data
```

the resolved source is `Examples/data`, not `<working-directory>/data`.

## `CASE_FILE_NOT_FOUND`

Examples 2-5 expect `artifacts/case.docchrono.json`, created by example 1. Confirm:

- example 1 exit was `0` or `2`;
- its response names the expected case file;
- all examples use the same request tree/workspace;
- no cleanup moved the case between steps.

Do not treat an old case file as proof the current build succeeded. Correlate request ID, job workspace, timestamps, and preferably hashes.

## Exit `2` / `status: partial`

This is not a Python process crash. DocChrono produced a usable case but recorded one or more document failures. The response contains warnings; `build_case` also includes generic failure records. The supplied UiPath runner validates that partial envelope and then intentionally throws `InvalidDataException` to fail closed.

Production handling should preserve the case, prevent silent complete processing, and route according to document criticality. A retry is appropriate only if a transient storage/parser condition is understood.

## Response exceeds 64 MiB

The bridge CLI can write a large response, but the supplied UiPath runner refuses to load an envelope larger than 67,108,864 bytes. Reduce the business query/corpus scope or design a governed paged/artifact-reference contract; do not raise the limit without memory and security testing.

## A previous response disappeared

This is deliberate. Before starting Python, the runner deletes the configured response path so stale success cannot be mistaken for the current request. Python atomically replaces a temporary sibling on successful write, but a launch failure, timeout, or response-write failure can leave no response. Use a unique response path per attempt and preserve completed artifacts in governed storage before retrying.

## Exit `1`

Read `errors[0].code` from the response. Typical causes are invalid schema, wrong paths, an unknown command, missing case, or ambiguous graph reference. Do not branch on the message text.

If no response exists, verify that both CLI flags were supplied; argument parsing can return `CLI_ARGUMENT_ERROR` before normal response handling.

## Exit `70`

The bridge encountered an unexpected error or could not write the response. Check:

- response parent directory ACL and available disk space;
- antivirus/endpoint protection events;
- filesystem support for temporary creation and replacement;
- secure operational logs that do not expose evidence.

Quarantine the workspace. Do not retry repeatedly without bounding or diagnosing the failure.

## `REFERENCE_NOT_FOUND`

`find_path` uses exact case-sensitive name/alias/title matching or an internal node ID. `Maya Chen` works; `maya chen` does not. Export/inspect known case nodes in a controlled diagnostic before correcting the request.

## `AMBIGUOUS_REFERENCE`

More than one node has the exact supplied name. Use a unique internal node ID. Do not choose the first match automatically.

## `found: false` with exit `0`

The query succeeded but no traversable path was found. This is a business result, not an error. It does not prove the people/items are unrelated; it means the current extracted graph has no path.

## Timeline has zero undated events

That is expected for the fixed corpus: `dated_count=5`, `undated_count=0`. `includes_undated=true` means the export includes the undated bucket and would not discard undated events from another case. It does not mean one must exist.

## Evidence seems contradictory

The sample intentionally has one affirmed and one negated `WORKS_FOR` claim. The bridge preserves these as `supporting_evidence` and `opposing_evidence`; it does not automatically label or resolve a contradiction. Review both original documents and context.

## Graph arrows appear wrong

Path traversal and stored relationship direction are different concepts. Render `traversal` for route order, and render arrow semantics from `stored_direction`. On the final sample hop, `matches_traversal=false` because the path walks from the payment event to `Payment #982` against the stored participant-to-event direction.

## Review candidate disappeared or changed

Confirm exact fixture content and pinned versions. NLP/scoring upgrades can change candidates. This repository expects exactly one `entity_merge_candidate` for Jordan/Jordon under DocChrono 0.1.0. Never turn a count change into an automatic merge.

## Timeout

The build example uses 120 seconds; query examples use 60 seconds. These are demonstration values. On timeout, the workflow attempts to kill the process tree and throws. A case or temporary/response file may already exist.

1. Quarantine the workspace.
2. Check whether the child truly exited.
3. Inspect safe metadata and protected endpoint events.
4. Measure representative corpus performance.
5. Set a bounded production timeout and retry limit.

Do not simply multiply the timeout until jobs stop failing.

## Works attended, fails unattended

Compare the Robot service identity and session:

- absolute Python path and ACLs;
- source/output paths and permissions;
- mapped network drives (usually absent in service sessions);
- proxy/feed access during package restore (runtime should not install packages);
- antivirus policy;
- current/working directory;
- free disk and profile/temp location.

Use UNC paths only when explicitly supported and authorized, and prefer staging source files to a local isolated job workspace.

## Sensitive data appeared in logs

Stop sharing the log, restrict access, and follow incident/retention policy. The sample XAML does not log response bodies or stderr. Check downstream deserialization, exception handling, queue item payloads, and custom logging. Evidence quotes and filenames are sensitive even in the sanitized case.

## XAML validation

XML well-formedness does not prove UiPath compatibility. Open and analyze every XAML in the target Studio version, restore the exact activity package, and run the synthetic end-to-end workflow on the target Robot image before release.

## When filing an issue

Include only:

- operating system, UiPath/Robot version, Python minor version;
- DocChrono and bridge versions;
- command name, exit code, stable error code;
- synthetic reproduction steps;
- redacted stack trace only if it contains no paths, names, quotes, or secrets.

Never attach real source documents, case/response JSON, credentials, personal data, internal paths, or unrestricted Robot logs.
