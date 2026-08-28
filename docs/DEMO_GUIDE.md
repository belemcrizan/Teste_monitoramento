# Guia de demonstração

## Objetivo

Demonstrar que a arquitetura do MD virou comportamento executável e auditável. Não apresentar os dados sintéticos como evidência de eficácia real.

## Preparação

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
```

No PowerShell, use `.venv\Scripts\Activate.ps1`.

## Demo por terminal

```bash
vertice demo --policy configs/policy.example.json
```

Resultado de referência:

```text
VÉRTICE — execução concluída
run_id: RUN-5353610D6E486F06
quality: PASS
findings: 11 | alerts: 6 | cases: 6
scenario_coverage: 8/8
```

Abra `artifacts/RUN-5353610D6E486F06/REPORT.md` e depois:

- `run.json`: visão completa do processamento;
- `evidence/*.json`: dossiê congelado antes da IA;
- `assistant/*.json`: notas auxiliares separadas;
- `audit.json`: eventos de caso encadeados por hash.

## Demo visual

```bash
vertice serve --host 127.0.0.1 --port 8000 --policy configs/policy.example.json
```

1. Abra <http://127.0.0.1:8000/demo>.
2. Clique em **Executar golden cases**.
3. Mostre os indicadores e os estados dos casos.
4. Abra <http://127.0.0.1:8000/docs>.
5. Execute `GET /v1/cases` e inspecione um caso.
6. Mostre a transição controlada e o endpoint de auditoria.

## Roteiro de oito minutos

### 0:00–1:00 — problema

“A plataforma não tenta gerar mais alertas. Ela tenta reduzir o custo de chegar de dados a uma decisão defensável.”

### 1:00–2:00 — objetos

Explique `Feature → Finding → Alert → Case`. A regra produz evidência; correlação e política definem a fila; a pessoa decide.

### 2:00–3:00 — qualidade

Mostre `quality: PASS` e o warning `OTC_VALUATION_PARTIAL`. Ressalte que o warning não desapareceu: virou caso aguardando evidência.

### 3:00–5:00 — catálogo de oito detectores

- concentração: participação no universo observado, recorrência e simetria;
- manipulação: janela, desvio, direção, participação e posição beneficiada;
- churning: turnover, custo/equity, reversões e controle desconhecido;
- OTC: desvio IPV, suitability/complexidade e rollover.
- Renda Fixa: PU, taxa e spread contra referência contemporânea;
- participação observada: três denominadores e cobertura declarada;
- resposta pós-negócio: associação temporal sem alegação causal;
- principal versus cliente: preço adverso contra benchmark, sem conclusão de conflito.

### 5:00–6:00 — grafo e correlação

Mostre que CLIENT-A possui dois findings correlacionados e relação temporal. Um caso agrega as evidências, em vez de criar duas filas desconectadas.

### 6:00–7:00 — governança

Mostre IDs estáveis, versão da política, reason codes, evidence refs, máquina de estados e quatro olhos.

### 7:00–8:00 — AWS e limite

“O núcleo já está separado de infraestrutura. Substituímos filesystem por S3, memória por SQS/Aurora e fallback por Bedrock. Ainda precisamos validar dados, coortes e eficácia em shadow mode.”

## Exercícios de falha

### Duplicidade crítica

O teste `test_duplicate_trade_blocks_all_scenarios` prova que a carga não é consumida silenciosamente.

### IA indisponível

O teste `test_assistant_failure_does_not_block_cases` injeta timeout; casos e dossiês continuam existindo.

### Quatro olhos

O teste `test_four_eyes_blocks_self_review` impede que o investigador feche o próprio caso.

### Fluxo benigno

```bash
vertice validate --dataset benign
```

O teste end-to-end benigno não cria findings nem casos.

## Perguntas difíceis e respostas honestas

**Isso detecta fraude?** Não. Detecta padrões técnicos que merecem investigação.

**Está pronto para produção?** Não. Está pronto para validação técnica, discovery de dados e shadow mode controlado.

**Por que um caso inconclusivo tem prioridade?** Porque evidência ausente não deve empurrar silenciosamente uma exposição material para baixo da fila.

**Por que não usar Bedrock para decidir?** Porque fatos, cálculo e workflow precisam continuar reproduzíveis mesmo sem modelo generativo.

**Os thresholds são reais?** Não. São configuração ilustrativa e versionada. Produção exige replay, coortes, capacidade da equipe e aprovação.

**Isso prova dominância ou influência de preço?** Não. A solução usa os termos
“participação no universo observado” e “resposta pós-negócio” justamente para preservar
o limite da evidência.
