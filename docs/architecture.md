# Architecture

## Design objective

This repository demonstrates a narrow, inspectable boundary between a UiPath Windows process and DocChrono. UiPath owns orchestration, timeout policy, process isolation, routing, and downstream actions. Python owns document interpretation and emits a versioned JSON result. Files are the integration contract.

The design is intentionally local and requires no cloud AI service.

## Component map

| Component | Responsibility | Must not do |
|---|---|---|
| `UiPath/DocChronoUiPathExamples/Main.xaml` | Supply external Python/workspace arguments and run the five examples in dependency order. | Parse evidence or make business decisions. |
| `UiPath/DocChronoUiPathExamples/Examples/*.xaml` | Select one root request, one response path, and one timeout; return the response path only on complete success. | Construct ad hoc command strings or log response bodies/streams. |
| `UiPath/DocChronoUiPathExamples/Framework/RunDocChronoBridge.xaml` | Delete stale response, launch Python, drain streams, enforce timeout, validate a correlated response up to 64 MiB, and fail closed on error/partial outcomes. | Interpret domain findings. |
| Root `Examples/` | Hold deployable request/data assets and source-controlled expected snapshots outside the UiPath project. | Be mistaken for XAML package content. |
| `docchrono_uipath_bridge.cli` | Validate CLI paths, read one bounded request, execute it, atomically write one response. | Read from stdin, emit findings to logs, or accept unspecified arguments. |
| `contracts.py` | Enforce schema `1.0`, exact keys, command names, envelope shapes, and exit mapping. | Coerce malformed input. |
| `bridge.py` | Map five commands to DocChrono public APIs and convert opaque IDs into reviewable records. | Auto-merge entities or decide which evidence is true. |
| DocChrono `0.1.0` | Parse documents and produce documents, mentions, entities, claims, events, relationships, review items, chronology, and graph traversal. | Supply UiPath deployment or access controls. |
| JSON artifacts | Preserve a correlation-friendly, language-neutral handoff. | Serve as an unrestricted log format. |

## Execution sequence

```text
UiPath                 Framework XAML          Python bridge          DocChrono
  | request/response paths   |                      |                    |
  |------------------------->|                      |                    |
  |                          | Process.Start        |                    |
  |                          |--------------------->|                    |
  |                          |                      | validate request   |
  |                          |                      |------------------->|
  |                          |                      | build/query        |
  |                          |                      |<-------------------|
  |                          |                      | atomic response    |
  |                          | exit 0/1/2/70        |                    |
  |                          |<---------------------|                    |
  | complete response path   |                      |                    |
  | or validated exception   |                      |                    |
  |<-------------------------|                      |                    |
```

The Python process writes to a temporary sibling file, flushes it, calls `fsync`, and atomically replaces the target where the filesystem supports those semantics. The UiPath runner first deletes any stale response so an old success cannot satisfy a new request. Consequently the whole runner sequence does **not** preserve the prior artifact atomically: a launch failure, timeout, or write failure can leave no response. A successful Python write is still a complete replacement rather than a partially written JSON file.

## Why an external process

The nested project's `Framework/RunDocChronoBridge.xaml` uses UiPath **Invoke Code** only for VB.NET process management and response-envelope validation. It does not embed Python. The child process boundary provides:

- an explicit Python executable per robot;
- ordinary Python dependency management and native-wheel isolation;
- a bounded timeout with process-tree termination;
- deterministic process exit codes;
- captured/drained stdout and stderr that the five example workflows intentionally discard;
- a durable, replayable request/response pair;
- no dependence on a shell or PowerShell execution policy;
- fewer language-marshalling concerns than passing rich Python objects through activities.

`UseShellExecute` is `False`, `CreateNoWindow` is `True`, and arguments use `ArgumentList`. This matters for paths containing spaces and prevents shell metacharacters in a path from becoming commands.

## Data flow and provenance

```text
immutable source documents
  -> source references (filenames in sanitized save)
    -> parsed documents
      -> evidence spans (quote + location)
        -> claims (polarity + modality + participants)
          -> events / relationships
            -> chronology / graph / review exports
```

