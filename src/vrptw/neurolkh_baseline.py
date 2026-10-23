"""CPU NeuroLKH adaptation: pinned assets, cold fleet-reduction restarts, prefix incumbents."""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType

import numpy as np

from .config import Config
from .core import Inst, Plan
from .integer_baseline import DISTANCE_SCALE, quantize_vrptw

UPSTREAM_URL = "https://github.com/liangxinedu/NeuroLKH.git"
UPSTREAM_COMMIT = "32ab884c2fe6548ca4011eeb181af70fbfedc72b"
CHECKPOINT_SHA256 = "58287b23eedf9eecab5aadcf8ba640b56c50b1b6cfa3259eb39cd443a6072394"
NEIGHBOURS = 20


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def asset_identity(root: Path) -> dict:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if commit != UPSTREAM_COMMIT:
        raise ValueError(f"NeuroLKH requires pinned commit {UPSTREAM_COMMIT}, got {commit}")
    changed = subprocess.check_output(["git", "diff", "HEAD", "--name-only"], cwd=root, text=True)
    if changed.strip():
        raise ValueError("NeuroLKH tracked source/checkpoint is modified; refusing unaudited assets")
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    hashes = {
        name: file_sha256(root / name)
        for name in sorted(files)
        if name and (name.startswith(("SRC/", "net/")) or name in ("CVRPTW_test.py", "Makefile"))
    }
    checkpoint_hash = file_sha256(root / "pretrained/cvrptw_neurolkh.pt")
    if checkpoint_hash != CHECKPOINT_SHA256:
        raise ValueError("NeuroLKH checkpoint hash mismatch")
    return {
        "commit": commit,
        "source_sha256": hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
        "source_files": hashes,
        "checkpoint_sha256": checkpoint_hash,
        "binary_sha256": file_sha256(root / "LKH"),
    }


def neural_features(inst: Inst):
    if inst.n < NEIGHBOURS or not np.isfinite(inst.coords).all():
        raise ValueError("NeuroLKH needs at least 20 customers and finite coordinates")
    scale = float(np.ptp(inst.coords, axis=0).max())
    if scale <= 0:
        raise ValueError("NeuroLKH coordinates need nonzero span")
    coords = (inst.coords - inst.coords.min(axis=0)) / scale
    x = np.column_stack(
        (
            coords,
            inst.demands / 50,
            inst.ready_times / (10 * scale),
            inst.due_times / (10 * scale),
            np.zeros(inst.n + 1),
        )
    )
    x[0, -1] = 1
    # Features use geometry only; constraints use the unnormalised integer model.
    distances = np.linalg.norm(coords[:, None] - coords[None, :], axis=2)
    ranking = distances.copy()
    np.fill_diagonal(ranking, np.inf)
    edges = np.argsort(ranking, axis=1, kind="stable")[:, :NEIGHBOURS]
    inverse = np.full(distances.shape, -1, dtype=np.int64)
    rows = np.arange(inst.n + 1)[:, None]
    inverse[edges, rows] = np.arange((inst.n + 1) * NEIGHBOURS).reshape(-1, NEIGHBOURS)
    return x, distances[rows, edges], edges, inverse[rows, edges], scale


def write_candidates(path: Path, outgoing: np.ndarray, incoming: np.ndarray, vehicles: int):
    n = len(outgoing) - 1
    base = n + vehicles
    if not 1 <= vehicles <= n or outgoing.shape != incoming.shape or outgoing.shape != (n + 1, NEIGHBOURS):
        raise ValueError("Invalid NeuroLKH candidate shape/fleet")
    if any(not np.isfinite(a).all() or (a < 0).any() or (a > n).any() for a in (outgoing, incoming)):
        raise ValueError("Invalid neural candidate indices")
    lines = [str(2 * base)]
    # Each split node has its fixed mate plus four ranked opposite-half arcs.
    for half in (0, 1):
        offset, opposite = half * base, (1 - half) * base
        for node in range(1, base + 1):
            if 2 <= node <= n + 1:
                ranked = (outgoing if half else incoming)[node - 1]
                choices = [int(idx) + 1 for idx in ranked]
            elif node > n + 1 and half == 0:
                choices = [1, *range(n + 2, base + 1), *range(2, n + 2)]
            else:
                choices = list(range(base, n + 1, -1)) + [1] + list(range(2, n + 2))
            selected = list(dict.fromkeys(idx for idx in choices if idx != node))[:4]
            if len(selected) != 4:
                raise ValueError("Insufficient distinct candidates")
            arcs = [node + opposite, 0 if node == 1 or node > n + 1 else 1]
            arcs += [value for idx in selected for value in (idx + opposite, 1)]
            lines.append(" ".join(map(str, [node + offset, 0, 5, *arcs])))
    path.write_text("\n".join([*lines, "-1", "EOF", ""]), encoding="ascii")


