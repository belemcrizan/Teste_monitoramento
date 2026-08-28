# Walkthrough dos golden cases

## Dataset

O fixture é sintético, datado e imutável. Ele contém 15 negócios listados confirmados,
sete negócios de Renda Fixa, cinco snapshots de cliente, três posições, duas estruturas
OTC, seis referências de Renda Fixa, um snapshot de cobertura e quatro relações temporais.

## CLIENT-A — evidência correlacionada

### Fatos

- seis negócios no `INST-Z` com `CP-X` em três dias;
- compras e vendas acumuladas simétricas;
- duas compras próximas ao fechamento em 28/08;
- preços 104,8 e 105,2 diante de referência 100 e spread 0,5;
- posição comprada anterior positiva;
- CLIENT-A e CLIENT-B compartilham `ADV-1` com vínculo vigente.

### Findings

O detector de concentração registra participação no universo observado, recorrência, simetria e HHI. O detector de comportamento de preço registra janela de fechamento, desvio robusto, direção, participação e posição beneficiada.

O grafo adiciona `TEMPORAL_GRAPH_RELATION_RELEVANT`. Ele não conclui coordenação; apenas prova que a relação existia na janela.

### Correlação

Os dois findings compartilham o mesmo sujeito e entram em um alerta. A política registra as interações:

- `MULTI_SCENARIO_CORROBORATION`;
- `FINDING_PLUS_TEMPORAL_RELATION`;
- `CONCENTRATION_PLUS_PRICE_BEHAVIOR`.

O caso é aberto com prioridade operacional alta/crítica. A explicação lembra explicitamente que prioridade não é culpa.

### Contrafatos que ainda precisam ser avaliados

- baixa liquidez;
- ordem-mãe legítima;
- hedge ou rebalanceamento;
- evento de mercado;
- erro de contraparte ou cancelamento tardio.

## CLIENT-C — atividade potencialmente excessiva

### Fatos

- oito negócios alternados em oito dias;
- R$ 800 mil de volume bruto aproximado;
- patrimônio médio de R$ 100 mil;
- fees sintéticos elevados;
- perfil conservador;
- origem do controle marcada como desconhecida.

### Resultado

O detector calcula turnover bruto, turnover casado, custo/patrimônio e reversões rápidas. Ele emite `CLIENT_CONTROL_UNKNOWN` e degrada a qualidade da evidência, mas não reduz silenciosamente a prioridade.

### Limite

A reversão rápida é proxy demonstrativa. Produção exige lot matching aprovado, custos completos, objetivo, recomendação/controle e benefício econômico do intermediário.

## CLIENT-D — OTC acionável

### Fatos

- notional de R$ 2,5 milhões;
- prêmio de R$ 180 mil;
- IPV de R$ 100 mil;
- incerteza de R$ 10 mil e banda de liquidez de R$ 15 mil;
- produto com complexidade 4 para cliente com limite 1;
- operação vinculada a uma cadeia de rollover.

### Resultado

O desvio normalizado é calculado por:

$$
Z^{IPV}=\frac{Premium^{trade}-Value^{independent}}{\max(Uncertainty,LiquidityBand,\varepsilon)}
$$

O finding registra desvio IPV, mismatch de complexidade e rollover. A conclusão de inadequação ou irregularidade permanece humana e requer especialista/Model Risk.

## CLIENT-E — falha segura

### Fatos ausentes

- IPV independente;
- incerteza de modelo;
- identificador e versão do modelo;
- snapshot de mercado.

### Resultado

O detector não calcula zero e não afirma normalidade. Ele produz `INCONCLUSIVE_VALUATION`; o caso entra em `AWAITING_EVIDENCE`.

Este é um teste central da arquitetura: uma ausência crítica gera trabalho explícito e rastreável.

## CLIENT-FI e TREASURY-DESK — Tesouraria/Renda Fixa

### Fatos

- três compras da mesma debênture pelo cliente contra Tesouraria proprietária;
- PU, taxa e spread afastados das referências sintéticas contemporâneas;
- três movimentos posteriores alinhados ao lado comprador;
- cobertura declarada de 95% do universo regulatório sintético;
- capacidade `PRINCIPAL`, mesa, book e trader identificados.

### Resultado

O cliente recebe quatro findings correlacionados: conduta de Renda Fixa, participação
observada, resposta pós-negócio e principal versus cliente. A mesa recebe os findings
aplicáveis ao seu próprio papel econômico. O denominador de mercado conta cada negócio
uma vez, embora as duas pontas possam receber contexto investigativo.

### Limites

O caso não prova dominância, influência de preço, conflito ou preço injusto. A fonte de
referência e a cobertura são sintéticas; eventos, liquidez, mandato e hedge precisam de
avaliação humana. Remover referências ou cobertura transforma os cenários dependentes
em `INCONCLUSIVE`.

## Controle benigno

O fixture benigno possui dois negócios pequenos, contrapartes diferentes, preços próximos à referência e patrimônio elevado. O pipeline não produz findings ou casos. Isso não mede taxa de falso positivo, mas prova que o código não classifica toda atividade como suspeita.

## Da evidência ao audit trail

Para cada caso:

```text
Case
└── Alert
    ├── RiskExplanation
    └── Finding(s)
        ├── feature_values
        ├── reason_codes
        ├── evidence_refs
        ├── missing_data
        └── limitations
```

O ledger registra `CASE_CREATED` e toda transição subsequente com ator, papel, justificativa, estado anterior/novo, hash anterior e hash atual.
