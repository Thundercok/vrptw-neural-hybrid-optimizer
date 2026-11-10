"""Cleanup proof must precede optional final counters, even on solver failure."""

import json
import sys
import time
from dataclasses import asdict

import pytest
from test_external_supervision import inst, load_script


@pytest.mark.parametrize("solver_error", [False, True])
def test_interrupted_completion_cannot_prevent_descendant_cleanup(tmp_path, monkeypatch, solver_error):
    worker = load_script("native_supervisor_worker")
    session = tmp_path / "session"
    session.mkdir()
    instance = inst()
    _, cfg = worker.cli.get_solver_and_config("neurolkh", 10)
    cfg.output_dir = str(session / "work/archive")
    cfg.neurolkh_root = str(tmp_path)
    identity = {
        "case": "neurolkh",
        "seed": 99,
        "requested_config": asdict(cfg),
        "source_sha256": "fixture",
        "instance_sha256": "input",
        "gnn_model_sha256": None,
        "backend_identity": {"pin": "fixture"},
    }
    request = {
        "session_dir": str(session),
        "identity": identity,
        "instance": "input.txt",
        "gnn_model": None,
        "time_limit": 10,
        "token": "fixture",
        "neurolkh_root": str(tmp_path),
    }
    (session / "request.json").write_text(json.dumps(request))
    start = time.perf_counter()
    (session / "start.json").write_text(
        json.dumps({"token": "fixture", "start_perf": start, "deadline_perf": start + 10})
    )

    class Solver:
        def __init__(self, instance, cfg):
            self.cfg, self.search_iterations, self.diagnostics = cfg, 0, {}

        def solve(self, *, seed, _certifier, _process_owner):
            if solver_error:
                raise RuntimeError("injected solver failure")
            self.native_certification = _certifier.diagnostics

    monkeypatch.setattr(worker.cli, "get_solver_and_config", lambda *a, **kw: (Solver, cfg))
    monkeypatch.setattr(worker.cli, "load_solomon_instance", lambda *a: instance)
    monkeypatch.setattr(worker.cli, "sha256_file", lambda *a: "input")
    monkeypatch.setattr(worker.cli, "extract_instrumentation", lambda *a: {})
    monkeypatch.setattr(worker.cli, "cold_start_state", lambda *a: {})
    monkeypatch.setattr(
        worker.cli,
        "get_env_info",
        lambda: {
            "source_sha256": "fixture",
            "process_entry": {"cwd": "work", "cache_dir": "cache", "cwd_entries": [], "cache_entries": []},
            "jit_environment": {},
            "numba": {},
        },
    )
    monkeypatch.setattr(worker, "backend_identity", lambda *a: identity["backend_identity"])
    monkeypatch.setattr(sys, "argv", ["worker", str(session / "request.json")])
    original = worker.atomic_json
    observed = []

    class CompletionInterrupted(BaseException):
        pass

    def write(path, payload):
        if path.name == "completion.json":
            observed.append((session / "descendant_cleanup.json").is_file())
            raise CompletionInterrupted
        return original(path, payload)

    monkeypatch.setattr(worker, "atomic_json", write)
    with pytest.raises(CompletionInterrupted):
        worker.main()
    assert observed == [True], "cleanup proof must already exist before completion publication starts"
    assert json.loads((session / "descendant_cleanup.json").read_text())["all_reaped"] is True
