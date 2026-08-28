# Roadmap orientado por gates

## Agora — baseline executável

- quatro detectores e golden cases;
- qualidade/reconciliação;
- grafo temporal mínimo;
- correlação/prioridade;
- casos, quatro olhos e auditoria;
- API/painel/CLI;
- política versionada;
- adaptadores AWS iniciais.

## Próximo — 30 a 60 dias

1. obter amostra real anonimizável/autorizada;
2. criar mapeamento de fonte → contrato;
3. reconciliar um dia completo;
4. implementar coortes de concentração;
5. adjudicar casos e benign hard cases;
6. medir volume/tempo/capacidade;
7. executar em ECS com S3/SQS no ambiente de teste.

Gate: slice de concentração reproduzível e útil em shadow mode.

## 60 a 120 dias

- Case Repository Aurora com outbox;
- autenticação/roles e UI investigativa;
- grafo Neptune e entity resolution determinística;
- churning com lot matching/custos/controle;
- observabilidade e dashboards reconciliados;
- replay automatizado e change reports.

Gate: workflow e evidência passam UAT, concorrência e restore.

## 120 a 240 dias

- order lifecycle/livro e cenários intradiários;
- Kinesis e reconciliação stream/batch;
- pricing OTC aprovado e cadeias de estratégia;
- Bedrock com RAG, citações por afirmação e red-team;
- calibração por coorte e análise de capacidade;
- FinOps, SLO e DR.

Gate: cada cenário passa avaliação independente antes de afetar fila regulatória.

## Ordem de investimento recomendada

```text
qualidade de dados
→ validação com analistas
→ caso transacional
→ grafo/streaming
→ IA e modelos mais sofisticados
```

Mais inteligência sobre dados não reconciliados apenas torna o erro mais convincente.

