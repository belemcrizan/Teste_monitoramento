"""Utilitários compartilhados; não há score corporativo dentro dos detectores."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def scaled(value: float, threshold: float, ceiling_multiple: float = 2.0) -> float:
    if threshold <= 0:
        raise ValueError("threshold precisa ser positivo")
    return clamp(value / (threshold * ceiling_multiple))


def window(events: Iterable[object], attr: str = "event_time") -> tuple[datetime, datetime]:
    timestamps = [getattr(event, attr) for event in events]
    if not timestamps:
        raise ValueError("não é possível formar janela vazia")
    return min(timestamps), max(timestamps)

