# Example 4: find an evidence graph path

## Outcome

Find one three-hop graph path from `Maya Chen` to `Payment #982` and return evidence for every hop. The bridge explicitly distinguishes route traversal from the stored direction of each relationship.

## Files

- UiPath: [`04_FindGraphPath.xaml`](../../UiPath/DocChronoUiPathExamples/Examples/04_FindGraphPath.xaml)
- Request: [`../../Examples/requests/04_find_path.json`](../../Examples/requests/04_find_path.json)
- Required input: `artifacts/case.docchrono.json`
- Generated response: `artifacts/responses/04_find_path.response.json`

## Request

```json
{
  "command": "find_path",
  "parameters": {
    "case_file": "../../artifacts/case.docchrono.json",
    "end": "Payment #982",
    "start": "Maya Chen"
  },
  "request_id": "example-04-find-path",
  "schema_version": "1.0"
}
```

`start` and `end` accept an exact internal node ID, canonical entity name, alias, or event title. Name matching is exact and case-sensitive. Ambiguity is an error instead of a first-match guess.

## UiPath sequence

1. Assign the graph response path.
2. Invoke the shared framework with a 60-second timeout.
3. Validate the correlated response and fail closed on error or partial status.
4. Discard captured stdout/stderr and return `out_ResponsePath` only for complete success.

## Run directly

```powershell
.\.venv\Scripts\python.exe -m docchrono_uipath_bridge `
  --request .\Examples\requests\04_find_path.json `
  --response .\artifacts\responses\04_find_path.response.json

$path = Get-Content .\artifacts\responses\04_find_path.response.json -Raw | ConvertFrom-Json
$path.result.found
$path.result.hop_count
$path.result.hops | ForEach-Object {
  [pscustomobject]@{
    Hop = $_.hop
    From = $_.traversal.from.name
    Type = $_.relationship_type
    To = $_.traversal.to.name
    MatchesStoredDirection = $_.stored_direction.matches_traversal
  }
}
```

## Verified path

```text
Maya Chen
  --WORKS_FOR-->
Northstar Logistics Corporation
  --PARTICIPATED_IN-->
Paid: Payment #982
  <--PARTICIPATED_IN--
Payment #982
```

The response reports `found: true` and `hop_count: 3`.

| Hop | Traversal from | Relationship | Traversal to | Stored direction matches? |
|---:|---|---|---|---:|
| 1 | Maya Chen | `WORKS_FOR` | Northstar Logistics Corporation | `true` |
| 2 | Northstar Logistics Corporation | `PARTICIPATED_IN` | Paid: Payment #982 | `true` |
| 3 | Paid: Payment #982 | `PARTICIPATED_IN` | Payment #982 | `false` |

The third stored relationship is:

```text
Payment #982 --PARTICIPATED_IN--> Paid: Payment #982
```

The path walks it backward. A display that blindly draws `traversal.from --type--> traversal.to` would make a false directional assertion.

## Hop record anatomy

```json
{
  "hop": 3,
  "relationship_type": "PARTICIPATED_IN",
  "score": 0.92,
  "traversal": {
    "from": {"kind": "event", "name": "Paid: Payment #982", "type": "TRANSACTION"},
    "to": {"kind": "entity", "name": "Payment #982", "type": "OTHER"}
  },
  "stored_direction": {
    "matches_traversal": false,
    "source": {"kind": "entity", "name": "Payment #982", "type": "OTHER"},
    "target": {"kind": "event", "name": "Paid: Payment #982", "type": "TRANSACTION"}
  },
  "supporting_evidence": [],
  "opposing_evidence": []
}
```

The actual evidence arrays are populated; they are shortened above to focus on direction.

## Rendering rule

Use `traversal` to order cards or rows. Use `stored_direction` to draw arrowheads or state subject/object semantics. A safe textual renderer can say:

```text
Route: Paid: Payment #982 -> Payment #982
Stored: Payment #982 --PARTICIPATED_IN--> Paid: Payment #982
Traversed in reverse: yes
```

## Evidence rule

Every hop includes supporting and opposing claim records when present. Hop 1 carries both affirmed and negated employment evidence. Hops 2 and 3 share evidence from the payment statement. Keep hop evidence attached when copying the path into a queue or visualization.

## Business-result branches

| Result | Meaning | UiPath route |
|---|---|---|
| `found: true` | One available traversable path was returned | Display with evidence and stored direction; human review as needed. |
| `found: false` | Query succeeded but current graph has no path | Normal no-result branch; do not call it proof of no relationship. |
| `REFERENCE_NOT_FOUND` | Exact start/end node absent | Correct reference or route to data review. |
| `AMBIGUOUS_REFERENCE` | Exact reference maps to multiple nodes | Select a unique ID through a reviewed step. |

## Acceptance checks

- `found=true`, `hop_count=3`, and three hop records;
- each next traversal node equals the prior hop's destination;
- hop 3 has `matches_traversal=false`;
- every hop retains relationship type, score, and evidence arrays;
- no path is described as causal proof;
- ambiguous names are never automatically resolved.

## What this example does not prove

A path proves only connectivity in the current extracted graph. It is not causal reasoning, authorization analysis, shortest-path uniqueness, every possible path, or a complete ontology inference.
