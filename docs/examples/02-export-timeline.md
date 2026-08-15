# Example 2: export the complete chronology

## Outcome

Load the case created by example 1 and export all events in deterministic chronology order, including the explicit undated partition. Every event keeps participants, confidence/provisional metadata, normalized temporal expressions, evidence quotes, locations, and source filenames.

## Files

- UiPath: [`02_ExportTimeline.xaml`](../../UiPath/DocChronoUiPathExamples/Examples/02_ExportTimeline.xaml)
- Request: [`../../Examples/requests/02_export_timeline.json`](../../Examples/requests/02_export_timeline.json)
- Required input: `artifacts/case.docchrono.json`
- Generated response: `artifacts/responses/02_export_timeline.response.json`

## Request

```json
{
  "command": "export_timeline",
  "parameters": {
    "case_file": "../../artifacts/case.docchrono.json"
  },
  "request_id": "example-02-export-timeline",
  "schema_version": "1.0"
}
```

The case path resolves relative to `Examples/requests`.

## UiPath sequence

1. **Assign** sets the deterministic timeline response path.
2. **Invoke Workflow File** calls the shared framework with a 60-second timeout.
3. The framework starts the isolated Python bridge, validates a correlated response no larger than 64 MiB, and rejects malformed/error envelopes.
4. Exit `2` is validated and preserved but then fails closed with an exception; only exit `0` reaches normal completion.
5. Captured stdout/stderr are discarded. The workflow logs only metadata and returns `out_ResponsePath` on complete success.

Run example 1 first. This example never rebuilds the case, so the chronology is a stable query over one saved artifact.

## Run directly

```powershell
.\.venv\Scripts\python.exe -m docchrono_uipath_bridge `
  --request .\Examples\requests\02_export_timeline.json `
  --response .\artifacts\responses\02_export_timeline.response.json

$timeline = Get-Content .\artifacts\responses\02_export_timeline.response.json -Raw | ConvertFrom-Json
$timeline.result.events | Select-Object chronology_position,date,date_status,title
```

## Verified summary

```json
{
  "dated_count": 5,
  "includes_undated": true,
  "total_count": 5,
  "undated_count": 0
}
```

The fixed corpus deliberately has zero undated events. `includes_undated: true` means the exporter uses `timeline.all` and preserves the undated bucket; it does not promise that every case contains an undated event.

## Verified order

| Position | Date | Type | Title | Primary source |
|---:|---|---|---|---|
| 1 | `2026-03-03` | `DECISION` | Approved: Invoice #381 for Northstar Logistics Corporation | `01_invoice_approval.txt` |
| 2 | `2026-03-05` | `DECISION` | Approved: Invoice #700 for Northstar Logistics Corporation | `05_review_candidate_a.md` |
| 3 | `2026-03-06` | `DECISION` | Approved: Invoice #701 for Northstar Logistics Corporation | `06_review_candidate_b.md` |
| 4 | `2026-03-07` | `TRANSACTION` | Paid: Payment #982 | `04_payment_notice.eml` |
| 5 | `2026-03-07T10:15:00-06:00` | `COMMUNICATION` | Email Sent | `04_payment_notice.eml` |

The negated March 4 authorization statement is retained as a claim but is not converted into an affirmative event. A chronology is therefore not a list of every sentence or date mention.

## Event record anatomy

Representative shape:

```json
{
  "chronology_position": 1,
  "date": "2026-03-03",
  "date_status": "dated",
  "title": "Approved: Invoice #381 for Northstar Logistics Corporation",
  "type": "DECISION",
  "participants": [
    "Invoice #381",
    "Maya Chen",
    "Northstar Logistics Corporation"
  ],
  "provisional": true,
  "score": 0.92,
  "temporal": [],
  "evidence": []
}
```

The actual `temporal` and `evidence` arrays are populated. They are shortened above to emphasize the record shape.

For an undated event from another corpus:

```json
{
  "date": null,
  "date_status": "undated"
}
```

Never sort `null` dates away after export. Preserve `chronology_position` or maintain a visible **Undated** section.

## Build a UiPath DataTable

A consuming workflow can:

1. Read and deserialize the response.
2. Validate envelope and status.
3. Iterate `result.events` in array order.
4. Add columns for Position, Date, Date Status, Title, Type, Participants, Score, Provisional, Sources, and Quote.
5. Put unresolved dates into an explicit review view, not an error bucket.
6. Keep the full evidence JSON or governed response reference with each row.

If formatting for Excel or a report, do not reduce an instant with timezone to a date without recording that transformation. `2026-03-07T10:15:00-06:00` and `2026-03-07` have different precision.

## Acceptance checks

- case came from the same job/correlation;
- exit/status match; the sample completes only for exit `0` and throws after validating partial exit `2`;
- `total_count = dated_count + undated_count`;
- `events.Count = total_count`;
- chronology positions are contiguous starting at 1;
- each event retains evidence or is routed for review;
- dates are displayed with original precision/timezone information;
- undated items remain visible.

## What this example does not prove

Chronological order is not causal order. A date extracted from a statement does not prove the event occurred, and an absent event does not prove nothing happened. The export does not perform report generation or automatic contradiction detection.
