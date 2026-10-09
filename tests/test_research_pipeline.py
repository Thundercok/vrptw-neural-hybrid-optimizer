"""Check supported entry points without running expensive experiments."""

import argparse
import runpy
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = runpy.run_path(str(ROOT / "scripts/research_pipeline.py"))


def commands():
    return PIPELINE["_commands"](
        argparse.Namespace(out_dir=None, sweep_csv=None, gnn_csv=None, iterations=25, workers=1)
    )


def test_smoke_enables_test_dependencies():
    assert commands()["smoke"][0].argv[:5] == ["uv", "run", "--extra", "dev", "pytest"]


def test_pipeline_script_targets_exist():
    for stage in commands().values():
        for command in stage:
            for argument in command.argv:
                if argument.endswith(".py"):
                    assert (ROOT / argument).is_file(), argument


def test_audit_precedes_paper_build():
    stages = PIPELINE["_ordered_stages"]("all")
    assert stages.index("audit") < stages.index("paper")


def test_make_uses_supported_runner():
    result = subprocess.run(["make", "-n", "benchmark"], cwd=ROOT, capture_output=True, text=True, check=True)
    assert "scripts/run_paper_benchmarks.py --mode quick" in result.stdout


def test_pure_research_dependencies():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert "fastapi" not in project["dependencies"]
    assert "demo" not in project.get("optional-dependencies", {})
    assert "torch>=2.4" in project["dependencies"]
