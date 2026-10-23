from __future__ import annotations

import csv
import importlib
import importlib.util
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from numba import njit
from numba.core import event

from vrptw.phase_trace import PhaseTrace, audit_trace

ROOT = Path(__file__).resolve().parents[1]


def tracer(clock):
    return PhaseTrace(SimpleNamespace(_t_start=100.0, _deadline=110.0), clock=lambda: clock.now)


def runner():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location(
            "kernel_diagnostic", ROOT / "scripts/run_kernel_timing_diagnostic.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def test_classmethod_keeps_subclass_binding_and_exact_descriptor_on_restore():
    class Base:
        @classmethod
        def make(cls, value):
            return cls, value

    class Child(Base):
        pass

    original = vars(Base)["make"]
    t = tracer(SimpleNamespace(now=100.0))
    t.patch(Base, "make", "cache.make")
    try:
        assert Child.make(7) == (Child, 7)
        assert Base.make(8) == (Base, 8)
    finally:
        t.restore()
    assert vars(Base)["make"] is original
    assert Child.make(9) == (Child, 9)


def test_inherited_classmethod_restores_by_removing_temporary_override():
    class Base:
        @classmethod
        def make(cls):
            return cls

    class Child(Base):
        pass

    t = tracer(SimpleNamespace(now=100.0))
    t.patch(Child, "make", "cache.make")
    try:
        assert Child.make() is Child
    finally:
        t.restore()
    assert "make" not in vars(Child) and Child.make() is Child


def test_property_getter_is_traced_and_setter_deleter_and_descriptor_survive():
    class Item:
        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, value):
            self._value = value

        @value.deleter
        def value(self):
            del self._value

    original = vars(Item)["value"]
    t = tracer(SimpleNamespace(now=100.0))
    t.patch(Item, "value", "plan.value")
    try:
        item = Item()
        item.value = 12
        assert item.value == 12
        del item.value
        with pytest.raises(AttributeError):
            _ = item.value
        assert [e["name"] for e in t.events] == ["plan.value", "plan.value"]
        assert t.events[-1]["outcome"] == "AttributeError"
    finally:
        t.restore()
    assert vars(Item)["value"] is original


def test_compiler_events_are_nested_monotonic_spans_and_restore_on_exception(tmp_path):
    clock = SimpleNamespace(now=109.0)
    t = tracer(clock)
    t.install_numba_events()
    data = {
        "dispatcher": SimpleNamespace(py_func=test_compiler_events_are_nested_monotonic_spans_and_restore_on_exception),
        "args": ("fixture_type",),
    }

    def compile_event():
        with event.trigger_event("numba:compile", data=data):
            clock.now = 109.5
            with event.trigger_event("numba:compile", data=data):
                clock.now = 111.0
            clock.now = 112.0
            raise ValueError("compiler fixture failure")

    try:
        with pytest.raises(ValueError, match="compiler fixture failure"):
            t.call("solve", compile_event)
    finally:
        t.restore()
    before = len(t.events)
    with event.trigger_event("numba:compile", data=data):
        pass
    assert len(t.events) == before == 3 and t.stack == []
    assert [e["parent_id"] for e in t.events] == [0, 1, 2]
    assert all(e["name"].startswith("numba.compile:") for e in t.events[1:])
    assert all("fixture_type" in e["detail"] for e in t.events[1:])
    path = tmp_path / "compile.csv"
    t.write(path)
    assert audit_trace(path)["post_cutoff_sec"] == 2
    rows = list(csv.DictReader(path.open()))
    assert [float(r["post_cutoff_exclusive_sec"]) for r in rows] == [0, 1, 1]


def test_compiler_listener_ignores_outside_solve_and_other_threads():
    t = tracer(SimpleNamespace(now=100.0))
    t.install_numba_events()
    data = {
        "dispatcher": SimpleNamespace(py_func=test_compiler_listener_ignores_outside_solve_and_other_threads),
        "args": (),
    }

    def emit():
        with event.trigger_event("numba:compile", data=data):
            pass

    try:
        emit()

        def root():
            worker = threading.Thread(target=emit)
            worker.start()
            worker.join()

        t.call("solve", root)
        assert [e["name"] for e in t.events] == ["solve"]
    finally:
        t.restore()


def test_real_jit_event_is_observed_without_replacing_dispatcher(tmp_path):
    @njit
    def tiny(value):
        return value + 1

    t = PhaseTrace(SimpleNamespace(_t_start=0.0, _deadline=1.0))
    t.install_numba_events()
    try:
        assert t.call("solve", tiny, 7) == 8
        assert len(tiny.signatures) == 1
        assert any("tiny" in e["name"] for e in t.events[1:])
        path = tmp_path / "real.csv"
        t.write(path)
        assert audit_trace(path)["spans"] >= 2
    finally:
        t.restore()


def test_install_covers_opaque_python_boundaries_and_leaves_dispatchers_intact():
    local = importlib.import_module("vrptw.local_search")
    from vrptw.core import Plan

    names = ("_two_opt_best", "_best_relocate", "_best_swap", "_best_swap_21", "_best_or_opt")
    functions = {name: getattr(local, name) for name in names}
    descriptor = vars(local._PlanCache)["from_plan"]
    properties = {name: vars(Plan)[name] for name in ("cost", "feasible", "route_arrays")}
    kernels = {name: value for name, value in vars(local).items() if hasattr(value, "py_func")}
    t = tracer(SimpleNamespace(now=100.0))
    t.install()
    try:
        assert all(getattr(local, name) is not value for name, value in functions.items())
        assert vars(local._PlanCache)["from_plan"] is not descriptor
        assert all(vars(Plan)[name] is not value for name, value in properties.items())
        assert all(getattr(local, name) is value for name, value in kernels.items())
    finally:
        t.restore()
    assert all(getattr(local, name) is value for name, value in functions.items())
    assert vars(local._PlanCache)["from_plan"] is descriptor
    assert all(vars(Plan)[name] is value for name, value in properties.items())


