"""Orquestração síncrona do slice vertical reproduzível."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .adapters.local import (
    DeterministicAssistant,
    LocalJsonObjectStore,
    MemoryCaseRepository,
    MemoryEventPublisher,
)
from .cases import CaseManager
from .config import PolicyConfig
from .detectors import (
    ChurningDetector,
    ConcentrationDetector,
    ManipulationBehaviorDetector,
    OtcComplexDetector,
)
from .graph import TemporalGraphEnricher
from .ids import stable_id
from .models import Finding, PipelineRun, SurveillanceDataset
from .ports import EventPublisher, InvestigativeAssistant, ObjectStore
from .quality import validate_dataset
from .risk import CorrelationEngine, RiskPolicy


class SurveillancePipeline:
    version = "1.0.0"

    def __init__(
        self,
        object_store: ObjectStore | None = None,
        event_publisher: EventPublisher | None = None,
        assistant: InvestigativeAssistant | None = None,
        case_manager: CaseManager | None = None,
        policy_config: PolicyConfig | None = None,
    ) -> None:
        self.object_store = object_store or LocalJsonObjectStore()
        self.publisher = event_publisher or MemoryEventPublisher()
        self.assistant = assistant or DeterministicAssistant()
        self.case_manager = case_manager or CaseManager(MemoryCaseRepository(), self.publisher)
        policy = policy_config or PolicyConfig()
        self.detectors = (
            ConcentrationDetector(
                share_threshold=policy.concentration.share_threshold,
                recurring_days_threshold=policy.concentration.recurring_days_threshold,
                symmetry_threshold=policy.concentration.symmetry_threshold,
            ),
            ManipulationBehaviorDetector(
                robust_deviation_threshold=policy.manipulation.robust_deviation_threshold
            ),
            ChurningDetector(
                turnover_threshold=policy.churning.turnover_threshold,
                cost_equity_threshold=policy.churning.cost_equity_threshold,
            ),
            OtcComplexDetector(ipv_z_threshold=policy.otc.ipv_z_threshold),
        )
        self.correlation = CorrelationEngine(
            RiskPolicy(version=policy.policy_version, weights=policy.risk)
        )

    def run(self, dataset: SurveillanceDataset) -> PipelineRun:
        started = datetime.now(UTC)
        run_id = stable_id("RUN", self.version, dataset.snapshot_id, dataset.as_of)
        quality = validate_dataset(dataset)
        findings: list[Finding] = []
        if quality.passed:
            for detector in self.detectors:
                findings.extend(detector.detect(dataset, quality))
            graph = TemporalGraphEnricher(dataset.relationships, dataset.as_of)
            findings = [graph.enrich(item) for item in findings]

        findings.sort(key=lambda item: (item.subject_id, item.scenario, item.finding_id))
        alerts = self.correlation.correlate(findings, dataset.snapshot_id) if findings else []
        cases = []
        for alert in alerts:
            if alert.risk.priority_class not in {"HIGH", "CRITICAL", "INCONCLUSIVE"}:
                continue
            related = [item for item in findings if item.finding_id in alert.finding_ids]
            dossier: dict[str, Any] = {
                "run_id": run_id,
                "snapshot_id": dataset.snapshot_id,
                "alert": alert.model_dump(mode="json"),
                "findings": [item.model_dump(mode="json") for item in related],
                "quality": quality.model_dump(mode="json"),
            }
            evidence_key = f"{run_id}/evidence/{alert.alert_id}"
            evidence_ref = self.object_store.put_json(evidence_key, dossier)
            case = self.case_manager.create_from_alert(alert, evidence_ref)
            cases.append(case)
            try:
                note = self.assistant.summarize(dossier)
            except Exception as error:  # fail-safe: detecção e caso continuam
                note = {
                    "mode": "ASSISTANT_UNAVAILABLE",
                    "executive_summary": "Nota assistiva indisponível; use o dossiê determinístico.",
                    "source_refs": [],
                    "limitations": [type(error).__name__],
                }
            self.object_store.put_json(f"{run_id}/assistant/{case.case_id}", note)

        completed = datetime.now(UTC)
        metrics: dict[str, float | int | str] = {
            "quality_passed": int(quality.passed),
            "trade_count": quality.record_count,
            "finding_count": len(findings),
            "alert_count": len(alerts),
            "case_count": len(cases),
            "inconclusive_finding_count": sum(
                item.disposition.value == "INCONCLUSIVE" for item in findings
            ),
            "scenario_coverage": len({item.scenario for item in findings}),
            "audit_chain_valid": int(self.case_manager.ledger.verify()),
            "duration_ms": round((completed - started).total_seconds() * 1000, 3),
        }
        result = PipelineRun(
            run_id=run_id,
            snapshot_id=dataset.snapshot_id,
            started_at=started,
            completed_at=completed,
            quality=quality,
            findings=tuple(findings),
            alerts=tuple(alerts),
            cases=tuple(cases),
            metrics=metrics,
        )
        self.object_store.put_json(f"{run_id}/run", result.model_dump(mode="json"))
        self.object_store.put_json(
            f"{run_id}/audit",
            [item.model_dump(mode="json") for item in self.case_manager.ledger.records()],
        )
        return result
