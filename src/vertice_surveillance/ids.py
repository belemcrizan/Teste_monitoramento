"""Identificadores determinísticos usados para idempotência e replay."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def stable_id(prefix: str, *parts: object, length: int = 16) -> str:
    """Gera um ID estável a partir de valores serializáveis.

    O mesmo cenário, versão, sujeito, janela e snapshot sempre produz o mesmo ID.
    """

    payload = json.dumps(parts, sort_keys=True, default=str, ensure_ascii=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}-{digest.upper()}"


def canonical_json(value: Mapping[str, Any] | Sequence[Any]) -> str:
    """Serialização canônica para hashing e trilhas de auditoria."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)

