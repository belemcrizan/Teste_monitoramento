"""Adaptadores locais determinísticos para demonstração e testes."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

from ..ids import stable_id
from ..models import Case


class LocalJsonObjectStore:
    def __init__(self, root: Path | str = "artifacts") -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise ValueError("chave tenta escapar do diretório de artefatos")
        return candidate.with_suffix(".json") if candidate.suffix != ".json" else candidate

    def put_json(self, key: str, value: dict[str, Any] | list[Any]) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(path)
        return f"file://{path}"

    def get_json(self, ref: str) -> dict[str, Any] | list[Any]:
        path = Path(ref.removeprefix("file://"))
        return cast(
            dict[str, Any] | list[Any],
            json.loads(path.read_text(encoding="utf-8")),
        )


class MemoryEventPublisher:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def publish(self, event_type: str, payload: dict[str, Any]) -> str:
        event_id = stable_id("EVT", event_type, payload)
        self.events.append({"event_id": event_id, "event_type": event_type, "payload": payload})
        return event_id


class MemoryCaseRepository:
    def __init__(self) -> None:
        self._cases: dict[str, Case] = {}

    def save(self, case: Case) -> None:
        self._cases[case.case_id] = case

    def get(self, case_id: str) -> Case | None:
        return self._cases.get(case_id)

    def list(self) -> list[Case]:
        return sorted(self._cases.values(), key=lambda item: item.created_at)


class DeterministicAssistant:
    """Fallback factual que continua funcionando sem LLM."""

    def summarize(self, dossier: dict[str, Any]) -> dict[str, Any]:
        findings = dossier.get("findings", [])
        refs = sorted(
            {
                ref
                for finding in findings
                for ref in finding.get("evidence_refs", [])
            }
        )
        return deepcopy(
            {
                "mode": "DETERMINISTIC_FALLBACK",
                "executive_summary": (
                    f"O dossiê contém {len(findings)} achado(s) técnico(s). "
                    "A conclusão permanece sob responsabilidade humana."
                ),
                "factual_timeline": [],
                "triggered_scenarios": sorted(
                    {finding.get("scenario") for finding in findings if finding.get("scenario")}
                ),
                "supporting_evidence": [
                    {"finding_id": finding.get("finding_id"), "reason_codes": finding.get("reason_codes", [])}
                    for finding in findings
                ],
                "counter_evidence": [],
                "unknowns": sorted(
                    {
                        item
                        for finding in findings
                        for item in finding.get("missing_data", [])
                    }
                ),
                "suggested_next_steps": ["Revisar evidências e contrafatos no Case Manager."],
                "source_refs": refs,
                "limitations": ["Resumo determinístico; nenhuma inferência de culpa ou intenção."],
            }
        )
