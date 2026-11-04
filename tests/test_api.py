from fastapi.testclient import TestClient

from multitrack import config
from multitrack.app import Jobs, create_app
from multitrack.state import atomic_json


def test_local_security_and_missing_models(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MODELS", tmp_path / "missing")
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/").status_code == 200
        assert "default-src 'self'" in client.get("/").headers["content-security-policy"]
        assert client.get("/", headers={"Host": "attacker.example"}).status_code == 400
        assert client.post("/api/jobs", content=b"evil").status_code == 403
        assert (
            client.post(
                "/api/jobs", headers={"X-Multitrack": "local"}, content=b"video"
            ).status_code
            == 503
        )
        assert client.get("/api/jobs/not-a-job").status_code == 404
        assert client.get("/api/jobs/" + "a" * 32 + "/media/secret").status_code == 404


def test_sizes_empty_upload_and_job_recovery(tmp_path, monkeypatch):
    import multitrack.app as module

    monkeypatch.setattr(module, "model_ready", lambda _: True)
    monkeypatch.setattr(config, "MAX_BYTES", 10)
    with TestClient(create_app(tmp_path)) as client:
        h = {"X-Multitrack": "local"}
        assert client.post("/api/jobs", headers=h, content=b"").status_code == 422
        assert client.post("/api/jobs", headers=h, content=b"1" * 11).status_code == 413
        assert client.post("/api/jobs?speakers=13", headers=h, content=b"1").status_code == 422
        assert client.get("/api/jobs").json() == []
    manager = Jobs(tmp_path / "jobs")
    ident, folder = manager.reserve()
    Jobs(tmp_path / "jobs")
    assert __import__("json").loads((folder / "status.json").read_text())["state"] == "interrupted"
    with TestClient(create_app(tmp_path)) as client:
        assert client.get(f"/api/jobs/{ident}/download").status_code == 409
        assert client.post(f"/api/jobs/{ident}/cancel", headers=h).status_code == 409
        assert client.delete(f"/api/jobs/{ident}", headers=h).status_code == 200


def test_only_one_job_and_cancellation(tmp_path):
    manager = Jobs(tmp_path / "jobs")
    ident, folder = manager.reserve()
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as e:
        manager.reserve()
    assert e.value.status_code == 409
    from multitrack.state import Progress

    (folder / "cancel").touch()
    with pytest.raises(InterruptedError):
        Progress(folder).update("phase")
    manager.release()
    manager.reserve()


def test_completed_job_download_and_safe_media(tmp_path):
    folder = tmp_path / "jobs" / ("a" * 32)
    folder.mkdir(parents=True)
    atomic_json(folder / "status.json", {"state": "done"})
    (folder / "result.zip").write_bytes(b"ZIP")
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/api/jobs/" + "a" * 32 + "/download").content == b"ZIP"
        assert client.get("/api/jobs/" + "a" * 32 + "/media/worker.log").status_code == 404


def test_reference_upload_cancel_and_error_cleanup(tmp_path, monkeypatch):
    import multitrack.app as module

    monkeypatch.setattr(module, "model_ready", lambda _: True)
    with TestClient(create_app(tmp_path)) as client:
        h = {"X-Multitrack": "local"}
        response = client.post("/api/jobs?reference=true", headers=h, content=b"video")
        assert response.status_code == 202
        ident = response.json()["id"]
        assert client.get(f"/api/jobs/{ident}").json()["state"] == "awaiting_reference"
        assert (
            client.post(f"/api/jobs/{ident}/reference", headers=h, content=b"").status_code == 422
        )
        assert client.get(f"/api/jobs/{ident}").json()["state"] == "error"
        second = client.post("/api/jobs?reference=true", headers=h, content=b"video").json()["id"]
        assert client.post(f"/api/jobs/{second}/cancel", headers=h).status_code == 200
        assert client.get(f"/api/jobs/{second}").json()["state"] == "cancelled"
        assert client.delete(f"/api/jobs/{second}", headers=h).status_code == 200


def test_music_missing_model_is_explicit(tmp_path, monkeypatch):
    import multitrack.app as module

    monkeypatch.setattr(module, "model_ready", lambda _: True)
    monkeypatch.setattr(module, "music_ready", lambda _: False)
    with TestClient(create_app(tmp_path)) as client:
        assert (
            client.post(
                "/api/jobs?music=true", content=b"video", headers={"X-Multitrack": "local"}
            ).status_code
            == 503
        )
        assert (
            client.post(
                "/api/jobs?reference_offset=nan",
                content=b"video",
                headers={"X-Multitrack": "local"},
            ).status_code
            == 422
        )


def test_status_does_not_report_unknown_job_from_a_transient_file_stat(tmp_path, monkeypatch):
    from pathlib import Path

    folder = tmp_path / 'jobs' / ('a' * 32)
    folder.mkdir(parents=True)
    atomic_json(folder / 'status.json', {'state': 'done'})
    with TestClient(create_app(tmp_path)) as client:
        original_stat = Path.is_file

        def hidden_during_replace(path):
            return False if path == folder / 'status.json' else original_stat(path)

        monkeypatch.setattr(Path, 'is_file', hidden_during_replace)
        response = client.get('/api/jobs/' + 'a' * 32)
        assert response.status_code == 200, response.text
        assert response.json()['state'] == 'done'
