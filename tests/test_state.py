import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

import multitrack.state as state_module
from multitrack.state import atomic_json, open_shared_text, read_json


def test_concurrent_status_writers_never_share_temporary_files(tmp_path):
    path = tmp_path / "status.json"
    atomic_json(path, {"step": -1})

    def writer(n):
        for i in range(30):
            atomic_json(path, {"writer": n, "step": i, "payload": "x" * 1000})
            assert isinstance(read_json(path), dict)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(writer, range(4)))
    assert read_json(path)["step"] == 29
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("winerror", [5, 32, 33, 1176])
def test_windows_sharing_violation_is_retried_and_old_data_preserved(
    tmp_path, monkeypatch, winerror
):
    path = tmp_path / "status.json"
    atomic_json(path, {"old": True})
    replace = state_module.replace_file
    count = 0

    def locked(a, b):
        nonlocal count
        count += 1
        if count <= 3:
            assert read_json(path) == {"old": True}
            e = PermissionError("simulated Windows sharing violation")
            e.winerror = winerror
            raise e
        return replace(a, b)

    monkeypatch.setattr(state_module, "replace_file", locked)
    atomic_json(path, {"new": True})
    assert count == 4 and read_json(path) == {"new": True}
    assert not list(tmp_path.glob("*.tmp"))


def test_permanent_denial_keeps_previous_status_and_reports_error(tmp_path, monkeypatch):
    path = tmp_path / "status.json"
    atomic_json(path, {"old": True})

    def denied(*args):
        raise PermissionError("permanent denial")

    monkeypatch.setattr(state_module, "replace_file", denied)
    with pytest.raises(PermissionError):
        atomic_json(path, {"new": True})
    assert read_json(path) == {"old": True}
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(sys.platform != "win32", reason="Actual Windows handle sharing")
def test_windows_reader_allows_atomic_replace_while_handle_is_open(tmp_path):
    path = tmp_path / "status.json"
    atomic_json(path, {"old": True})
    with open_shared_text(path) as reader:
        atomic_json(path, {"new": True})
        assert json.load(reader) == {"old": True}
        assert read_json(path) == {"new": True}


@pytest.mark.skipif(sys.platform != "win32", reason="Actual Windows file lock")
def test_windows_legacy_lock_can_be_released_during_retry(tmp_path):
    path = tmp_path / "status.json"
    atomic_json(path, {"old": True})
    # The ordinary Python handle reproduces the old app's deny-delete reader.
    reader = path.open()
    release = threading.Timer(0.3, reader.close)
    release.start()
    try:
        atomic_json(path, {"new": True})
        assert read_json(path) == {"new": True}
    finally:
        reader.close()
        release.join()


def test_diagnostic_export_contains_logs_but_no_media_or_environment(tmp_path):
    import io
    import zipfile

    from multitrack.diagnostics import log_bundle

    folder = tmp_path / "jobs" / "example"
    folder.mkdir(parents=True)
    (tmp_path / "server.log").write_text("server failure")
    (folder / "worker.log").write_text("worker failure")
    atomic_json(folder / "status.json", {"state": "error"})
    (folder / "input.mp4").write_bytes(b"private video")
    (folder / "original.wav").write_bytes(b"private sound")
    with zipfile.ZipFile(io.BytesIO(log_bundle(tmp_path))) as z:
        assert "server.log" in z.namelist()
        assert "jobs/example/worker.log" in z.namelist()
        assert not any(n.endswith((".wav", ".mp4")) for n in z.namelist())


def test_locked_interrupted_job_does_not_block_new_uploads(tmp_path, monkeypatch):
    import multitrack.app as module
    from multitrack.app import Jobs

    path = tmp_path / "oldjob"
    path.mkdir()
    atomic_json(path / "status.json", {"state": "running"})

    def blocked(target, value):
        if target.parent == path:
            raise PermissionError("persistent target lock")
        return atomic_json(target, value)

    monkeypatch.setattr(module, "atomic_json", blocked)
    jobs = Jobs(tmp_path)
    assert jobs.active is None
    assert jobs.read_status(path)["state"] == "interrupted"
    assert (path / "status.json").is_file()
    ident, new_folder = jobs.reserve()
    assert jobs.active == ident and read_json(new_folder / "status.json")["state"] == "uploading"


def test_status_writers_in_separate_processes_are_serialized(tmp_path):
    import subprocess

    path = tmp_path / "status.json"
    code = 'from pathlib import Path; import sys; from multitrack.state import atomic_json; p=Path(sys.argv[1]); [atomic_json(p,{"writer":sys.argv[2],"step":i}) for i in range(20)]'
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", code, str(path), str(i)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for i in range(4)
    ]
    for process in processes:
        output, error = process.communicate(timeout=30)
        assert process.returncode == 0, (output, error)
    assert read_json(path)["step"] == 19
    assert not list(tmp_path.glob("*.tmp"))


def test_windows_transient_status_open_is_retried(tmp_path, monkeypatch):
    path = tmp_path / 'status.json'
    atomic_json(path, {'state': 'running'})
    original_open = state_module.open_shared_text
    attempts = 0

    def transient(path):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            error = FileNotFoundError('replacement in progress')
            error.winerror = 2
            raise error
        return original_open(path)

    monkeypatch.setattr(state_module, 'open_shared_text', transient)
    assert read_json(path) == {'state': 'running'}
    assert attempts == 3
