"""Contract, exit-code, privacy, and failure-path tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from conftest import EXAMPLES, load_object
from docchrono import Case
from docchrono.persistence import SanitizedCaseWarning

import docchrono_uipath_bridge.cli as cli
from docchrono_uipath_bridge import BridgeError, Request, execute
from docchrono_uipath_bridge.contracts import parse_request
from docchrono_uipath_bridge.json_io import MAX_REQUEST_BYTES, read_json


def _write_request(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({}, "INVALID_REQUEST"),
        (
            {
                "schema_version": "2.0",
                "request_id": "bad-version",
                "command": "build_case",
                "parameters": {},
            },
            "UNSUPPORTED_SCHEMA_VERSION",
        ),
        (
            {
                "schema_version": "1.0",
                "request_id": "unknown-command",
                "command": "delete_case",
                "parameters": {},
            },
            "UNKNOWN_COMMAND",
        ),
    ],
)
def test_invalid_requests_have_stable_known_error_codes(
    payload: dict[str, object],
    code: str,
) -> None:
    with pytest.raises(BridgeError) as captured:
        parse_request(payload)
    assert captured.value.code == code


def test_known_cli_error_returns_one_and_writes_error_response(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    _write_request(
        request_path,
        {
            "schema_version": "2.0",
            "request_id": "known-error",
            "command": "build_case",
            "parameters": {},
        },
    )
    assert cli.main(["--request", str(request_path), "--response", str(response_path)]) == 1
    response = load_object(response_path)
    errors = cast("list[dict[str, object]]", response["errors"])
    assert response["status"] == "error"
    assert errors[0]["code"] == "UNSUPPORTED_SCHEMA_VERSION"
    status = cast("dict[str, object]", json.loads(capsys.readouterr().out))
    assert status["response_file"] == "response.json"


def test_partial_build_returns_two_and_a_usable_sanitized_case(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "record.txt").write_text(
        "On March 3, 2026, Maya Chen approved Invoice #381 for Northstar Logistics Corporation.\n",
        encoding="utf-8",
    )
    (source_directory / "unsupported.bin").write_bytes(b"synthetic unsupported input")
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    _write_request(
        request_path,
        {
            "schema_version": "1.0",
            "request_id": "partial-build",
            "command": "build_case",
            "parameters": {
                "source_directory": "source",
                "case_file": "case.docchrono.json",
                "strict": False,
            },
        },
    )
    assert cli.main(["--request", str(request_path), "--response", str(response_path)]) == 2
    response = load_object(response_path)
    assert response["status"] == "partial"
    assert cast("dict[str, object]", response["result"])["failures"]
    assert Case.load(tmp_path / "case.docchrono.json").documents
    assert json.loads(capsys.readouterr().out)["status"] == "partial"


def test_unexpected_error_returns_seventy_without_exception_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    _write_request(
        request_path,
        {
            "schema_version": "1.0",
            "request_id": "unexpected-error",
            "command": "build_case",
            "parameters": {
                "source_directory": ".",
                "case_file": "case.docchrono.json",
            },
        },
    )

    def fail_unexpectedly(_request: Request, *, request_directory: Path) -> object:
        del request_directory
        raise RuntimeError("private diagnostic detail")

    monkeypatch.setattr(cli, "execute", fail_unexpectedly)
    assert cli.main(["--request", str(request_path), "--response", str(response_path)]) == 70
    response_text = response_path.read_text(encoding="utf-8")
    assert "private diagnostic detail" not in response_text
    errors = cast("list[dict[str, object]]", load_object(response_path)["errors"])
    assert errors[0]["code"] == "UNEXPECTED_ERROR"
    assert json.loads(capsys.readouterr().out)["status"] == "error"


def test_request_reader_enforces_limit_on_bytes_actually_read(tmp_path: Path) -> None:
    path = tmp_path / "large.json"
    path.write_bytes(b" " * (MAX_REQUEST_BYTES + 1))
    with pytest.raises(BridgeError) as captured:
        read_json(path)
    assert captured.value.code == "REQUEST_TOO_LARGE"


def test_response_is_sorted_utf8_newline_and_leaves_no_temp_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    _write_request(
        request_path,
        {
            "schema_version": "2.0",
            "request_id": "atomic-response",
            "command": "build_case",
            "parameters": {},
        },
    )
    assert cli.main(["--request", str(request_path), "--response", str(response_path)]) == 1
    raw = response_path.read_bytes()
    assert raw.endswith(b"\n")
    assert raw.startswith(b'{\n  "command"')
    assert not list(tmp_path.glob(".response.json.*.tmp"))
    capsys.readouterr()


def test_review_export_uses_pending_items_not_resolved_history(tmp_path: Path) -> None:
    case = Case.build(EXAMPLES / "data", strict=True)
    pending = case.review.pending
    assert len(pending) == 1
    decision = case.review.accept(pending[0].id, reason="Synthetic pending-queue test")
    reviewed_case = Case(case.data.model_copy(update={"review_decisions": (decision,)}))
    case_path = tmp_path / "reviewed.docchrono.json"
    with pytest.warns(SanitizedCaseWarning):
        reviewed_case.save_sanitized(case_path)
    request = Request(
        request_id="pending-only",
        command="export_review_queue",
        parameters={"case_file": case_path.name},
    )
    outcome = execute(request, request_directory=tmp_path)
    assert outcome.status == "complete"
    assert outcome.result["item_count"] == 0
    assert outcome.result["items"] == []
