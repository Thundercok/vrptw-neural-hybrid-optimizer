"""Real cooperative cleanup after TERM; cutoff admission remains closed."""

import json
import signal
from pathlib import Path

import pytest

from vrptw import supervisor as m

pytest_plugins = ["test_supervisor"]


@pytest.fixture
def cleanup_worker(worker_script):
    source = worker_script.read_text()
    source = source.replace(
        "if r['mode']=='setup_error':",
        "sys.path.insert(0, " + repr(str(Path(m.__file__).resolve().parents[1])) + ")\n"
        "from vrptw.supervised_process import BackendProcesses\n"
        "owner=BackendProcesses(s, identity=r['identity'], token=r['token']); owner.install()\n"
        "if r['mode']=='missing':\n"
        " def omit_signal_proof(*_): owner.stop_requested=True\n"
        " signal.signal(signal.SIGTERM, omit_signal_proof)\n"
        "if r['mode']=='setup_error':",
    )
    source = source.replace(
        "if r['mode']=='late':",
        "owner.spawn([sys.executable, '-c', 'import time; time.sleep(60)'])\nif r['mode']=='late':",
    )
    source = source.replace(
        "while True: time.sleep(60)",
        "while not owner.stop_requested: time.sleep(.001)\n"
        "time.sleep(r.get('cleanup_delay', .25))\n"
        "if r['mode'] != 'missing': owner.close()\n"
        "if r['mode']=='corrupt_cleanup':\n"
        " p=s/'descendant_cleanup.json'; v=json.loads(p.read_text()); v['all_reaped']=False; p.write_text(json.dumps(v))\n"
        "if r['mode'] != 'none':\n"
        " packet['sequence']=2; packet['certificate']['captured_sec']=time.perf_counter()-start['start_perf']\n"
        " write('incumbent_000002.json', packet)\n",
    )
    worker_script.write_text(source)
    return worker_script


def run_owned(case, cleanup_worker, tmp_path, monkeypatch, **extra):
    original, owned = m.subprocess.Popen, []

    def popen(*args, **kwargs):
        process = original(*args, **kwargs)
        owned.append(process)
        return process

    monkeypatch.setattr(m.subprocess, "Popen", popen)
    try:
        return m.supervise(
            case.inst,
            cleanup_worker,
            {
                "time_limit": 0.2,
                "identity": {},
                "expected_cold": {},
                "mode": "blocked",
                "descendant_cleanup_required": True,
                **extra,
            },
            tmp_path / "session",
            setup_timeout=10,
        )
    finally:
        for process in owned:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=2)


def test_delayed_owned_cleanup_survives_and_cannot_admit_post_cutoff_packet(
    case, cleanup_worker, tmp_path, monkeypatch
):
    plan, result = run_owned(case, cleanup_worker, tmp_path, monkeypatch)
    assert plan is not None and "error" not in result
    assert result["worker_reaped"] and result["descendants_reaped"] and not result["kill_sent"]
    assert result["cleanup_terminate_grace_sec"] == 1.0
    assert result["descendant_cleanup"]["processes"][0]["reaped"] is True
    assert result["native_certification"]["certificate"]["captured_sec"] < 0.2
    assert (tmp_path / "session/incumbent_000002.json").exists()
    assert [p["file"] for p in result["packet_observations"]] == ["incumbent_000001.json"]


@pytest.mark.parametrize("mode", ["missing", "corrupt_cleanup"])
def test_missing_or_unreaped_cleanup_stays_fail_closed(case, cleanup_worker, tmp_path, monkeypatch, mode):
    plan, result = run_owned(case, cleanup_worker, tmp_path, monkeypatch, mode=mode)
    assert plan is None and not result["descendants_reaped"]
    assert result["error"].startswith("SupervisorProtocolError:")


def test_resistant_worker_is_still_killed_after_bounded_descendant_grace(case, cleanup_worker, tmp_path, monkeypatch):
    plan, result = run_owned(case, cleanup_worker, tmp_path, monkeypatch, mode="resist")
    assert plan is None and result["kill_sent"] and result["worker_reaped"]
    assert result["worker_returncode"] == -signal.SIGKILL
    assert not result["descendants_reaped"]
    assert 0.2 <= result["runtime_sec"] < 2.5


def test_delayed_cleanup_is_timed_and_can_fail_the_unchanged_return_gate(case, cleanup_worker, tmp_path, monkeypatch):
    plan, result = run_owned(case, cleanup_worker, tmp_path, monkeypatch, cleanup_delay=0.6)
    assert plan is not None and result["descendants_reaped"]
    assert result["runtime_sec"] > 0.2 + 0.5
    assert result["native_certification"]["certificate"]["cutoff_sec"] == pytest.approx(0.2)
    request = json.loads((tmp_path / "session/request.json").read_text())
    assert request["time_limit"] == 0.2
