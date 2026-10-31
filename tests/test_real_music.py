import socket

import numpy as np
import pytest
import soundfile as sf

from multitrack.config import MODELS, ROOT
from multitrack.hardware import inspect_hardware
from multitrack.music import ready, separate_music
from multitrack.state import Progress


@pytest.mark.models
@pytest.mark.skipif(not ready(MODELS), reason="Optional real HDemucs weights/runtime not installed")
def test_real_music_inference_offline_and_native_rate_reconstruction(tmp_path, monkeypatch):
    from multitrack.audio import resample

    speech_path = ROOT / ".local-data/test-speech.wav"
    if not speech_path.exists():
        pytest.skip("Real speech fixture missing")
    speech, rate = sf.read(speech_path, dtype="float32")
    speech = resample(speech[: rate * 3], rate, 48000)
    t = np.arange(len(speech)) / 48000
    instrumental = (0.08 * np.sin(2 * np.pi * 220 * t) + 0.04 * np.sin(2 * np.pi * 330 * t)).astype(
        "float32"
    )
    mixed = np.stack([speech + instrumental, 0.8 * speech + instrumental], axis=1)
    sf.write(tmp_path / "original.wav", mixed, 48000, subtype="FLOAT")

    def forbidden(*args, **kwargs):
        raise AssertionError("Model inference tried to use the network")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    info = separate_music(
        tmp_path / "original.wav", tmp_path, MODELS, inspect_hardware(), Progress(tmp_path)
    )
    vocal, vr = sf.read(tmp_path / "working.wav", dtype="float32")
    music, mr = sf.read(tmp_path / "music.wav", dtype="float32")
    assert vr == mr == 48000 and vocal.shape == music.shape == mixed.shape
    assert np.isfinite(vocal).all() and np.isfinite(music).all()
    assert np.max(np.abs(vocal)) > 1e-4 and np.max(np.abs(music)) > 1e-4
    np.testing.assert_allclose(vocal + music, mixed, atol=1e-7)
    assert info["model_sample_rate"] == 44100
