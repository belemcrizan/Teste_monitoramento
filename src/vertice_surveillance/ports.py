"""Portas da arquitetura hexagonal.

O núcleo conhece capacidades, não SDKs de cloud. Os adaptadores locais e AWS
implementam estes contratos sem alterar detectores, correlação ou casos.
"""

from __future__ import annotations

from typing import Any, Protocol

from .models import Case


class ObjectStore(Protocol):
    def put_json(self, key: str, value: dict[str, Any] | list[Any]) -> str: ...

    def get_json(self, ref: str) -> dict[str, Any] | list[Any]: ...


class EventPublisher(Protocol):
    def publish(self, event_type: str, payload: dict[str, Any]) -> str: ...


class CaseRepository(Protocol):
    def save(self, case: Case) -> None: ...

    def get(self, case_id: str) -> Case | None: ...

    def list(self) -> list[Case]: ...


class InvestigativeAssistant(Protocol):
    def summarize(self, dossier: dict[str, Any]) -> dict[str, Any]: ...

