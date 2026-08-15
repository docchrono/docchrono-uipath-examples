# Example 3: trace supporting and opposing evidence

## Outcome

Export the `WORKS_FOR` relationship while preserving one affirmed source claim and one negated source claim. The result gives a UiPath reviewer enough provenance to locate both statements without deciding which is true.

## Files

- UiPath: [`03_TraceEvidence.xaml`](../../UiPath/DocChronoUiPathExamples/Examples/03_TraceEvidence.xaml)
- Request: [`../../Examples/requests/03_export_evidence.json`](../../Examples/requests/03_export_evidence.json)
- Supporting fixture: [`../../Examples/data/01_invoice_approval.txt`](../../Examples/data/01_invoice_approval.txt)
- Opposing fixture: [`../../Examples/data/02_employment_exception.md`](../../Examples/data/02_employment_exception.md)
- Generated response: `artifacts/responses/03_export_evidence.response.json`

## Request

```json
{
  "command": "export_evidence",
  "parameters": {
    "case_file": "../../artifacts/case.docchrono.json",
    "relationship_type": "WORKS_FOR"
  },
  "request_id": "example-03-export-evidence",
  "schema_version": "1.0"
}
```

Remove `relationship_type` from a generated request to export every stored relationship. The filter is exact; do not assume fuzzy or ontology-subtype matching.

## UiPath sequence

1. Assign the response path.
2. Invoke the shared framework with a 60-second timeout.
3. Validate the correlated response and fail closed on error or partial status.
4. Discard captured stdout/stderr and return the response path only for complete success.

The XAML does not flatten or log claims. The consuming workflow decides how to display or route them.

## Run directly

```powershell
.\.venv\Scripts\python.exe -m docchrono_uipath_bridge `
  --request .\Examples\requests\03_export_evidence.json `
  --response .\artifacts\responses\03_export_evidence.response.json

$evidence = Get-Content .\artifacts\responses\03_export_evidence.response.json -Raw | ConvertFrom-Json
$relationship = $evidence.result.relationships[0]
$relationship.source.name
$relationship.relationship_type
$relationship.target.name
$relationship.supporting_evidence.Count
$relationship.opposing_evidence.Count
```

## Verified result

```text
relationship_count: 1
source:              Maya Chen (PERSON)
relationship_type:   WORKS_FOR
target:              Northstar Logistics Corporation (ORGANIZATION)
score:               0.94
supporting claims:   1
opposing claims:     1
```

Supporting quote and source:

```text
"Maya Chen works for Northstar Logistics Corporation"
01_invoice_approval.txt
polarity: AFFIRMED
```

Opposing quote and source:

```text
"Maya Chen does not work for Northstar Logistics Corporation"
02_employment_exception.md
polarity: NEGATED
```

Each source record also includes paragraph/sentence/raw offsets where available, claim participants, modality, kind, and score.

## Review-table pattern in UiPath

Create one parent relationship row and separate child evidence rows:

| Relationship ID/key | Side | Polarity | Quote | Source | Location | Score |
|---|---|---|---|---|---|---:|
| Maya/Northstar/WORKS_FOR | supporting | AFFIRMED | retained quote | `01_invoice_approval.txt` | paragraph/sentence/offset | 0.94 |
| Maya/Northstar/WORKS_FOR | opposing | NEGATED | retained quote | `02_employment_exception.md` | paragraph/offset | 0.94 |

Do not overwrite the supporting row when an opposing row exists. Do not average polarities into one boolean. Preserve source-level records so a reviewer can inspect both originals.

## Important interpretation rules

- `supporting_evidence` means an affirmed extracted claim supports the stored relationship.
- `opposing_evidence` means a negated extracted claim opposes it.
- This organization is **not** an automatic contradiction verdict.
- The relationship score is not probability or factual resolution.
- `status: complete` means the query completed, not that either claim is true.
- A missing opposing claim is not proof that no opposing evidence exists in the real world.

## Downstream workflow

A production UiPath process can:

1. Store the relationship and both evidence sides in a governed review database.
2. Create a human-review task containing only a secure link, source names, and minimal metadata.
3. Require the reviewer to open immutable originals and inspect surrounding context.
4. Record reviewer identity, rationale, and disposition separately from extracted data.
5. Leave the source extraction immutable; add adjudication as a new layer.

## Acceptance checks

- exactly one filtered relationship;
- exact source/target/type values;
- one supporting and one opposing claim;
- supporting polarity `AFFIRMED`, opposing polarity `NEGATED`;
- both claims include evidence quote and source filename;
- no workflow automatically selects a winner;
- response content is not logged.

## What this example does not prove

It does not implement contradiction detection, temporal reconciliation, authority rules, or legal fact finding. It only demonstrates source-linked claim polarity around a relationship.
