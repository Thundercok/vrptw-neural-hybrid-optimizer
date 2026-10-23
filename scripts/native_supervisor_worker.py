#!/usr/bin/env python3
"""Owned fresh native worker. Run through benchmark_supervised.py."""

from __future__ import annotations

import sys
import time
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

import benchmark as cli
from benchmark_supervised import backend_identity

from vrptw.native_certification import NativeIncumbent
from vrptw.supervised_process import BackendProcesses
from vrptw.supervisor import atomic_json, read_json, require


def main():
    request = read_json(Path(sys.argv[1]))
    session, identity = Path(request["session_dir"]), request["identity"]
    solver, owner = None, None
    try:
        solver_cls, cfg = cli.get_solver_and_config(
            identity["case"],
            request["time_limit"],
            seed=identity["seed"],
            gnn_model=Path(request["gnn_model"]) if request["gnn_model"] else None,
        )
        if identity["case"] == "neurolkh":
            cfg.neurolkh_root = request["neurolkh_root"]
        cfg.output_dir = str(session / "work/archive")
        require(asdict(cfg) == identity["requested_config"], "requested worker config drift")
        require(cli.sha256_file(Path(request["instance"])) == identity["instance_sha256"], "worker input drift")
        model_hash = cli.sha256_file(Path(request["gnn_model"])) if request["gnn_model"] else None
        require(model_hash == identity["gnn_model_sha256"], "worker model drift")
        inst = cli.load_solomon_instance(request["instance"])
        setup = time.perf_counter()
        solver = solver_cls(inst, cfg)
        constructor_sec = time.perf_counter() - setup
        cold = cli.cold_start_state(solver)
        model_start = time.perf_counter()
        if request["gnn_model"]:
            solver.load_gnn_model(request["gnn_model"])
            require(solver.gnn_model is not None, "requested worker GNN was not loaded")
        model_sec = time.perf_counter() - model_start
        require(
            backend_identity(identity["case"], cfg) == identity.get("backend_identity"), "worker backend assets drift"
        )
        environment = cli.get_env_info()
        require(environment["source_sha256"] == identity["source_sha256"], "worker source drift")
        entry = environment["process_entry"]
        atomic_json(
            session / "ready.json",
            {
                "identity": identity,
                "cold_start_evidence": cold,
                "environment": environment,
                "entry": {
                    "cwd": entry["cwd"],
                    "cache_dir": entry["cache_dir"],
                    "work_entries": entry["cwd_entries"],
                    "cache_entries": entry["cache_entries"],
                },
                "jit_environment": environment["jit_environment"],
                "effective_numba": environment["numba"],
                "setup_timings": {
                    "constructor_sec": constructor_sec,
                    "model_load_sec": model_sec,
                    "entry_to_ready_sec": time.perf_counter() - cli.PROCESS_ENTRY_TIME,
                },
                "worker_ready_perf": time.perf_counter(),
            },
        )
        if identity["case"] == "neurolkh":
            owner = BackendProcesses(session, identity=identity, token=request["token"])
            owner.install()
        while not (session / "start.json").exists():
            time.sleep(0.002)
        start = read_json(session / "start.json")
        require(start["token"] == request["token"], "foreign worker start")
        received = time.perf_counter()
        atomic_json(session / "ack.json", {**start, "worker_received_perf": received})
        sequence = 0

        def snapshot():
            result = {
                "effective_config": asdict(solver.cfg),
                "instrumentation": cli.extract_instrumentation(solver, solver.cfg, identity["case"]),
                "iterations": int(getattr(solver, "search_iterations", 0)),
            }
            if identity["case"] in ("pyvrp", "neurolkh"):
                diagnostics = deepcopy(solver.diagnostics)
                diagnostics.pop("assets", None)  # The full asset identity is already bound in request/ready.
                result["adapter_diagnostics"] = diagnostics
                result["iterations"] = diagnostics.get("ils_iterations") if identity["case"] == "pyvrp" else None
                result["iteration_scope"] = "completed PyVRP ILS total or null; NeuroLKH trial total unavailable"
            return result

        def publish(payload):
            nonlocal sequence
            sequence += 1
            atomic_json(
                session / f"incumbent_{sequence:06d}.json",
                {**start, "sequence": sequence, **payload, "checkpoint": snapshot()},
            )

        tracker = NativeIncumbent(
            inst,
            start=start["start_perf"],
            deadline=start["deadline_perf"],
            clock=time.perf_counter,
            on_capture=publish,
        )
        extra = {"_process_owner": owner} if owner is not None else {}
        solver.solve(seed=identity["seed"], _certifier=tracker, **extra)
        atomic_json(
            session / "completion.json",
            {
                "token": request["token"],
                "identity": identity,
                "counters": snapshot(),
                "native_certification": solver.native_certification,
            },
        )
        return 0
    except Exception as exc:
        failure = {"token": request["token"], "identity": identity, "error": f"{type(exc).__name__}: {exc}"}
        if solver is not None:
            failure["native_certification"] = getattr(solver, "native_certification", None)
        atomic_json(session / "completion.json", failure)
        return 1
    finally:
        if owner is not None:
            owner.close()


if __name__ == "__main__":
    raise SystemExit(main())
