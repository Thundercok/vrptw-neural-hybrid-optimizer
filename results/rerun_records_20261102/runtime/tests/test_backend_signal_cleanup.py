import os
import signal
from pathlib import Path

import pytest

from vrptw import supervised_process as m
from vrptw.supervisor import check_descendant_cleanup

assert Path(m.__file__).resolve() == Path(__file__).resolve().parents[1] / "src/vrptw/supervised_process.py"
pytest_plugins = ["test_supervisor", "test_cleanup_grace"]


class Child:
    pid = 12345

    def __init__(self):
        self.returncode = None
        self.on_wait = lambda: None

    def poll(self):
        return self.returncode

    def terminate(self):
        pass

    def kill(self):
        self.returncode = -signal.SIGKILL

    def wait(self, timeout=None):
        self.on_wait()
        self.returncode = -signal.SIGTERM
        return self.returncode


def owner(tmp_path):
    return m.BackendProcesses(tmp_path, identity={"case": "fixture"}, token="owned")


def verified(p, session):
    receipt = check_descendant_cleanup(session, {"token": "owned", "identity": {"case": "fixture"}}, os.getpid())
    assert receipt["all_reaped"] is True
    assert all(e["reaped"] is True and e["returncode"] is not None for e in receipt["processes"])
    return receipt


def test_stop_signal_publishes_proof_before_returning_to_busy_solver(tmp_path, monkeypatch):
    p, child = owner(tmp_path), Child()
    monkeypatch.setattr(m.subprocess, "Popen", lambda *a, **k: child)
    assert p.spawn(["owned"]) is child
    p.request_stop()
    assert p.closed is True
    assert len(verified(p, tmp_path)["processes"]) == 1
    assert p.spawn(["forbidden"]) is None


def test_signal_during_popen_waits_until_handle_and_start_receipt_are_registered(tmp_path, monkeypatch):
    p, child = owner(tmp_path), Child()

    def popen(*a, **k):
        p.request_stop()
        assert not p.closed
        assert not (tmp_path / "descendant_cleanup.json").exists()
        return child

    monkeypatch.setattr(m.subprocess, "Popen", popen)
    p.spawn(["owned"])
    receipt = verified(p, tmp_path)
    assert p.closed and len(receipt["processes"]) == 1
    assert receipt["processes"][0]["pid"] == child.pid


def test_signal_during_stop_cannot_reenter_popen_wait(tmp_path, monkeypatch):
    p, child = owner(tmp_path), Child()
    monkeypatch.setattr(m.subprocess, "Popen", lambda *a, **k: child)
    p.spawn(["owned"])
    calls = []

    def during_wait():
        calls.append("wait")
        assert len(calls) == 1, "reentrant owned-child wait"
        p.request_stop()
        assert not p.closed

    child.on_wait = during_wait
    p.stop(child)
    assert p.closed and calls == ["wait"]
    verified(p, tmp_path)


def test_repeated_signal_and_close_do_not_rewrite_receipts(tmp_path):
    p = owner(tmp_path)
    p.request_stop()
    before = (tmp_path / "descendant_cleanup.json").read_bytes()
    p.request_stop()
    p.close()
    assert (tmp_path / "descendant_cleanup.json").read_bytes() == before
    assert verified(p, tmp_path)["processes"] == []


def test_spawn_failure_after_deferred_signal_does_not_invent_a_child(tmp_path, monkeypatch):
    p = owner(tmp_path)

    def failed(*a, **k):
        p.request_stop()
        raise OSError("controlled spawn failure")

    monkeypatch.setattr(m.subprocess, "Popen", failed)
    with pytest.raises(OSError):
        p.spawn(["owned"])
    assert p.closed and verified(p, tmp_path)["processes"] == []


def test_no_signal_keeps_normal_registration_and_close_semantics(tmp_path, monkeypatch):
    p, child = owner(tmp_path), Child()
    monkeypatch.setattr(m.subprocess, "Popen", lambda *a, **k: child)
    p.spawn(["owned"])
    p.stop(child)
    assert not p.closed and not (tmp_path / "descendant_cleanup.json").exists()
    p.close()
    verified(p, tmp_path)


def test_busy_real_worker_can_be_killed_after_owned_cleanup_without_late_admission(
    case, cleanup_worker, tmp_path, monkeypatch
):
    from test_cleanup_grace import run_owned

    plan, result = run_owned(case, cleanup_worker, tmp_path, monkeypatch, cleanup_delay=3.0)
    assert result["kill_sent"] and result["worker_reaped"]
    assert result["descendants_reaped"] is True
    assert result["descendant_cleanup"]["all_reaped"] is True
    assert plan is not None and "error" not in result
    assert result["native_certification"]["certificate"]["captured_sec"] < 0.2
    assert result["runtime_sec"] > 0.2 + 0.5
    assert [p["file"] for p in result["packet_observations"]] == ["incumbent_000001.json"]
    assert result["cleanup_terminate_grace_sec"] == 1.0
