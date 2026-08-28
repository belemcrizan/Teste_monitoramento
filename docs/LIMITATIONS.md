# Limitações e não alegações

## Status

O VÉRTICE é uma baseline executável para validação técnica e shadow mode. Não é um produto regulatório pronto para produção.

## O que não deve ser alegado

- “detecta manipulação/fraude”;
- “prova churning”;
- “tem precisão de X%”;
- “reduz falsos positivos em X%”;
- “é aderente automaticamente a CVM/B3/PLD”;
- “está production-ready na AWS”;
- “cobre spoofing/layering”;
- “o score é probabilidade de culpa”.

Nenhuma dessas afirmações foi validada.

## Limitações por área

### Dados

- golden cases sintéticos;
- sem feed B3/OTC real;
- sem ciclo completo de ordens/livro;
- sem correções/eventos tardios em escala;
- sem coortes reais;
- sem catálogo/licenças de referências.

### Detectores

- thresholds ilustrativos;
- churning usa proxy de reversão, não lot matching institucional completo;
- manipulação cobre apenas composto de trade/reference/posição;
- OTC usa uma fórmula demonstrativa, não biblioteca de pricing validada;
- concentração usa universo observado, não market share.

### Grafo

- enriquecedor em memória;
- sem entity resolution probabilística;
- sem community detection/graph ML;
- sem avaliação de falso vínculo;
- sem Neptune ou benchmark de consulta.

### Risco

- pesos especialistas não calibrados;
- sem outcomes adjudicados;
- histórico é zero na baseline;
- correlação atual agrupa por sujeito, não por estratégia/beneficiário/janela complexa;
- sem análise de capacidade da fila.

### Case Manager

- repositório local em memória;
- sem autenticação/SSO;
- sem persistência concorrente, optimistic lock, SLA scheduler, anexos ou legal hold;
- não substitui sistema transacional institucional.

### IA

- fallback determinístico é simples;
- adaptador Bedrock valida refs globais, não entailment por frase;
- sem RAG institucional, red-team ou avaliação de factualidade;
- sem política final de logging/PII.

### Operação

- sem benchmark de volume/latência;
- sem Kinesis/Glue/Neptune/Aurora implantados;
- sem DR, chaos, backup/restore e runbook exercitados;
- sem SLO contratado e sem FinOps real.

## Uso responsável da demonstração

Apresente como prova de comportamento e contrato. Diferencie sempre:

- demonstrado por teste;
- projetado por arquitetura;
- dependente de integração;
- dependente de validação humana/regulatória.

Esse rigor aumenta a credibilidade do projeto; não reduz seu valor.

