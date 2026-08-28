"""Gates de qualidade e reconciliação antes dos detectores."""

from __future__ import annotations

from collections import Counter

from .models import (
    ActorType,
    QualityIssue,
    QualityReport,
    QualitySeverity,
    SurveillanceDataset,
)

CORE_SCENARIOS = ("CONCENTRATION", "MANIPULATION_BEHAVIOR", "CHURNING", "OTC_COMPLEX")
TREASURY_SCENARIOS = (
    "FIXED_INCOME_CONDUCT",
    "FIXED_INCOME_OBSERVED_PARTICIPATION",
    "FIXED_INCOME_POST_TRADE_RESPONSE",
    "PRINCIPAL_CUSTOMER_CONDUCT",
)
ALL_SCENARIOS = CORE_SCENARIOS + TREASURY_SCENARIOS


def validate_dataset(dataset: SurveillanceDataset) -> QualityReport:
    issues: list[QualityIssue] = []
    blocked: set[str] = set()
    confirmed = [trade for trade in dataset.trades if trade.status == "CONFIRMED"]
    record_count = len(confirmed)
    gross_notional = sum(trade.notional for trade in confirmed)
    confirmed_fixed_income = [
        trade for trade in dataset.fixed_income_trades if trade.status == "CONFIRMED"
    ]
    fixed_income_record_count = len(confirmed_fixed_income)
    fixed_income_financial_value = sum(trade.financial_value for trade in confirmed_fixed_income)

    duplicate_ids = sorted(
        trade_id
        for trade_id, count in Counter(t.trade_id for t in dataset.trades).items()
        if count > 1
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

    duplicate_fixed_income_ids = sorted(
        trade_id
        for trade_id, count in Counter(
            trade.trade_id for trade in dataset.fixed_income_trades
        ).items()
        if count > 1
    )
    if duplicate_fixed_income_ids:
        issues.append(
            QualityIssue(
                code="DUPLICATE_FIXED_INCOME_TRADE_ID",
                severity=QualitySeverity.CRITICAL,
                message="Há trade_id de Renda Fixa duplicado; cenários de Tesouraria bloqueados.",
                affected_scenarios=TREASURY_SCENARIOS,
                record_refs=tuple(duplicate_fixed_income_ids),
            )
        )
        blocked.update(TREASURY_SCENARIOS)

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
        expected_fi_count = dataset.manifest.expected_fixed_income_record_count
        if expected_fi_count is not None and expected_fi_count != fixed_income_record_count:
            issues.append(
                QualityIssue(
                    code="FIXED_INCOME_MANIFEST_COUNT_MISMATCH",
                    severity=QualitySeverity.CRITICAL,
                    message=(
                        f"Manifesto esperava {expected_fi_count} negócios de Renda Fixa, "
                        f"mas foram encontrados {fixed_income_record_count}."
                    ),
                    affected_scenarios=TREASURY_SCENARIOS,
                )
            )
            blocked.update(TREASURY_SCENARIOS)
        expected_fi_value = dataset.manifest.expected_fixed_income_financial_value
        if expected_fi_value is not None:
            fi_tolerance = max(0.01, expected_fi_value * 1e-9)
            if abs(expected_fi_value - fixed_income_financial_value) > fi_tolerance:
                issues.append(
                    QualityIssue(
                        code="FIXED_INCOME_MANIFEST_VALUE_MISMATCH",
                        severity=QualitySeverity.CRITICAL,
                        message="O financeiro de Renda Fixa não reconcilia com o manifesto.",
                        affected_scenarios=TREASURY_SCENARIOS,
                    )
                )
                blocked.update(TREASURY_SCENARIOS)

    known_clients = {client.client_id for client in dataset.clients}
    missing_clients = sorted(
        {trade.client_id for trade in confirmed if trade.client_id not in known_clients}
    )
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

    if confirmed_fixed_income and not dataset.fixed_income_references:
        issues.append(
            QualityIssue(
                code="FIXED_INCOME_REFERENCE_MISSING",
                severity=QualitySeverity.HIGH,
                message=(
                    "Não há referência de Renda Fixa; cenários dependentes devem retornar inconclusivo."
                ),
                affected_scenarios=(
                    "FIXED_INCOME_CONDUCT",
                    "FIXED_INCOME_POST_TRADE_RESPONSE",
                    "PRINCIPAL_CUSTOMER_CONDUCT",
                ),
            )
        )

    if confirmed_fixed_income and not dataset.market_coverage:
        issues.append(
            QualityIssue(
                code="FIXED_INCOME_COVERAGE_MISSING",
                severity=QualitySeverity.HIGH,
                message="O denominador observado não tem declaração de cobertura.",
                affected_scenarios=("FIXED_INCOME_OBSERVED_PARTICIPATION",),
            )
        )

    unknown_actor_trade_ids = sorted(
        trade.trade_id
        for trade in confirmed_fixed_income
        if ActorType.UNKNOWN in {trade.buyer_actor_type, trade.seller_actor_type}
    )
    if unknown_actor_trade_ids:
        issues.append(
            QualityIssue(
                code="FIXED_INCOME_ACTOR_TYPE_UNKNOWN",
                severity=QualitySeverity.HIGH,
                message="Há ponta sem papel econômico resolvido; a análise principal versus cliente é limitada.",
                affected_scenarios=("PRINCIPAL_CUSTOMER_CONDUCT",),
                record_refs=tuple(unknown_actor_trade_ids),
            )
        )

    return QualityReport(
        snapshot_id=dataset.snapshot_id,
        passed=not any(issue.severity == QualitySeverity.CRITICAL for issue in issues),
        blocked_scenarios=tuple(sorted(blocked)),
        issues=tuple(issues),
        record_count=record_count,
        gross_notional=round(gross_notional, 2),
        fixed_income_record_count=fixed_income_record_count,
        fixed_income_financial_value=round(fixed_income_financial_value, 2),
    )
