from pathlib import Path

from fastapi.testclient import TestClient

from multitrack import config
from multitrack.app import Jobs, create_app
from multitrack.paths import default_data_dir
from multitrack.state import atomic_json


def test_new_installed_app_keeps_projects_outside_program_files(tmp_path):
    home, appdata = tmp_path / "home", tmp_path / "appdata"
    selected = default_data_dir(home, appdata, packaged_windows=True)
    assert selected == appdata / "Multitrackert Audio" / "Data"
    # Existing source-install projects take precedence and are never moved or deleted.
    legacy = home / ".multitrackert"
    project = legacy / "jobs" / "old-project" / "export"
    project.mkdir(parents=True)
    (project / "speaker_01.wav").write_bytes(b"previously-generated-audio")
    assert default_data_dir(home, appdata, packaged_windows=True) == legacy
    assert (project / "speaker_01.wav").read_bytes() == b"previously-generated-audio"
    assert default_data_dir(home, appdata, packaged_windows=False) == legacy


def test_recover_saved_export_after_interrupted_browser_download(tmp_path, monkeypatch):
    import multitrack.app as module

    ident = "a" * 32
    folder = tmp_path / "jobs" / ident
    (folder / "export").mkdir(parents=True)
    original = b"original video bytes"
    archive = b"PK" + bytes(range(256)) * 100
    (folder / "input.mp4").write_bytes(original)
    (folder / "result.zip").write_bytes(archive)
    atomic_json(folder / "status.json", {"state": "done"})
    opened = []
    monkeypatch.setattr(module, "open_folder", lambda path: opened.append(path.resolve()))
    # New server/browser session still finds the same completed files.
    with TestClient(create_app(tmp_path)) as client:
        response = client.get(f"/api/jobs/{ident}/download", headers={"Range": "bytes=0-31"})
        assert response.status_code == 206 and response.content == archive[:32]
        later = client.get(f"/api/jobs/{ident}/download", headers={"Range": "bytes=32-"})
        assert later.status_code == 206 and later.content == archive[32:]
        info = client.get(f"/api/jobs/{ident}/storage").json()
        assert Path(info["zip"]).read_bytes() == archive
        assert Path(info["source"]).read_bytes() == original
        assert (
            client.post(
                f"/api/jobs/{ident}/open-folder", headers={"X-Multitrack": "local"}
            ).status_code
            == 200
        )
        assert opened == [(folder / "export").resolve()]
        assert (
            client.post("/api/storage/open", headers={"X-Multitrack": "local"}).status_code == 200
        )
        assert opened[-1] == (tmp_path / "jobs").resolve()
        assert client.get("/api/jobs").json()[0]["id"] == ident


def test_original_name_is_metadata_and_cannot_change_saved_source_path(tmp_path, monkeypatch):
    import multitrack.app as module

    monkeypatch.setattr(module, "model_ready", lambda _: True)
    monkeypatch.setattr(Jobs, "start", lambda *args: None)
    monkeypatch.setattr(config, "MAX_BYTES", 100)
    with TestClient(create_app(tmp_path)) as client:
        response = client.post(
            "/api/jobs",
            content=b"video",
            headers={"X-Multitrack": "local", "X-Filename": "..%2F..%2Fvergadering%20oktober.mp4"},
        )
        assert response.status_code == 202
        ident = response.json()["id"]
        job = client.get(f"/api/jobs/{ident}").json()
        assert job["project"]["name"] == "vergadering oktober.mp4"
        info = client.get(f"/api/jobs/{ident}/storage").json()
        assert Path(info["source"]) == tmp_path / "jobs" / ident / "input.mp4"
        assert not (tmp_path / "vergadering oktober.mp4").exists()
