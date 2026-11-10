from pathlib import Path

from test_backend_signal_cleanup import Child, owner, verified

from vrptw import supervised_process as m

assert Path(m.__file__).resolve() == Path(__file__).resolve().parents[1] / "src/vrptw/supervised_process.py"


def test_signal_during_start_receipt_does_not_close_partial_registry(tmp_path, monkeypatch):
    p, child = owner(tmp_path), Child()
    monkeypatch.setattr(m.subprocess, "Popen", lambda *a, **k: child)
    write = m.atomic_json

    def injected(path, value):
        if path.name.endswith("_start.json"):
            p.request_stop()
            assert not p.closed and not (tmp_path / "descendant_cleanup.json").exists()
        return write(path, value)

    monkeypatch.setattr(m, "atomic_json", injected)
    p.spawn(["owned"])
    assert p.closed
    verified(p, tmp_path)


def test_repeated_signal_during_aggregate_write_is_not_reentrant(tmp_path, monkeypatch):
    p = owner(tmp_path)
    write, calls = m.atomic_json, []

    def injected(path, value):
        if path.name == "descendant_cleanup.json":
            calls.append(path.name)
            assert len(calls) == 1
            p.request_stop()
        return write(path, value)

    monkeypatch.setattr(m, "atomic_json", injected)
    p.request_stop()
    assert p.closed and calls == ["descendant_cleanup.json"]
    verified(p, tmp_path)
