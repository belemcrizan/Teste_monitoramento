"""Representação neutra das pontas de um negócio de Tesouraria."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import ActorType, FixedIncomeTrade, Side


@dataclass(frozen=True, slots=True)
class PartyView:
    party_id: str
    actor_type: ActorType
    side: Side
    counterparty_id: str
    counterparty_actor_type: ActorType


MONITORED_ACTOR_TYPES = {
    ActorType.CLIENT,
    ActorType.TREASURY_PROP,
    ActorType.RELATED_PARTY,
}


def party_views(trade: FixedIncomeTrade) -> tuple[PartyView, ...]:
    views = (
        PartyView(
            party_id=trade.buyer_party_id,
            actor_type=trade.buyer_actor_type,
            side=Side.BUY,
            counterparty_id=trade.seller_party_id,
            counterparty_actor_type=trade.seller_actor_type,
        ),
        PartyView(
            party_id=trade.seller_party_id,
            actor_type=trade.seller_actor_type,
            side=Side.SELL,
            counterparty_id=trade.buyer_party_id,
            counterparty_actor_type=trade.buyer_actor_type,
        ),
    )
    return tuple(item for item in views if item.actor_type in MONITORED_ACTOR_TYPES)


def client_view(trade: FixedIncomeTrade) -> PartyView | None:
    return next((item for item in party_views(trade) if item.actor_type == ActorType.CLIENT), None)
