from __future__ import annotations

from vertice_surveillance.detectors import (
    FixedIncomeMarketConductDetector,
    ObservedParticipationDetector,
    PostTradeMarketResponseDetector,
    PrincipalCustomerConductDetector,
)
from vertice_surveillance.models import EvidenceQuality, FindingDisposition
from vertice_surveillance.quality import validate_dataset
from vertice_surveillance.sample_data import build_demo_dataset


def _context():  # type: ignore[no-untyped-def]
    dataset = build_demo_dataset()
    return dataset, validate_dataset(dataset)


def test_fixed_income_conduct_uses_pu_yield_and_spread() -> None:
    dataset, quality = _context()
    findings = FixedIncomeMarketConductDetector().detect(dataset, quality)
    client = next(item for item in findings if item.subject_id == "CLIENT-FI")
    assert client.disposition == FindingDisposition.ACTIONABLE
    assert "FIXED_INCOME_PRICE_DEVIATION_HIGH" in client.reason_codes
    assert "FIXED_INCOME_YIELD_DEVIATION_HIGH" in client.reason_codes
    assert "FIXED_INCOME_SPREAD_DEVIATION_HIGH" in client.reason_codes


def test_observed_participation_names_denominator_and_coverage() -> None:
    dataset, quality = _context()
    findings = ObservedParticipationDetector().detect(dataset, quality)
    client = next(item for item in findings if item.subject_id == "CLIENT-FI")
    assert client.feature_values["coverage_ratio"] == 0.95
    assert client.feature_values["coverage_universe"] == "REGULATORY_REPORTED"
    assert any("universo observado" in item for item in client.limitations)
    assert not any("MARKET_DOMINANCE" in code for code in client.reason_codes)


def test_missing_coverage_makes_participation_inconclusive() -> None:
    dataset = build_demo_dataset().model_copy(update={"market_coverage": ()})
    quality = validate_dataset(dataset)
    findings = ObservedParticipationDetector().detect(dataset, quality)
    client = next(item for item in findings if item.subject_id == "CLIENT-FI")
    assert client.disposition == FindingDisposition.INCONCLUSIVE
    assert client.evidence_quality == EvidenceQuality.INCONCLUSIVE
    assert "market_coverage_snapshot" in client.missing_data


def test_post_trade_response_is_explicitly_non_causal() -> None:
    dataset, quality = _context()
    findings = PostTradeMarketResponseDetector().detect(dataset, quality)
    client = next(item for item in findings if item.subject_id == "CLIENT-FI")
    assert "REPEATED_ALIGNED_POST_TRADE_RESPONSE" in client.reason_codes
    assert any("não atribui causalidade" in item for item in client.limitations)


def test_principal_customer_signal_preserves_neutrality() -> None:
    dataset, quality = _context()
    findings = PrincipalCustomerConductDetector().detect(dataset, quality)
    client = next(item for item in findings if item.subject_id == "CLIENT-FI")
    assert "TREASURY_PROP_COUNTERPARTY" in client.reason_codes
    assert client.feature_values["max_client_adverse_price_bps"] > 50
    assert any("não prova conflito" in item for item in client.limitations)


def test_missing_reference_returns_inconclusive_instead_of_low_risk() -> None:
    dataset = build_demo_dataset().model_copy(update={"fixed_income_references": ()})
    quality = validate_dataset(dataset)
    conduct = FixedIncomeMarketConductDetector().detect(dataset, quality)
    principal = PrincipalCustomerConductDetector().detect(dataset, quality)
    response = PostTradeMarketResponseDetector().detect(dataset, quality)
    assert next(item for item in conduct if item.subject_id == "CLIENT-FI").disposition == (
        FindingDisposition.INCONCLUSIVE
    )
    assert principal[0].disposition == FindingDisposition.INCONCLUSIVE
    assert response[0].disposition == FindingDisposition.INCONCLUSIVE
