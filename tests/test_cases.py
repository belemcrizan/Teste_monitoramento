from __future__ import annotations

import pytest

from vertice_surveillance.adapters.local import MemoryCaseRepository, MemoryEventPublisher
from vertice_surveillance.cases import CaseManager
from vertice_surveillance.models import CaseState
from vertice_surveillance.pipeline import SurveillancePipeline
from vertice_surveillance.sample_data import build_demo_dataset


def _alert():  # type: ignore[no-untyped-def]
    return SurveillancePipeline().correlation.correlate(
        SurveillancePipeline().run(build_demo_dataset()).findings,
        build_demo_dataset().snapshot_id,
    )[0]


def test_case_creation_is_idempotent() -> None:
    manager = CaseManager(MemoryCaseRepository(), MemoryEventPublisher())
    first = manager.create_from_alert(_alert(), "file://evidence.json")
    second = manager.create_from_alert(_alert(), "file://evidence.json")
    assert first.case_id == second.case_id
    assert len(manager.repository.list()) == 1


def test_invalid_transition_is_rejected() -> None:
    manager = CaseManager(MemoryCaseRepository(), MemoryEventPublisher())
    case = manager.create_from_alert(_alert(), "file://evidence.json")
    with pytest.raises(ValueError, match="transição inválida"):
        manager.transition(case.case_id, CaseState.CLOSED, "alice", "REVIEWER", "atalho")


def test_four_eyes_blocks_self_review() -> None:
    manager = CaseManager(MemoryCaseRepository(), MemoryEventPublisher())
    case = manager.create_from_alert(_alert(), "file://evidence.json")
    case = manager.transition(case.case_id, CaseState.INVESTIGATING, "alice", "ANALYST", "início")
    case = manager.transition(case.case_id, CaseState.PENDING_REVIEW, "alice", "ANALYST", "análise pronta")
    with pytest.raises(PermissionError, match="quatro olhos"):
        manager.transition(case.case_id, CaseState.CLOSED, "alice", "REVIEWER", "aprovo")
    closed = manager.transition(case.case_id, CaseState.CLOSED, "bob", "REVIEWER", "revisado")
    assert closed.state == CaseState.CLOSED
    assert closed.reviewer == "bob"
    assert manager.ledger.verify() is True

