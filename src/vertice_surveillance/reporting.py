"""Relatório Markdown legível por público executivo e técnico."""

from __future__ import annotations

from .models import PipelineRun


def render_run_report(run: PipelineRun) -> str:
    scenario_counts: dict[str, int] = {}
    for finding in run.findings:
        scenario_counts[finding.scenario] = scenario_counts.get(finding.scenario, 0) + 1
    scenario_rows = "\n".join(
        f"| {scenario} | {count} |" for scenario, count in sorted(scenario_counts.items())
    ) or "| Nenhum | 0 |"
    case_rows = "\n".join(
        (
            f"| `{case.case_id}` | `{case.subject_id}` | {case.state.value} | "
            f"{case.priority:.2f} |"
        )
        for case in run.cases
    ) or "| — | — | — | — |"
    issue_rows = "\n".join(
        f"| {issue.severity.value} | `{issue.code}` | {issue.message} |"
        for issue in run.quality.issues
    ) or "| — | Nenhuma ocorrência | A carga passou pelos gates configurados. |"
    return f"""# VÉRTICE — Relatório de validação

**Run:** `{run.run_id}`  
**Snapshot:** `{run.snapshot_id}`  
**Qualidade:** {"APROVADA" if run.quality.passed else "BLOQUEADA"}  

## Leitura executiva

O processamento recebeu **{run.quality.record_count} negócios**, produziu
**{len(run.findings)} achados técnicos**, correlacionou **{len(run.alerts)} alertas**
e abriu **{len(run.cases)} casos**. Um achado não é uma acusação: é evidência
estruturada que precisa de revisão humana e preserva limitações e dados ausentes.

## Cobertura exercitada

| Cenário | Findings |
|---|---:|
{scenario_rows}

## Qualidade e reconciliação

| Severidade | Código | Resultado |
|---|---|---|
{issue_rows}

## Casos

| Caso | Sujeito | Estado | Prioridade operacional |
|---|---|---|---:|
{case_rows}

## Controles verificados

- Separação entre `Feature`, `Finding`, `Alert` e `Case`.
- IDs determinísticos para replay e idempotência.
- Ausência de dados críticos tratada como `INCONCLUSIVE`.
- Grafo temporal enriquece antes da prioridade final.
- Score registra componentes, interações e versão da política.
- Evidência é salva antes do resumo assistivo.
- Falha do assistente não impede a abertura de casos.
- Audit ledger encadeado por hash: **{"VÁLIDO" if run.metrics['audit_chain_valid'] else "INVÁLIDO"}**.

## Limite da demonstração

Os dados são sintéticos e os limiares são ilustrativos. O resultado valida o
comportamento do software e a rastreabilidade; não valida eficácia regulatória,
performance com dados reais nem prontidão de produção.
"""

