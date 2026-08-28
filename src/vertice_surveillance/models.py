"""Contratos canônicos e objetos de domínio do VÉRTICE."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class EvidenceQuality(StrEnum):
    COMPLETE = "COMPLETE"
    DEGRADED = "DEGRADED"
    INCONCLUSIVE = "INCONCLUSIVE"


class FindingDisposition(StrEnum):
    ACTIONABLE = "ACTIONABLE"
    OBSERVATION = "OBSERVATION"
    INCONCLUSIVE = "INCONCLUSIVE"


class QualitySeverity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    INFO = "INFO"


class CaseState(StrEnum):
    CANDIDATE = "CANDIDATE"
    SUPPRESSED = "SUPPRESSED"
    TRIAGED = "TRIAGED"
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    AWAITING_EVIDENCE = "AWAITING_EVIDENCE"
    PENDING_REVIEW = "PENDING_REVIEW"
    CLOSED = "CLOSED"
    ESCALATED = "ESCALATED"
    REOPENED = "REOPENED"


class ActorType(StrEnum):
    CLIENT = "CLIENT"
    TREASURY_PROP = "TREASURY_PROP"
    RELATED_PARTY = "RELATED_PARTY"
    INSTITUTION = "INSTITUTION"
    MARKET_MAKER = "MARKET_MAKER"
    BROKER = "BROKER"
    UNKNOWN = "UNKNOWN"


class ExecutionCapacity(StrEnum):
    AGENCY = "AGENCY"
    PRINCIPAL = "PRINCIPAL"
    RISKLESS_PRINCIPAL = "RISKLESS_PRINCIPAL"
    UNKNOWN = "UNKNOWN"


class FixedIncomeProduct(StrEnum):
    DEBENTURE = "DEBENTURE"
    LF = "LF"
    CRI_CRA = "CRI_CRA"
    GOVERNMENT_BOND = "GOVERNMENT_BOND"
    OTHER = "OTHER"


class CoverageUniverse(StrEnum):
    INTERNAL_OBSERVED = "INTERNAL_OBSERVED"
    REGULATORY_REPORTED = "REGULATORY_REPORTED"
    VENUE_COMPLETE = "VENUE_COMPLETE"


class TradeEvent(FrozenModel):
    trade_id: str
    event_time: datetime
    source_update_time: datetime | None = None
    ingest_time: datetime | None = None
    venue: str = "B3"
    instrument_id: str
    client_id: str
    account_id: str
    advisor_id: str | None = None
    counterparty_id: str | None = None
    side: Side
    price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    fees: float = Field(default=0, ge=0)
    reference_price: float | None = Field(default=None, gt=0)
    market_spread: float | None = Field(default=None, ge=0)
    position_before: float | None = None
    order_id: str | None = None
    status: Literal["CONFIRMED", "CANCELLED", "CORRECTED"] = "CONFIRMED"

    @field_validator("event_time", "source_update_time", "ingest_time")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamps devem conter timezone")
        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def notional(self) -> float:
        return self.price * self.quantity


class FixedIncomeTrade(FrozenModel):
    """Negócio de Renda Fixa com as duas pontas e capacidade econômica explícitas."""

    trade_id: str
    event_time: datetime
    source_update_time: datetime | None = None
    ingest_time: datetime | None = None
    instrument_id: str
    product_type: FixedIncomeProduct
    issuer_id: str | None = None
    buyer_party_id: str
    buyer_actor_type: ActorType
    seller_party_id: str
    seller_actor_type: ActorType
    buyer_account_id: str | None = None
    seller_account_id: str | None = None
    execution_capacity: ExecutionCapacity = ExecutionCapacity.UNKNOWN
    desk_id: str | None = None
    book_id: str | None = None
    trader_id: str | None = None
    price_unit: float = Field(gt=0)
    quantity: float = Field(gt=0)
    financial_value: float = Field(gt=0)
    yield_rate: float | None = Field(default=None, gt=-1)
    spread_bps: float | None = None
    duration_years: float | None = Field(default=None, gt=0)
    dv01: float | None = Field(default=None, gt=0)
    currency: str = "BRL"
    source_system: str = "TREASURY_LEDGER"
    status: Literal["CONFIRMED", "CANCELLED", "CORRECTED"] = "CONFIRMED"

    @field_validator("event_time", "source_update_time", "ingest_time")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamps devem conter timezone")
        return value


class FixedIncomeReference(FrozenModel):
    """Referência contemporânea e versionada para um instrumento de Renda Fixa."""

    reference_id: str
    instrument_id: str
    product_type: FixedIncomeProduct
    reference_time: datetime
    source: str
    methodology_version: str
    price_unit: float | None = Field(default=None, gt=0)
    yield_rate: float | None = Field(default=None, gt=-1)
    spread_bps: float | None = None
    benchmark_curve_id: str | None = None
    duration_years: float | None = Field(default=None, gt=0)
    dv01: float | None = Field(default=None, gt=0)
    liquidity_band_bps: float | None = Field(default=None, gt=0)
    freshness_seconds: int = Field(default=0, ge=0)
    confidence: float = Field(default=1, ge=0, le=1)

    @field_validator("reference_time")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamps devem conter timezone")
        return value

    @model_validator(mode="after")
    def require_observable(self) -> FixedIncomeReference:
        if self.price_unit is None and self.yield_rate is None and self.spread_bps is None:
            raise ValueError("referência exige PU, taxa ou spread")
        return self


class MarketCoverageSnapshot(FrozenModel):
    """Declara o denominador e sua cobertura; não transforma amostra em market share."""

    instrument_id: str
    window_start: datetime
    window_end: datetime
    source: str
    universe: CoverageUniverse
    coverage_ratio: float = Field(ge=0, le=1)
    observed_record_count: int = Field(ge=0)
    expected_record_count: int | None = Field(default=None, ge=0)

    @field_validator("window_start", "window_end")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamps devem conter timezone")
        return value

    @model_validator(mode="after")
    def validate_window(self) -> MarketCoverageSnapshot:
        if self.window_end < self.window_start:
            raise ValueError("window_end deve ser posterior a window_start")
        return self


class OrderEvent(FrozenModel):
    order_id: str
    sequence: int = Field(ge=0)
    event_type: Literal["NEW", "AMEND", "CANCEL", "PARTIAL_FILL", "FILL"]
    event_time: datetime
    receive_time: datetime
    instrument_id: str
    client_id: str
    account_id: str
    side: Side
    price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    visible_quantity: float | None = Field(default=None, ge=0)


class PositionSnapshot(FrozenModel):
    account_id: str
    client_id: str
    instrument_id: str
    as_of_time: datetime
    quantity: float
    market_value: float
    average_equity: float = Field(gt=0)
    source: str = "POSITION_SYSTEM"


class ClientSnapshot(FrozenModel):
    client_id: str
    valid_from: datetime
    valid_to: datetime | None = None
    segment: str
    risk_class: str
    economic_group: str | None = None
    beneficial_owner_id: str | None = None
    suitability_profile: str
    objective: str
    horizon_days: int = Field(gt=0)
    control_source: Literal["CLIENT", "ADVISOR", "DISCRETIONARY", "UNKNOWN"]
    complexity_limit: int = Field(default=1, ge=1, le=5)


class MarketReference(FrozenModel):
    instrument_id: str
    reference_time: datetime
    bid: float | None = Field(default=None, gt=0)
    ask: float | None = Field(default=None, gt=0)
    mid: float = Field(gt=0)
    robust_dispersion: float = Field(gt=0)
    source: str
    freshness_seconds: int = Field(ge=0)


class OtcTrade(FrozenModel):
    structure_id: str
    client_id: str
    advisor_id: str | None = None
    event_time: datetime
    underlying_id: str
    strategy_chain_id: str | None = None
    notional: float = Field(gt=0)
    trade_premium: float
    independent_value: float | None = None
    model_uncertainty: float | None = Field(default=None, gt=0)
    liquidity_band: float | None = Field(default=None, gt=0)
    model_id: str | None = None
    model_version: str | None = None
    market_snapshot_id: str | None = None
    product_complexity: int = Field(default=3, ge=1, le=5)
    rolled_from: str | None = None


class RelationshipEdge(FrozenModel):
    from_id: str
    to_id: str
    relation_type: str
    valid_from: datetime
    valid_to: datetime | None = None
    observed_at: datetime
    source: str
    confidence: float = Field(ge=0, le=1)
    resolution_method: str = "DETERMINISTIC"


class LoadManifest(FrozenModel):
    source_system: str
    source_extract_id: str
    contract_version: str
    business_date: date
    expected_record_count: int = Field(ge=0)
    expected_gross_notional: float = Field(ge=0)
    expected_fixed_income_record_count: int | None = Field(default=None, ge=0)
    expected_fixed_income_financial_value: float | None = Field(default=None, ge=0)
    sha256: str


class SurveillanceDataset(FrozenModel):
    snapshot_id: str
    as_of: datetime
    trades: tuple[TradeEvent, ...] = ()
    orders: tuple[OrderEvent, ...] = ()
    positions: tuple[PositionSnapshot, ...] = ()
    clients: tuple[ClientSnapshot, ...] = ()
    market_references: tuple[MarketReference, ...] = ()
    otc_trades: tuple[OtcTrade, ...] = ()
    fixed_income_trades: tuple[FixedIncomeTrade, ...] = ()
    fixed_income_references: tuple[FixedIncomeReference, ...] = ()
    market_coverage: tuple[MarketCoverageSnapshot, ...] = ()
    relationships: tuple[RelationshipEdge, ...] = ()
    manifest: LoadManifest | None = None


class QualityIssue(FrozenModel):
    code: str
    severity: QualitySeverity
    message: str
    affected_scenarios: tuple[str, ...] = ()
    record_refs: tuple[str, ...] = ()


class QualityReport(FrozenModel):
    snapshot_id: str
    passed: bool
    blocked_scenarios: tuple[str, ...]
    issues: tuple[QualityIssue, ...]
    record_count: int
    gross_notional: float
    fixed_income_record_count: int = 0
    fixed_income_financial_value: float = 0


FeatureValue = float | int | str | bool | None


class Finding(FrozenModel):
    finding_id: str
    scenario: str
    scenario_version: str
    subject_id: str
    subject_type: str
    window_start: datetime
    window_end: datetime
    strength: float = Field(ge=0, le=1)
    materiality: float = Field(ge=0, le=1)
    urgency: float = Field(ge=0, le=1)
    evidence_quality: EvidenceQuality
    disposition: FindingDisposition
    reason_codes: tuple[str, ...]
    feature_values: dict[str, FeatureValue]
    evidence_refs: tuple[str, ...]
    missing_data: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RiskExplanation(FrozenModel):
    priority: float = Field(ge=0, le=100)
    priority_class: Literal["OBSERVATION", "TRIAGE", "HIGH", "CRITICAL", "INCONCLUSIVE"]
    components: dict[str, float]
    interactions: tuple[str, ...]
    policy_version: str
    explanation: tuple[str, ...]


class Alert(FrozenModel):
    alert_id: str
    subject_id: str
    finding_ids: tuple[str, ...]
    scenarios: tuple[str, ...]
    risk: RiskExplanation
    status: str = "TRIAGED"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Case(FrozenModel):
    case_id: str
    alert_ids: tuple[str, ...]
    subject_id: str
    state: CaseState
    priority: float = Field(ge=0, le=100)
    owner: str | None = None
    evidence_manifest_ref: str
    policy_version: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    investigator: str | None = None
    reviewer: str | None = None


class AuditRecord(FrozenModel):
    audit_id: str
    aggregate_id: str
    action: str
    actor: str
    actor_role: str
    occurred_at: datetime
    payload: dict[str, Any]
    previous_hash: str
    record_hash: str


class PipelineRun(FrozenModel):
    run_id: str
    snapshot_id: str
    started_at: datetime
    completed_at: datetime
    quality: QualityReport
    findings: tuple[Finding, ...]
    alerts: tuple[Alert, ...]
    cases: tuple[Case, ...]
    metrics: dict[str, float | int | str]
