"""Delayed observation of an owned child's exit must be finalized on close."""

import json
import os
import signal
import subprocess

import pytest

from vrptw import supervised_process as m
from vrptw.supervisor import SupervisorProtocolError, check_descendant_cleanup


class DelayedOwnedChild:
    pid = 98765

    def __init__(self, stuck=False):
        self.returncode = None
        self.stuck = stuck
        self.waits, self.signals = [], []

    def poll(self):
        return self.returncode

    def terminate(self):
        self.signals.append(signal.SIGTERM)

    def kill(self):
        self.signals.append(signal.SIGKILL)

    def wait(self, timeout):
        self.waits.append(timeout)
        if self.returncode is None and (self.stuck or timeout < 0.2):
            raise subprocess.TimeoutExpired("owned fake child", timeout)
        self.returncode = -signal.SIGKILL
        return self.returncode


def make_owner(tmp_path, monkeypatch, *, stuck=False):
    process = DelayedOwnedChild(stuck)
    monkeypatch.setattr(m.subprocess, "Popen", lambda *a, **kw: process)
    owner = m.BackendProcesses(tmp_path, identity={"fixture": True}, token="fixture")
    assert owner.spawn(["owned-fixture"]) is process
    return owner, process


def test_nonfinal_timeout_is_retained_then_closed_by_the_same_owned_handle(tmp_path, monkeypatch):
    owner, process = make_owner(tmp_path, monkeypatch)
    first = owner.stop(process)
    assert first["reaped"] is False and owner.stop_requested
    assert not (tmp_path / "descendant_000001_stop.json").exists()
    attempts = list(tmp_path.glob("descendant_000001_attempt_*.json"))
    assert len(attempts) == 1 and json.loads(attempts[0].read_text())["reaped"] is False
    before = attempts[0].read_bytes()
    assert owner.spawn(["forbidden-after-incomplete-stop"]) is None
    owner.close()
    request = {"identity": {"fixture": True}, "token": "fixture"}
    receipt = check_descendant_cleanup(tmp_path, request, os.getpid())
    assert receipt["all_reaped"] is True
    entry = receipt["processes"][0]
    assert entry["returncode"] == -signal.SIGKILL and entry["reaped"] is True
    assert entry["terminate_sent"] and entry["kill_sent"]
    assert process.waits == [0.03, 0.03, 0.5]
    assert process.signals == [signal.SIGTERM, signal.SIGKILL]
    assert attempts[0].read_bytes() == before
    stopped = (tmp_path / "descendant_000001_stop.json").read_bytes()
    owner.close()
    owner.stop(process)
    assert (tmp_path / "descendant_000001_stop.json").read_bytes() == stopped


def test_final_unreaped_child_is_never_claimed_successful(tmp_path, monkeypatch):
    owner, process = make_owner(tmp_path, monkeypatch, stuck=True)
    owner.stop(process)
    owner.close()
    raw = json.loads((tmp_path / "descendant_cleanup.json").read_text())
    assert raw["all_reaped"] is False and raw["processes"][0]["returncode"] is None
    assert process.waits == [0.03, 0.03, 0.5]
    with pytest.raises(SupervisorProtocolError, match="incomplete"):
        check_descendant_cleanup(tmp_path, {"identity": {"fixture": True}, "token": "fixture"}, os.getpid())


def test_exit_observed_before_close_is_reaped_without_an_extra_signal(tmp_path, monkeypatch):
    owner, process = make_owner(tmp_path, monkeypatch)
    owner.stop(process)
    process.returncode = -signal.SIGKILL
    owner.close()
    assert process.signals == [signal.SIGTERM, signal.SIGKILL]
    assert process.waits == [0.03, 0.03]
    assert json.loads((tmp_path / "descendant_cleanup.json").read_text())["all_reaped"]
