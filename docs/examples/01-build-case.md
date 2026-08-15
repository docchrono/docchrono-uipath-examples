# Example 1: build a source-linked case

## Outcome

Build one deterministic DocChrono case from six synthetic files and return counts, build completion, generic failures, software version, and explicit privacy properties. This step creates `artifacts/case.docchrono.json`, required by examples 2-5.

## Files

- UiPath: [`01_BuildCase.xaml`](../../UiPath/DocChronoUiPathExamples/Examples/01_BuildCase.xaml)
- Request: [`../../Examples/requests/01_build_case.json`](../../Examples/requests/01_build_case.json)
- Data: [`../../Examples/data`](../../Examples/data)
- Shared process runner: [`RunDocChronoBridge.xaml`](../../UiPath/DocChronoUiPathExamples/Framework/RunDocChronoBridge.xaml)
- Generated response: `artifacts/responses/01_build_case.response.json`
- Generated case: `artifacts/case.docchrono.json`

## Request

```json
{
  "command": "build_case",
  "parameters": {
    "case_file": "../../artifacts/case.docchrono.json",
    "source_directory": "../data",
    "strict": true
  },
  "request_id": "example-01-build-case",
  "schema_version": "1.0"
}
```

Both paths are relative to `Examples/requests`, the request file's directory:

```text
Examples/requests + ../data
  -> Examples/data

Examples/requests + ../../artifacts/case.docchrono.json
  -> artifacts/case.docchrono.json
```

`strict: true` makes a source-processing failure fail this demonstration. A production intake that permits partial cases can set `false`, but must route exit `2` and report failures explicitly.

## UiPath sequence

1. **Assign** sets `out_ResponsePath` to `artifacts\responses\01_build_case.response.json`.
2. **Invoke Workflow File** calls `Framework\RunDocChronoBridge.xaml`.
3. Arguments include Python path, project working directory, request/response paths, and `120000` ms timeout.
4. The framework launches `python -m docchrono_uipath_bridge` without a shell.
5. A stale response is deleted before launch, then the new response must exist, be non-empty, and be no larger than 64 MiB.
6. The framework validates schema, correlation, command, fields, status/exit pairing, and result/error shape.
7. Exit `1`/`70` raises after error-envelope validation; exit `2` raises after partial-envelope validation so the sample fails closed.
8. Captured stdout/stderr are discarded by this example. **Log Message** records only exit code and response filename after exit `0`; `out_ResponsePath` then returns to the parent.

## Run from Python first

```powershell
.\.venv\Scripts\python.exe -m docchrono_uipath_bridge `
  --request .\Examples\requests\01_build_case.json `
  --response .\artifacts\responses\01_build_case.response.json

$exit = $LASTEXITCODE
$payload = Get-Content .\artifacts\responses\01_build_case.response.json -Raw | ConvertFrom-Json
$payload.status
$payload.result.counts
$exit
```

## Verified result

With the fixed corpus and pins:

```json
{
  "build_complete": true,
  "counts": {
    "claims": 10,
    "documents": 6,
    "entities": 12,
    "events": 5,
    "relationships": 16,
    "review_items": 1
  },
  "docchrono_version": "0.1.0",
  "failures": [],
  "privacy": {
    "document_raw_text_saved": false,
    "evidence_quotes_saved": true,
    "local_source_paths_saved": false
  },
  "strict": true
}
```

The outer envelope also contains `schema_version`, `request_id`, `command`, `status`, `warnings`, and `errors`. The complete build returns exit `0`, `status: complete`, and one warning explaining the privacy-reduced save. A non-strict partial build would write exit `2`, be fully validated, and then cause the sample XAML to throw for explicit review/retry routing.

## What the case contains

The case holds structured source references, documents, evidence spans, mentions, entities, claims, events, relationships, review items, and build report. Evidence quotes support later audit and review.

This bridge first removes local absolute source paths/metadata and redacts parser diagnostics, then calls DocChrono's sanitized save. Standard `Case.save_sanitized()` alone still retains source paths/metadata and evidence quotations. Both sanitized variants omit raw document text and therefore cannot provide full round-trip verification without the original documents.

Do not interpret `document_raw_text_saved: false` as anonymized, declassified, or safe to log.

## Downstream UiPath pattern

After the XAML returns `out_ResponsePath`:

1. Read the response as UTF-8.
2. Match `request_id`.
3. Require `status=complete` for the normal route.
4. Store the case file and response in governed evidence storage.
5. Write only safe counts/status/checksums to logs.
6. Invoke the timeline/evidence/path/review workflows against the same case artifact.

If the downstream workflow creates a queue item, include a governed case reference, not the full response or source directory.

## Failure exercises

Copy the request to a temporary job folder and change one field at a time:

- missing source directory -> `SOURCE_DIRECTORY_NOT_FOUND`, exit `1`;
- string `"true"` instead of boolean `true` -> `INVALID_REQUEST`, exit `1`;
- unknown parameter -> `INVALID_REQUEST`, exit `1`;
- unsupported source under strict build -> `BUILD_FAILED`, exit `1`.

Do not modify the checked-in request while multiple jobs or developers might use it.

## Acceptance checks

- response is valid UTF-8 JSON and schema `1.0`;
- response request ID matches;
- exit `0`, `status=complete`, no errors;
- exactly 6 documents and zero failures;
- counts match the pinned fixture baseline;
- privacy block says raw text/path false and quotes true;
- case exists and is non-empty;
- no source or response content appears in UiPath logs.

## What this example does not prove

It does not prove that every extraction is true, that the corpus is complete, that a source is authentic, or that the sanitized file is non-sensitive. It does not demonstrate OCR, spreadsheets, `.msg`, or semantic search.
