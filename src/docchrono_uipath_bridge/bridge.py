"""Five deterministic DocChrono commands designed for UiPath process invocation."""

from __future__ import annotations

import json
import warnings
from collections.abc import Iterable
from pathlib import Path

import docchrono
from docchrono import Case
from docchrono.domain import (
    Claim,
    DocumentBuildResult,
    DocumentFailure,
    Entity,
    Event,
    EvidenceSpan,
    Relationship,
    ReviewItem,
    TemporalExpression,
)
from docchrono.errors import BuildFailed, DocChronoError, SourceError

from docchrono_uipath_bridge.contracts import (
    BridgeError,
    Outcome,
    Request,
    Status,
    require_bool,
    require_exact_keys,
    require_string,
)

_SANITIZED_NOTICE = (
    "The saved case omits document raw text and local source paths; evidence quotations remain."
)
_PARTIAL_NOTICE = (
    "DocChrono completed only part of the requested build. Inspect failures before relying on "
    "the output."
)
_HUMAN_REVIEW_POLICY = (
    "Route every item to a qualified human reviewer; this command never accepts, rejects, "
    "or merges findings."
)


def execute(request: Request, *, request_directory: Path) -> Outcome:
    """Execute exactly one validated command against public DocChrono APIs."""

    try:
        if request.command == "build_case":
            return _build_case(request, request_directory=request_directory)
        if request.command == "export_timeline":
            return _export_timeline(request, request_directory=request_directory)
        if request.command == "export_evidence":
            return _export_evidence(request, request_directory=request_directory)
        if request.command == "find_path":
            return _find_path(request, request_directory=request_directory)
        return _export_review_queue(request, request_directory=request_directory)
    except BridgeError:
        raise
    except BuildFailed as error:
        raise BridgeError(
            "BUILD_FAILED",
            "DocChrono could not complete the requested build.",
        ) from error
    except SourceError as error:
        raise BridgeError(
            "SOURCE_UNAVAILABLE",
            "DocChrono could not read a supported source document.",
        ) from error
    except DocChronoError as error:
        raise BridgeError(
            "DOCCHRONO_ERROR",
            "DocChrono rejected the requested operation or case file.",
        ) from error
    except OSError as error:
        raise BridgeError(
            "FILE_OPERATION_FAILED",
            "A requested input or output file could not be accessed.",
        ) from error


def _build_case(request: Request, *, request_directory: Path) -> Outcome:
    parameters = request.parameters
    require_exact_keys(
        parameters,
        required={"source_directory", "case_file"},
        optional={"strict"},
        label="build_case parameters",
    )
    source_value = require_string(parameters["source_directory"], label="source_directory")
    case_value = require_string(parameters["case_file"], label="case_file")
    strict = require_bool(parameters.get("strict", False), label="strict")
    source_directory = _resolve_parameter_path(source_value, request_directory=request_directory)
    case_file = _resolve_parameter_path(case_value, request_directory=request_directory)

    if not source_directory.is_dir():
        raise BridgeError(
            "SOURCE_DIRECTORY_NOT_FOUND",
            "source_directory must identify an existing directory.",
        )
    case = Case.build(source_directory, strict=strict)
    case_file.parent.mkdir(parents=True, exist_ok=True)
    _save_privacy_safe_case(case, case_file)

    result: dict[str, object] = {
        "build_complete": case.report.complete,
        "case_file": case_file.name,
        "counts": {
            "claims": len(case.claims),
            "documents": len(case.documents),
            "entities": len(case.entities),
            "events": len(case.events),
            "relationships": len(case.relationships),
            "review_items": len(case.review_items),
        },
        "docchrono_version": docchrono.__version__,
        "failures": _failure_records(case),
        "privacy": {
            "document_raw_text_saved": False,
            "evidence_quotes_saved": True,
            "local_source_paths_saved": False,
        },
        "strict": strict,
    }
    status = _case_status(case)
    notices = (_SANITIZED_NOTICE,) if status == "complete" else (_SANITIZED_NOTICE, _PARTIAL_NOTICE)
    return Outcome(status=status, result=result, warnings=notices)


