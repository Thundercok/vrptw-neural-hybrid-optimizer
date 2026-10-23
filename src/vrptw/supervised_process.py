"""Opt-in worker ownership of backend children; no PID reconstructed for signals."""

from __future__ import annotations

import copy
import hashlib
import os
import resource
import signal
import subprocess
import time

from .supervisor import atomic_json


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def child_cpu():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


class BackendProcesses:
    def __init__(self, session, *, identity, token):
        self.session, self.identity, self.token = session, copy.deepcopy(identity), token
        self.processes = []
        self.stop_requested = self.closed = self.installed = False
        self.initial_cpu = child_cpu()

    def request_stop(self, *_):
        # Never throw between Popen returning and registering its owned handle.
        self.stop_requested = True

    def install(self):
        if not self.installed:
            self.previous_handler = signal.signal(signal.SIGTERM, self.request_stop)
            self.installed = True

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

    def stop(self, process):
        entry = next(entry for owned, entry in self.processes if owned is process)
        if "stop_file" in entry:
            return entry
        terminate_sent = kill_sent = False
        if process.poll() is None:
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
                try:
                    process.wait(timeout=0.03)
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
        name = entry["start_file"].replace("_start.json", "_stop.json")
        atomic_json(self.session / name, {"token": self.token, "worker_pid": os.getpid(), **entry})
        entry.update(stop_file=name, stop_sha256=file_hash(self.session / name))
        if not reaped:
            self.stop_requested = True
        return entry

    def close(self):
        if self.closed:
            return
        try:
            for process, _ in self.processes:
                self.stop(process)
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
            if self.installed:
                signal.signal(signal.SIGTERM, self.previous_handler)
                self.installed = False
