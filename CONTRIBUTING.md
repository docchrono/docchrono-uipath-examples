# Contributing

Thank you for improving the DocChrono UiPath examples. Changes should keep the repository executable, deterministic, source-linked, privacy-conscious, and honest about current capabilities.

## Before opening a change

1. Open an issue for a new command, contract change, new dependency, or XAML architecture change.
2. For vulnerabilities, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.
3. Use only synthetic data. Names, organizations, events, identifiers, and email addresses must be invented; use reserved domains such as `.test`.
4. Do not commit `.venv`, generated `artifacts`, real documents, credentials, local absolute paths, or Studio/user caches.

## Development setup

```powershell
git clone https://github.com/docchrono/docchrono-uipath-examples.git
Set-Location .\docchrono-uipath-examples
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r .\requirements-dev.txt
```

Supported development interpreters are CPython 3.11-3.13. Keep `docchrono==0.1.0` unless the change explicitly performs and documents an upgrade.

Only `UiPath/DocChronoUiPathExamples/` is the UiPath project. Keep the root Python bridge, `Examples` fixtures/requests/expected snapshots, `.venv`, tests, and generated `artifacts` physically outside that publish root.

The repository's `.uipath/config.json` disables automatic CLI/tool version synchronization and pins the `1.197` line used for governed validation. Review a CLI-line change explicitly with all XAML, runtime, and package checks; do not let a runner silently upgrade it.

## Required checks

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
npx --yes pyright@1.1.413
```

For XAML or project changes:

1. Restore the exact activity dependencies in the target UiPath Studio version.
2. Open every affected XAML.
3. Run **Analyze File** and the repository's governed **Analyze Project** policy.
4. Run `UiPath/DocChronoUiPathExamples/Main.xaml` against the root synthetic corpus.
5. Verify five response artifacts and expected counts/semantics.
6. Test on a representative Robot environment if runtime behavior changed.

XML well-formedness alone is not UiPath validation.

Public CI tests Python 3.11, 3.12, and 3.13 and runs secret-free static UiPath boundary/XML/response-contract checks. Full Analyzer/compiler/runtime/package validation requires an authenticated UiPath Studio/Robot or governed CI runner; the four `scripts/*uipath*.ps1` checks are the release evidence and must all pass.

## Design rules

- Keep the external-process JSON boundary. Do not introduce shell command construction.
- Use `ProcessStartInfo.ArgumentList`; never concatenate untrusted paths into a command line.
- Requests must remain versioned, bounded, exact-key, and strictly typed.
- Keep the runner's stale-response deletion, 64 MiB response cap, exact correlation validation, and fail-closed partial behavior covered by tests.
- Treat Python's atomic response replacement separately from the runner lifecycle, which can leave no response after deleting stale output.
- Use stable error codes for automation; human-readable messages are not routing keys.
- Preserve evidence quote, source filename, location, polarity, modality, score, and provisional markers where relevant.
- Keep supporting and opposing claims separate.
- Keep traversal order and stored graph direction separate.
- Keep review exports read-only; never auto-merge a candidate.
- Do not treat confidence as truth probability or authorization.
- Do not add a cloud AI requirement.
- Avoid new dependencies unless the benefit and supply-chain/deployment cost are documented.

## Adding or changing a bridge command

A pull request must include:

- contract definition and exact parameter validation;
- complete/partial/error behavior and exit mapping;
- privacy and provenance analysis;
- deterministic unit and integration tests;
- synthetic request/fixture when necessary;
- a focused UiPath XAML example or a clear reason none is needed;
- README, bridge contract, troubleshooting, and example guide updates;
- migration/versioning plan if any existing meaning changes.

Breaking request/response changes require a new schema version. Do not silently reinterpret schema `1.0`.

## Synthetic corpus baseline

With pinned versions, the unchanged six-document corpus yields:

- 6 documents;
- 12 entities;
- 5 events, all dated;
- 16 relationships;
- 10 claims;
- 1 entity merge review candidate;
- 1 `WORKS_FOR` relationship with one supporting and one opposing claim;
- a three-hop Maya Chen to Payment #982 path whose final traversal reverses stored direction.

If a change alters this baseline, explain every intentional difference and update tests/docs together. Count drift is not automatically a regression, but unexplained drift is unacceptable.

## Documentation rules

- Use exact filenames, commands, versions, and verified outputs.
- Keep quick-start commands runnable in PowerShell.
- Link to official UiPath documentation for mutable product behavior.
- Never claim support for OCR, spreadsheets, `.msg`, semantic search, or automatic contradiction detection unless implementation and tests exist.
- Describe the graph as a lightweight typed application ontology, not OWL/RDF/SPARQL.
- State that standard `save_sanitized()` retains quotes and paths/metadata, while this bridge adds path/metadata redaction; neither output is anonymized.

## Pull request scope

Keep changes focused. Do not mix dependency upgrades, fixture rewrites, contract changes, XAML redesign, and formatting unless they are inseparable. Describe:

- user outcome;
- files/contract affected;
- test evidence;
- security/privacy impact;
- compatibility impact;
- rollback path.

By contributing, you agree that your contribution is licensed under the repository's Apache License 2.0.
