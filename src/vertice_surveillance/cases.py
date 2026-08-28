"""Case Manager mínimo com idempotência, estados e regra de quatro olhos."""

from __future__ import annotations

from datetime import UTC, datetime

from .audit import AuditLedger
from .ids import stable_id
from .models import Alert, Case, CaseState
from .ports import CaseRepository, EventPublisher

ALLOWED_TRANSITIONS: dict[CaseState, set[CaseState]] = {
    CaseState.CANDIDATE: {CaseState.SUPPRESSED, CaseState.TRIAGED},
    CaseState.SUPPRESSED: {CaseState.REOPENED},
    CaseState.TRIAGED: {CaseState.OPEN},
    CaseState.OPEN: {CaseState.INVESTIGATING},
    CaseState.INVESTIGATING: {CaseState.AWAITING_EVIDENCE, CaseState.PENDING_REVIEW},
    CaseState.AWAITING_EVIDENCE: {CaseState.INVESTIGATING},
    CaseState.PENDING_REVIEW: {CaseState.CLOSED, CaseState.ESCALATED},
    CaseState.CLOSED: {CaseState.REOPENED},
    CaseState.ESCALATED: {CaseState.INVESTIGATING},
    CaseState.REOPENED: {CaseState.INVESTIGATING},
}


class CaseManager:
    def __init__(
        self,
        repository: CaseRepository,
        publisher: EventPublisher,
        ledger: AuditLedger | None = None,
    ) -> None:
        self.repository = repository
        self.publisher = publisher
        self.ledger = ledger or AuditLedger()

    def create_from_alert(self, alert: Alert, evidence_manifest_ref: str) -> Case:
        case_id = stable_id("C", alert.alert_id, alert.risk.policy_version)
        existing = self.repository.get(case_id)
        if existing:
            return existing
        state = (
            CaseState.AWAITING_EVIDENCE
            if alert.risk.priority_class == "INCONCLUSIVE"
            else CaseState.OPEN
        )
        case = Case(
            case_id=case_id,
            alert_ids=(alert.alert_id,),
            subject_id=alert.subject_id,
            state=state,
            priority=alert.risk.priority,
            evidence_manifest_ref=evidence_manifest_ref,
            policy_version=alert.risk.policy_version,
        )
        self.repository.save(case)
        self.ledger.append(
            aggregate_id=case_id,
            action="CASE_CREATED",
            actor="vertice-system",
            actor_role="SYSTEM",
            payload={"state": state.value, "alert_id": alert.alert_id},
        )
        self.publisher.publish("CaseCreated", case.model_dump(mode="json"))
        return case

    def transition(
        self,
        case_id: str,
        target: CaseState,
        actor: str,
        actor_role: str,
        reason: str,
    ) -> Case:
        current = self.repository.get(case_id)
        if current is None:
            raise KeyError(case_id)
        if target not in ALLOWED_TRANSITIONS.get(current.state, set()):
            raise ValueError(f"transição inválida: {current.state.value} -> {target.value}")
        if not reason.strip():
            raise ValueError("toda transição exige justificativa")

        updates: dict[str, object] = {"state": target, "updated_at": datetime.now(UTC)}
        if target == CaseState.INVESTIGATING and current.investigator is None:
            updates["investigator"] = actor
        if target in {CaseState.CLOSED, CaseState.ESCALATED}:
            if actor_role not in {"REVIEWER", "COMPLIANCE", "SURVEILLANCE_MANAGER"}:
                raise PermissionError("fechamento/escalonamento exige papel de revisão")
            if current.investigator == actor:
                raise PermissionError("regra de quatro olhos: investigador não pode revisar o próprio caso")
            updates["reviewer"] = actor

        updated = current.model_copy(update=updates)
        self.repository.save(updated)
        self.ledger.append(
            aggregate_id=case_id,
            action="CASE_STATE_CHANGED",
            actor=actor,
            actor_role=actor_role,
            payload={"from": current.state.value, "to": target.value, "reason": reason},
        )
        self.publisher.publish(
            "CaseStateChanged",
            {"case_id": case_id, "from": current.state.value, "to": target.value},
        )
        return updated

