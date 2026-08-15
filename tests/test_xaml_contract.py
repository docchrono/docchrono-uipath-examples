"""Static safety assertions over the checked-in UiPath response boundary."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import cast

ROOT = Path(__file__).parents[1]
UIPATH_PROJECT = ROOT / "UiPath" / "DocChronoUiPathExamples"
UI_NAMESPACE = "http://schemas.uipath.com/workflow/activities"


def test_framework_validates_bounded_correlated_response_envelope() -> None:
    root = ET.parse(UIPATH_PROJECT / "Framework" / "RunDocChronoBridge.xaml").getroot()
    invoke_code = root.findall(f".//{{{UI_NAMESPACE}}}InvokeCode")
    validation = next(
        activity
        for activity in invoke_code
        if activity.attrib.get("DisplayName") == "Validate correlated response envelope"
    )
    code = validation.attrib["Code"]
    for field in (
        "schema_version",
        "request_id",
        "command",
        "status",
        "errors",
        "warnings",
        "result",
    ):
        assert f'"{field}"' in code
    assert "67108864" in code
    assert 'expectedStatus = "partial"' in code
    assert "response status does not match the process exit code" in code
    assert "Fail closed on partial result" in ET.tostring(root, encoding="unicode")

    shape_validation = next(
        activity
        for activity in invoke_code
        if activity.attrib.get("DisplayName") == "Validate response value shapes"
    )
    shape_code = shape_validation.attrib["Code"]
    assert "warnings must contain only strings" in shape_code
    assert "error items must be JSON objects" in shape_code
    assert "result must be a JSON object" in shape_code
    assert "exactly code and message" in shape_code


def test_examples_do_not_log_captured_bridge_stdout() -> None:
    for path in sorted((UIPATH_PROJECT / "Examples").glob("*.xaml")):
        text = path.read_text(encoding="utf-8")
        assert "bridgeStatus" not in text
        assert 'x:Key="out_Stdout" />' in text


def test_uipath_publish_excludes_local_and_sensitive_artifacts() -> None:
    project = cast(
        "dict[str, object]",
        json.loads((UIPATH_PROJECT / "project.json").read_text(encoding="utf-8")),
    )
    design_options = cast("dict[str, object]", project["designOptions"])
    process_options = cast("dict[str, object]", design_options["processOptions"])
    assert cast("list[str]", process_options["ignoredFiles"]) == []
    for excluded in (".venv", "artifacts", "src", "tests", "docs", ".github"):
        assert not (UIPATH_PROJECT / excluded).exists()
    assert (ROOT / "src").is_dir()
    assert (ROOT / "Examples" / "data").is_dir()
