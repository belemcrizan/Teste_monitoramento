"""Golden cases sintéticos, transparentes e determinísticos.

Os dados não representam pessoas nem eventos reais. Eles foram desenhados para
exercitar sinais, contrafatos e falhas seguras dos quatro eixos.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime

from .models import (
    ClientSnapshot,
    LoadManifest,
    OtcTrade,
    PositionSnapshot,
    RelationshipEdge,
    Side,
    SurveillanceDataset,
    TradeEvent,
)


def _dt(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, day, hour, minute, tzinfo=UTC)


def _client(
    client_id: str,
    profile: str,
    control: str,
    complexity: int,
    segment: str = "RETAIL",
) -> ClientSnapshot:
    return ClientSnapshot(
        client_id=client_id,
        valid_from=_dt(1, 0),
        segment=segment,
        risk_class="STANDARD",
        suitability_profile=profile,
        objective="CAPITAL_GROWTH" if profile != "CONSERVATIVE" else "CAPITAL_PRESERVATION",
        horizon_days=365,
        control_source=control,  # type: ignore[arg-type]
        complexity_limit=complexity,
    )


def build_demo_dataset() -> SurveillanceDataset:
    trades = (
        # Concentração recorrente e simétrica no universo observado.
        TradeEvent(
            trade_id="T-CONC-01",
            event_time=_dt(26, 14),
            instrument_id="INST-Z",
            client_id="CLIENT-A",
            account_id="ACC-A",
            advisor_id="ADV-1",
            counterparty_id="CP-X",
            side=Side.BUY,
            price=100,
            quantity=500,
            fees=20,
            reference_price=100,
            market_spread=0.5,
        ),
        TradeEvent(
            trade_id="T-CONC-02",
            event_time=_dt(26, 14, 20),
            instrument_id="INST-Z",
            client_id="CLIENT-A",
            account_id="ACC-A",
            advisor_id="ADV-1",
            counterparty_id="CP-X",
            side=Side.SELL,
            price=100.1,
            quantity=1_000,
            fees=20,
            reference_price=100,
            market_spread=0.5,
        ),
        TradeEvent(
            trade_id="T-CONC-03",
            event_time=_dt(27, 13),
            instrument_id="INST-Z",
            client_id="CLIENT-A",
            account_id="ACC-A",
            advisor_id="ADV-1",
            counterparty_id="CP-X",
            side=Side.BUY,
            price=99.9,
            quantity=500,
            fees=20,
            reference_price=100,
            market_spread=0.5,
        ),
        TradeEvent(
            trade_id="T-CONC-04",
            event_time=_dt(27, 13, 15),
            instrument_id="INST-Z",
            client_id="CLIENT-A",
            account_id="ACC-A",
            advisor_id="ADV-1",
            counterparty_id="CP-X",
            side=Side.SELL,
            price=100,
            quantity=1_000,
            fees=20,
            reference_price=100,
            market_spread=0.5,
        ),
        # Janela de fechamento: desvio + direção + participação + posição beneficiada.
        TradeEvent(
            trade_id="T-MANIP-01",
            event_time=_dt(28, 16, 50),
            instrument_id="INST-Z",
            client_id="CLIENT-A",
            account_id="ACC-A",
            advisor_id="ADV-1",
            counterparty_id="CP-X",
            side=Side.BUY,
            price=104.8,
            quantity=500,
            fees=25,
            reference_price=100,
            market_spread=0.5,
            position_before=10_000,
        ),
        TradeEvent(
            trade_id="T-MANIP-02",
            event_time=_dt(28, 16, 56),
            instrument_id="INST-Z",
            client_id="CLIENT-A",
            account_id="ACC-A",
            advisor_id="ADV-1",
            counterparty_id="CP-X",
            side=Side.BUY,
            price=105.2,
            quantity=500,
            fees=25,
            reference_price=100,
            market_spread=0.5,
            position_before=10_500,
        ),
        # Fluxo comparável para tornar o denominador explícito.
        TradeEvent(
            trade_id="T-COHORT-01",
            event_time=_dt(28, 16, 52),
            instrument_id="INST-Z",
            client_id="CLIENT-B",
            account_id="ACC-B",
            advisor_id="ADV-1",
            counterparty_id="CP-Y",
            side=Side.SELL,
            price=100.2,
            quantity=500,
            fees=10,
            reference_price=100,
            market_spread=0.5,
        ),
        # Atividade potencialmente excessiva: volume/equity, custo e reversões rápidas.
        *tuple(
            TradeEvent(
                trade_id=f"T-CHURN-{index:02d}",
                event_time=_dt(index, 12),
                instrument_id="INST-X",
                client_id="CLIENT-C",
                account_id="ACC-C",
                advisor_id="ADV-2",
                counterparty_id=None,
                side=Side.BUY if index % 2 else Side.SELL,
                price=100,
                quantity=1_000,
                fees=3_000,
                reference_price=100,
                market_spread=0.4,
            )
            for index in range(1, 9)
        ),
    )
    positions = (
        PositionSnapshot(
            account_id="ACC-A",
            client_id="CLIENT-A",
            instrument_id="INST-Z",
            as_of_time=_dt(28, 16),
            quantity=10_000,
            market_value=1_000_000,
            average_equity=2_000_000,
        ),
        PositionSnapshot(
            account_id="ACC-B",
            client_id="CLIENT-B",
            instrument_id="INST-Z",
            as_of_time=_dt(28, 16),
            quantity=-500,
            market_value=-50_000,
            average_equity=1_000_000,
        ),
        PositionSnapshot(
            account_id="ACC-C",
            client_id="CLIENT-C",
            instrument_id="INST-X",
            as_of_time=_dt(28, 16),
            quantity=0,
            market_value=0,
            average_equity=100_000,
        ),
    )
    clients = (
        _client("CLIENT-A", "MODERATE", "ADVISOR", 3),
        _client("CLIENT-B", "MODERATE", "CLIENT", 3),
        _client("CLIENT-C", "CONSERVATIVE", "UNKNOWN", 1),
        _client("CLIENT-D", "CONSERVATIVE", "ADVISOR", 1),
        _client("CLIENT-E", "SOPHISTICATED", "CLIENT", 5, segment="PRIVATE"),
    )
    otc_trades = (
        OtcTrade(
            structure_id="OTC-STRUCT-001",
            client_id="CLIENT-D",
            advisor_id="ADV-3",
            event_time=_dt(28, 15),
            underlying_id="IBOV",
            strategy_chain_id="CHAIN-OTC-1",
            notional=2_500_000,
            trade_premium=180_000,
            independent_value=100_000,
            model_uncertainty=10_000,
            liquidity_band=15_000,
            model_id="LOCAL_VOL",
            model_version="2.1.0",
            market_snapshot_id="MKT-20260828-1500",
            product_complexity=4,
            rolled_from="OTC-STRUCT-000",
        ),
        OtcTrade(
            structure_id="OTC-STRUCT-002",
            client_id="CLIENT-E",
            advisor_id="ADV-4",
            event_time=_dt(28, 15, 10),
            underlying_id="USD-BRL",
            strategy_chain_id="CHAIN-OTC-2",
            notional=1_000_000,
            trade_premium=50_000,
            independent_value=None,
            model_uncertainty=None,
            liquidity_band=8_000,
            product_complexity=5,
        ),
    )
    relationships = (
        RelationshipEdge(
            from_id="CLIENT-A",
            to_id="ADV-1",
            relation_type="ADVISED_BY",
            valid_from=_dt(1, 0),
            observed_at=_dt(28, 20),
            source="CRM",
            confidence=1,
        ),
        RelationshipEdge(
            from_id="CLIENT-B",
            to_id="ADV-1",
            relation_type="ADVISED_BY",
            valid_from=_dt(1, 0),
            observed_at=_dt(28, 20),
            source="CRM",
            confidence=1,
        ),
        RelationshipEdge(
            from_id="CLIENT-A",
            to_id="GROUP-G1",
            relation_type="BELONGS_TO_GROUP",
            valid_from=_dt(1, 0),
            observed_at=_dt(28, 20),
            source="KYC",
            confidence=1,
        ),
        RelationshipEdge(
            from_id="CLIENT-D",
            to_id="ADV-3",
            relation_type="ADVISED_BY",
            valid_from=_dt(1, 0),
            observed_at=_dt(28, 20),
            source="CRM",
            confidence=1,
        ),
    )
    gross_notional = sum(trade.notional for trade in trades)
    manifest = LoadManifest(
        source_system="SYNTHETIC_GOLDEN_CASES",
        source_extract_id="DEMO-20260828",
        contract_version="1.0.0",
        business_date=date(2026, 8, 28),
        expected_record_count=len(trades),
        expected_gross_notional=gross_notional,
        sha256=hashlib.sha256(b"vertice-demo-20260828").hexdigest(),
    )
    return SurveillanceDataset(
        snapshot_id="SNAPSHOT-DEMO-20260828",
        as_of=_dt(28, 23, 59),
        trades=trades,
        positions=positions,
        clients=clients,
        otc_trades=otc_trades,
        relationships=relationships,
        manifest=manifest,
    )


def build_benign_dataset() -> SurveillanceDataset:
    trades = (
        TradeEvent(
            trade_id="T-BENIGN-01",
            event_time=_dt(28, 11),
            instrument_id="LIQUID-ETF",
            client_id="CLIENT-BENIGN",
            account_id="ACC-BENIGN",
            counterparty_id="CP-1",
            side=Side.BUY,
            price=100,
            quantity=10,
            fees=1,
            reference_price=100,
            market_spread=0.1,
        ),
        TradeEvent(
            trade_id="T-BENIGN-02",
            event_time=_dt(28, 12),
            instrument_id="LIQUID-ETF",
            client_id="CLIENT-BENIGN",
            account_id="ACC-BENIGN",
            counterparty_id="CP-2",
            side=Side.SELL,
            price=100.05,
            quantity=5,
            fees=1,
            reference_price=100,
            market_spread=0.1,
        ),
    )
    client = _client("CLIENT-BENIGN", "MODERATE", "CLIENT", 3)
    position = PositionSnapshot(
        account_id="ACC-BENIGN",
        client_id="CLIENT-BENIGN",
        instrument_id="LIQUID-ETF",
        as_of_time=_dt(28, 16),
        quantity=5,
        market_value=500,
        average_equity=1_000_000,
    )
    return SurveillanceDataset(
        snapshot_id="SNAPSHOT-BENIGN-20260828",
        as_of=_dt(28, 23, 59),
        trades=trades,
        clients=(client,),
        positions=(position,),
    )

