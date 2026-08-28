"""CLI sem dependência extra para demo, validação e API."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .adapters.local import LocalJsonObjectStore
from .api import create_app
from .config import load_policy
from .pipeline import SurveillancePipeline
from .quality import validate_dataset
from .reporting import render_run_report
from .sample_data import build_benign_dataset, build_demo_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vertice", description="VÉRTICE Surveillance Intelligence"
    )
    parser.add_argument("--version", action="version", version="vertice 0.1.0")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="executa o catálogo completo de golden cases")
    demo.add_argument("--output", default="artifacts", help="diretório para evidências e relatório")
    demo.add_argument("--json", action="store_true", help="imprime o run completo em JSON")
    demo.add_argument("--policy", help="arquivo JSON de política versionada")

    validate = sub.add_parser("validate", help="executa somente gates de qualidade")
    validate.add_argument("--dataset", choices=("demo", "benign"), default="demo")

    serve = sub.add_parser("serve", help="inicia API, Swagger e painel")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--policy", help="arquivo JSON de política versionada")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "demo":
        output = Path(args.output)
        policy = load_policy(args.policy) if args.policy else None
        pipeline = SurveillancePipeline(
            object_store=LocalJsonObjectStore(output), policy_config=policy
        )
        run = pipeline.run(build_demo_dataset())
        report_path = output / run.run_id / "REPORT.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_run_report(run), encoding="utf-8")
        if args.json:
            print(json.dumps(run.model_dump(mode="json"), indent=2, ensure_ascii=False))
        else:
            print("VÉRTICE — execução concluída")
            print(f"run_id: {run.run_id}")
            print(f"quality: {'PASS' if run.quality.passed else 'FAIL'}")
            print(
                f"findings: {len(run.findings)} | alerts: {len(run.alerts)} | cases: {len(run.cases)}"
            )
            print(
                "scenario_coverage: "
                f"{run.metrics['scenario_coverage']}/{run.metrics['scenario_catalog_size']}"
            )
            print(f"report: {report_path.resolve()}")
        return 0 if run.quality.passed else 2
    if args.command == "validate":
        dataset = build_demo_dataset() if args.dataset == "demo" else build_benign_dataset()
        report = validate_dataset(dataset)
        print(json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False))
        return 0 if report.passed else 2
    if args.command == "serve":
        import uvicorn

        policy = load_policy(args.policy) if args.policy else None
        uvicorn.run(
            create_app(SurveillancePipeline(policy_config=policy)),
            host=args.host,
            port=args.port,
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