def _export_timeline(request: Request, *, request_directory: Path) -> Outcome:
    case = _case_from_parameters(
        request.parameters,
        label="export_timeline parameters",
        request_directory=request_directory,
    )
    source_index = _SourceIndex(case)
    claim_by_id = {claim.id: claim for claim in case.claims}
    entity_by_id = {entity.id: entity for entity in case.entities}
    events: list[dict[str, object]] = []
    dated_ids = {event.id for event in case.timeline.dated}
    for position, event in enumerate(case.timeline.all, start=1):
        evidence = _unique_records(
            _evidence_record(source_index, span)
            for claim_id in event.claim_ids
            if claim_id in claim_by_id
            for span in case.evidence(claim_by_id[claim_id])
        )
        resolved: set[str] = set()
        for temporal in event.temporal:
            value = temporal.start or temporal.end
            if temporal.resolved and value is not None:
                resolved.add(value)
        resolved_values = sorted(resolved)
        events.append(
            {
                "chronology_position": position,
                "date": resolved_values[0] if resolved_values else None,
                "date_status": "dated" if event.id in dated_ids else "undated",
                "evidence": evidence,
                "participants": sorted(
                    entity_by_id[entity_id].canonical_name
                    for entity_id in event.participant_entity_ids
                    if entity_id in entity_by_id
                ),
                "provisional": event.provisional,
                "score": event.score,
                "temporal": [_temporal_record(item) for item in event.temporal],
                "title": event.title,
                "type": event.type.value,
            }
        )
    result: dict[str, object] = {
        "dated_count": len(case.timeline.dated),
        "events": events,
        "includes_undated": True,
        "total_count": len(case.timeline.all),
        "undated_count": len(case.timeline.undated),
    }
    return _case_outcome(case, result)


def _export_evidence(request: Request, *, request_directory: Path) -> Outcome:
    parameters = request.parameters
    require_exact_keys(
        parameters,
        required={"case_file"},
        optional={"relationship_type"},
        label="export_evidence parameters",
    )
    relationship_type: str | None = None
    if "relationship_type" in parameters:
        relationship_type = require_string(
            parameters["relationship_type"],
            label="relationship_type",
        )
    case = _load_case_parameter(parameters, request_directory=request_directory)
    context = _CaseContext(case)
    relationships = [
        _relationship_record(context, relationship)
        for relationship in case.relationships
        if relationship_type is None or relationship.type == relationship_type
    ]
    relationships.sort(key=_record_sort_key)
    result: dict[str, object] = {
        "human_review_notice": (
            "Supporting and opposing source claims are preserved separately; this export does "
            "not decide which claim is true."
        ),
        "relationship_count": len(relationships),
        "relationship_type_filter": relationship_type,
        "relationships": relationships,
    }
    return _case_outcome(case, result)


