"""Integration against real pretrained models. No canned diarization responses."""

import os
import subprocess
import time
import zipfile
from pathlib import Path

import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from multitrack import config
from multitrack.app import create_app
from multitrack.diarize import diarize, model_ready
from multitrack.state import Progress

MODELS = config.MODELS
SAMPLE = Path(
    os.environ.get("MULTITRACK_TEST_AUDIO", str(config.ROOT / ".local-data" / "test-speech.wav"))
)
pytestmark = [
    pytest.mark.models,
    pytest.mark.skipif(
        not model_ready(MODELS) or not SAMPLE.exists(),
        reason="Real models/test speech not installed",
    ),
]


def test_real_four_speaker_inference_offline(tmp_path):
    data, rate = sf.read(SAMPLE, dtype="float32")
    assert rate == 16000
    segments = diarize(data, MODELS, 4, 2, Progress(tmp_path))
    assert len({s.speaker for s in segments}) == 4
    assert len(segments) >= 4
    assert all(0 <= s.start < s.end <= len(data) / rate for s in segments)
    (tmp_path / "result.txt").write_text(str(segments))


def test_real_upload_to_download(tmp_path, monkeypatch):
    monkeypatch.setenv("MULTITRACK_MODELS", str(MODELS))
    video = tmp_path / "fixture.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=s=160x90:r=25",
            "-i",
            str(SAMPLE),
            "-c:v",
            "mpeg4",
            "-c:a",
            "aac",
            "-shortest",
            str(video),
        ],
        check=True,
    )
    with TestClient(create_app(tmp_path / "data")) as client:
        with video.open("rb") as f:
            response = client.post(
                "/api/jobs?speakers=4", content=f.read(), headers={"X-Multitrack": "local"}
            )
        assert response.status_code == 202, response.text
        ident = response.json()["id"]
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            status = client.get(f"/api/jobs/{ident}").json()
            if status["state"] in {"done", "error", "cancelled"}:
                break
            time.sleep(0.2)
        assert status["state"] == "done", status
        assert status["speakers"] == [1, 2, 3, 4]
        response = client.get(f"/api/jobs/{ident}/download")
        assert response.status_code == 200
        export = tmp_path / "download.zip"
        export.write_bytes(response.content)
        with zipfile.ZipFile(export) as z:
            assert z.testzip() is None
            z.extractall(tmp_path / "unpacked")
        original = sf.info(tmp_path / "unpacked/original.wav")
        for p in (tmp_path / "unpacked/speakers").glob("*.wav"):
            assert sf.info(p).frames == original.frames
        assert client.get(f"/api/jobs/{ident}/timeline").json()["segments"]
        assert (
            client.get(
                f"/api/jobs/{ident}/media/speaker_01.wav", headers={"Range": "bytes=0-63"}
            ).status_code
            == 206
        )


def test_real_silence_produces_no_speakers(tmp_path):
    import numpy as np

    segments = diarize(np.zeros(16000 * 12, dtype="float32"), MODELS, 0, 2, Progress(tmp_path))
    assert segments == []


def test_real_model_has_no_python_network_calls(tmp_path, monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("Inference tried to open a network connection")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    audio, _ = sf.read(SAMPLE, dtype="float32")
    assert diarize(audio[: 16000 * 20], MODELS, 0, 2, Progress(tmp_path))


def test_real_overlap_detection_with_two_mixed_voices(tmp_path):
    import numpy as np

    from multitrack.diarize import intervals

    data, rate = sf.read(SAMPLE, dtype="float32")
    a = data[round(0.4 * rate) : round(3.9 * rate)]
    b = data[round(7 * rate) : round(10.5 * rate)]
    mix = np.concatenate(
        [a, np.zeros(rate // 2), b, np.zeros(rate // 2), 0.5 * a + 0.5 * b, np.zeros(rate // 2)]
    ).astype("float32")
    segments = diarize(mix, MODELS, 2, 2, Progress(tmp_path))
    overlaps = [(a, b) for a, b, active in intervals(segments, len(mix) / rate) if len(active) == 2]
    assert sum(b - a for a, b in overlaps) > 0.5
    assert all(7.8 < a < b < 11.8 for a, b in overlaps)
