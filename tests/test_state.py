import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

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


def test_windows_sharing_violation_is_retried_and_old_data_preserved(tmp_path, monkeypatch):
    path = tmp_path / "status.json"
    atomic_json(path, {"old": True})
    replace = os.replace
    count = 0

    def locked(a, b):
        nonlocal count
        count += 1
        if count <= 3:
            assert read_json(path) == {"old": True}
            e = PermissionError("simulated Windows sharing violation")
            e.winerror = 5
            raise e
        return replace(a, b)

    monkeypatch.setattr(os, "replace", locked)
    atomic_json(path, {"new": True})
    assert count == 4 and read_json(path) == {"new": True}
    assert not list(tmp_path.glob("*.tmp"))


def test_permanent_denial_keeps_previous_status_and_reports_error(tmp_path, monkeypatch):
    path = tmp_path / "status.json"
    atomic_json(path, {"old": True})

    def denied(*args):
        raise PermissionError("permanent denial")

    monkeypatch.setattr(os, "replace", denied)
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
