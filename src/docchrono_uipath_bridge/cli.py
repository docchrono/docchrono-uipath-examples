"""Process entry point used by UiPath to invoke the DocChrono bridge."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Never, cast

from docchrono_uipath_bridge.bridge import execute
from docchrono_uipath_bridge.contracts import (
    BridgeError,
    complete_response,
    error_response,
    parse_request,
)
from docchrono_uipath_bridge.json_io import atomic_write_json, read_json


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise BridgeError("CLI_ARGUMENT_ERROR", message)


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="python -m docchrono_uipath_bridge",
        description="Execute one versioned DocChrono request and atomically write its response.",
    )
    parser.add_argument("--request", required=True, help="UTF-8 JSON request file")
    parser.add_argument("--response", required=True, help="UTF-8 JSON response file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one request with stable exit codes for UiPath branching."""

    try:
        namespace = _parser().parse_args(argv)
    except BridgeError as error:
        sys.stderr.write(f"{error.code}: {error.public_message}\n")
        return 1

    request_path = Path(cast("str", namespace.request))
    response_path = Path(cast("str", namespace.response))
    request_id: str | None = None
    command: str | None = None
    exit_code = 1
    try:
        if request_path.resolve() == response_path.resolve():
            raise BridgeError(
                "PATH_CONFLICT",
                "The request and response files must be different.",
            )
        payload = read_json(request_path)
        request_id, command = _request_hints(payload)
        request = parse_request(payload)
        request_id = request.request_id
        command = request.command
        outcome = execute(request, request_directory=request_path.parent)
        response = complete_response(request, outcome)
        exit_code = outcome.exit_code
    except BridgeError as error:
        response = error_response(error, request_id=request_id, command=command)
    except Exception:
        response = error_response(
            BridgeError(
                "UNEXPECTED_ERROR",
                "The bridge failed unexpectedly; inspect secure robot logs for diagnostics.",
            ),
            request_id=request_id,
            command=command,
        )
        exit_code = 70

    try:
        atomic_write_json(response_path, response)
    except OSError:
        sys.stderr.write("RESPONSE_WRITE_FAILED: The response file could not be written.\n")
        return 70
    status_record = {
        "command": response["command"],
        "request_id": response["request_id"],
        "response_file": response_path.name,
        "status": response["status"],
    }
    sys.stdout.write(
        json.dumps(status_record, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    )
    return exit_code


def _request_hints(payload: object) -> tuple[str | None, str | None]:
    if not isinstance(payload, dict):
        return None, None
    record = cast("dict[object, object]", payload)
    request_id = record.get("request_id")
    command = record.get("command")
    return (
        request_id if isinstance(request_id, str) else None,
        command if isinstance(command, str) else None,
    )
