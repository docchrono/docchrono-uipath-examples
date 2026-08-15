"""Bounded JSON input and atomic canonical output helpers."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import cast

from docchrono_uipath_bridge.contracts import BridgeError

MAX_REQUEST_BYTES = 1024 * 1024


def read_json(path: Path) -> object:
    """Read one UTF-8 request with an explicit size limit."""

    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise BridgeError(
                "REQUEST_TOO_LARGE",
                f"Request exceeds the {MAX_REQUEST_BYTES}-byte limit.",
            )
    except BridgeError:
        raise
    except FileNotFoundError as error:
        raise BridgeError("REQUEST_NOT_FOUND", "The request file does not exist.") from error
    except OSError as error:
        raise BridgeError("REQUEST_READ_FAILED", "The request file could not be read.") from error
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise BridgeError("INVALID_REQUEST_ENCODING", "The request must be UTF-8.") from error
    try:
        return cast("object", json.loads(text))
    except json.JSONDecodeError as error:
        raise BridgeError("INVALID_JSON", "The request is not valid JSON.") from error


def atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    """Write sorted UTF-8 JSON atomically in the destination directory."""

    content = (
        json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
