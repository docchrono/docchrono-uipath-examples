# Security and privacy

## Data classification

Assume every source corpus, saved case, response, review item, and temporary file has the source corpus's highest classification. Local processing and no cloud AI key reduce one exposure path; they do not make the workflow private by default.

## What is retained

DocChrono's full `Case.save()` output retains:

- raw parsed document text;
- evidence quotations;
- local source paths;
- structured documents, mentions, entities, claims, events, relationships, and review items;
- build/provenance metadata.

Standard `Case.save_sanitized()` removes raw document text but still retains evidence quotations and source paths/metadata. This bridge pre-redacts those paths/metadata and diagnostics, then calls the sanitized save. It therefore:

- removes document raw text;
- replaces local source paths with source filenames;
- removes source metadata;
- replaces detailed parser failure messages and warnings with generic text.

It still retains:

- evidence quotations, which can contain the most sensitive sentence in a document;
- source filenames, which can reveal people, matters, customers, or allegations;
- structured names, events, claims, relationships, scores, and dates;
- evidence locations and provenance identifiers.

Sanitized output therefore remains sensitive. Because raw text is removed, the saved case alone cannot provide full round-trip verification of surrounding context. Maintain controlled access to immutable originals.

## Threats and controls

| Threat | Example | Required control |
|---|---|---|
| Source exfiltration | Response body copied into Robot logs | Log metadata only; classify and restrict logs. |
| Path substitution | Attacker changes `in_PythonExe` | Use an absolute allow-listed path; restrict write ACLs on interpreter and environment. |
| Dependency compromise | Robot installs from public PyPI at runtime | Build, hash, scan, mirror, and install immutable wheels before runtime. |
| Workspace collision | Two jobs use `artifacts/case.json` | Allocate a unique workspace per job. |
| Path traversal | Untrusted case ID becomes a directory path | Canonicalize beneath an allow-listed root; do not concatenate unchecked input. |
| Malicious/oversized request | Huge JSON consumes resources | Bridge caps requests at 1 MiB and rejects unknown/wrong-typed fields. |
| Malicious document | Parser/native library exploit | Patch dependencies, scan inputs, isolate robot, enforce file-size/type policy, and apply OS controls. |
| Shell injection | Source path contains metacharacters | Framework uses `ProcessStartInfo.ArgumentList` with `UseShellExecute=False`; preserve that design. |
| Hung child process | Parser never returns | Use measured bounded timeouts and kill the process tree; quarantine possible partial artifacts. |
| False automation | High score automatically approves/merges | Require human review and independent authorization for consequential action. |
| Evidence loss | Sanitized case replaces originals | Retain immutable originals and hashes according to evidence policy. |

## Filesystem permissions

The Robot identity needs:

- read/execute on the provisioned Python interpreter and packages;
- read on staged source documents;
- create/write/replace on its own request/output/temp directories;
- no write permission to the shared interpreter, bridge package, or another job's workspace.

Use separate identities or folders for cases requiring stronger separation. Do not run the bridge as a local administrator merely to avoid ACL configuration.

## Request security

Requests are data, not authorization. The bridge will operate on any path the process identity can access. The caller must enforce allowed roots and case-level authorization before constructing a request.

`request_id` may appear in logs. Make it a non-sensitive opaque correlation value. The request does not accept credentials and should never contain them.

## Response security

Responses include evidence quotes and filenames. Do not:

- log the full response;
- attach it to unrestricted incidents or email;
- store it in a general-purpose queue payload without encryption/classification review;
- expose it through an output argument when Orchestrator users do not need it;
- use filenames as public labels.

Prefer a governed storage reference plus minimal safe metadata for downstream queues.

## Logging

The nested project's `RunDocChronoBridge.xaml` captures stdout and stderr so redirected pipes cannot block; all five examples discard both. It logs only request/response filenames and complete exit metadata. The framework's exception tells operators where to look but does not echo either stream or the response body.

The runner deletes a stale response before launch, caps the new envelope at 64 MiB, validates correlation and shape, and fails closed on partial status. Python's successful temporary-file replacement is atomic where supported, but the end-to-end runner intentionally does not retain stale output after a failed launch.

If enhanced diagnostics are required, add a separate restricted diagnostic sink. Scrub paths, names, quotes, email headers, and exception messages; set explicit access and retention.

## Human review and decision safety

- `score` is an extraction/similarity signal, not truth probability.
- `provisional` is preserved on events.
- supporting/opposing claim buckets are evidence organization, not a contradiction verdict.
- `entity_merge_candidate` is exported, never applied.
- a graph path is connectivity, not causation or authorization.
- `status: complete` describes processing completion, not factual correctness.

For legal, employment, financial, safety, compliance, or investigative consequences, reviewers must inspect the quote in its full original context and follow the applicable authorization process.

## Chain of custody

This example preserves source filename and evidence location but is not a complete chain-of-custody system. If evidentiary integrity matters, the surrounding automation should record:

- authoritative source and acquisition time;
- cryptographic hash of each original and output;
- tool, bridge, DocChrono, Python, and activity versions;
- immutable job/request ID;
- access, transfer, review, and disposition audit records;
- timezone and clock source.

Never claim that the sanitized case can replace originals.

## Secrets

No cloud AI key is required. Orchestrator connection credentials, storage credentials, signing keys, and internal feed tokens may still exist in a production system. Store them in approved credential/secret services, inject only where needed, and never place them in request JSON, source fixtures, XAML defaults, or repository configuration.

## Retention and deletion

Define retention separately for originals, full temporary text, sanitized case, response JSON, review records, logs, and backups. A timeout or failed job can still leave artifacts. Cleanup must be retry-safe, auditable, and blocked by legal hold or preservation requirements.

The repository intentionally does not auto-delete outputs.

## Vulnerability reporting

Follow [the security policy](../SECURITY.md). Do not include real evidence, secrets, personal data, internal hostnames, or sensitive paths in a report. Reproduce against the synthetic corpus where possible.
