# Security policy

## Supported versions

This example repository follows the latest release on the default branch. Security fixes are applied to the current release line; older snapshots are not promised backports.

The integration currently pins DocChrono `0.1.0`, CPython `3.11`-`3.13`, and `UiPath.System.Activities 26.6.1`. A version change is a compatibility and security review, not a routine unbounded dependency update.

## Report a vulnerability privately

Do not open a public issue for a suspected vulnerability. Use GitHub's private vulnerability reporting flow at:

<https://github.com/docchrono/docchrono-uipath-examples/security/advisories/new>

If that form is unavailable, open the repository **Security** tab and select **Report a vulnerability**. Do not send real case data.

Include only:

- affected version/commit;
- operating system, UiPath/Robot version, and Python minor version;
- minimal synthetic reproduction;
- security impact and affected trust boundary;
- suggested mitigation, if known.

Do not include source documents, evidence quotes, response/case files, credentials, tokens, personal data, client or matter names, internal hostnames, or sensitive filesystem paths. Reproduce against `Examples/data` or a newly invented `.test` fixture.

## Expected handling

Maintainers will acknowledge a usable report, validate it privately, assess affected versions, coordinate a fix and disclosure, and credit the reporter if requested and appropriate. Timelines depend on severity, reproducibility, and upstream dependencies.

## Security properties

The bridge:

- uses a shell-free `ProcessStartInfo.ArgumentList` launch;
- caps request JSON at 1 MiB;
- requires UTF-8 and exact schema keys/types;
- atomically replaces response files inside Python where supported; the UiPath runner first deletes stale output, so the full run may leave no response on failure;
- rejects UiPath response envelopes larger than 64 MiB;
- uses stable public errors rather than returning stack traces;
- sets a bounded process timeout in the UiPath workflow;
- discards captured stdout/stderr in the five examples and avoids logging response bodies;
- performs no cloud AI call and requires no AI API key;
- saves a privacy-reduced case that removes raw document text and local absolute paths.

These controls do not authenticate the caller, authorize paths, encrypt storage, sandbox parsers, anonymize evidence, or determine truth.

Only `UiPath/DocChronoUiPathExamples/` is the UiPath project. Keeping the root Python bridge, `.venv`, fixtures, tests, and generated artifacts outside that publish root reduces accidental package inclusion, but deployers must provision and protect those external assets separately.

## Sensitive artifacts

Evidence quotations and source filenames remain in saved cases and JSON responses. Standard DocChrono `Case.save_sanitized()` removes raw document text but still retains evidence quotes and source paths/metadata; this example performs additional path/metadata redaction before sanitized save. Either output remains sensitive, and removing raw text means the saved case alone cannot provide full round-trip verification.

Keep real artifacts out of Git, logs, public issues, CI uploads, screenshots, and unrestricted queues. Use job-specific encrypted storage and organizational retention/incident policies.

## Dependency and deployment reports

Issues caused only by deploying with an unsupported Python version, writable interpreter, runtime public-PyPI install, shared job workspace, elevated Robot identity, or disabled access controls are deployment risks described in the documentation. We still welcome a private report if the repository makes a dangerous deployment appear safe or a documented boundary can be bypassed.

## Scope

In scope:

- request validation bypasses;
- command/path injection through provided XAML or bridge code;
- response-file race or unsafe replacement within the documented threat model;
- leakage of raw text/local paths despite advertised bridge redaction;
- unexpected case mutation by read-only query commands;
- unsafe error/diagnostic disclosure;
- reproducible dependency or workflow configuration vulnerabilities in this repository.

Usually upstream or environment-specific:

- vulnerabilities in DocChrono, UiPath, Python, or parser dependencies with no repository-specific exploit path;
- misconfigured filesystem, Orchestrator, feed, queue, or log permissions;
- malicious documents outside the supported/tested input contract;
- factual errors, extraction quality, or similarity scores without a security impact.

We will coordinate responsibly with upstream maintainers when a report crosses boundaries.
