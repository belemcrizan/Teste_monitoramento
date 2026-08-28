"""API e painel demonstrativo do VÉRTICE."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict

from .models import CaseState, PipelineRun
from .pipeline import SurveillancePipeline
from .sample_data import build_demo_dataset


class TransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: CaseState
    actor: str
    actor_role: str
    reason: str


class ApplicationState:
    def __init__(self, pipeline: SurveillancePipeline) -> None:
        self.pipeline = pipeline
        self.latest_run: PipelineRun | None = None


def create_app(pipeline: SurveillancePipeline | None = None) -> FastAPI:
    service = pipeline or SurveillancePipeline()
    state = ApplicationState(service)
    app = FastAPI(
        title="VÉRTICE Surveillance Intelligence",
        version="0.1.0",
        description=(
            "Inteligência investigativa explicável. Achados e prioridades não representam culpa."
        ),
    )
    app.state.vertice = state

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "vertice-surveillance", "version": "0.1.0"}

    @app.post("/v1/demo/run")
    def run_demo() -> dict[str, Any]:
        state.latest_run = service.run(build_demo_dataset())
        return state.latest_run.model_dump(mode="json")

    @app.get("/v1/runs/latest")
    def latest_run() -> dict[str, Any]:
        if state.latest_run is None:
            raise HTTPException(status_code=404, detail="Execute POST /v1/demo/run primeiro.")
        return state.latest_run.model_dump(mode="json")

    @app.get("/v1/cases")
    def list_cases() -> list[dict[str, Any]]:
        return [item.model_dump(mode="json") for item in service.case_manager.repository.list()]

    @app.get("/v1/cases/{case_id}")
    def get_case(case_id: str) -> dict[str, Any]:
        case = service.case_manager.repository.get(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="Caso não encontrado.")
        return case.model_dump(mode="json")

    @app.post("/v1/cases/{case_id}/transition")
    def transition_case(case_id: str, request: TransitionRequest) -> dict[str, Any]:
        try:
            case = service.case_manager.transition(
                case_id=case_id,
                target=request.target,
                actor=request.actor,
                actor_role=request.actor_role,
                reason=request.reason,
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Caso não encontrado.") from error
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return case.model_dump(mode="json")

    @app.get("/v1/cases/{case_id}/audit")
    def case_audit(case_id: str) -> list[dict[str, Any]]:
        if service.case_manager.repository.get(case_id) is None:
            raise HTTPException(status_code=404, detail="Caso não encontrado.")
        return [
            item.model_dump(mode="json") for item in service.case_manager.ledger.records(case_id)
        ]

    @app.get("/demo", response_class=HTMLResponse)
    def demo_page() -> str:
        return DEMO_HTML

    return app


app = create_app()


DEMO_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VÉRTICE — Trade Surveillance</title>
  <style>
    :root{color-scheme:dark;--bg:#07111f;--panel:#0d1b2a;--line:#1f3850;--text:#e7f0f8;--muted:#94a9ba;--cyan:#36d6c7;--amber:#ffbf69;--red:#ff6b6b}
    *{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top right,#12324a,var(--bg) 42%);color:var(--text);font:16px/1.5 Inter,Segoe UI,sans-serif}
    main{max-width:1180px;margin:auto;padding:40px 22px 80px}.eyebrow{color:var(--cyan);letter-spacing:.14em;text-transform:uppercase;font-size:.78rem}
    h1{font-size:clamp(2.2rem,6vw,4.7rem);line-height:.95;margin:.2em 0}.sub{max-width:760px;color:var(--muted);font-size:1.08rem}
    button{background:var(--cyan);color:#04231f;border:0;border-radius:10px;padding:13px 18px;font-weight:800;cursor:pointer;margin:18px 0}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}.card{background:rgba(13,27,42,.88);border:1px solid var(--line);border-radius:14px;padding:18px}
    .metric{font-size:2.2rem;font-weight:800}.label,.muted{color:var(--muted)}table{width:100%;border-collapse:collapse;margin-top:14px}th,td{text-align:left;padding:11px;border-bottom:1px solid var(--line)}
    .pill{display:inline-block;padding:3px 9px;border-radius:999px;background:#19354d;color:var(--cyan);font-size:.78rem}.warn{color:var(--amber)}code{color:var(--cyan)}
  </style>
</head>
<body><main>
  <div class="eyebrow">Surveillance intelligence • evidence first</div>
  <h1>VÉRTICE</h1>
  <p class="sub">Dos eventos reconciliados a casos auditáveis. O catálogo modular inclui mercado listado, OTC e Renda Fixa/Tesouraria; o grafo enriquece, a política correlaciona e pessoas decidem.</p>
  <button id="run">Executar golden cases</button><span id="status" class="muted"></span>
  <section id="metrics" class="grid"></section>
  <section class="card" style="margin-top:14px"><h2>Casos investigativos</h2><div id="cases" class="muted">Execute a demonstração.</div></section>
  <section class="card" style="margin-top:14px"><h2>O que este resultado significa</h2><p class="muted">Prioridade organiza a fila; não mede culpa. <code>INCONCLUSIVE</code> exige evidência adicional. A nota assistiva pode falhar sem interromper a detecção ou a abertura do caso.</p></section>
  <p class="muted">Swagger: <a href="/docs" style="color:var(--cyan)">/docs</a> • Health: <a href="/health" style="color:var(--cyan)">/health</a></p>
</main><script>
const button=document.querySelector('#run'),status=document.querySelector('#status');
button.onclick=async()=>{button.disabled=true;status.textContent=' Processando…';try{const response=await fetch('/v1/demo/run',{method:'POST'});const run=await response.json();render(run);status.textContent=' Execução concluída.'}catch(error){status.textContent=' Falha: '+error}finally{button.disabled=false}};
function render(run){const items=[['Listados',run.quality.record_count],['Renda Fixa',run.quality.fixed_income_record_count],['Findings',run.findings.length],['Alertas',run.alerts.length],['Casos',run.cases.length],['Cobertura',run.metrics.scenario_coverage+'/'+run.metrics.scenario_catalog_size],['Audit chain',run.metrics.audit_chain_valid?'Válida':'Inválida']];document.querySelector('#metrics').innerHTML=items.map(x=>`<div class="card"><div class="metric">${x[1]}</div><div class="label">${x[0]}</div></div>`).join('');document.querySelector('#cases').innerHTML=`<table><thead><tr><th>Caso</th><th>Sujeito</th><th>Estado</th><th>Prioridade</th></tr></thead><tbody>${run.cases.map(c=>`<tr><td><code>${c.case_id}</code></td><td>${c.subject_id}</td><td><span class="pill">${c.state}</span></td><td>${c.priority.toFixed(2)}</td></tr>`).join('')}</tbody></table>`}
  </script></body></html>"""