@pytest.mark.parametrize("raises", [False, True])
def test_installed_property_trace_excludes_reads_after_solve_even_on_exception(tmp_path, raises):
    from vrptw.core import Plan

    plan = Plan([[1]], SimpleNamespace())
    plan._cost, plan._ok = 3.0, True
    t = tracer(SimpleNamespace(now=100.0))
    t.install()

    def solve():
        _ = plan.route_arrays
        if raises:
            raise ValueError("fixture failure")

    try:
        if raises:
            with pytest.raises(ValueError, match="fixture failure"):
                t.call("solve", solve)
        else:
            t.call("solve", solve)
        assert plan.cost == 3 and plan.feasible and len(plan.route_arrays) == 1
        path = tmp_path / "solve.csv"
        t.write(path)
        assert audit_trace(path)["spans"] == 2
    finally:
        t.restore()


def test_cli_success_trace_has_only_solve_root(monkeypatch, tmp_path):
    import numpy as np

    from vrptw import Inst, Plan
    from vrptw.ablation import AblationHybridSolver

    spec = importlib.util.spec_from_file_location("kernel_cli", ROOT / "scripts/benchmark.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    data = np.zeros((3, 7))
    data[:, 0], data[:, 1], data[:, 5] = range(3), range(3), 100
    data[1:, 3] = 1
    inst = Inst({"name": "trace_scope_fixture", "capacity": 10, "data": data})
    monkeypatch.setattr(cli, "load_solomon_instance", lambda *a: inst)
    monkeypatch.setattr(cli, "get_env_info", lambda: {})

    def solve(solver, **kwargs):
        solver._t_start = cli.time.perf_counter()
        solver._deadline = solver._t_start + 10
        solver.search_iterations, solver.time_limit_hit = 0, False
        return Plan([[1, 2]], inst), []

    monkeypatch.setattr(AblationHybridSolver, "solve", solve)
    output, trace = tmp_path / "raw.json", tmp_path / "trace.csv"
    monkeypatch.setattr(
        cli.sys,
        "argv",
        [
            "benchmark",
            "--instance",
            str(ROOT / "pyproject.toml"),
            "--ablation",
            "F000000",
            "--time-limit",
            "10",
            "--output-json",
            str(output),
            "--phase-trace",
            str(trace),
        ],
    )
    assert cli.main() == 0
    raw = json.loads(output.read_text())
    assert raw["feasible"] and raw["nv"] == 1
    assert audit_trace(trace)["spans"] == 1


def test_installed_repair_dispatch_also_ignores_calls_outside_solve(monkeypatch):
    import vrptw.solvers as solvers

    monkeypatch.setattr(solvers, "REPAIR", [lambda value: value + 1])
    t = tracer(SimpleNamespace(now=100.0))
    t.install()
    try:
        assert t.call("solve", solvers.REPAIR[0], 7) == 8
        assert len(t.events) == 2
        assert solvers.REPAIR[0](7) == 8
        assert len(t.events) == 2
    finally:
        t.restore()


def test_selection_is_exactly_the_five_confirmation_failures():
    module = runner()
    jobs = module.select_jobs(module.PREVIOUS)
    assert [(Path(j["instance"]).stem, j["ablation"]) for j in jobs] == [
        ("R1_2_1", "F101111"),
        ("R1_2_1", "F111111"),
        ("R1_2_1", "F000000"),
        ("c101", "F000000"),
        ("c101", "F111011"),
    ]
    assert len({j["run"] for j in jobs}) == 5
    assert all(j["phase_traced"] and not j["profiled"] and j["seed"] == 42 and j["time_limit"] == 10 for j in jobs)
    assert sum(j["time_limit"] for j in jobs) == 50


@pytest.mark.parametrize("tamper", ["source", "order", "integrity", "hash", "audit_hash", "count"])
def test_selection_rejects_tampered_prior_evidence(tmp_path, tamper):
    module = runner()
    for name in ("plan.json", "audit.json", "summary.csv"):
        (tmp_path / name).write_bytes((module.PREVIOUS / name).read_bytes())
    plan = json.loads((tmp_path / "plan.json").read_text())
    audit = json.loads((tmp_path / "audit.json").read_text())
    if tamper == "source":
        plan["source_sha256"] = "wrong"
    elif tamper == "order":
        plan["jobs"].reverse()
    elif tamper == "integrity":
        audit["verified_runs"][0]["cold_ok"] = False
    elif tamper == "count":
        plan["jobs"].pop()
    audit["artifact_hashes"] = {}
    if tamper == "audit_hash":
        audit["artifact_hashes"]["summary.csv"] = "conflicting audit seal"
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    (tmp_path / "audit.json").write_text(json.dumps(audit))
    manifest = {name: module.sha256(tmp_path / name) for name in ("plan.json", "audit.json", "summary.csv")}
    if tamper == "hash":
        manifest["summary.csv"] = "wrong"
    (tmp_path / "artifact_hashes.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        module.select_jobs(tmp_path)
