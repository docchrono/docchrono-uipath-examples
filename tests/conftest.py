"""Shared end-to-end fixtures for the five committed bridge examples."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

ROOT = Path(__file__).parents[1]
EXAMPLES = ROOT / "Examples"


@dataclass(frozen=True, slots=True)
class ChainRun:
    """Results from executing every committed request through the module CLI."""

    root: Path
    responses: dict[str, dict[str, object]]
    stdout_records: dict[str, dict[str, object]]


def load_object(path: Path) -> dict[str, object]:
    """Read one JSON object for assertions."""

    value = cast("object", json.loads(path.read_text(encoding="utf-8")))
    assert isinstance(value, dict)
    record = cast("dict[object, object]", value)
    assert all(isinstance(key, str) for key in record)
    return cast("dict[str, object]", record)


@pytest.fixture(scope="session")
def example_chain(tmp_path_factory: pytest.TempPathFactory) -> ChainRun:
    """Run the exact committed requests in an isolated, production-like tree."""

    root = tmp_path_factory.mktemp("bridge-chain")
    shutil.copytree(EXAMPLES / "data", root / "Examples" / "data")
    shutil.copytree(EXAMPLES / "requests", root / "Examples" / "requests")
    response_dir = root / "responses"
    responses: dict[str, dict[str, object]] = {}
    stdout_records: dict[str, dict[str, object]] = {}
    for request_path in sorted((root / "Examples" / "requests").glob("*.json")):
        response_path = response_dir / request_path.name
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "docchrono_uipath_bridge",
                "--request",
                str(request_path),
                "--response",
                str(response_path),
            ],
            check=False,
            capture_output=True,
            encoding="utf-8",
            timeout=60,
        )
        assert completed.returncode == 0, completed.stderr
        assert completed.stderr == ""
        stdout_lines = completed.stdout.splitlines()
        assert len(stdout_lines) == 1
        stdout_value = cast("object", json.loads(stdout_lines[0]))
        assert isinstance(stdout_value, dict)
        responses[request_path.name] = load_object(response_path)
        stdout_records[request_path.name] = cast("dict[str, object]", stdout_value)
    return ChainRun(root=root, responses=responses, stdout_records=stdout_records)
