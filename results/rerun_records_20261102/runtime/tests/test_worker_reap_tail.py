import errno
import signal
import subprocess
from pathlib import Path

import pytest

from vrptw import supervisor as m

assert Path(m.__file__).resolve() == Path(__file__).resolve().parents[1] / "src/vrptw/supervisor.py", (
    "wrong source under test"
)


class DelayedChild:
    pid = 31415

    def __init__(self, *, group_denied=False, owned_denied=False, immediate=False):
        self.returncode = None
        self.group_denied = group_denied
        self.owned_denied = owned_denied
        self.immediate = immediate
        self.killed = False
        self.waits = []
        self.signals = []

    def poll(self):
        return self.returncode

    def group_signal(self, pid, sig):
        assert pid == self.pid
        self.signals.append(("group", sig))
        if self.group_denied and sig == signal.SIGKILL:
            raise PermissionError(errno.EPERM, "controlled group denial")
        if sig == signal.SIGKILL:
            self.killed = True

    def send_signal(self, sig):
        self.signals.append(("owned", sig))
        if self.owned_denied:
            raise PermissionError(errno.EPERM, "controlled owned denial")
        self.killed = sig == signal.SIGKILL

    def wait(self, timeout=None):
        self.waits.append(timeout)
        if timeout is None:
            assert self.killed, "must not block if no successful kill delivery"
            self.returncode = -signal.SIGKILL
            return self.returncode
        if self.immediate and self.killed:
            self.returncode = -signal.SIGKILL
            return self.returncode
        raise subprocess.TimeoutExpired("controlled owned child", timeout)


@pytest.mark.parametrize("grace", [0.1, 1.0])
@pytest.mark.parametrize("group_denied", [False, True])
def test_delayed_reap_is_completed_on_same_owned_handle(monkeypatch, grace, group_denied):
    child = DelayedChild(group_denied=group_denied)
    monkeypatch.setattr(m.os, "killpg", child.group_signal)
    result = m._stop_worker(child, terminate_grace=grace)
    assert result["worker_reaped"] is True
    assert result["worker_returncode"] == -signal.SIGKILL
    assert result["post_kill_reap_waited"] is True
    assert result["kill_delivery_confirmed"] is True
    assert child.waits == [grace, 0.1, None]
    assert result["cleanup_terminate_grace_sec"] == grace


def test_no_unbounded_wait_when_both_kill_paths_are_denied(monkeypatch):
    child = DelayedChild(group_denied=True, owned_denied=True)
    monkeypatch.setattr(m.os, "killpg", child.group_signal)
    result = m._stop_worker(child)
    assert result["worker_reaped"] is False
    assert result["kill_delivery_confirmed"] is False
    assert result["post_kill_reap_waited"] is False
    assert None not in child.waits
    assert len(result["cleanup_signal_errors"]) == 2


def test_fast_kill_does_not_add_wait(monkeypatch):
    child = DelayedChild(immediate=True)
    monkeypatch.setattr(m.os, "killpg", child.group_signal)
    result = m._stop_worker(child)
    assert result["worker_reaped"] is True
    assert result["post_kill_reap_waited"] is False
    assert child.waits == [0.1, 0.1]


def test_already_reaped_child_is_not_signalled(monkeypatch):
    child = DelayedChild()
    child.returncode = 0
    monkeypatch.setattr(m.os, "killpg", lambda *_: pytest.fail("already reaped child signalled"))
    result = m._stop_worker(child)
    assert result["worker_reaped"] is True
    assert result["worker_returncode"] == 0
    assert child.waits == []
    assert result["post_kill_reap_waited"] is False


def test_ordinary_termination_keeps_existing_grace(monkeypatch):
    child = DelayedChild()
    monkeypatch.setattr(m.os, "killpg", child.group_signal)

    def finished(timeout=None):
        child.waits.append(timeout)
        child.returncode = -signal.SIGTERM

    monkeypatch.setattr(child, "wait", finished)
    result = m._stop_worker(child)
    assert result["worker_reaped"] is True
    assert result["kill_sent"] is False
    assert child.waits == [0.1]


def test_real_owned_fallback_can_reap_after_short_wait_expires(monkeypatch):
    import sys

    process = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-c",
            'import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);print("ready",flush=True);time.sleep(60)',
        ],
        stdout=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    original_wait, original_group = process.wait, m.os.killpg
    try:
        assert process.stdout.readline().strip() == "ready"
        waits = []

        def delayed_wait(timeout=None):
            waits.append(timeout)
            if len(waits) == 2:
                raise subprocess.TimeoutExpired("controlled short wait expiry", timeout)
            return original_wait(timeout=timeout)

        def denied_group(pid, sig):
            if sig == signal.SIGKILL:
                raise PermissionError(errno.EPERM, "controlled group denial")
            return original_group(pid, sig)

        monkeypatch.setattr(process, "wait", delayed_wait)
        monkeypatch.setattr(m.os, "killpg", denied_group)
        result = m._stop_worker(process)
        assert result["worker_reaped"] is True
        assert result["post_kill_reap_waited"] is True
        assert result["owned_signal_fallbacks"] == [int(signal.SIGKILL)]
        assert waits == [0.1, 0.1, None]
    finally:
        if process.poll() is None:
            process.kill()
        original_wait(timeout=5)
        process.stdout.close()
