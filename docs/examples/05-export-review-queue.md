# Example 5: export a read-only review queue

## Outcome

Export DocChrono review items in a UiPath-friendly JSON structure without accepting, rejecting, or applying them. The fixed corpus produces one possible entity merge between `Jordan Carmichael` and `Jordon Carmichael`.

## Files

- UiPath: [`05_ExportReviewQueue.xaml`](../../UiPath/DocChronoUiPathExamples/Examples/05_ExportReviewQueue.xaml)
- Request: [`../../Examples/requests/05_export_review_queue.json`](../../Examples/requests/05_export_review_queue.json)
- Candidate A: [`../../Examples/data/05_review_candidate_a.md`](../../Examples/data/05_review_candidate_a.md)
- Candidate B: [`../../Examples/data/06_review_candidate_b.md`](../../Examples/data/06_review_candidate_b.md)
- Generated response: `artifacts/responses/05_export_review_queue.response.json`

## Request

```json
{
  "command": "export_review_queue",
  "parameters": {
    "case_file": "../../artifacts/case.docchrono.json"
  },
  "request_id": "example-05-export-review-queue",
  "schema_version": "1.0"
}
```

## UiPath sequence

1. Assign the review response path.
2. Invoke the shared framework with a 60-second timeout.
3. Validate the correlated response and fail closed on error or partial status.
4. Discard captured stdout/stderr and return the response path only for complete success.

No activity in this workflow writes an Orchestrator Queue item or mutates the DocChrono case. That makes rerunning the export safe at the case level.

## Run directly

```powershell
.\.venv\Scripts\python.exe -m docchrono_uipath_bridge `
  --request .\Examples\requests\05_export_review_queue.json `
  --response .\artifacts\responses\05_export_review_queue.response.json

$review = Get-Content .\artifacts\responses\05_export_review_queue.response.json -Raw | ConvertFrom-Json
$review.result.automation_policy
$review.result.item_count
$review.result.items[0] | Format-List
```

## Verified result

```json
{
  "automation_policy": "Route every item to a qualified human reviewer; this command never accepts, rejects, or merges findings.",
  "item_count": 1,
  "items": [
    {
      "kind": "entity_merge_candidate",
      "reason": "RapidFuzz token similarity 0.941",
      "recommended_action": "HUMAN_REVIEW",
      "score": 0.912941
    }
  ]
}
```

The real item also contains two candidate records and two evidence records:

| Candidate | Type | Quote source |
|---|---|---|
| Jordan Carmichael | `PERSON` mention | `05_review_candidate_a.md` |
| Jordon Carmichael | `PERSON` mention | `06_review_candidate_b.md` |

## Meaning of the candidate

DocChrono's similarity logic found that the two mentions are close enough to review. It did **not** establish that they are the same person. The score is not an identity probability. Context such as email address, organization, role, geography, date, and authoritative identifiers may confirm or reject a merge.

The bridge exports the recommendation but never changes aliases, entities, claims, events, or relationships.

## Add Orchestrator Queue items safely

A separate consuming workflow can create one transaction per review item:

1. Read and validate the response.
2. Build an idempotency key from case ID, request ID, review kind, sorted candidate names/IDs, and bridge schema.
3. Check whether that item already exists or has been dispositioned.
4. Store minimal non-sensitive queue data plus a secure artifact reference.
5. Route to a qualified reviewer with appropriate case access.
6. Record approve/reject/needs-more-information as a separate adjudication record.
7. Apply a merge only through a separately tested, authorized process—this sample has no merge command.

Do not place evidence quotes in a broadly visible queue payload. Store them in governed case storage and pass a reference when possible.

## Example queue fields

| Field | Safe purpose |
|---|---|
| `Reference` | Deterministic idempotency key, not a person's name. |
| `CaseReference` | Opaque link/key into governed case storage. |
| `RequestId` | Correlation with bridge response. |
| `ReviewKind` | `entity_merge_candidate`. |
| `CandidateCount` | `2`. |
| `Score` | Sorting aid only. |
| `ResponseChecksum` | Detect artifact substitution. |
| `BridgeSchema` | `1.0`. |

Candidate names, source filenames, quotes, and reasons may be sensitive; include only when the queue and its viewers are authorized for the case.

## Human review checklist

- open both original documents, not just quotes;
- confirm source authenticity and context;
- compare independent identifiers;
- check whether two different people could plausibly have the names;
- review downstream impact of merging existing claims/events;
- record reviewer, timestamp, evidence considered, rationale, and disposition;
- provide an undo/correction path in any external resolution system.

## Acceptance checks

- export has no side effects on the case;
- `item_count=1` and item kind is `entity_merge_candidate`;
- candidate names are Jordan and Jordon Carmichael;
- two source-linked evidence records remain;
- action is `HUMAN_REVIEW`;
- no threshold automatically approves/rejects;
- retry does not create duplicate downstream review work.

## What this example does not prove

It does not implement Action Center, queue creation, reviewer assignment, entity merge application, or identity verification. It demonstrates the read-only handoff that a governed UiPath review process can consume.
