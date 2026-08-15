# DocChrono for UiPath: five complete examples

Use [DocChrono 0.1.0](https://pypi.org/project/docchrono/0.1.0/) from a UiPath Windows process to turn local documents into a source-linked case, chronology, evidence export, graph path, and human-review queue. The repository is executable: it contains a VB XAML project, a versioned JSON bridge, six synthetic documents, five requests, automated tests, and deterministic expected results.

No OpenAI, Anthropic, or other cloud AI key is required. Documents remain on the robot unless your surrounding automation moves or logs them.

> This is an integration example, not a legal, compliance, investigative, or factual decision system. Treat every extracted item as a candidate finding and retain a qualified human reviewer for consequential use.

## What you get

| # | UiPath workflow | Bridge command | Business outcome |
|---:|---|---|---|
| 1 | [`01_BuildCase.xaml`](UiPath/DocChronoUiPathExamples/Examples/01_BuildCase.xaml) | `build_case` | Build a privacy-reduced, source-linked DocChrono case from six documents. |
| 2 | [`02_ExportTimeline.xaml`](UiPath/DocChronoUiPathExamples/Examples/02_ExportTimeline.xaml) | `export_timeline` | Export every event in chronology order and explicitly separate dated from undated items. |
| 3 | [`03_TraceEvidence.xaml`](UiPath/DocChronoUiPathExamples/Examples/03_TraceEvidence.xaml) | `export_evidence` | Show supporting and opposing evidence for the same `WORKS_FOR` relationship. |
| 4 | [`04_FindGraphPath.xaml`](UiPath/DocChronoUiPathExamples/Examples/04_FindGraphPath.xaml) | `find_path` | Find an evidence-bearing path from Maya Chen to Payment #982 while preserving edge direction. |
| 5 | [`05_ExportReviewQueue.xaml`](UiPath/DocChronoUiPathExamples/Examples/05_ExportReviewQueue.xaml) | `export_review_queue` | Export one possible entity merge for human review without changing the case. |

[`Main.xaml`](UiPath/DocChronoUiPathExamples/Main.xaml) invokes all five in order. Every individual example calls the reusable [`RunDocChronoBridge.xaml`](UiPath/DocChronoUiPathExamples/Framework/RunDocChronoBridge.xaml) workflow.

## Architecture

```text
UiPath/DocChronoUiPathExamples (publishable Windows/VB project)
  -> Main.xaml
    -> Examples/*.xaml
      -> Framework/RunDocChronoBridge.xaml
        -> Invoke Code (VB.NET ProcessStartInfo)
          -> isolated CPython process
            -> python -m docchrono_uipath_bridge
              -> read root Examples/requests JSON + Examples/data
              -> DocChrono 0.1.0 public API
              -> atomically write response JSON
        <- exit code + response artifact
  <- branch, log metadata, and hand results to the next activity
```

The bridge uses an external process instead of UiPath Python activities. That keeps CPython and its native dependencies isolated from the Robot process, supports explicit timeouts and exit codes, avoids shell quoting, and gives unattended jobs a durable JSON artifact. `ProcessStartInfo.ArgumentList` passes each argument separately; the workflow never constructs a command string. The nested UiPath project is the only directory packaged as the UiPath process. The root Python bridge, fixtures, virtual environment, and generated cases are deployed and governed separately.

Python writes a temporary sibling and atomically replaces its response destination. Before launch, the UiPath runner deliberately deletes any stale response so an old success can never satisfy a new run. Therefore the end-to-end runner does not preserve the previous response atomically: a timeout or failure can correctly leave no response file.

Read [architecture](docs/architecture.md) for component boundaries and failure flow, and [bridge contract](docs/bridge-contract.md) for the complete JSON schema.

## Compatibility

| Component | Tested/pinned contract |
|---|---|
| UiPath project | Windows compatibility, Visual Basic expressions, background-capable XAML process |
| UiPath activity | `UiPath.System.Activities` `26.6.1` |
| UiPath CLI in CI | `@uipath/cli` `1.197.1`; repository config disables automatic version sync and pins the `1.197` tool line |
| Python | 64-bit CPython `3.11`, `3.12`, or `3.13` |
| DocChrono | exactly `0.1.0` |
| Operating system | Windows robot or Studio machine with permission to start the configured Python executable |
| AI service | none; no cloud AI API key is used |

Python 3.14 is outside DocChrono 0.1.0's declared range. The sample is a **Windows** project, not Windows-Legacy or cross-platform. UiPath documents Windows as the default .NET project compatibility; see [About Automation Projects](https://docs.uipath.com/studio/standalone/latest/user-guide/about-automation-projects).

The project pins an activity version to make the example reproducible. If organizational governance requires another supported package or Studio release, change it only in a branch and revalidate all XAML and tests.

## 90-second quick start

Prerequisites: Git, UiPath Studio on Windows, and a supported 64-bit Python registered with the Python launcher. The commands below are PowerShell commands run from a normal user session.

```powershell
git clone https://github.com/docchrono/docchrono-uipath-examples.git
Set-Location .\docchrono-uipath-examples

py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install .

# Prove the Python side works and create the case used by examples 2-5.
.\.venv\Scripts\python.exe -m docchrono_uipath_bridge `
  --request .\Examples\requests\01_build_case.json `
  --response .\artifacts\responses\01_build_case.response.json

Get-Content .\artifacts\responses\01_build_case.response.json

# Record these absolute values for Main.xaml input arguments.
(Resolve-Path .\.venv\Scripts\python.exe).Path
(Resolve-Path .).Path

# Open only the nested publishable UiPath project.
Invoke-Item .\UiPath\DocChronoUiPathExamples\project.json
```

In Studio:

1. Allow dependency restore and confirm `UiPath.System.Activities 26.6.1` resolves.
2. Open `Main.xaml` in the nested project.
3. Set `in_PythonExe` to the absolute root `.venv\Scripts\python.exe` path and `in_WorkingDirectory` to the absolute repository root. The root contains `Examples`, the installed bridge environment, and writable `artifacts`.
4. Select **Run File** or press `F6` while `Main.xaml` is active.
5. Inspect `artifacts\responses\*.response.json`.

If `Invoke-Item` is not associated with Studio, open Studio, select **Home > Open > Browse Local**, and choose `UiPath\DocChronoUiPathExamples\project.json`. UiPath's [Studio user interface guide](https://docs.uipath.com/studio/standalone/latest/user-guide/the-user-interface) documents that flow.

You can also run all five bridge requests without Studio:

```powershell
$pythonExe = (Resolve-Path .\.venv\Scripts\python.exe).Path
$requests = @(
  '01_build_case',
  '02_export_timeline',
  '03_export_evidence',
  '04_find_path',
  '05_export_review_queue'
)

foreach ($name in $requests) {
  & $pythonExe -m docchrono_uipath_bridge `
    --request ".\Examples\requests\$name.json" `
    --response ".\artifacts\responses\$name.response.json"
  if ($LASTEXITCODE -notin 0, 2) { throw "Bridge request $name failed." }
}
```

At the bridge CLI boundary, exit `2` is a written, usable partial result. The sample UiPath runner validates its envelope and correlation first, then deliberately throws to fail closed. Preserve the response and route it through an explicit review/retry workflow.

## Project layout

```text
.
|-- UiPath/DocChronoUiPathExamples/   # only this subtree is the UiPath project
|   |-- Main.xaml
|   |-- project.json
|   |-- project.uiproj
|   |-- Framework/
|   |   `-- RunDocChronoBridge.xaml
|   `-- Examples/                     # five UiPath example XAML files
|-- Examples/
|   |-- data/                         # six root-level synthetic inputs
|   |-- expected/                     # five verified response snapshots
|   `-- requests/                     # five contract-v1 requests
|-- src/docchrono_uipath_bridge/      # validated JSON bridge
|-- .uipath/config.json               # reproducible CLI/tool version policy
|-- scripts/generate_synthetic_data.py
|-- tests/                            # contract and integration tests
|-- docs/                             # production and example guides
`-- artifacts/                        # generated locally; not source evidence
```

## UiPath arguments

`Main.xaml` exposes these input arguments:

| Argument | Type | Default | Meaning |
|---|---|---|---|
| `in_PythonExe` | `String` | `.venv\Scripts\python.exe` | Exact CPython executable with this bridge and DocChrono installed. Prefer an absolute, machine-managed path in unattended jobs. |
| `in_WorkingDirectory` | `String` | `..\..` | External workspace root containing `Examples` requests/data and writable `artifacts`. The relative default is only a local-checkout convenience; prefer an absolute per-job workspace in Studio and unattended jobs. |

Each example accepts the same two inputs and returns `out_ResponsePath` on complete success. The framework captures stdout/stderr, exit code, and timeout status. The five examples intentionally discard captured stdout and stderr and never log response bodies because any of them can carry sensitive operational context.

The sample `Main.xaml` has no output argument. In a consuming project, invoke an individual example or the framework and pass `out_ResponsePath` into **Read Text File**, JSON deserialization, a queue writer, or a business-rule workflow.

## Synthetic corpus and verified result

All people, organizations, invoices, payments, addresses, and events are invented. Email addresses use the reserved `.test` domain.

| File | Synthetic fact exercised |
|---|---|
| `01_invoice_approval.txt` | Maya Chen approved Invoice #381 on March 3, 2026; it also affirms Maya works for Northstar Logistics Corporation. |
| `02_employment_exception.md` | Negates that same `WORKS_FOR` claim. |
| `03_authorization_hold.txt` | Maya did not authorize Payment #982 on March 4, 2026. This is retained as a negated claim, not turned into an affirmative event. |
| `04_payment_notice.eml` | Northstar paid Payment #982 on March 7, 2026; email headers also yield a communication event. |
| `05_review_candidate_a.md` | Jordan Carmichael approved Invoice #700 on March 5, 2026. |
| `06_review_candidate_b.md` | Jordon Carmichael approved Invoice #701 on March 6, 2026. |

With the pinned versions and unchanged fixtures, example 1 reports:

```json
{
  "claims": 10,
  "documents": 6,
  "entities": 12,
  "events": 5,
  "relationships": 16,
  "review_items": 1
}
```

The chronology contains `dated_count: 5`, `undated_count: 0`, and `total_count: 5`. The bridge deliberately iterates `timeline.all` and returns `includes_undated: true`; a production corpus can therefore contain undated items without silently dropping them. Zero is the verified count for this fixed corpus, not a promise that all inputs will resolve to dates.

Parser and NLP improvements can legitimately change extracted counts in future DocChrono versions. That is why this repository pins `docchrono==0.1.0` and asserts the result in tests.

## Five detailed examples

### 1. Build a source-linked case

[`01_BuildCase.xaml`](UiPath/DocChronoUiPathExamples/Examples/01_BuildCase.xaml) sends [`01_build_case.json`](Examples/requests/01_build_case.json). `source_directory` and `case_file` are resolved relative to the request file, not the UiPath working directory.

```json
{
  "schema_version": "1.0",
  "request_id": "example-01-build-case",
  "command": "build_case",
  "parameters": {
    "source_directory": "../data",
    "case_file": "../../artifacts/case.docchrono.json",
    "strict": true
  }
}
```

The successful response has `status: "complete"`, exit code `0`, the verified counts above, `failures: []`, and a privacy block. `strict: true` makes an unprocessable document fail the build instead of quietly becoming a partial corpus.

The bridge pre-redacts local source paths/metadata and parser diagnostics, then uses DocChrono's sanitized save. Standard `Case.save_sanitized()` by itself still retains evidence quotations and source paths/metadata; it removes raw document text and therefore loses full round-trip verification from the case alone. This bridge additionally replaces paths with filenames, but quotes remain. Read the [example 1 guide](docs/examples/01-build-case.md).

### 2. Export the complete chronology

[`02_ExportTimeline.xaml`](UiPath/DocChronoUiPathExamples/Examples/02_ExportTimeline.xaml) loads the case created by example 1 and exports `case.timeline.all`. Each event includes chronology position, normalized date or `null`, `date_status`, participants, confidence score, provisional flag, temporal details, evidence quotes, locations, and source filenames.

Expected order:

1. March 3 — Invoice #381 approval.
2. March 5 — Invoice #700 approval.
3. March 6 — Invoice #701 approval.
4. March 7 — Payment #982 payment.
5. March 7 at 10:15 -06:00 — email sent.

Undated events, when present, follow the dated sequence and carry `date: null` plus `date_status: "undated"`. The fixed corpus has none, so `undated_count` is `0`. Read the [example 2 guide](docs/examples/02-export-timeline.md).

### 3. Trace supporting and opposing evidence

[`03_TraceEvidence.xaml`](UiPath/DocChronoUiPathExamples/Examples/03_TraceEvidence.xaml) filters relationships to `WORKS_FOR`. It returns one relationship:

```text
Maya Chen --WORKS_FOR--> Northstar Logistics Corporation
  supporting: 01_invoice_approval.txt
  opposing:   02_employment_exception.md
```

Supporting and opposing claims are separate arrays with polarity, modality, participants, score, quote, source filename, and location. The bridge does not call this an automatically detected contradiction and does not decide which statement is true. Read the [example 3 guide](docs/examples/03-trace-evidence.md).

### 4. Find a graph path without losing direction

[`04_FindGraphPath.xaml`](UiPath/DocChronoUiPathExamples/Examples/04_FindGraphPath.xaml) asks for an exact-name path from `Maya Chen` to `Payment #982`. The verified path has three hops:

```text
Maya Chen
  --WORKS_FOR-->
Northstar Logistics Corporation
  --PARTICIPATED_IN-->
Paid: Payment #982
  <--PARTICIPATED_IN--
Payment #982
```

Path discovery treats edges as traversable in either direction. Each hop therefore has:

- `traversal.from` and `traversal.to`: the route UiPath is following;
- `stored_direction.source` and `stored_direction.target`: the relationship as stored;
- `stored_direction.matches_traversal`: `false` on the final hop;
- supporting and opposing evidence arrays.

Do not render every hop as a forward arrow. Read the [example 4 guide](docs/examples/04-find-graph-path.md).

### 5. Export a read-only human-review queue

[`05_ExportReviewQueue.xaml`](UiPath/DocChronoUiPathExamples/Examples/05_ExportReviewQueue.xaml) returns one `entity_merge_candidate`: `Jordan Carmichael` and `Jordon Carmichael`, score `0.912941`, with both source quotations. The recommendation is always `HUMAN_REVIEW`.

This command is read-only. It does not accept, reject, or merge candidates and it does not modify the case. A UiPath process can transform each item into an Orchestrator Queue item or a governed human task, but that downstream action is deliberately outside this sample. Read the [example 5 guide](docs/examples/05-export-review-queue.md).

## UiPath activity sequence

Every example uses this visible sequence:

1. **Assign** the deterministic response path.
2. **Invoke Workflow File** calls the nested project's `Framework\RunDocChronoBridge.xaml` with Python, external working directory, request, response, and timeout arguments.
3. The framework **Log Message** records only request filename/start metadata.
4. **Invoke Code** creates the response directory, deletes any stale response, creates `ProcessStartInfo`, disables shell execution, redirects stdout/stderr, uses `ArgumentList`, starts Python, drains both streams asynchronously, and enforces the timeout.
5. **If** timed out, kill the process tree and throw `TimeoutException`.
6. **If** the response is missing or empty, throw `InvalidDataException`.
7. **Invoke Code** rejects responses over 64 MiB, parses both envelopes, and verifies exact fields, schema, request ID, command, exit/status pairing, and result/error shape.
8. **If** exit is `1` or `70`, throw after validating the error response; if exit is `2`, throw after validating the partial response so the sample fails closed.
9. **Log Message** records only exit code and response filename for exit `0`; the example returns `out_ResponsePath` only on complete success.

UiPath's official references describe [Invoke Code](https://docs.uipath.com/activities/other/latest/workflow/invoke-code) and [Invoke Workflow File](https://docs.uipath.com/activities/other/latest/workflow/invoke-workflow-file).

## Request, response, and exit-code contract

Every request is UTF-8 JSON, at most 1 MiB, with exactly four top-level keys. Unknown keys are rejected. Before reading a response, the UiPath runner enforces a 64 MiB maximum envelope size.

```json
{
  "schema_version": "1.0",
  "request_id": "caller-generated-correlation-id",
  "command": "build_case",
  "parameters": {}
}
```

Every written response uses one envelope:

```json
{
  "schema_version": "1.0",
  "request_id": "caller-generated-correlation-id",
  "command": "build_case",
  "status": "complete",
  "result": {},
  "warnings": [],
  "errors": []
}
```

| Exit | Response status | UiPath handling |
|---:|---|---|
| `0` | `complete` | Continue after validating the envelope and business result. |
| `2` | `partial` | Validate and preserve the response, then the sample throws to fail closed; a surrounding workflow must route review/retry explicitly. |
| `1` | `error` for a known request/operation problem | Stop normal processing; use the structured error code, not stderr text, for routing. |
| `70` | `error` for unexpected failure, or response-write failure | Stop, protect logs, and escalate as an operational defect. A write failure may leave no response artifact. |

Argument parsing can fail before a response path is usable; in that case stderr contains a short code and exit is `1`. The XAML passes both required CLI arguments, so a deployed workflow should normally receive a response. See [bridge contract](docs/bridge-contract.md) for command parameters and error codes.

## Consuming a response in your UiPath project

After an example returns `out_ResponsePath` on exit `0`:

1. Use **Read Text File** with UTF-8.
2. Deserialize JSON with your organization's approved JSON activity/package, or use a small typed `System.Text.Json` adapter.
3. Verify `schema_version = "1.0"` and the expected `request_id`.
4. Branch on process exit code and response `status`.
5. Check `errors` before accessing `result`.
6. Keep `warnings`, evidence quotes, source filenames, scores, and provisional markers with any downstream record.
7. Use business keys plus `request_id` for idempotent queue writes; retries must not create duplicate review work.

Never branch on human-readable `message`, `reason`, or `warning` text. Those are diagnostic content, not stable enums.

## Orchestrator and unattended deployment

Package only `UiPath\DocChronoUiPathExamples`. Do not publish the root `.venv`, Python source tree, fixtures, or generated cases inside the UiPath package. Provision a pinned, access-controlled bridge environment and authorized external request/data workspace separately, then supply absolute `in_PythonExe` and `in_WorkingDirectory` values. Give each job a separate working/output directory.

Recommended flow:

1. Build and test a golden Windows robot image with 64-bit CPython and the pinned wheel/dependencies.
2. Scan dependencies and lock the artifact in your internal package repository.
3. Publish the UiPath project to Orchestrator and create a background process.
4. Configure absolute Python and workspace arguments at the process, job, or trigger level.
5. Grant the robot identity read access to the input corpus and write access only to its job workspace.
6. Move completed artifacts to governed storage; do not use the local package directory as a permanent evidence store.
7. Monitor exit codes, response status, failures, duration, and count drift without logging quotes or document text.

UiPath documents [publishing automation projects](https://docs.uipath.com/studio/standalone/latest/user-guide/about-publishing-automation-projects), [processes and runtime arguments](https://docs.uipath.com/orchestrator/automation-cloud/latest/user-guide/about-processes), and [input/output arguments](https://docs.uipath.com/orchestrator/automation-cloud/latest/user-guide/about-input-and-output-arguments). See the complete [production deployment guide](docs/production-deployment.md).

## Privacy, provenance, and safe handling

DocChrono's normal full `Case.save()` representation retains document raw text, evidence quotations, and local source paths. Standard `Case.save_sanitized()` removes raw text but still retains evidence quotations and source paths/metadata. This bridge first replaces paths with filenames, removes source metadata, and redacts parser diagnostics, then calls `save_sanitized()`.

Sanitization is **not anonymization**:

- evidence quotations remain and can contain personal, confidential, privileged, or regulated content;
- source filenames remain and can themselves be sensitive;
- entities, events, claims, scores, and relationships remain;
- sanitization removes the full raw document text, so full round-trip verification against the saved case alone is no longer possible;
- reviewers still need controlled access to immutable originals to verify context.

Response JSON repeats evidence quotations and source filenames. Keep responses out of general Robot logs, use encrypted storage and transport, apply retention rules, and restrict access by case. See [security and privacy](docs/security-and-privacy.md) and the repository [security policy](SECURITY.md).

## Chronology and ontology: what is covered

Chronology is a first-class output: events carry normalized temporal expressions, evidence, participants, confidence, and a deterministic ordering with explicit dated and undated partitions.

The evidence graph is a **lightweight application ontology**: typed entities/events and typed edges such as `WORKS_FOR` and `PARTICIPATED_IN`, all connected to claims and evidence. It is useful for traversal and application queries.

It is not an OWL/RDF ontology engine. This repository does not provide RDF triples, URIs as global identities, RDFS/OWL reasoning, SHACL validation, SPARQL, ontology alignment, or a domain taxonomy editor. If those are requirements, map reviewed DocChrono records into a dedicated semantic-web layer; do not label the saved JSON as an OWL knowledge base.

## Testing and CI

Create the environment, then run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
npx --yes pyright@1.1.413
```

The integration tests use the real pinned DocChrono package and verify schema validation, safe failure envelopes, complete/partial exit semantics, fixture counts, chronology buckets, evidence polarity, graph traversal direction, the read-only review candidate, and Python's atomic response replacement. CI runs Python 3.11, 3.12, and 3.13, plus a UiPath XAML analysis/build/run, executable rejection tests for mismatched, malformed, and partial response envelopes, and package-content validation. XAML must also be opened, analyzed, and run in the pinned UiPath Studio/Robot environment before a production release.

## Limitations

- Input support is whatever DocChrono 0.1.0 actually parses. These examples verify plain text, Markdown, and `.eml`; they do not demonstrate OCR, spreadsheets, or Outlook `.msg`.
- Scanned PDFs require an upstream OCR stage; this repository does not supply one.
- Semantic search is not exposed by this bridge.
- Supporting/opposing evidence is surfaced, but automatic contradiction detection is not claimed.
- Entity merge candidates are proposed only; the bridge never merges them.
- Confidence is a ranking/review aid, not probability, truth, authorization, or legal sufficiency.
- Exact-name graph lookup is case-sensitive and rejects ambiguity.
- `find_path` returns one available path, not every path and not a causal proof.
- Processing is local but not automatically private; filesystem, logging, backup, and operator controls still matter.
- The example reads a local directory. A production automation must first stage remote files into an authorized, isolated workspace.

## Troubleshooting

| Symptom | Likely cause | First action |
|---|---|---|
| Studio cannot restore the activity | Feed/governance does not expose `UiPath.System.Activities 26.6.1` | Restore from an approved feed or validate a governed version change. |
| Python exits immediately | Unsupported Python or bridge not installed in that interpreter | Run `& $pythonExe -c "import sys, docchrono, docchrono_uipath_bridge; print(sys.version, docchrono.__version__)"`. |
| `REQUEST_NOT_FOUND` | Request path is wrong for the Robot working directory | Pass absolute framework paths or correct `in_WorkingDirectory`. |
| `SOURCE_DIRECTORY_NOT_FOUND` | Request parameter was interpreted relative to the request file | Resolve from `Examples\requests`, not the process current directory. |
| `CASE_FILE_NOT_FOUND` in examples 2-5 | Example 1 did not finish or used another workspace | Run example 1 first and inspect its result. |
| Exit `2` | One or more documents failed while non-strict processing continued | Preserve output, inspect `warnings` and build `failures`, then apply review policy. |
| `REFERENCE_NOT_FOUND` | Exact graph name is absent | Export/review known entities and use the exact canonical name or ID. |
| `AMBIGUOUS_REFERENCE` | More than one node has the exact supplied name | Use a unique node ID in the request. |
| Timeout | Corpus is larger than the example timeout or process is stalled | Quarantine partial artifacts, measure on representative data, then set a bounded production timeout. |
| Response exists but is sensitive | Expected: evidence quotations are retained | Restrict access; never attach responses to unrestricted logs or tickets. |

See [the full troubleshooting guide](docs/troubleshooting.md).

## FAQ

### Does it require a cloud LLM or API key?

No. The example uses local deterministic/NLP processing through DocChrono 0.1.0.

### Why not use UiPath Python Scope?

The external-process boundary makes interpreter selection, package isolation, timeouts, exit codes, stdout/stderr draining, and JSON artifacts explicit. It also avoids coupling the Robot process to Python runtime loading. Python activities may be suitable in another governed design, but they are not required here.

### Can I run only one example?

Yes. Open an individual XAML and use **Run File**, or invoke its request with the bridge CLI. Examples 2-5 require the case produced by example 1.

### Can I send document contents in the request JSON?

No. The contract accepts paths, and requests are capped at 1 MiB. Stage documents in a protected job directory and pass that directory.

### Does `status: complete` mean the findings are true?

No. It means the requested processing completed without recorded document failures. Findings remain extracted, scored, often provisional, and subject to source verification.

### Does the sanitized case contain no sensitive data?

No. It removes raw document text and local source paths, but keeps evidence quotations, source filenames, and structured findings. It also loses full round-trip verification without the originals.

### Does DocChrono automatically merge Jordan and Jordon?

No. The bridge exports that pair as a review candidate and never mutates the case.

### Is this a full ontology platform?

No. It provides typed graph data, not OWL/RDF/SPARQL reasoning.

### How should a retry work?

Reuse the request's business correlation ID, write to a job-specific temporary response name, and make downstream queue/storage operations idempotent. Never assume that a timed-out process produced no case file; inspect and quarantine artifacts before retrying.

## Documentation

- [Architecture](docs/architecture.md)
- [Bridge request/response contract](docs/bridge-contract.md)
- [UiPath setup](docs/uipath-setup.md)
- [Production and Orchestrator deployment](docs/production-deployment.md)
- [Security and privacy](docs/security-and-privacy.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Example 1: build case](docs/examples/01-build-case.md)
- [Example 2: export timeline](docs/examples/02-export-timeline.md)
- [Example 3: trace evidence](docs/examples/03-trace-evidence.md)
- [Example 4: find graph path](docs/examples/04-find-graph-path.md)
- [Example 5: export review queue](docs/examples/05-export-review-queue.md)

## Upstream and official references

- [DocChrono on PyPI](https://pypi.org/project/docchrono/0.1.0/)
- [DocChrono source](https://github.com/docchrono/docchrono)
- [UiPath: About Automation Projects](https://docs.uipath.com/studio/standalone/latest/user-guide/about-automation-projects)
- [UiPath: Invoke Code](https://docs.uipath.com/activities/other/latest/workflow/invoke-code)
- [UiPath: Invoke Workflow File](https://docs.uipath.com/activities/other/latest/workflow/invoke-workflow-file)
- [UiPath: About Publishing Automation Projects](https://docs.uipath.com/studio/standalone/latest/user-guide/about-publishing-automation-projects)
- [UiPath Orchestrator: About Processes](https://docs.uipath.com/orchestrator/automation-cloud/latest/user-guide/about-processes)
- [UiPath Orchestrator: Input and Output Arguments](https://docs.uipath.com/orchestrator/automation-cloud/latest/user-guide/about-input-and-output-arguments)
- [UiPath Robot: Command Line Interface](https://docs.uipath.com/robot/standalone/latest/admin-guide/command-line-interface)

## Contributing, security, and license

See [CONTRIBUTING.md](CONTRIBUTING.md) before proposing changes. Report vulnerabilities privately using [SECURITY.md](SECURITY.md). The repository is licensed under the Apache License 2.0; see `LICENSE` and [NOTICE](NOTICE).