def _find_path(request: Request, *, request_directory: Path) -> Outcome:
    parameters = request.parameters
    require_exact_keys(
        parameters,
        required={"case_file", "start", "end"},
        label="find_path parameters",
    )
    start = require_string(parameters["start"], label="start")
    end = require_string(parameters["end"], label="end")
    case = _load_case_parameter(parameters, request_directory=request_directory)
    context = _CaseContext(case)
    start_node = context.resolve_node(start)
    end_node = context.resolve_node(end)
    relationships = case.graph.find_path(start_node, end_node)
    if relationships is None:
        result: dict[str, object] = {
            "end": _node_record(end_node),
            "found": False,
            "hop_count": 0,
            "hops": [],
            "start": _node_record(start_node),
        }
        return _case_outcome(case, result)

    cursor_id = start_node.id
    hops: list[dict[str, object]] = []
    for number, relationship in enumerate(relationships, start=1):
        if relationship.source_id == cursor_id:
            next_id = relationship.target_id
        elif relationship.target_id == cursor_id:
            next_id = relationship.source_id
        else:
            raise RuntimeError("DocChrono returned a discontinuous graph path")
        current_node = context.nodes[cursor_id]
        next_node = context.nodes[next_id]
        source_node = context.nodes[relationship.source_id]
        target_node = context.nodes[relationship.target_id]
        supporting = [
            _claim_record(context, context.claims[claim_id])
            for claim_id in relationship.supporting_claim_ids
            if claim_id in context.claims
        ]
        opposing = [
            _claim_record(context, context.claims[claim_id])
            for claim_id in relationship.opposing_claim_ids
            if claim_id in context.claims
        ]
        hops.append(
            {
                "hop": number,
                "opposing_evidence": sorted(opposing, key=_record_sort_key),
                "relationship_type": relationship.type,
                "score": relationship.score,
                "stored_direction": {
                    "matches_traversal": relationship.source_id == cursor_id,
                    "source": _node_record(source_node),
                    "target": _node_record(target_node),
                },
                "supporting_evidence": sorted(supporting, key=_record_sort_key),
                "traversal": {
                    "from": _node_record(current_node),
                    "to": _node_record(next_node),
                },
            }
        )
        cursor_id = next_id
    result = {
        "end": _node_record(end_node),
        "found": True,
        "hop_count": len(hops),
        "hops": hops,
        "start": _node_record(start_node),
    }
    return _case_outcome(case, result)


def _export_review_queue(request: Request, *, request_directory: Path) -> Outcome:
    case = _case_from_parameters(
        request.parameters,
        label="export_review_queue parameters",
        request_directory=request_directory,
    )
    context = _CaseContext(case)
    items = [_review_record(context, item) for item in case.review.pending]
    items.sort(key=_record_sort_key)
    result: dict[str, object] = {
        "automation_policy": _HUMAN_REVIEW_POLICY,
        "item_count": len(items),
        "items": items,
    }
    return _case_outcome(case, result)


def _case_from_parameters(
    parameters: dict[str, object],
    *,
    label: str,
    request_directory: Path,
) -> Case:
    require_exact_keys(parameters, required={"case_file"}, label=label)
    return _load_case_parameter(parameters, request_directory=request_directory)


def _load_case_parameter(
    parameters: dict[str, object],
    *,
    request_directory: Path,
) -> Case:
    case_value = require_string(parameters["case_file"], label="case_file")
    case_file = _resolve_parameter_path(case_value, request_directory=request_directory)
    if not case_file.is_file():
        raise BridgeError("CASE_FILE_NOT_FOUND", "case_file must identify an existing file.")
    return Case.load(case_file)


