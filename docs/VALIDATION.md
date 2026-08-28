# Estratégia e evidências de validação

## O que esta versão permite afirmar

| Afirmação | Evidência | Status |
|---|---|---|
| A arquitetura é implementável | pipeline executável e pacote instalável | demonstrado |
| Quatro eixos compartilham contratos | golden cases com cobertura 4/4 | demonstrado |
| Crítico bloqueia processamento | testes de duplicidade e manifesto | demonstrado |
| Dados ausentes não viram zero | caminhos inconclusivos OTC/churning/manipulação | demonstrado |
| IDs lógicos são reprodutíveis | teste de replay em duas stores | demonstrado |
| IA não bloqueia casos | assistente que lança timeout | demonstrado |
| Quatro olhos é aplicado | tentativa de autoaprovação rejeitada | demonstrado |
| Adaptadores AWS são substituíveis | testes S3/SQS/Bedrock com clientes falsos | demonstrado |
| Detectores funcionam em dados reais | nenhum dataset real autorizado | não demonstrado |
| Recall/precision regulatórios | sem adjudicação e prevalência reais | não demonstrado |
| Escala/latência AWS | sem benchmark distribuído | não demonstrado |
| Aderência jurídica automática | fora do escopo técnico | não alegado |

## Suite automatizada

Os testes cobrem:

- contratos e quality gates;
- duplicidade e divergência de manifesto;
- fórmulas/reason codes dos quatro detectores;
- controle benigno;
- correlação multi-scenario;
- replay e idempotência;
- evidência persistida;
- fallback assistivo;
- máquina de estados, RBAC mínimo e quatro olhos;
- integridade do audit hash chain;
- endpoints REST e painel;
- S3/SQS/Bedrock por injeção de clientes;
- bootstrap local e falha explícita para persistência não implementada.

Comandos usados pelo CI:

```bash
python -m pytest --cov=vertice_surveillance --cov-report=term-missing --cov-fail-under=80
python -m ruff check .
python -m mypy src/vertice_surveillance
python -m build
python -m vertice_surveillance demo --policy configs/policy.example.json
```

## Pirâmide necessária para o piloto

### Unitários

Fórmulas, denominadores, zero/nulo, limites, timezone, arredondamento e lot matching.

### Contratos

Compatibilidade de schema, semântica de cancelamento/correção, unidades, calendários e eventos tardios.

### Integração

Fonte → Raw → qualidade → Curated → feature → finding → alerta → caso.

### Golden cases

Manter sintéticos e adicionar históricos anonimizados/autorizados, benignos difíceis, limítrofes, regimes de estresse e dados corrompidos.

### Replay histórico

Executar `as of`, sem usar cadastro, preço ou outcome conhecido apenas no futuro.

### UAT investigativo

Analistas avaliam utilidade, clareza, contrafatos, evidence acquisition, tempo e workflow.

### Segurança e resiliência

Autorização, exfiltração, prompt injection, indisponibilidade, DLQ, restore, failover e concurrency.

## Métricas científicas/operacionais

Medir por cenário e coorte:

- precision em amostra adjudicada;
- recall em biblioteca de cenários conhecidos;
- coverage por produto/venue/canal;
- findings por milhão de eventos;
- finding → alert → case;
- duplicação evitada;
- tempo até detectar/triagem/decisão;
- inconclusivos por causa raiz;
- estabilidade de features/prioridade;
- reabertura e override;
- citation precision/coverage e unsupported claim rate;
- custo por cenário e caso.

## Gates sugeridos

1. **Gate de dados:** reconciliação, temporalidade e lineage aprovados.
2. **Gate de detector:** golden cases e benign hard cases passam; limitações documentadas.
3. **Gate de shadow:** volume, estabilidade e capacidade são sustentáveis.
4. **Gate operacional:** Case Manager, quatro olhos, auditoria e runbooks passam UAT.
5. **Gate de modelo/IA:** avaliação congelada, red-team e fallback aprovados.
6. **Gate de produção:** segurança, DR, FinOps e ownership aprovados.

Falha em um gate não deve ser escondida por resultado agregado.

