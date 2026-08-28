# Contratos de dados

## Regra geral

Todo input precisa declarar granularidade, owner, chave, unidade, timezone, semântica de nulo, vigência, política de atraso e classificação de sensibilidade. Os modelos Pydantic rejeitam campos extras e valores estruturalmente inválidos.

## Contratos implementados

| Contrato | Granularidade | Campos centrais |
|---|---|---|
| `TradeEvent` | uma execução/negócio | IDs, quatro tempos opcionais, venue, instrumento, conta, cliente, contraparte, lado, preço, quantidade, fees, referência |
| `OrderEvent` | uma mudança da ordem | order, sequence, tipo, event/receive time, lado, preço e quantidades |
| `PositionSnapshot` | conta × instrumento × instante | quantidade, market value, patrimônio médio |
| `ClientSnapshot` | cliente × vigência | segmento, perfil, objetivo, controle, limite de complexidade |
| `MarketReference` | instrumento × instante | bid/ask/mid, dispersão, source, freshness |
| `OtcTrade` | estrutura × negócio | prêmio, IPV, incerteza, liquidity band, modelo, snapshot, complexidade e cadeia |
| `RelationshipEdge` | relação × vigência | origem/destino, tipo, valid from/to, source, confiança e método |
| `LoadManifest` | extração/carga | contagem, financeiro, data, versão de contrato e SHA-256 |

## Tempos

O contrato separa:

- `event_time`: quando o fato econômico ocorreu;
- `source_update_time`: quando a origem registrou/corrigiu;
- `ingest_time`: quando a plataforma recebeu;
- tempo de processamento: registrado no `PipelineRun`.

Timestamps de eventos precisam conter timezone. Cadastro e relacionamentos possuem `valid_from`/`valid_to`; enriquecimento usa somente arestas vigentes no `as_of`.

## Nulos e dados ausentes

Nulo não significa zero.

| Dado ausente | Tratamento |
|---|---|
| referência de mercado | manipulação fica inconclusiva quando o padrão depende dela |
| patrimônio médio | churning fica inconclusivo |
| IPV/modelo/snapshot | OTC retorna `INCONCLUSIVE_VALUATION` |
| snapshot do cliente | cenários dependentes são bloqueados pelo quality gate |
| contraparte | o negócio não participa da métrica relacional por par |

## Manifesto e reconciliação

O quality gate compara:

- record count de negócios confirmados;
- financeiro bruto derivado de `price × quantity`;
- duplicidade de `trade_id`;
- integridade mínima de snapshots;
- presença de referências críticas.

Divergência do manifesto ou duplicidade crítica bloqueia todos os detectores. Warnings de cobertura podem permitir execução degradada quando o próprio detector possui caminho inconclusivo.

## Finding

O contrato de saída inclui:

```json
{
  "finding_id": "F-CONC-...",
  "scenario": "CONCENTRATION",
  "scenario_version": "1.0.0",
  "subject_id": "CLIENT-A",
  "window_start": "2026-08-26T14:00:00Z",
  "window_end": "2026-08-28T16:56:00Z",
  "strength": 0.8,
  "materiality": 0.4,
  "evidence_quality": "COMPLETE",
  "disposition": "ACTIONABLE",
  "reason_codes": ["PAIR_OBSERVED_VOLUME_SHARE_HIGH"],
  "feature_values": {"pair_observed_volume_share": 0.8},
  "evidence_refs": ["record://trade/T-CONC-01"],
  "missing_data": [],
  "limitations": []
}
```

`strength` é a força do padrão dentro do detector. Não é probabilidade de ilícito.

## IDs e compatibilidade

O ID estável usa SHA-256 sobre partes canônicas. Uma mudança de comportamento precisa alterar a versão do detector/política; isso evita confundir reexecução idêntica com resultado de metodologia nova.

Para integrar uma fonte real:

1. mapear o schema de origem para os contratos canônicos;
2. declarar timezone, unidades, cancelamentos e correções;
3. gerar manifesto por partição/carga;
4. rodar validação sem detectores;
5. reconciliar amostra com a origem;
6. congelar golden records;
7. habilitar um cenário em shadow mode.

