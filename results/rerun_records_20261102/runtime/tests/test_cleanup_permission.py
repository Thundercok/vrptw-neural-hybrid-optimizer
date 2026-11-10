import errno
import signal
import subprocess

import pytest

from vrptw import supervisor as m

pytest_plugins = ["test_supervisor"]


class OwnedProcess:
    pid = 12345

    def __init__(self, denial, exits_on_denial=False, fallback_denied=False):
        self.returncode = None
        self.denial = denial
        self.exits_on_denial = exits_on_denial
        self.fallback_denied = fallback_denied
        self.group_signals = []
        self.direct_signals = []

    def poll(self):
        return self.returncode

    def wait(self, timeout):
        assert timeout == 0.1
        if self.returncode is None:
            raise subprocess.TimeoutExpired("owned fixture", timeout)
        return self.returncode

    def group_signal(self, pid, sig):
        assert pid == self.pid
        self.group_signals.append(sig)
        if sig == self.denial:
            if self.exits_on_denial:
                self.returncode = -signal.SIGTERM
            raise PermissionError(errno.EPERM, "fixture group denial")
        if sig == signal.SIGKILL:
            self.returncode = -sig

    def send_signal(self, sig):
        self.direct_signals.append(sig)
        if self.fallback_denied:
            raise PermissionError(errno.EPERM, "fixture owned-child denial")
        self.returncode = -sig


@pytest.mark.parametrize("denial", [signal.SIGTERM, signal.SIGKILL])
@pytest.mark.parametrize("exited", [False, True])
def test_denied_group_signal_reaps_only_owned_child_and_records_denial(monkeypatch, denial, exited):
    process = OwnedProcess(denial, exits_on_denial=exited)
    monkeypatch.setattr(m.os, "killpg", process.group_signal)
    info = m._stop_worker(process)
    assert info["worker_reaped"] and info["worker_returncode"] in (-signal.SIGTERM, -signal.SIGKILL)
    assert info["cleanup_signal_errors"] == [
        {"operation": "process_group", "signal": int(denial), "errno": errno.EPERM}
    ]
    assert process.direct_signals == ([] if exited else [denial])


def test_denied_group_and_child_signals_never_claim_reaping_or_extend_waits(monkeypatch):
    process = OwnedProcess(signal.SIGKILL, fallback_denied=True)
    monkeypatch.setattr(m.os, "killpg", process.group_signal)
    info = m._stop_worker(process)
    assert not info["worker_reaped"] and info["worker_returncode"] is None
    assert len(info["cleanup_signal_errors"]) == 2
    assert process.direct_signals == [signal.SIGKILL]


def test_reaped_child_is_never_signalled(monkeypatch):
    process = OwnedProcess(signal.SIGKILL)
    process.returncode = 0
    monkeypatch.setattr(m.os, "killpg", process.group_signal)
    info = m._stop_worker(process)
    assert info["worker_reaped"] and not process.group_signals and not process.direct_signals


def test_exit_after_timeout_before_escalation_avoids_group_signal(monkeypatch):
    process = OwnedProcess(signal.SIGKILL)

    def wait(timeout):
        if process.returncode is None:
            process.returncode = -signal.SIGTERM
            raise subprocess.TimeoutExpired("owned fixture", timeout)
        return process.returncode

    process.wait = wait
    monkeypatch.setattr(m.os, "killpg", process.group_signal)
    info = m._stop_worker(process)
    assert process.group_signals == [signal.SIGTERM]
    assert not info["kill_sent"] and info["worker_reaped"]


def test_parent_keeps_certified_incumbent_after_real_owned_child_fallback(case, worker_script, tmp_path, monkeypatch):
    original = m.os.killpg
    original_popen = m.subprocess.Popen
    owned = []

    def popen(*args, **kwargs):
        process = original_popen(*args, **kwargs)
        owned.append(process)
        return process

    def denied_kill(pid, sig):
        if sig == signal.SIGKILL:
            raise PermissionError(errno.EPERM, "fixture group denial")
        original(pid, sig)

    monkeypatch.setattr(m.os, "killpg", denied_kill)
    monkeypatch.setattr(m.subprocess, "Popen", popen)
    try:
        plan, result = m.supervise(
            case.inst,
            worker_script,
            {"time_limit": 0.2, "identity": {}, "expected_cold": {}, "mode": "resist"},
            tmp_path / "session",
            setup_timeout=5,
        )
    finally:
        for process in owned:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=2)
    assert plan is not None and "error" not in result and result["worker_reaped"]
    assert result["worker_returncode"] == -signal.SIGKILL
    assert result["cleanup_signal_errors"]
    assert 0.2 <= result["runtime_sec"] <= 0.7
    assert result["native_certification"]["certificate"]["captured_sec"] < 0.2


def test_unreaped_worker_produces_failure_receipt_without_hiding_denial(case, worker_script, tmp_path, monkeypatch):
    original = m._stop_worker

    def stopped(process):
        # Reap the real fixture, then inject the fail-closed receipt branch.
        info = original(process)
        return {
            **info,
            "worker_reaped": False,
            "worker_returncode": None,
            "cleanup_signal_errors": [{"operation": "owned_process", "signal": 9, "errno": errno.EPERM}],
        }

    monkeypatch.setattr(m, "_stop_worker", stopped)
    plan, result = m.supervise(
        case.inst,
        worker_script,
        {"time_limit": 0.2, "identity": {}, "expected_cold": {}, "mode": "blocked"},
        tmp_path / "session",
        setup_timeout=5,
    )
    assert plan is None and not result["worker_reaped"]
    assert result["error"] == "SupervisorProtocolError: worker was not reaped"
    assert result["cleanup_signal_errors"]
