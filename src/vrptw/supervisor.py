"""Opt-in process isolation and original-space, pre-cutoff incumbent delivery."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import resource
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

from .core import Plan
from .native_certification import NativeNoSolutionError, routes_sha256, validate_routes


class SupervisorProtocolError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise SupervisorProtocolError(message)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def atomic_json(path, payload):
    """One writer, fresh session; incomplete .pending files are never delivered."""
    require(not path.exists(), f"message already exists: {path.name}")
    temporary = path.with_suffix(".pending")
    with temporary.open("x") as stream:
        json.dump(payload, stream, allow_nan=False)
    os.replace(temporary, path)


def read_json(path):
    return json.loads(path.read_text())


def check_descendant_cleanup(session, request, worker_pid):
    """Check owned cleanup evidence only; never admit routes from shutdown files."""
    try:
        record = read_json(session / "descendant_cleanup.json")
        require(
            record["token"] == request["token"]
            and record["identity"] == request["identity"]
            and record["worker_pid"] == worker_pid,
            "foreign descendant cleanup",
        )
        require(record["all_reaped"] is True, "descendant cleanup incomplete")
        require(
            finite(record["closed_perf"])
            and record["closed_perf"] <= time.perf_counter()
            and finite(record["descendant_cpu_sec"])
            and record["descendant_cpu_sec"] >= 0,
            "invalid descendant resource/clock evidence",
        )
        entries = record["processes"]
        require(isinstance(entries, list), "invalid descendant registry")
        for index, entry in enumerate(entries, 1):
            require(
                type(entry["pid"]) is int
                and entry["pid"] > 0
                and entry["reaped"] is True
                and type(entry["returncode"]) is int,
                "unreaped descendant",
            )
            require(
                finite(entry["spawn_perf"])
                and finite(entry["reaped_perf"])
                and entry["spawn_perf"] <= entry["reaped_perf"] <= record["closed_perf"],
                "descendant clock drift",
            )
            for phase in ("start", "stop"):
                name = f"descendant_{index:06d}_{phase}.json"
                require(entry[f"{phase}_file"] == name, "descendant event path drift")
                encoded = (session / name).read_bytes()
                require(hashlib.sha256(encoded).hexdigest() == entry[f"{phase}_sha256"], "descendant event hash drift")
                event = json.loads(encoded)
                require(
                    event["token"] == request["token"]
                    and event["worker_pid"] == worker_pid
                    and event["pid"] == entry["pid"]
                    and event["spawn_perf"] == entry["spawn_perf"],
                    "descendant event identity drift",
                )
                if phase == "stop":
                    require(
                        all(event[key] == entry[key] for key in ("returncode", "reaped", "reaped_perf")),
                        "descendant stop drift",
                    )
        require(len(list(session.glob("descendant_*_start.json"))) == len(entries), "unclosed descendant event")
        return record
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise SupervisorProtocolError(f"invalid descendant cleanup: {exc}") from exc


class SupervisorIncumbent:
    def __init__(self, inst, *, start, deadline, token, clock=time.perf_counter):
        require(finite(start) and finite(deadline) and deadline > start, "invalid supervisor clock")
        self.inst, self.start, self.deadline, self.token, self.clock = inst, start, deadline, token, clock
        self.best, self.checkpoint, self.sequence = None, None, 0
        self.worker_received_perf = None
        self.trajectory, self.receipts = [], []
        self.diagnostics = {
            "schema_version": 1,
            "status": "searching",
            "clock": "perf_counter",
            "policy": "worker capture, supervisor receipt and independent original-space validation strictly before cutoff",
            "cutoff_sec": deadline - start,
            "hard_return_deadline": False,
            "certificate": None,
            "rejected_late": 0,
        }

    def offer(self, packet):
        received = self.clock()
        if received >= self.deadline:
            self.diagnostics["rejected_late"] += 1
            self.receipts.append(
                {
                    "sequence": packet.get("sequence") if isinstance(packet, dict) else None,
                    "receipt_sec": received - self.start,
                    "validated_sec": None,
                    "admitted": False,
                    "reason": "late_receipt",
                }
            )
            return False
        try:
            require(packet["token"] == self.token, "foreign session")
            require(
                packet["start_perf"] == self.start and packet["deadline_perf"] == self.deadline, "foreign solve clock"
            )
            require(
                type(packet["sequence"]) is int and packet["sequence"] == self.sequence + 1, "packet sequence drift"
            )
            routes, cert = copy.deepcopy(packet["routes"]), copy.deepcopy(packet["certificate"])
            require(isinstance(routes, list) and all(isinstance(r, list) for r in routes), "invalid route container")
            require(all(type(n) is int for r in routes for n in r), "invalid customer IDs")
            require(
                cert["clock"] == "perf_counter" and cert["cutoff_sec"] == self.deadline - self.start,
                "certificate clock drift",
            )
            captured = cert["captured_sec"]
            require(
                finite(captured) and 0 <= captured <= received - self.start < cert["cutoff_sec"],
                "invalid worker capture time",
            )
            require(
                self.worker_received_perf is None or captured + self.start >= self.worker_received_perf,
                "capture precedes worker start receipt",
            )
            cost = validate_routes(routes, self.inst)
            require(cost is not None, "original-space feasibility failure")
            require(type(cert["nv"]) is int and cert["nv"] == len(routes), "fleet mismatch")
            require(finite(cert["td"]) and cert["td"] == cost, "distance mismatch")
            require(cert["routes_sha256"] == routes_sha256(routes), "route hash mismatch")
            require(
                all(cert["validation"][k] is True for k in ("exact_cover", "route_feasible", "objective_recomputed")),
                "invalid validation evidence",
            )
            require(
                isinstance(cert["phase"], str) and type(cert["iter"]) is int and cert["iter"] >= 0,
                "invalid capture context",
            )
            plan = Plan(routes, self.inst, "Native-Supervised")
            plan._cost, plan._ok = cost, True
            checkpoint = copy.deepcopy(packet.get("checkpoint"))
        except (KeyError, TypeError, ValueError) as exc:
            raise SupervisorProtocolError(f"malformed incumbent packet: {exc}") from exc
        validated = self.clock()
        self.sequence = packet["sequence"]
        if validated >= self.deadline:
            self.diagnostics["rejected_late"] += 1
            self.receipts.append(
                {
                    "sequence": self.sequence,
                    "receipt_sec": received - self.start,
                    "validated_sec": validated - self.start,
                    "admitted": False,
                    "reason": "late_validation",
                }
            )
            return False
        improve = (
            self.best is None or plan.nv < self.best.nv or (plan.nv == self.best.nv and cost < self.best.cost - 1e-6)
        )
        self.receipts.append(
            {
                "sequence": self.sequence,
                "receipt_sec": received - self.start,
                "validated_sec": validated - self.start,
                "admitted": improve,
            }
        )
        if not improve:
            return False
        cert.update(
            worker_captured_sec=captured, receipt_sec=received - self.start, captured_sec=validated - self.start
        )
        self.best, self.checkpoint = plan, checkpoint
        self.diagnostics["certificate"] = cert
        self.trajectory.append(
            {
                "t_sec": validated - self.start,
                "nv": plan.nv,
                "td": cost,
                "phase": cert["phase"],
                "iter": cert["iter"],
                "routes_sha256": cert["routes_sha256"],
            }
        )
        return True

    def finish(self):
        self.diagnostics["elapsed_sec"] = self.clock() - self.start
        if self.best is None:
            self.diagnostics["status"] = "no_certified_incumbent"
            raise NativeNoSolutionError("Supervisor has no certified incumbent received and validated before cutoff")
        self.diagnostics["status"] = "certified"
        return self.best


def _cpu(kind):
    usage = resource.getrusage(kind)
    return usage.ru_utime + usage.ru_stime


def _stop_worker(process):
    info = {"terminate_sent": False, "kill_sent": False}
    if process.poll() is None:
        info["terminate_sent"] = True
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=0.1)
        except subprocess.TimeoutExpired:
            info["kill_sent"] = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                pass
    info.update(worker_reaped=process.poll() is not None, worker_returncode=process.returncode)
    return info


def supervise(inst, worker_script, request, session, *, setup_timeout=120.0):
    """Run one owned POSIX native worker; all solve IPC/validation/cleanup is timed."""
    require(os.name == "posix", "native supervisor currently supports POSIX process groups")
    budget = request["time_limit"]
    require(finite(budget) and budget > 0 and finite(setup_timeout) and setup_timeout > 0, "invalid budget")
    session = session.resolve()
    session.mkdir(parents=True, exist_ok=False)
    work, cache = session / "work", session / "cache"
    work.mkdir()
    cache.mkdir()
    token = uuid.uuid4().hex
    request = {**request, "session_dir": str(session), "token": token}
    atomic_json(session / "request.json", request)
    overrides = {
        **dict.fromkeys(("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"), "1"),
        "NUMBA_CACHE_DIR": str(cache),
        "NUMBA_DISABLE_JIT": "0",
        "PYTHONHASHSEED": "42",
    }
    command = [sys.executable, str(Path(worker_script).resolve()), str(session / "request.json")]
    result = {
        "execution_mode": "native_supervisor_v1",
        "command": command,
        "worker_environment_overrides": overrides,
        "final_worker_counters": None,
        "worker_completion": None,
    }
    origin, cpu_self, cpu_child = time.perf_counter(), _cpu(resource.RUSAGE_SELF), _cpu(resource.RUSAGE_CHILDREN)
    start, admission, process, plan = None, None, None, None
    seen, packets = set(), []
    try:
        with (session / "worker.stdout.log").open("x") as stdout, (session / "worker.stderr.log").open("x") as stderr:
            process = subprocess.Popen(
                command, cwd=work, env={**os.environ, **overrides}, stdout=stdout, stderr=stderr, start_new_session=True
            )
        result["worker_pid"] = process.pid
        atomic_json(
            session / "launch.json",
            {
                "worker_pid": process.pid,
                "command": command,
                "cwd": str(work),
                "environment": overrides,
                "launch_start_perf": origin,
            },
        )
        while not (session / "ready.json").exists():
            require(process.poll() is None, f"worker exited during setup: {process.returncode}")
            require(time.perf_counter() - origin < setup_timeout, "worker setup timeout")
            time.sleep(0.002)
        ready = read_json(session / "ready.json")
        observed = time.perf_counter()
        require(ready["identity"] == request["identity"], "worker identity drift")
        require(ready["cold_start_evidence"] == request["expected_cold"], "worker cold-state drift")
        entry = ready["entry"]
        require(entry["cwd"] == str(work) and entry["cache_dir"] == str(cache), "worker directory drift")
        require(entry["work_entries"] == entry["cache_entries"] == [], "nonempty worker entry directories")
        require(
            ready["jit_environment"]
            == {k: overrides[k] for k in ("NUMBA_DISABLE_JIT", "NUMBA_CACHE_DIR", "PYTHONHASHSEED")},
            "worker JIT environment drift",
        )
        require(
            ready["effective_numba"]["cache_dir"] == str(cache) and ready["effective_numba"]["disable_jit"] is False,
            "effective worker JIT drift",
        )
        require(
            finite(ready["worker_ready_perf"]) and origin <= ready["worker_ready_perf"] <= observed,
            "worker ready clock drift",
        )
        result["worker_ready"] = ready
        start = time.perf_counter()
        deadline = start + budget
        admission = SupervisorIncumbent(inst, start=start, deadline=deadline, token=token)
        start_message = {"token": token, "start_perf": start, "deadline_perf": deadline}
        atomic_json(session / "start.json", start_message)
        result.update(solve_start_perf=start, solve_deadline_perf=deadline)

        def acknowledge():
            if "worker_ack" in result:
                return True
            if not (session / "ack.json").exists():
                return False
            ack = read_json(session / "ack.json")
            require(all(ack[k] == start_message[k] for k in start_message), "worker acknowledgment drift")
            require(
                finite(ack["worker_received_perf"]) and start <= ack["worker_received_perf"] <= time.perf_counter(),
                "worker clock drift",
            )
            result["worker_ack"] = ack
            admission.worker_received_perf = ack["worker_received_perf"]
            return True

        acknowledged = False
        while time.perf_counter() < deadline:
            acknowledged = acknowledge()
            for path in sorted(session.glob("incumbent_*.json")):
                if path.name in seen or time.perf_counter() >= deadline:
                    continue
                require(acknowledged or acknowledge(), "incumbent before start acknowledgment")
                encoded = path.read_bytes()
                packet = json.loads(encoded)
                require(int(path.stem.rsplit("_", 1)[1]) == packet["sequence"], "packet filename mismatch")
                admitted = admission.offer(packet)
                packets.append({"file": path.name, "sha256": hashlib.sha256(encoded).hexdigest(), "admitted": admitted})
                seen.add(path.name)
            if process.poll() is not None:
                # The worker may publish and exit after this iteration's scan.
                if any(path.name not in seen for path in session.glob("incumbent_*.json")):
                    continue
                result["stop_reason"] = "worker_exit"
                require(process.returncode == 0, f"worker failed: {process.returncode}")
                break
            remaining = deadline - time.perf_counter()
            if remaining > 0:
                time.sleep(min(0.002, remaining))
        else:
            result["stop_reason"] = "cutoff"
    except Exception as exc:
        result.update(error=f"{type(exc).__name__}: {exc}", stop_reason="protocol_or_worker_error")
    finally:
        if process is not None:
            result["cleanup_start_perf"] = time.perf_counter()
            result.update(_stop_worker(process))
            result["cleanup_end_perf"] = time.perf_counter()
            if not result["worker_reaped"]:
                result["error"] = "SupervisorProtocolError: worker was not reaped"
            if request.get("descendant_cleanup_required"):
                try:
                    result["descendant_cleanup"] = check_descendant_cleanup(session, request, process.pid)
                    result["descendants_reaped"] = True
                except SupervisorProtocolError as exc:
                    result.update(descendants_reaped=False, error=f"{type(exc).__name__}: {exc}")
                result["cleanup_end_perf"] = time.perf_counter()
        if (session / "completion.json").exists():
            try:
                completion = read_json(session / "completion.json")
                require(
                    completion["token"] == token and completion["identity"] == request["identity"],
                    "completion identity drift",
                )
                result["worker_completion"] = completion
                if "error" in completion:
                    result["error"] = completion["error"]
                else:
                    result["final_worker_counters"] = completion.get("counters")
            except Exception as exc:
                result["error"] = f"{type(exc).__name__}: {exc}"
        if admission is not None:
            try:
                candidate = admission.finish()
                if "error" not in result:
                    plan = candidate
            except NativeNoSolutionError as exc:
                result.setdefault("error", f"{type(exc).__name__}: {exc}")
            result.update(
                native_certification=admission.diagnostics,
                trajectory=admission.trajectory,
                worker_checkpoint=admission.checkpoint,
                receipts=admission.receipts,
            )
        result["runtime_sec"] = None if start is None else time.perf_counter() - start
        result["end_to_end_wall_sec"] = time.perf_counter() - origin
        result["resource_usage"] = {
            "parent_cpu_sec": _cpu(resource.RUSAGE_SELF) - cpu_self,
            "worker_cpu_sec": _cpu(resource.RUSAGE_CHILDREN) - cpu_child,
        }
        result["packet_observations"] = packets
    return plan, result
