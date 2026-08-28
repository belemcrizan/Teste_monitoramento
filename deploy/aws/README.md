# Bootstrap AWS do VÉRTICE

Este diretório contém templates de integração, não uma landing zone autônoma. Eles pressupõem VPC, subnets privadas, KMS, ECR, logs, roles e naming já aprovados pela organização.

## Artefatos

- `ecs-task-definition.template.json`: container Fargate usando S3/SQS e Bedrock opcional;
- `iam-task-policy.template.json`: permissões funcionais mínimas com placeholders de recurso.

## Fluxo recomendado

1. Execute testes e golden cases localmente.
2. Construa a imagem sem segredos.
3. Faça scan, gere SBOM e assine conforme o padrão corporativo.
4. Publique no ECR.
5. Substitua todos os placeholders dos templates por recursos reais.
6. Registre a task definition com execution role e task role separadas.
7. Execute em subnets privadas, sem IP público.
8. Restrinja S3/SQS/Bedrock por endpoint e IAM.
9. Rode golden cases e compare IDs/resultados com o local.
10. Só depois conecte uma fonte real em shadow mode.

## Comandos ilustrativos

```bash
docker build -t vertice-surveillance:0.1.0 .
docker run --rm -p 8000:8000 \
  -e VERTICE_ENV=local \
  -e VERTICE_OBJECT_STORE=local \
  vertice-surveillance:0.1.0
```

O deploy AWS real deve ser feito pela pipeline/IaC institucional. Não copie credenciais para comandos, imagem ou variáveis em repositório.

## Limite de segurança

O template mantém `VERTICE_CASE_REPOSITORY=memory`; portanto, ele serve apenas para smoke/integration/shadow efêmero. Antes de produção, implemente o `CaseRepository` Aurora descrito em `docs/AWS_ADOPTION.md`. O bootstrap recusará `aurora` enquanto esse adaptador não existir, evitando persistência falsa.