An exported event or edge is useful only with its evidence. Downstream UiPath automations should keep the quote, source filename, location, score, and provisional/polarity fields attached to the business record. Flattening a result to only `subject-predicate-object` destroys the central trust property of the package.

## Direction and graph traversal

DocChrono stores a directed relationship, such as:

```text
Payment #982 --PARTICIPATED_IN--> Paid: Payment #982
```

Path discovery can traverse that edge in reverse to get from an event to its participant. The bridge therefore exports both:

- `traversal`: route order for presentation;
- `stored_direction`: source/target semantics of the underlying edge.

`stored_direction.matches_traversal` prevents a UiPath visualization from falsely reversing a stored assertion.

## Completion and failure model

There are four meaningful process exits:

| Exit | Meaning | Artifact expectation |
|---:|---|---|
| `0` | Complete operation | Complete response required. |
| `2` | Partial DocChrono case | Partial response required; warnings/failures require policy. |
| `1` | Known request or domain error | Error response normally required; CLI argument errors can precede response creation. |
| `70` | Unexpected exception or response write failure | Error response may exist; do not assume it does. |

The XAML treats process completion and envelope validity as separate channels: exit code protects process control, while the correlated envelope protects business control.

More precisely, the runner recognizes exits `0`, `1`, `2`, and `70`, requires a response no larger than 64 MiB, and validates exact fields, schema, request ID, command, status/exit pairing, and result/error shape. It then throws for `1`/`70` and also throws for validated exit `2`, deliberately failing closed. Only exit `0` reaches the example's success log and returned response path.

## Packaging boundary

Only `UiPath/DocChronoUiPathExamples/` is the UiPath project and publish root. The Python package under `src/`, root `Examples/` fixtures/requests, `.venv`, tests, docs, and generated `artifacts/` are not bundled implicitly with that process. Deploy the bridge environment and authorized runtime assets separately, then pass absolute paths through `in_PythonExe` and `in_WorkingDirectory`. This physical boundary keeps UiPath publish artifacts small and prevents accidental inclusion of development environments or generated cases.

## Trust boundaries

1. **Source boundary:** documents are untrusted inputs. Stage them in a job-specific read-only folder.
2. **Request boundary:** JSON is untrusted even when created by UiPath. Exact-key and type validation rejects drift.
3. **Process boundary:** Python is a separately provisioned executable. Restrict who can replace it or its packages.
4. **Artifact boundary:** case and response files remain sensitive because evidence quotes and source filenames remain.
5. **Human boundary:** extraction and similarity scores never authorize a consequential action.

## Scaling pattern

Scale out by assigning independent case workspaces to independent robot jobs. Do not allow jobs to share request, response, case, or temporary paths. For very large corpora, first benchmark memory and runtime with representative documents, then use bounded batches whose case semantics are explicitly understood. This example does not implement distributed case merging.

## Extension rules

When adding a command:

1. Version the contract if an existing request or response meaning changes.
2. Add an exact-key parameter validator.
3. Use only supported DocChrono public APIs.
4. Return evidence and completion metadata, not just labels.
5. Define stable error codes and exit semantics.
6. Add a synthetic fixture and deterministic integration test.
7. Add a UiPath workflow only after the Python contract is tested.
8. Update privacy analysis and documentation.

Do not add semantic search, OCR, spreadsheet parsing, `.msg` parsing, or automatic contradiction decisions to documentation before an implemented and tested command exists.

## Official UiPath references

- [Invoke Code](https://docs.uipath.com/activities/other/latest/workflow/invoke-code)
- [Invoke Workflow File](https://docs.uipath.com/activities/other/latest/workflow/invoke-workflow-file)
- [About Automation Projects](https://docs.uipath.com/studio/standalone/latest/user-guide/about-automation-projects)
- [About Processes](https://docs.uipath.com/orchestrator/automation-cloud/latest/user-guide/about-processes)
