"""End-to-end assertions for the five UiPath-facing examples."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import cast

import docchrono
from conftest import EXAMPLES, ROOT, ChainRun, load_object


def test_uses_published_docchrono_release() -> None:
    assert docchrono.__version__ == "0.1.0"


def test_generator_matches_all_committed_synthetic_documents() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_synthetic_data.py"), "--check"],
        check=False,
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "6 deterministic synthetic documents verified" in completed.stdout


def test_all_five_responses_match_committed_snapshots(example_chain: ChainRun) -> None:
    expected_names = {
        "01_build_case.json",
        "02_export_timeline.json",
        "03_export_evidence.json",
        "04_find_path.json",
        "05_export_review_queue.json",
    }
    assert set(example_chain.responses) == expected_names
    for name, actual in example_chain.responses.items():
        assert actual == load_object(EXAMPLES / "expected" / name)


def test_stdout_is_one_small_path_safe_status_record(example_chain: ChainRun) -> None:
    for name, record in example_chain.stdout_records.items():
        assert set(record) == {"command", "request_id", "response_file", "status"}
        assert record["response_file"] == name
        assert record["status"] == "complete"
        assert "/" not in cast("str", record["response_file"])
        assert "\\" not in cast("str", record["response_file"])
        assert len(json.dumps(record)) < 256


def test_case_snapshot_is_sanitized_and_drops_local_source_paths(
    example_chain: ChainRun,
) -> None:
    case_path = example_chain.root / "artifacts" / "case.docchrono.json"
    serialized = case_path.read_text(encoding="utf-8")
    wrapper = load_object(case_path)
    payload = cast("dict[str, object]", wrapper["payload"])
    documents = cast("list[dict[str, object]]", payload["documents"])
    sources = cast("list[dict[str, object]]", payload["source_references"])

    assert wrapper["sanitized"] is True
    assert documents
    assert all(document["raw_text"] == "" for document in documents)
    assert all(document["normalized_text"] == "" for document in documents)
    assert all(source["path"] == source["filename"] for source in sources)
    assert str(example_chain.root) not in serialized
    assert "SYNTHETIC COMPLIANCE RECORD" not in serialized


def test_timeline_uses_all_and_preserves_source_evidence(example_chain: ChainRun) -> None:
    response = example_chain.responses["02_export_timeline.json"]
    result = cast("dict[str, object]", response["result"])
    events = cast("list[dict[str, object]]", result["events"])
    assert result["includes_undated"] is True
    dated_count = cast("int", result["dated_count"])
    undated_count = cast("int", result["undated_count"])
    assert result["total_count"] == dated_count + undated_count
    assert [event["chronology_position"] for event in events] == [1, 2, 3, 4, 5]
    assert all(event["evidence"] for event in events)
    assert events[0]["date"] == "2026-03-03"


def test_evidence_keeps_supporting_and_opposing_claims_separate(
    example_chain: ChainRun,
) -> None:
    response = example_chain.responses["03_export_evidence.json"]
    result = cast("dict[str, object]", response["result"])
    relationships = cast("list[dict[str, object]]", result["relationships"])
    assert result["relationship_count"] == 1
    relationship = relationships[0]
    supporting = cast("list[dict[str, object]]", relationship["supporting_evidence"])
    opposing = cast("list[dict[str, object]]", relationship["opposing_evidence"])
    assert [claim["polarity"] for claim in supporting] == ["AFFIRMED"]
    assert [claim["polarity"] for claim in opposing] == ["NEGATED"]


def test_path_distinguishes_traversal_from_stored_direction(example_chain: ChainRun) -> None:
    response = example_chain.responses["04_find_path.json"]
    result = cast("dict[str, object]", response["result"])
    hops = cast("list[dict[str, object]]", result["hops"])
    assert result["found"] is True
    assert result["hop_count"] == len(hops) == 3
    directions = [
        cast("dict[str, object]", hop["stored_direction"])["matches_traversal"] for hop in hops
    ]
    assert directions == [True, True, False]
    assert hops[0]["supporting_evidence"]
    assert hops[0]["opposing_evidence"]


def test_review_export_is_explicitly_human_only(example_chain: ChainRun) -> None:
    response = example_chain.responses["05_export_review_queue.json"]
    result = cast("dict[str, object]", response["result"])
    items = cast("list[dict[str, object]]", result["items"])
    assert result["item_count"] == 1
    assert "never accepts, rejects, or merges" in cast("str", result["automation_policy"])
    assert items[0]["recommended_action"] == "HUMAN_REVIEW"


def test_responses_never_contain_raw_documents_or_local_paths(example_chain: ChainRun) -> None:
    for response in example_chain.responses.values():
        serialized = json.dumps(response, ensure_ascii=False, sort_keys=True)
        assert "SYNTHETIC COMPLIANCE RECORD" not in serialized
        assert str(example_chain.root) not in serialized
        assert "C:\\" not in serialized
