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
| `FixedIncomeTrade` | negócio de Renda Fixa | produto, emissor, duas pontas, papéis econômicos, capacidade, mesa/book/trader, PU, taxa, spread, duration e DV01 |
| `FixedIncomeReference` | instrumento × instante | produto, PU/taxa/spread, curva, metodologia, fonte, freshness e confiança |
| `MarketCoverageSnapshot` | instrumento × janela | fonte, universo, ratio de cobertura, contagem observada e esperada |
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
| referência de Renda Fixa | conduta, resposta e principal versus cliente retornam `INCONCLUSIVE` |
| cobertura do denominador | participação observada retorna `INCONCLUSIVE`; nunca vira market share |
| papel econômico da ponta | quality issue explícita e limitação de principal versus cliente |
| snapshot do cliente | cenários dependentes são bloqueados pelo quality gate |
| contraparte | o negócio não participa da métrica relacional por par |

## Manifesto e reconciliação

O quality gate compara:

- record count de negócios confirmados;
- financeiro bruto derivado de `price × quantity`;
- contagem e financeiro próprios de Renda Fixa;
- duplicidade de `trade_id`;
- integridade mínima de snapshots;
- presença de referências críticas.

Divergência do manifesto ou duplicidade crítica bloqueia o catálogo afetado. Warnings
de referência, cobertura e resolução de ponta permitem execução apenas quando o detector
possui um caminho inconclusivo explícito.

## Semântica específica de Renda Fixa

- `price_unit` é o PU negociado, não preço genérico de tela;
- `yield_rate` usa taxa decimal (`0.135` = 13,5% a.a. conforme convenção da fonte);
- `spread_bps` usa pontos-base;
- `financial_value` vem da origem e é reconciliado; não é recalculado silenciosamente;
- `buyer_actor_type` e `seller_actor_type` separam cliente, Tesouraria proprietária e
  outras instituições;
- toda referência possui `reference_time`, fonte e versão metodológica;
- seleção `latest_at` só aceita referência conhecida no instante analisado;
- `MarketCoverageSnapshot` declara o denominador. Sem ele, há amostra, não participação
  de mercado defensável.

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
