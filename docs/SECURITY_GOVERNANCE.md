# Segurança, privacidade e governança

## Modelo de confiança

Eventos, documentos e prompts são entradas não confiáveis. Um dado estar “dentro da AWS” não o torna autorizado para todos os serviços nem adequado para logs/modelos.

## Papéis mínimos

| Papel | Pode investigar | Pode revisar | Pode configurar política | Pode operar infraestrutura |
|---|:---:|:---:|:---:|:---:|
| Analista | sim | não o próprio caso | não | não |
| Revisor/manager | sim | sim | conforme governança | não |
| Model Risk/Compliance | challenge | conforme mandato | aprova | não |
| Engenheiro | dados sintéticos/mascarados | não | propõe via mudança | dev/test |
| Operações cloud | não por padrão | não | não | sim |
| Auditor | leitura autorizada | não | não | não |

Produção exige identidade corporativa, MFA, sessões temporárias e logs de autorização.

## Controles já visíveis no código

- modelos rejeitam campos extras;
- timestamps de trades exigem timezone;
- paths locais impedem escape do diretório de artefatos;
- transições exigem justificativa;
- fechamento/escalonamento exige papel de revisão;
- investigador não revisa o próprio caso;
- audit ledger é append-only na interface e encadeado por hash;
- Bedrock só aceita citações presentes no dossiê;
- falha de modelo degrada, não bloqueia;
- configuração Aurora prematura falha explicitamente.

São controles demonstrativos. Autenticação forte, persistência imutável e enforcement de infraestrutura ainda pertencem ao ambiente-alvo.

## Dados e PII

- Preferir IDs tokenizados nos detectores.
- Resolver PII somente na tela autorizada do caso.
- Não replicar atributos sensíveis em cada camada.
- Congelar apenas evidência necessária à finalidade.
- Separar evidência do caso de conhecimento institucional.
- Definir retenção, legal hold e descarte com Jurídico/Privacidade.
- Proteger logs como dados do caso; não registrar payload indiscriminadamente.

## IA e prompt injection

O assistente recebe JSON estruturado e instrução restrita. Produção deve adicionar:

- redaction/tokenização antes do prompt;
- allowlist de fontes e tools;
- conteúdo recuperado tratado como dado, nunca instrução;
- schema de saída e limite de tokens;
- verificação por afirmação, não só lista global de refs;
- guardrails e filtros aprovados;
- timeout, circuit breaker e quotas;
- avaliação de PII leakage e jailbreak;
- registro de modelo, prompt, parâmetros e sources conforme política.

## Threats prioritárias

| Ameaça | Controle esperado |
|---|---|
| adulteração da evidência | S3 Versioning/Object Lock, KMS, hashes e acesso mínimo |
| bypass de workflow | autorização server-side e state machine |
| autoaprovação | segregação de ator e papel |
| reprocessamento duplicado | IDs, unique constraints e inbox/outbox |
| vínculo falso no grafo | fonte, confiança, vigência, review de zona cinzenta |
| exfiltração por prompt/log | redaction, egress control, VPC endpoints e logging mínimo |
| supply chain | lock/scan/SBOM, imagem assinada e dependências revisadas |
| segredo em configuração | Secrets Manager; nunca `.env` versionado |
| abuso de export | autorização, watermark, logging e limite de finalidade |

## Change management

Uma mudança de regra, peso, prompt ou contrato deve registrar:

```text
change_id
rationale
owner
old_version
new_version
impact_analysis
backtest_result
approval
effective_from
rollback_plan
```

`configs/policy.example.json` demonstra configuração versionada. Em produção, a política aprovada deve ser artefato imutável associado ao run, não um arquivo editado manualmente no container.

## Auditoria

Três trilhas precisam convergir:

1. dados: ingestão, qualidade, transformação e acesso;
2. máquina: features, regras, score, versão e correlação;
3. humano: visualização, comentário, decisão, justificativa e revisão.

O hash chain local demonstra tamper evidence. Produção precisa persistir o ledger em storage transacional/imutável e controlar acesso ao próprio mecanismo de auditoria.