def integer_data(inst: Inst) -> dict:
    if inst.n < NEIGHBOURS:
        raise ValueError("NeuroLKH requires at least 20 customers")
    q = quantize_vrptw(inst)
    service = np.ceil(inst.service_times * q.scale).astype(np.int64)
    distance = q.transit - service[:, None]
    # LKH uses signed 32-bit arc costs, including an INT_MAX/2 forbidden sentinel.
    limit = np.iinfo(np.int32).max // 2
    if int(distance.max()) >= limit or max(map(int, q.demands)) >= limit or q.capacity >= limit:
        raise ValueError("NeuroLKH data outside safe 32-bit backend range")
    return {
        "distance": distance,
        "service": service,
        "ready": q.ready,
        "due": q.due,
        "demands": q.demands,
        "capacity": q.capacity,
    }


def write_problem(path: Path, inst: Inst, vehicles: int) -> dict:
    if not 1 <= vehicles <= inst.n:
        raise ValueError("Invalid fleet")
    data = integer_data(inst)
    lines = [
        "NAME : benchmark",
        "TYPE : CVRPTW",
        f"DIMENSION : {inst.n + 1}",
        f"VEHICLES : {vehicles}",
        f"CAPACITY : {data['capacity']}",
        "EDGE_WEIGHT_TYPE : EXPLICIT",
        "EDGE_WEIGHT_FORMAT : FULL_MATRIX",
        "EDGE_WEIGHT_SECTION",
        *(" ".join(map(str, row)) for row in data["distance"]),
        "DEMAND_SECTION",
        *(f"{i + 1} {demand}" for i, demand in enumerate(data["demands"])),
        "TIME_WINDOW_SECTION",
        *(f"{i + 1} {a} {b}" for i, (a, b) in enumerate(zip(data["ready"], data["due"], strict=True))),
        "SERVICE_TIME_SECTION",
        *(f"{i + 1} {service}" for i, service in enumerate(data["service"])),
        "DEPOT_SECTION",
        "1",
        "-1",
        "EOF",
        "",
    ]
    path.write_text("\n".join(lines), encoding="ascii")
    return data


def write_parameters(path: Path, seed: int):
    path.write_text(
        "PROBLEM_FILE = instance.vrp\nCANDIDATE_FILE = candidates.txt\n"
        "OUTPUT_TOUR_FILE = incumbent.tour\nSPECIAL\nSUBGRADIENT = NO\n"
        "RUNS = 1\nMAX_TRIALS = 2147483647\nSTOP_AT_OPTIMUM = NO\n"
        f"SEED = {seed}\nPRECISION = 1\nMTSP_MIN_SIZE = 0\nTRACE_LEVEL = 0\n",
        encoding="ascii",
    )


def parse_tour(text: str, customers: int, vehicles: int) -> list[list[int]]:
    lines = [line.strip() for line in text.splitlines()]
    if not lines or lines[-1] != "EOF" or "TOUR_SECTION" not in lines:
        raise ValueError("Incomplete tour")
    start = lines.index("TOUR_SECTION") + 1
    tokens = [int(line) for line in lines[start:-1]]
    if not tokens or tokens.pop() != -1 or sorted(tokens) != list(range(1, customers + vehicles + 1)):
        raise ValueError("Tour is not a complete transformed-node permutation")
    depot = tokens.index(1)
    tokens = tokens[depot:] + tokens[:depot] + [1]
    routes, route = [], []
    for node in tokens:
        if node == 1 or node > customers + 1:
            if route:
                routes.append(route)
                route = []
        else:
            route.append(node - 1)
    return routes


class NeuroLKHNoSolutionError(RuntimeError):
    """No original-feasible incumbent was fully captured before the solve cutoff."""


