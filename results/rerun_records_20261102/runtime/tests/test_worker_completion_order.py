"""Execute the actual worker main body with controlled stdlib-only dependencies."""

import ast
import copy
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest


def run_main(tmp_path, behavior):
    events, holder = [], {}
    session = tmp_path / "session"
    session.mkdir()
    (session / "start.json").write_text("{}")
    cfg = SimpleNamespace(seed=42, output_dir=str(session / "work/archive"), neurolkh_root="backend")
    case = "alns" if behavior == "no_owner" else "neurolkh"
    identity = {
        "case": case,
        "seed": 42,
        "requested_config": vars(cfg).copy(),
        "instance_sha256": "input",
        "gnn_model_sha256": None,
        "source_sha256": "source",
        "backend_identity": "backend",
    }
    request = {
        "session_dir": str(session),
        "identity": identity,
        "token": "token",
        "time_limit": 60,
        "gnn_model": None,
        "instance": str(tmp_path / "input.txt"),
        "neurolkh_root": "backend",
    }

    def publish(path, value):
        events.append(path.name)
        path.write_text(json.dumps(value))

    class Owner:
        def __init__(self, *args, **kwargs):
            holder["owner"] = self
            self.closed = False

        def install(self):
            events.append("install")

        def close(self):
            if not self.closed:
                publish(session / "descendant_cleanup.json", {"all_reaped": True})
                self.closed = True

    class Failure(RuntimeError):
        def __str__(self):
            events.append("format_error")
            return "controlled solver error"

    class Solver:
        def __init__(self, inst, config):
            self.cfg = config
            self.diagnostics = {"assets": {"unused": True}}
            self.search_iterations = 1
            self.native_certification = {"certificate": None}

        def solve(self, **kwargs):
            events.append("solve")
            if behavior == "solver_error":
                raise Failure()

    def instrumentation(*args):
        events.append("counters")
        if behavior == "blocked_counters":
            # Controlled interruption point: mandatory proof must already exist.
            assert (session / "descendant_cleanup.json").exists()
        if behavior == "counter_error":
            raise RuntimeError("optional counter failure")
        return {}

    cli = SimpleNamespace(
        get_solver_and_config=lambda *a, **k: (Solver, cfg),
        sha256_file=lambda path: "input",
        load_solomon_instance=lambda path: object(),
        cold_start_state=lambda solver: {},
        get_env_info=lambda: {
            "source_sha256": "source",
            "process_entry": {"cwd": "work", "cache_dir": "cache", "cwd_entries": [], "cache_entries": []},
            "jit_environment": {},
            "numba": {},
        },
        PROCESS_ENTRY_TIME=time.perf_counter(),
        extract_instrumentation=instrumentation,
    )

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    worker = Path(__file__).parents[1] / "scripts/native_supervisor_worker.py"
    tree = ast.parse(worker.read_text())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    namespace = {
        "sys": SimpleNamespace(argv=["worker", "request.json"]),
        "Path": Path,
        "time": time,
        "asdict": lambda obj: vars(obj).copy(),
        "deepcopy": copy.deepcopy,
        "cli": cli,
        "backend_identity": lambda *a: "backend",
        "BackendProcesses": Owner,
        "NativeIncumbent": lambda *a, **k: object(),
        "atomic_json": publish,
        "require": require,
        "read_json": lambda path: (
            request if path.name == "request.json" else {"token": "token", "start_perf": 1.0, "deadline_perf": 61.0}
        ),
    }
    exec(compile(ast.Module(body=[main], type_ignores=[]), str(worker), "exec"), namespace)
    code = namespace["main"]()
    return code, events, json.loads((session / "completion.json").read_bytes())


@pytest.mark.parametrize("behavior,expected_code", [("normal", 0), ("blocked_counters", 0), ("counter_error", 1)])
def test_cleanup_receipt_precedes_optional_counters(tmp_path, behavior, expected_code):
    code, events, payload = run_main(tmp_path, behavior)
    assert code == expected_code
    assert events.index("descendant_cleanup.json") < events.index("counters")
    assert events.count("descendant_cleanup.json") == 1
    assert events[-1] == "completion.json"
    assert ("error" in payload) is (expected_code == 1)


def test_solver_error_cleanup_precedes_error_payload_formatting(tmp_path):
    code, events, payload = run_main(tmp_path, "solver_error")
    assert code == 1
    assert events.index("descendant_cleanup.json") < events.index("format_error")
    assert events.count("descendant_cleanup.json") == 1
    assert "controlled solver error" in payload["error"]


def test_non_descendant_worker_still_publishes_its_completion(tmp_path):
    code, events, payload = run_main(tmp_path, "no_owner")
    assert code == 0 and "error" not in payload
    assert "descendant_cleanup.json" not in events
    assert events[-1] == "completion.json"
