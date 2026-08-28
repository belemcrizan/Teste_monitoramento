"""Gates de qualidade e reconciliação antes dos detectores."""

from __future__ import annotations

from collections import Counter

from .models import (
    QualityIssue,
    QualityReport,
    QualitySeverity,
    SurveillanceDataset,
)

ALL_SCENARIOS = ("CONCENTRATION", "MANIPULATION_BEHAVIOR", "CHURNING", "OTC_COMPLEX")


def validate_dataset(dataset: SurveillanceDataset) -> QualityReport:
    issues: list[QualityIssue] = []
    blocked: set[str] = set()
    confirmed = [trade for trade in dataset.trades if trade.status == "CONFIRMED"]
    record_count = len(confirmed)
    gross_notional = sum(trade.notional for trade in confirmed)

    duplicate_ids = sorted(
        trade_id for trade_id, count in Counter(t.trade_id for t in dataset.trades).items() if count > 1
    )
    if duplicate_ids:
        issues.append(
            QualityIssue(
                code="DUPLICATE_TRADE_ID",
                severity=QualitySeverity.CRITICAL,
                message="Há trade_id duplicado; consumo analítico bloqueado.",
                affected_scenarios=ALL_SCENARIOS,
                record_refs=tuple(duplicate_ids),
            )
        )
        blocked.update(ALL_SCENARIOS)

    if dataset.manifest:
        if dataset.manifest.expected_record_count != record_count:
            issues.append(
                QualityIssue(
                    code="MANIFEST_COUNT_MISMATCH",
                    severity=QualitySeverity.CRITICAL,
                    message=(
                        f"Manifesto esperava {dataset.manifest.expected_record_count} registros "
                        f"confirmados, mas foram encontrados {record_count}."
                    ),
                    affected_scenarios=ALL_SCENARIOS,
                )
            )
            blocked.update(ALL_SCENARIOS)
        tolerance = max(0.01, dataset.manifest.expected_gross_notional * 1e-9)
        if abs(dataset.manifest.expected_gross_notional - gross_notional) > tolerance:
            issues.append(
                QualityIssue(
                    code="MANIFEST_NOTIONAL_MISMATCH",
                    severity=QualitySeverity.CRITICAL,
                    message="O financeiro bruto não reconcilia com o manifesto.",
                    affected_scenarios=ALL_SCENARIOS,
                )
            )
            blocked.update(ALL_SCENARIOS)

    known_clients = {client.client_id for client in dataset.clients}
    missing_clients = sorted({trade.client_id for trade in confirmed if trade.client_id not in known_clients})
    if missing_clients:
        affected = ("CONCENTRATION", "CHURNING")
        issues.append(
            QualityIssue(
                code="CLIENT_SNAPSHOT_MISSING",
                severity=QualitySeverity.HIGH,
                message="Há negócios sem snapshot de cliente vigente; cenários dependentes ficam bloqueados.",
                affected_scenarios=affected,
                record_refs=tuple(missing_clients),
            )
        )
        blocked.update(affected)

    if confirmed and not any(trade.reference_price for trade in confirmed):
        issues.append(
            QualityIssue(
                code="MARKET_REFERENCE_MISSING",
                severity=QualitySeverity.HIGH,
                message="Não há referência contemporânea; manipulação pode apenas retornar inconclusivo.",
                affected_scenarios=("MANIPULATION_BEHAVIOR",),
            )
        )

    if dataset.otc_trades and any(item.independent_value is None for item in dataset.otc_trades):
        issues.append(
            QualityIssue(
                code="OTC_VALUATION_PARTIAL",
                severity=QualitySeverity.HIGH,
                message="Há estrutura OTC sem IPV completo; o detector deve falhar de forma inconclusiva.",
                affected_scenarios=("OTC_COMPLEX",),
            )
        )

    return QualityReport(
        snapshot_id=dataset.snapshot_id,
        passed=not any(issue.severity == QualitySeverity.CRITICAL for issue in issues),
        blocked_scenarios=tuple(sorted(blocked)),
        issues=tuple(issues),
        record_count=record_count,
        gross_notional=round(gross_notional, 2),
    )

