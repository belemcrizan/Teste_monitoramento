from __future__ import annotations

from vertice_surveillance.models import LoadManifest
from vertice_surveillance.quality import ALL_SCENARIOS, validate_dataset
from vertice_surveillance.sample_data import build_demo_dataset


def test_demo_reconciles_and_preserves_high_quality_warnings() -> None:
    report = validate_dataset(build_demo_dataset())
    assert report.passed is True
    assert report.record_count == 15
    assert report.fixed_income_record_count == 7
    assert "OTC_VALUATION_PARTIAL" in {item.code for item in report.issues}


def test_duplicate_trade_blocks_all_scenarios() -> None:
    dataset = build_demo_dataset()
    broken = dataset.model_copy(
        update={"trades": dataset.trades + (dataset.trades[0],), "manifest": None}
    )
    report = validate_dataset(broken)
    assert report.passed is False
    assert set(report.blocked_scenarios) == set(ALL_SCENARIOS)


def test_manifest_count_mismatch_fails_closed() -> None:
    dataset = build_demo_dataset()
    assert dataset.manifest is not None
    bad_manifest: LoadManifest = dataset.manifest.model_copy(
        update={"expected_record_count": dataset.manifest.expected_record_count + 1}
    )
    report = validate_dataset(dataset.model_copy(update={"manifest": bad_manifest}))
    assert report.passed is False
    assert "MANIFEST_COUNT_MISMATCH" in {item.code for item in report.issues}


def test_missing_treasury_reference_is_visible_but_not_silently_blocked() -> None:
    dataset = build_demo_dataset().model_copy(update={"fixed_income_references": ()})
    report = validate_dataset(dataset)
    assert report.passed is True
    assert "FIXED_INCOME_REFERENCE_MISSING" in {item.code for item in report.issues}


def test_fixed_income_manifest_mismatch_blocks_treasury_scenarios() -> None:
    dataset = build_demo_dataset()
    assert dataset.manifest is not None
    manifest = dataset.manifest.model_copy(
        update={
            "expected_fixed_income_record_count": (
                dataset.manifest.expected_fixed_income_record_count or 0
            )
            + 1
        }
    )
    report = validate_dataset(dataset.model_copy(update={"manifest": manifest}))
    assert report.passed is False
    assert "FIXED_INCOME_MANIFEST_COUNT_MISMATCH" in {item.code for item in report.issues}