class NeuroLKHSolver:
    def __init__(self, inst: Inst, cfg: Config):
        import torch

        self.inst, self.cfg, self.torch = inst, cfg, torch
        self.root = Path(cfg.neurolkh_root).resolve()
        manifest = json.loads((self.root / "assets.json").read_text())
        self.assets = asset_identity(self.root)
        if self.assets != manifest["identity"]:
            raise ValueError("NeuroLKH assets differ from prepared build manifest")
        self.assets["build"] = manifest["build"]
        # Avoid executing an unrelated 'net' package from site-packages or cwd.
        if "net" not in sys.modules:
            package = ModuleType("net")
            package.__path__ = [str(self.root / "net")]
            sys.modules["net"] = package
        if list(sys.modules["net"].__path__) != [str(self.root / "net")]:
            raise ValueError("Conflicting net package already imported")
        module = importlib.import_module("net.sgcn_model")
        self.model = module.SparseGCNModel(problem="cvrptw").cpu()
        weights = torch.load(self.root / "pretrained/cvrptw_neurolkh.pt", map_location="cpu", weights_only=True)[
            "model"
        ]
        if len(weights) != 584 or any(not torch.isfinite(tensor).all().item() for tensor in weights.values()):
            raise ValueError("Invalid NeuroLKH checkpoint tensors")
        self.model.load_state_dict(weights, strict=True)
        self.model.eval()
        self.diagnostics, self.trajectory_log = {}, []
        self.search_iterations, self.elapsed_sec, self.time_limit_hit = 0, 0.0, False
        self._best_plan, self._best_key = None, (math.inf, math.inf)
        self._certifier = None
        self.native_certification = None

    def _infer(self):
        torch = self.torch
        x, distances, edges, inverse, scale = neural_features(self.inst)
        with torch.inference_mode():
            first, second, *_ = self.model.directed_forward(
                torch.tensor(x, dtype=torch.float32)[None],
                torch.tensor(distances.reshape(1, -1, 1), dtype=torch.float32),
                torch.tensor(edges.reshape(1, -1), dtype=torch.int64),
                torch.tensor(inverse.reshape(1, -1), dtype=torch.int64),
                None,
                None,
                None,
                NEIGHBOURS,
            )
        ranked = []
        for scores in (first, second):
            scores = scores[0, :, 1].reshape(self.inst.n + 1, NEIGHBOURS).numpy()
            if not np.isfinite(scores).all():
                raise ValueError("Nonfinite NeuroLKH inference")
            ranked.append(np.take_along_axis(edges, np.argsort(-scores, axis=1, kind="stable"), axis=1))
        self.diagnostics["feature_scale"] = scale
        return ranked

    def _capture_tour(self, path: Path, vehicles: int):
        if time.perf_counter() >= self._deadline or not path.is_file():
            return
        text = path.read_text(encoding="ascii")
        try:
            routes = parse_tour(text, self.inst.n, vehicles)
        except ValueError:
            return
        if time.perf_counter() >= self._deadline:
            return
        plan = Plan(routes, self.inst, "NeuroLKH-adapted")
        if not plan.feasible:
            self.diagnostics["invalid_original_tours"] += 1
            return
        key = (int(plan.nv), float(plan.cost))
        captured = time.perf_counter()
        if captured >= self._deadline or key >= self._best_key:
            return
        self._best_key, self._best_plan = key, plan
        self.diagnostics.update(incumbent_capture_sec=captured - self._start, selected_fleet_target=vehicles)
        self.trajectory_log.append({"t_sec": captured - self._start, "nv": key[0], "td": key[1], "phase": "incumbent"})
        if getattr(self, "_certifier", None) is not None:
            self._certifier.consider(plan, phase="neurolkh_tour")
        path.with_name("captured.tour").write_text(text, encoding="ascii")

    @staticmethod
    def _stop_process(process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def solve(self, seed: int | None = None, *, _certifier=None, _process_owner=None) -> tuple[Plan, list[float]]:
        seed = self.cfg.seed if seed is None else seed
        budget = self.cfg.time_limit
        if budget is None or not math.isfinite(budget) or budget <= 0:
            raise ValueError("NeuroLKH needs a finite positive solve budget")
        if seed is None or int(seed) != seed or not 1 <= seed <= 2_147_483_647:
            raise ValueError("NeuroLKH seed must be a positive signed 32-bit integer")
        self._certifier = _certifier
        self.native_certification = _certifier.diagnostics if _certifier is not None else None
        self._start = _certifier.start if _certifier is not None else time.perf_counter()
        self._deadline = _certifier.deadline if _certifier is not None else self._start + budget
        self._best_plan, self._best_key = None, (math.inf, math.inf)
        self.trajectory_log = []
        self.search_iterations, self.time_limit_hit = 0, False
        self.diagnostics = {
            "status": "preparing",
            "seed": int(seed),
            "requested_budget_sec": budget,
            "assets": self.assets,
            "backend": "adapted NeuroLKH CVRPTW, CPU, cold fleet-reduction restarts",
            "timer_scope": "solve includes features/inference/files/backend/poll validation/cleanup; excludes imports/checkpoint load",
            "objective": "lexicographic (original-feasible fleet, original TD); restart at max(capacity lower bound, best fleet - 1)",
            "distance_scale": DISTANCE_SCALE,
            "distance_rounding": "ceil for both travel cost and time",
            "time_rounding": "travel/service/ready ceil; due floor; conservative inner approximation",
            "distance_error_bound": 2 * self.inst.n / DISTANCE_SCALE,
            "invalid_original_tours": 0,
            "stages": [],
            "model_device": "cpu",
            "model_training": False,
        }
        if _certifier is not None and time.perf_counter() >= self._deadline:
            raise NeuroLKHNoSolutionError("NeuroLKH parent budget exhausted before inference")
        integer_data(self.inst)
        self.torch.manual_seed(int(seed))
        base = Path(self.cfg.output_dir) / "neurolkh"
        base.mkdir(parents=True, exist_ok=False)
        inference_start = time.perf_counter()
        outgoing, incoming = self._infer()
        self.diagnostics["inference_sec"] = time.perf_counter() - inference_start
        self.diagnostics["preparation_sec"] = time.perf_counter() - self._start
        np.savez(base / "candidates.npz", outgoing=outgoing, incoming=incoming)
        lower_bound = max(1, math.ceil(sum(map(int, self.inst.demands)) / int(self.inst.capacity)))
        self.diagnostics["capacity_fleet_lower_bound"] = lower_bound
        vehicles = self.inst.n
        while time.perf_counter() < self._deadline and not (_process_owner and _process_owner.stop_requested):
            stage = base / f"stage_{len(self.diagnostics['stages']):03d}_fleet{vehicles}"
            stage.mkdir()
            write_problem(stage / "instance.vrp", self.inst, vehicles)
            write_candidates(stage / "candidates.txt", outgoing, incoming, vehicles)
            write_parameters(stage / "solver.par", int(seed))
            if time.perf_counter() >= self._deadline or (_process_owner and _process_owner.stop_requested):
                break
            entry = {"fleet_target": vehicles, "seed": int(seed), "start_sec": time.perf_counter() - self._start}
            self.diagnostics["stages"].append(entry)
            process = None
            restart = False
            try:
                with (stage / "stdout.log").open("w") as stdout, (stage / "stderr.log").open("w") as stderr:
                    spawn = _process_owner.spawn if _process_owner is not None else subprocess.Popen
                    process = spawn([str(self.root / "LKH"), "solver.par"], cwd=stage, stdout=stdout, stderr=stderr)
                    if process is None:
                        break
                    seen = None
                    while time.perf_counter() < self._deadline:
                        tour = stage / "incumbent.tour"
                        try:
                            stat = tour.stat()
                            identity = (stat.st_mtime_ns, stat.st_size)
                        except FileNotFoundError:
                            identity = None
                        if identity is not None and identity != seen:
                            self._capture_tour(tour, vehicles)
                            seen = identity
                        if self._best_plan is not None:
                            target = max(lower_bound, self._best_plan.nv - 1)
                            if target < vehicles:
                                vehicles, restart = target, True
                                break
                        if process.poll() is not None:
                            if _process_owner is not None and (
                                _process_owner.stop_requested or time.perf_counter() >= self._deadline
                            ):
                                break
                            raise NeuroLKHNoSolutionError(
                                f"LKH exited early ({process.returncode}); inspect backend logs"
                            )
                        time.sleep(min(0.01, max(0, self._deadline - time.perf_counter())))
            finally:
                if process is not None:
                    if _process_owner is not None:
                        _process_owner.stop(process)
                    else:
                        self._stop_process(process)
                    entry["returncode"] = process.returncode
                entry.update(end_sec=time.perf_counter() - self._start, restart=restart)
            if not restart:
                break
        end = time.perf_counter()
        self.elapsed_sec, self.time_limit_hit = end - self._start, end >= self._deadline
        self.diagnostics["elapsed_sec"] = self.elapsed_sec
        if self._best_plan is None:
            self.diagnostics["status"] = "no_original_feasible_incumbent_before_cutoff"
            raise NeuroLKHNoSolutionError("NeuroLKH found no original-feasible incumbent before solve cutoff")
        self.diagnostics["status"] = "completed"
        plan = _certifier.finish() if _certifier is not None else self._best_plan
        return plan, [point["td"] for point in self.trajectory_log]
