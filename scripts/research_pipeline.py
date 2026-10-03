#!/usr/bin/env python3
"""Research-first workflow driver for the VRPTW project.

The script is deliberately a thin orchestrator over existing tools. It makes
the intended NCKH/report pipeline discoverable without hiding the underlying
benchmark, table, figure, and manuscript commands.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUICK_OUT = ROOT / "results" / "research_pipeline" / "quick"
DEFAULT_TABLE_SWEEP = ROOT / "results" / "ultimate-publication-suite" / "combined_clean.csv"


@dataclass(frozen=True)
class PipelineCommand:
    name: str
    description: str
    argv: list[str]


def _project_python() -> list[str]:
    return ["uv", "run", "python"]


def _env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src if not existing else f"{src}{os.pathsep}{existing}"
    return env


def _commands(args: argparse.Namespace) -> dict[str, list[PipelineCommand]]:
    quick_out = Path(args.out_dir).resolve() if args.out_dir else DEFAULT_QUICK_OUT

    sweep_csv = args.sweep_csv or str(DEFAULT_TABLE_SWEEP)
    gnn_csv = args.gnn_csv

    tables_cmd = [
        *_project_python(),
        "scripts/make_paper_tables.py",
        "--sweep",
        sweep_csv,
        "--out-dir",
        "docs/tables",
    ]
    if gnn_csv:
        tables_cmd.extend(["--gnn", gnn_csv])

    return {
        "smoke": [
            PipelineCommand(
                "pytest",
                "Run the solver regression suite, excluding slower e2e tests.",
                ["uv", "run", "pytest", "tests/", "-v"],
            ),
            PipelineCommand(
                "cli-smoke",
                "Run the package entry point on a small synthetic instance.",
                [*_project_python(), "-m", "vrptw", "smoke-test", "--nodes", "25", "--dist", "RC"],
            ),
        ],
        "quick": [
            PipelineCommand(
                "paper-quick-benchmark",
                "Run representative paired experiments for paper iteration.",
                [
                    *_project_python(),
                    "scripts/run_paper_benchmarks.py",
                    "--mode",
                    "quick",
                    "--iterations",
                    str(args.iterations),
                    "--workers",
                    str(args.workers),
                    "--out-dir",
                    str(quick_out),
                ],
            )
        ],
        "tables": [
            PipelineCommand(
                "paper-tables",
                "Regenerate LaTeX tables from a benchmark sweep CSV.",
                tables_cmd,
            )
        ],
        "figures": [
            PipelineCommand(
                "paper-figures",
                "Regenerate publication figures used by the manuscript.",
                [*_project_python(), "scripts/generate_paper_figures.py"],
            )
        ],
        "paper": [
            PipelineCommand(
                "paper-build",
                "Compile manuscript PDF and package the Overleaf bundle.",
                [*_project_python(), "docs/build_paper.py"],
            )
        ],
        "audit": [
            PipelineCommand(
                "paper-integrity-audit",
                "Audit manuscript claims against raw benchmark data.",
                [*_project_python(), "scripts/audit_paper_integrity.py"],
            )
        ],
        "app": [
            PipelineCommand(
                "app-demo",
                "Start the secondary FastAPI/Vite dispatch demo.",
                ["make", "dev-all"],
            )
        ],
    }


def _ordered_stages(selected: str) -> list[str]:
    if selected == "plan":
        return ["smoke", "quick", "tables", "figures", "paper", "audit", "app"]
    if selected == "all":
        return ["smoke", "quick", "tables", "figures", "paper", "audit"]
    return [selected]


def _print_plan(commands_by_stage: dict[str, list[PipelineCommand]], stages: list[str]) -> None:
    print("Research-first workflow")
    print("Priority: paper/report -> reproducible pipeline -> app demo")
    print()
    for stage in stages:
        print(f"[{stage}]")
        for command in commands_by_stage[stage]:
            print(f"  {command.name}: {command.description}")
            print(f"    {' '.join(command.argv)}")
        print()


def _run(commands: list[PipelineCommand]) -> int:
    for command in commands:
        print(f"\n==> {command.name}")
        print(command.description)
        print("$ " + " ".join(command.argv))
        result = subprocess.run(command.argv, cwd=ROOT, env=_env(), check=False)
        if result.returncode != 0:
            print(f"\nStage failed at {command.name} with exit code {result.returncode}.")
            return result.returncode
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or print the VRPTW research pipeline.")
    parser.add_argument(
        "--stage",
        choices=["plan", "smoke", "quick", "tables", "figures", "paper", "audit", "app", "all"],
        default="plan",
        help="Pipeline stage to run. 'plan' only prints commands.",
    )
    parser.add_argument("--iterations", type=int, default=200, help="Quick benchmark iteration budget.")
    parser.add_argument("--workers", type=int, default=1, help="Quick benchmark worker count.")
    parser.add_argument("--out-dir", type=str, default=str(DEFAULT_QUICK_OUT), help="Quick benchmark output directory.")
    parser.add_argument("--sweep-csv", type=str, default=None, help="CSV for table generation.")
    parser.add_argument("--gnn-csv", type=str, default=None, help="Optional GNN validation CSV for table generation.")
    args = parser.parse_args()

    commands_by_stage = _commands(args)
    stages = _ordered_stages(args.stage)

    if args.stage == "plan":
        _print_plan(commands_by_stage, stages)
        return 0

    for stage in stages:
        rc = _run(commands_by_stage[stage])
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
