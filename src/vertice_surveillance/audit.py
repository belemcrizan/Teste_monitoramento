"""Ledger append-only com encadeamento de hashes."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from .ids import canonical_json, stable_id
from .models import AuditRecord


class AuditLedger:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def append(
        self,
        aggregate_id: str,
        action: str,
        actor: str,
        actor_role: str,
        payload: dict[str, Any],
        occurred_at: datetime | None = None,
    ) -> AuditRecord:
        timestamp = occurred_at or datetime.now(UTC)
        previous_hash = self._records[-1].record_hash if self._records else "GENESIS"
        body = {
            "aggregate_id": aggregate_id,
            "action": action,
            "actor": actor,
            "actor_role": actor_role,
            "occurred_at": timestamp.isoformat(),
            "payload": payload,
            "previous_hash": previous_hash,
        }
        record_hash = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
        record = AuditRecord(
            audit_id=stable_id("AUD", aggregate_id, action, timestamp, previous_hash),
            aggregate_id=aggregate_id,
            action=action,
            actor=actor,
            actor_role=actor_role,
            occurred_at=timestamp,
            payload=payload,
            previous_hash=previous_hash,
            record_hash=record_hash,
        )
        self._records.append(record)
        return record

    def records(self, aggregate_id: str | None = None) -> list[AuditRecord]:
        if aggregate_id is None:
            return list(self._records)
        return [item for item in self._records if item.aggregate_id == aggregate_id]

    def verify(self) -> bool:
        previous = "GENESIS"
        for record in self._records:
            body = {
                "aggregate_id": record.aggregate_id,
                "action": record.action,
                "actor": record.actor,
                "actor_role": record.actor_role,
                "occurred_at": record.occurred_at.isoformat(),
                "payload": record.payload,
                "previous_hash": previous,
            }
            expected = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
            if record.previous_hash != previous or record.record_hash != expected:
                return False
            previous = record.record_hash
        return True

