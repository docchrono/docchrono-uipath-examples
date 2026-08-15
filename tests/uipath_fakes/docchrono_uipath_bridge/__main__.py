"""Synthetic bridge used to prove UiPath rejects inconsistent response envelopes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    mapping = cast("dict[object, object]", value)
    result: dict[str, object] = {}
    for key, item in mapping.items():
        if not isinstance(key, str):
            raise ValueError("expected a JSON object with string keys")
        result[key] = item
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    arguments = parser.parse_args()
    request_path = Path(cast("str", arguments.request))
    response_path = Path(cast("str", arguments.response))
    request = _object(cast("object", json.loads(request_path.read_text(encoding="utf-8"))))
    parameters = _object(request["parameters"])
    mode = parameters["fake_mode"]
    if not isinstance(mode, str):
        raise ValueError("fake_mode must be a string")

    request_id = request["request_id"]
    command = request["command"]
    if not isinstance(request_id, str) or not isinstance(command, str):
        raise ValueError("request_id and command must be strings")

    if mode == "mismatched_request_id":
        response_request_id = "wrong-correlation-id"
        status = "complete"
        exit_code = 0
        result: object = {"synthetic": True}
        warnings: list[object] = []
        errors: list[object] = []
    elif mode == "partial":
        response_request_id = request_id
        status = "partial"
        exit_code = 2
        result = {"synthetic": True}
        warnings = ["Synthetic partial result for XAML validation testing."]
        errors = []
    elif mode == "malformed_result":
        response_request_id = request_id
        status = "complete"
        exit_code = 0
        result = True
        warnings = []
        errors = []
    elif mode == "malformed_warning":
        response_request_id = request_id
        status = "complete"
        exit_code = 0
        result = {"synthetic": True}
        warnings = [{"not": "a string"}]
        errors = []
    elif mode == "malformed_error":
        response_request_id = request_id
        status = "error"
        exit_code = 1
        result = None
        warnings = []
        errors = ["not a structured error"]
    elif mode == "mismatched_exit_status":
        response_request_id = request_id
        status = "partial"
        exit_code = 0
        result = {"synthetic": True}
        warnings = []
        errors = []
    else:
        raise ValueError("unsupported fake_mode")

    response = {
        "command": command,
        "errors": errors,
        "request_id": response_request_id,
        "result": result,
        "schema_version": "1.0",
        "status": status,
        "warnings": warnings,
    }
    response_path.parent.mkdir(parents=True, exist_ok=True)
    response_path.write_text(
        json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"status": status}, separators=(",", ":"), sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
