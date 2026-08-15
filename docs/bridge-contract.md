# Bridge contract 1.0

## Invocation

```powershell
python -m docchrono_uipath_bridge `
  --request C:\job\request.json `
  --response C:\job\response.json
```

Both flags are required. Request and response must be different paths. The bridge reads one UTF-8 JSON request no larger than 1,048,576 bytes and atomically replaces one UTF-8 JSON response through a temporary sibling. It does not read stdin and does not use stdout as the data channel; stdout contains only a small status record.

Relative CLI paths are interpreted by the Python process working directory. Relative paths **inside request parameters** are interpreted relative to the request file's parent directory.

## Additional UiPath runner contract

`UiPath/DocChronoUiPathExamples/Framework/RunDocChronoBridge.xaml` adds controls around the CLI:

1. Resolve Python against the external working directory.
2. Create the response directory and delete a stale response before launch.
3. Capture and drain stdout/stderr; the five examples discard both values.
4. Enforce the supplied timeout and attempt to kill the process tree.
5. Require a non-empty response no larger than 67,108,864 bytes (64 MiB).
6. Parse request and response JSON and require exactly the seven response fields.
7. Verify schema `1.0`, request ID, command, status/exit pairing, errors, and result shape.
8. Throw for error exits and also for validated partial exit `2`; only validated exit `0` completes normally.

The Python replacement is atomic where supported, but the full runner sequence does not retain a previous response atomically because the stale file is deliberately removed first. After a failed or timed-out run, absence of a response is expected and safer than accepting stale data.

## Request envelope

The top level requires exactly these four keys:

```json
{
  "schema_version": "1.0",
  "request_id": "case-428-build-001",
  "command": "build_case",
  "parameters": {}
}
```

| Field | Type | Constraint |
|---|---|---|
| `schema_version` | string | Exactly `1.0`. |
| `request_id` | string | Non-empty; at most 128 characters. The caller owns uniqueness and correlation semantics. |
| `command` | string | One of the five commands below. |
| `parameters` | object | Exact keys depend on the command. Unknown keys are rejected. |

The parser does not coerce strings to booleans, objects, or numbers.

## Commands

### `build_case`

```json
{
  "source_directory": "../data",
  "case_file": "../../artifacts/case.docchrono.json",
  "strict": true
}
```

| Parameter | Required | Type | Meaning |
|---|---:|---|---|
| `source_directory` | yes | non-empty string | Existing local directory containing source documents. |
| `case_file` | yes | non-empty string | Destination for the privacy-reduced DocChrono case. Parent directories are created. |
| `strict` | no | boolean | Defaults to `false`. When true, a document failure fails the build instead of returning a partial case. |

Result fields:

- `build_complete`: whether DocChrono recorded a complete build;
- `case_file`: destination basename only;
- `counts`: claims, documents, entities, events, relationships, review items;
- `docchrono_version`;
- `failures`: stable generic failure records without local paths or parser exception text;
- `privacy`: explicit booleans for raw text, evidence quotes, and local source paths;
- `strict`.

Standard DocChrono `Case.save_sanitized()` removes raw document text but still retains evidence quotations and source paths/metadata. The bridge first removes metadata, replaces local paths with filenames, and redacts report diagnostics, then calls the sanitized save. Evidence quotes remain, and loss of raw text means full round-trip verification requires the originals.

### `export_timeline`

```json
{
  "case_file": "../../artifacts/case.docchrono.json"
}
```

Result fields:

- `dated_count`, `undated_count`, `total_count`;
- `includes_undated: true`;
- `events`, ordered from `case.timeline.all`.

Each event includes `chronology_position`, `date`, `date_status`, `title`, `type`, `participants`, `provisional`, `score`, all temporal expressions, and deduplicated evidence records. An undated event carries `date: null` and `date_status: "undated"`.

### `export_evidence`

```json
{
  "case_file": "../../artifacts/case.docchrono.json",
  "relationship_type": "WORKS_FOR"
}
```

`relationship_type` is optional. When omitted, all relationships are exported. The filter is an exact string match.

Each relationship includes source and target node records, type, score, `supporting_evidence`, and `opposing_evidence`. Each claim record includes kind, predicate, polarity, modality, participants, temporal expressions, score, and evidence.

The result includes a `human_review_notice`. Separate evidence polarities are not an automated contradiction verdict.

### `find_path`

```json
{
  "case_file": "../../artifacts/case.docchrono.json",
  "start": "Maya Chen",
  "end": "Payment #982"
}
```

`start` and `end` accept an exact internal node ID, canonical entity name, entity alias, or event title. Name matching is exact and case-sensitive. Zero matches returns `REFERENCE_NOT_FOUND`; multiple exact matches return `AMBIGUOUS_REFERENCE`.

No available path is a successful query with `found: false`, zero hops, and exit `0` or `2` according to the loaded case status. A found hop includes:

