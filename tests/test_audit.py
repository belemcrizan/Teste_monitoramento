from __future__ import annotations

from vertice_surveillance.audit import AuditLedger


def test_hash_chain_is_verifiable_and_tamper_evident() -> None:
    ledger = AuditLedger()
    ledger.append("C-1", "CREATED", "system", "SYSTEM", {"state": "OPEN"})
    ledger.append("C-1", "CHANGED", "analyst", "ANALYST", {"state": "INVESTIGATING"})
    assert ledger.verify() is True
    assert ledger.records()[1].previous_hash == ledger.records()[0].record_hash

