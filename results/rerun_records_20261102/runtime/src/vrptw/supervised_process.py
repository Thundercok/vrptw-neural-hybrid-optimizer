"""Opt-in worker ownership of backend children; no PID reconstructed for signals."""

from __future__ import annotations

import copy
import hashlib
import os
import resource
import signal
import subprocess
import time
from functools import wraps

from .supervisor import atomic_json


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def child_cpu():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def _owned_operation(method):
    @wraps(method)
    def guarded(self, *args, **kwargs):
        # A signal must not close a partially registered child or re-enter wait.
        self._operation_depth += 1
        try:
            return method(self, *args, **kwargs)
        finally:
            self._operation_depth -= 1
            if self._signal_stop_requested and not self._operation_depth and not self._closing and not self.closed:
                self.close()

    return guarded


class BackendProcesses:
    def __init__(self, session, *, identity, token):
        self.session, self.identity, self.token = session, copy.deepcopy(identity), token
        self.processes = []
        self.stop_requested = self.closed = self.installed = False
        self._operation_depth = 0
        self._signal_stop_requested = self._closing = False
        self.initial_cpu = child_cpu()

    def request_stop(self, *_):
        self.stop_requested = self._signal_stop_requested = True
        # Publish proof before returning to solver work. Registry operations
        # defer this until their owned handle and receipt are consistent.
        if not self._operation_depth and not self._closing and not self.closed:
            self.close()

    def install(self):
        if not self.installed:
            self.previous_handler = signal.signal(signal.SIGTERM, self.request_stop)
            self.installed = True

    @_owned_operation
    def spawn(self, argv, **kwargs):
        if self.stop_requested or self.closed:
            return None
        if kwargs.get("start_new_session") or kwargs.get("process_group", -1) != -1:
            raise ValueError("owned backend must inherit the worker process group")
        process = subprocess.Popen(argv, **kwargs)
        entry = {"pid": process.pid, "spawn_perf": time.perf_counter()}
        self.processes.append((process, entry))
        name = f"descendant_{len(self.processes):06d}_start.json"
        entry["start_file"] = name
        atomic_json(self.session / name, {"token": self.token, "worker_pid": os.getpid(), **entry, "command": argv})
        entry["start_sha256"] = file_hash(self.session / name)
        return process

    @_owned_operation
    def stop(self, process, *, final=False):
        entry = next(entry for owned, entry in self.processes if owned is process)
        if "stop_file" in entry:
            return entry
        terminate_sent = entry.get("terminate_sent", False)
        kill_sent = entry.get("kill_sent", False)
        if process.poll() is None:
            if not kill_sent:
                terminate_sent = True
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=0.03)
                except subprocess.TimeoutExpired:
                    kill_sent = True
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
            if process.poll() is None:
                try:
                    process.wait(timeout=0.5 if final else 0.03)
                except subprocess.TimeoutExpired:
                    pass
        reaped = process.poll() is not None
        entry.update(
            returncode=process.returncode,
            reaped=reaped,
            reaped_perf=time.perf_counter() if reaped else None,
            terminate_sent=terminate_sent,
            kill_sent=kill_sent,
        )
        if not reaped:
            self.stop_requested = True
            if not final:
                # Keep the unsuccessful observation without finalizing it. The
                # owned handle can establish reaping later during close().
                attempt = entry.get("stop_attempts", 0) + 1
                entry["stop_attempts"] = attempt
                name = entry["start_file"].replace("_start.json", f"_attempt_{attempt:06d}.json")
                atomic_json(self.session / name, {"token": self.token, "worker_pid": os.getpid(), **entry})
                return entry
        name = entry["start_file"].replace("_start.json", "_stop.json")
        atomic_json(self.session / name, {"token": self.token, "worker_pid": os.getpid(), **entry})
        entry.update(stop_file=name, stop_sha256=file_hash(self.session / name))
        return entry

    @_owned_operation
    def close(self):
        if self.closed or self._closing:
            return
        self._closing = True
        try:
            for process, _ in self.processes:
                self.stop(process, final=True)
            entries = [entry for _, entry in self.processes]
            atomic_json(
                self.session / "descendant_cleanup.json",
                {
                    "token": self.token,
                    "identity": self.identity,
                    "worker_pid": os.getpid(),
                    "closed_perf": time.perf_counter(),
                    "all_reaped": all(entry["reaped"] for entry in entries),
                    "processes": entries,
                    "descendant_cpu_sec": child_cpu() - self.initial_cpu,
                },
            )
        finally:
            self.closed = True
            self._closing = False
            if self.installed:
                signal.signal(signal.SIGTERM, self.previous_handler)
                self.installed = False