- `traversal.from` / `traversal.to`;
- `stored_direction.source` / `stored_direction.target`;
- `stored_direction.matches_traversal`;
- relationship type and score;
- supporting and opposing evidence.

### `export_review_queue`

```json
{
  "case_file": "../../artifacts/case.docchrono.json"
}
```

This is a read-only export. The result contains `automation_policy`, `item_count`, and sorted `items`. Each item contains kind, reason, score, evidence, candidates, and `recommended_action: "HUMAN_REVIEW"`. It never accepts, rejects, or merges a candidate.

## Response envelope

Complete or partial response:

```json
{
  "command": "export_timeline",
  "errors": [],
  "request_id": "example-02-export-timeline",
  "result": {},
  "schema_version": "1.0",
  "status": "complete",
  "warnings": []
}
```

Error response:

```json
{
  "command": "find_path",
  "errors": [
    {
      "code": "REFERENCE_NOT_FOUND",
      "message": "No graph node has the exact name 'Unknown'."
    }
  ],
  "request_id": "query-17",
  "result": null,
  "schema_version": "1.0",
  "status": "error",
  "warnings": []
}
```

Fields are always present when a response can be written. `request_id` and `command` can be `null` when malformed input prevents reliable extraction.

## Exit codes

| Code | Meaning | Normal response |
|---:|---|---|
| `0` | Complete | `status: complete` |
| `2` | Usable partial build/query at the CLI boundary | `status: partial`; the sample UiPath runner validates, preserves, then throws to fail closed |
| `1` | Known validation, source, or domain error | `status: error`; CLI argument failure can occur before response handling |
| `70` | Unexpected internal error or response write failure | `status: error` when write succeeds; otherwise no artifact |

The UiPath caller must verify exit code, file existence/non-zero length and 64 MiB limit, response schema, correlation ID, command, status/exit pairing, errors, and result shape. The supplied runner performs those checks before it branches.

## Stable error codes

| Code | Typical cause | Retry guidance |
|---|---|---|
| `CLI_ARGUMENT_ERROR` | Missing/unknown CLI flag | Configuration defect; do not retry unchanged. |
| `PATH_CONFLICT` | Same request and response path | Configuration defect. |
| `REQUEST_TOO_LARGE` | Request exceeds 1 MiB | Reduce request; documents belong in the source directory. |
| `REQUEST_NOT_FOUND` | Request path absent | Fix staging/path. |
| `REQUEST_READ_FAILED` | Permission or I/O failure | Retry only after storage condition changes. |
| `INVALID_REQUEST_ENCODING` | Request is not UTF-8 | Regenerate correctly. |
| `INVALID_JSON` | Malformed JSON | Correct caller serialization. |
| `INVALID_REQUEST` | Missing, unknown, empty, or wrong-typed field | Contract defect; do not retry unchanged. |
| `UNSUPPORTED_SCHEMA_VERSION` | Version is not `1.0` | Route to compatible bridge. |
| `UNKNOWN_COMMAND` | Command is not supported | Caller defect. |
| `SOURCE_DIRECTORY_NOT_FOUND` | Build input directory absent | Correct stage/path. |
| `CASE_FILE_NOT_FOUND` | Query case file absent | Run build or correct path. |
| `REFERENCE_NOT_FOUND` | Graph name/ID absent | Review input, then correct reference. |
| `AMBIGUOUS_REFERENCE` | Exact name resolves to multiple nodes | Use a unique node ID. |
| `BUILD_FAILED` | Strict build could not complete | Inspect protected operational diagnostics and source set. |
| `SOURCE_UNAVAILABLE` | DocChrono could not read a source | Verify support, permissions, and file integrity. |
| `DOCCHRONO_ERROR` | Case or operation was rejected | Quarantine artifact and investigate. |
| `FILE_OPERATION_FAILED` | Input/output I/O failure | Retry only after storage condition changes. |
| `UNEXPECTED_ERROR` | Unhandled defect | Escalate with sanitized telemetry. |

`RESPONSE_WRITE_FAILED` is written to stderr if even the error response cannot be written; exit is `70`.

## Versioning policy

`schema_version` versions the bridge, not DocChrono's own saved-case schema. Additive fields can be introduced only if consumers are documented to ignore them; this implementation deliberately rejects unknown request keys to expose drift. Any changed field meaning, required field, enum, or path rule requires a new bridge schema and parallel compatibility during migration.

## Security properties and non-properties

The contract provides bounded request input, exact validation, shell-free argument passing, generic external error messages, and atomic Python response replacement; the UiPath runner adds a 64 MiB response-envelope limit. The runner deletes stale output before launch, so an end-to-end failure can leave no response. The contract does not authenticate callers, encrypt files, authorize filesystem access, scrub evidence quotes, or verify source-document truth. Those controls belong to the robot host and surrounding UiPath process.