def _resolve_parameter_path(value: str, *, request_directory: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else request_directory / path


def _save_privacy_safe_case(case: Case, case_file: Path) -> None:
    safe_sources = tuple(
        source.model_copy(update={"metadata": {}, "path": source.filename})
        for source in case.source_references
    )
    safe_report = case.report.model_copy(
        update={
            "documents": tuple(_redact_build_result(item) for item in case.report.documents),
            "failures": tuple(_redact_failure(item) for item in case.report.failures),
            "warnings": (),
        }
    )
    safe_case = Case(
        case.data.model_copy(update={"report": safe_report, "source_references": safe_sources})
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        safe_case.save_sanitized(case_file)


def _redact_build_result(item: DocumentBuildResult) -> DocumentBuildResult:
    return item.model_copy(
        update={
            "failures": tuple(_redact_failure(failure) for failure in item.failures),
            "warnings": (() if not item.warnings else ("Source emitted one or more warnings.",)),
        }
    )


def _redact_failure(item: DocumentFailure) -> DocumentFailure:
    return item.model_copy(update={"message": "DocChrono reported a processing failure."})


def _case_status(case: Case) -> Status:
    return "complete" if case.report.complete else "partial"


def _case_outcome(case: Case, result: dict[str, object]) -> Outcome:
    status = _case_status(case)
    return Outcome(
        status=status,
        result=result,
        warnings=() if status == "complete" else (_PARTIAL_NOTICE,),
    )


def _failure_records(case: Case) -> list[dict[str, object]]:
    sources = {source.id: source.filename for source in case.source_references}
    values = [*case.report.failures]
    values.extend(failure for result in case.report.documents for failure in result.failures)
    records: dict[tuple[str, str, str | None], dict[str, object]] = {
        (
            failure.code.value,
            failure.stage.value,
            sources.get(failure.source_reference_id or ""),
        ): {
            "code": failure.code.value,
            "message": "DocChrono reported a document-processing failure.",
            "source": sources.get(failure.source_reference_id or ""),
            "stage": failure.stage.value,
        }
        for failure in values
    }
    return [records[key] for key in sorted(records, key=lambda item: tuple(str(v) for v in item))]


class _SourceIndex:
    """Resolve evidence provenance to safe document filenames."""

    def __init__(self, case: Case) -> None:
        references = {source.id: source.filename for source in case.source_references}
        self._filenames = {
            document.id: tuple(
                sorted(
                    {
                        references[source_id]
                        for source_id in document.source_reference_ids
                        if source_id in references
                    }
                )
            )
            for document in case.documents
        }

    def filenames(self, document_id: str) -> tuple[str, ...]:
        return self._filenames.get(document_id, ())


class _CaseContext:
    """Read-only indexes used to turn opaque IDs into business-facing records."""

    def __init__(self, case: Case) -> None:
        self.case = case
        self.sources = _SourceIndex(case)
        self.claims = {claim.id: claim for claim in case.claims}
        self.mentions = {mention.id: mention for mention in case.mentions}
        self.entities = {entity.id: entity for entity in case.entities}
        self.events = {event.id: event for event in case.events}
        self.relationships = {item.id: item for item in case.relationships}
        self.documents = {item.id: item for item in case.documents}
        self.source_references = {item.id: item for item in case.source_references}
        self.evidence_spans = {item.id: item for item in case.evidence_spans}
        self.nodes: dict[str, Entity | Event] = {**self.entities, **self.events}

    def resolve_node(self, reference: str) -> Entity | Event:
        if reference in self.nodes:
            return self.nodes[reference]
        candidates = [node for node in self.nodes.values() if reference in _node_names(node)]
        if not candidates:
            raise BridgeError(
                "REFERENCE_NOT_FOUND",
                f"No graph node has the exact name {reference!r}.",
            )
        if len(candidates) > 1:
            raise BridgeError(
                "AMBIGUOUS_REFERENCE",
                f"More than one graph node has the exact name {reference!r}.",
            )
        return candidates[0]


def _relationship_record(
    context: _CaseContext,
    relationship: Relationship,
) -> dict[str, object]:
    supporting = [
        _claim_record(context, context.claims[claim_id])
        for claim_id in relationship.supporting_claim_ids
        if claim_id in context.claims
    ]
    opposing = [
        _claim_record(context, context.claims[claim_id])
        for claim_id in relationship.opposing_claim_ids
        if claim_id in context.claims
    ]
    return {
        "opposing_evidence": sorted(opposing, key=_record_sort_key),
        "relationship_type": relationship.type,
        "score": relationship.score,
        "source": _node_record(context.nodes[relationship.source_id]),
        "supporting_evidence": sorted(supporting, key=_record_sort_key),
        "target": _node_record(context.nodes[relationship.target_id]),
    }


def _claim_record(context: _CaseContext, claim: Claim) -> dict[str, object]:
    participants: list[dict[str, object]] = []
    for participant in claim.participants:
        value: str | None = participant.literal
        if value is None and participant.entity_id in context.entities:
            value = context.entities[participant.entity_id].canonical_name
        if value is None and participant.mention_id in context.mentions:
            value = context.mentions[participant.mention_id].text
        participants.append({"role": participant.role, "value": value})
    participants.sort(key=lambda item: (str(item["role"]), str(item["value"])))
    evidence = _unique_records(
        _evidence_record(context.sources, span) for span in context.case.evidence(claim)
    )
    return {
        "evidence": evidence,
        "kind": claim.kind.value,
        "modality": claim.modality.value,
        "participants": participants,
        "polarity": claim.polarity.value,
        "predicate": claim.predicate,
        "score": claim.score,
        "temporal": [_temporal_record(item) for item in claim.temporal],
    }


def _evidence_record(source_index: _SourceIndex, span: EvidenceSpan) -> dict[str, object]:
    return {
        "location": {
            "field": span.field,
            "page": span.page,
            "paragraph": span.paragraph,
            "raw_end": span.raw_end,
            "raw_start": span.raw_start,
            "sentence": span.sentence,
        },
        "quote": span.quote,
        "sources": list(source_index.filenames(span.document_id)),
    }


def _temporal_record(temporal: TemporalExpression) -> dict[str, object]:
    return {
        "end": temporal.end,
        "is_relative": temporal.is_relative,
        "original_text": temporal.original_text,
        "precision": temporal.precision.value,
        "resolved": temporal.resolved,
        "start": temporal.start,
        "timezone": temporal.timezone,
    }


def _review_record(context: _CaseContext, item: ReviewItem) -> dict[str, object]:
    candidates = [_review_target_record(context, target_id) for target_id in item.target_ids]
    candidates.sort(key=_record_sort_key)
    evidence = [
        _evidence_record(context.sources, context.evidence_spans[span_id])
        for span_id in item.evidence_span_ids
        if span_id in context.evidence_spans
    ]
    return {
        "candidates": candidates,
        "evidence": sorted(evidence, key=_record_sort_key),
        "kind": item.kind,
        "reason": item.reason,
        "recommended_action": "HUMAN_REVIEW",
        "score": item.score,
    }


def _review_target_record(context: _CaseContext, target_id: str) -> dict[str, object]:
    if target_id in context.mentions:
        mention = context.mentions[target_id]
        return {"kind": "mention", "name": mention.text, "type": mention.entity_type.value}
    if target_id in context.entities:
        return _node_record(context.entities[target_id])
    if target_id in context.events:
        return _node_record(context.events[target_id])
    if target_id in context.relationships:
        relationship = context.relationships[target_id]
        source = _node_label(context.nodes[relationship.source_id])
        target = _node_label(context.nodes[relationship.target_id])
        return {
            "kind": "relationship",
            "name": f"{source} --{relationship.type}--> {target}",
            "type": relationship.type,
        }
    if target_id in context.claims:
        claim = context.claims[target_id]
        return {
            "kind": "claim",
            "name": f"{claim.predicate} ({claim.polarity.value})",
            "type": claim.kind.value,
        }
    if target_id in context.source_references:
        return {
            "kind": "source",
            "name": context.source_references[target_id].filename,
            "type": context.source_references[target_id].media_type,
        }
    if target_id in context.documents:
        filenames = context.sources.filenames(target_id)
        return {
            "kind": "document",
            "name": ", ".join(filenames) if filenames else "Document",
            "type": context.documents[target_id].media_type,
        }
    if target_id in context.evidence_spans:
        return {
            "kind": "evidence",
            "name": context.evidence_spans[target_id].quote,
            "type": "quotation",
        }
    return {"kind": "unknown", "name": "Unresolved target", "type": None}


def _node_record(node: Entity | Event) -> dict[str, object]:
    if isinstance(node, Entity):
        return {
            "kind": "entity",
            "name": node.canonical_name,
            "type": node.type.value,
        }
    return {"kind": "event", "name": node.title, "type": node.type.value}


def _node_label(node: Entity | Event) -> str:
    return node.canonical_name if isinstance(node, Entity) else node.title


def _node_names(node: Entity | Event) -> tuple[str, ...]:
    if isinstance(node, Entity):
        return tuple(dict.fromkeys((node.canonical_name, *node.aliases)))
    return (node.title,)


def _unique_records(records: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    by_json: dict[str, dict[str, object]] = {}
    for record in records:
        by_json[_canonical_record(record)] = record
    return [by_json[key] for key in sorted(by_json)]


def _record_sort_key(record: dict[str, object]) -> str:
    return _canonical_record(record)


def _canonical_record(record: dict[str, object]) -> str:
    return json.dumps(record, allow_nan=False, ensure_ascii=False, sort_keys=True)
