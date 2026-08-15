"""Strict, dependency-light request and response contracts for the bridge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

BRIDGE_SCHEMA_VERSION = "1.0"

Command = Literal[
    "build_case",
    "export_timeline",
    "export_evidence",
    "find_path",
    "export_review_queue",
]
Status = Literal["complete", "partial"]

_COMMANDS: tuple[Command, ...] = (
    "build_case",
    "export_timeline",
    "export_evidence",
    "find_path",
    "export_review_queue",
)


class BridgeError(Exception):
    """A known integration error safe to return to an unattended workflow."""

    def __init__(self, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


@dataclass(frozen=True, slots=True)
class Request:
    """Validated top-level bridge request."""

    request_id: str
    command: Command
    parameters: dict[str, object]


@dataclass(frozen=True, slots=True)
class Outcome:
    """Successful command result and completion classification."""

    status: Status
    result: dict[str, object]
    warnings: tuple[str, ...] = ()

    @property
    def exit_code(self) -> int:
        """Map the response state to the documented process exit code."""

        return 0 if self.status == "complete" else 2


def parse_request(payload: object) -> Request:
    """Validate an untrusted decoded JSON request without coercion."""

    record = require_object(payload, label="request")
    require_exact_keys(
        record,
        required={"schema_version", "request_id", "command", "parameters"},
        label="request",
    )
    schema_version = require_string(record["schema_version"], label="schema_version")
    if schema_version != BRIDGE_SCHEMA_VERSION:
        raise BridgeError(
            "UNSUPPORTED_SCHEMA_VERSION",
            f"schema_version must be {BRIDGE_SCHEMA_VERSION!r}.",
        )
    request_id = require_string(record["request_id"], label="request_id")
    if len(request_id) > 128:
        raise BridgeError("INVALID_REQUEST", "request_id must contain at most 128 characters.")
    raw_command = require_string(record["command"], label="command")
    if raw_command not in _COMMANDS:
        supported = ", ".join(_COMMANDS)
        raise BridgeError("UNKNOWN_COMMAND", f"command must be one of: {supported}.")
    parameters = require_object(record["parameters"], label="parameters")
    return Request(
        request_id=request_id,
        command=raw_command,
        parameters=parameters,
    )


def require_object(value: object, *, label: str) -> dict[str, object]:
    """Require a JSON object with string keys."""

    if not isinstance(value, dict):
        raise BridgeError("INVALID_REQUEST", f"{label} must be a JSON object.")
    record = cast("dict[object, object]", value)
    if not all(isinstance(key, str) for key in record):
        raise BridgeError("INVALID_REQUEST", f"{label} keys must be strings.")
    return cast("dict[str, object]", record)


def require_string(value: object, *, label: str) -> str:
    """Require a non-empty JSON string."""

    if not isinstance(value, str) or not value.strip():
        raise BridgeError("INVALID_REQUEST", f"{label} must be a non-empty string.")
    return value


def require_bool(value: object, *, label: str) -> bool:
    """Require a JSON boolean without truthiness coercion."""

    if not isinstance(value, bool):
        raise BridgeError("INVALID_REQUEST", f"{label} must be a boolean.")
    return value


def require_exact_keys(
    record: dict[str, object],
    *,
    required: set[str],
    optional: set[str] | None = None,
    label: str,
) -> None:
    """Reject missing and unknown fields so contract changes remain visible."""

    optional_keys = optional or set()
    missing = sorted(required - record.keys())
    unknown = sorted(record.keys() - required - optional_keys)
    if missing:
        raise BridgeError(
            "INVALID_REQUEST",
            f"{label} is missing required field(s): {', '.join(missing)}.",
        )
    if unknown:
        raise BridgeError(
            "INVALID_REQUEST",
            f"{label} contains unsupported field(s): {', '.join(unknown)}.",
        )


def complete_response(request: Request, outcome: Outcome) -> dict[str, object]:
    """Create the stable response envelope for a complete or partial result."""

    return {
        "command": request.command,
        "errors": [],
        "request_id": request.request_id,
        "result": outcome.result,
        "schema_version": BRIDGE_SCHEMA_VERSION,
        "status": outcome.status,
        "warnings": list(outcome.warnings),
    }


def error_response(
    error: BridgeError,
    *,
    request_id: str | None,
    command: str | None,
) -> dict[str, object]:
    """Create a deterministic error envelope without exception or path details."""

    return {
        "command": command,
        "errors": [{"code": error.code, "message": error.public_message}],
        "request_id": request_id,
        "result": None,
        "schema_version": BRIDGE_SCHEMA_VERSION,
        "status": "error",
        "warnings": [],
    }
