"""Explicitly distinguish the unrun real separator from deterministic adapter tests."""

import numpy as np
import pytest

from multitrack.config import MODELS, ROOT
from multitrack.separate import Separator, ready


@pytest.mark.skipif(not ready(MODELS), reason="Optional SepFormer weights not installed")
def test_real_separator_local_inference(monkeypatch):
    import socket

    import soundfile as sf

    sample = ROOT / ".local-data" / "test-speech.wav"
    if not sample.is_file():
        pytest.skip("Real speech fixture not installed")

    def forbidden(*args, **kwargs):
        raise AssertionError("Separator tried to open a network connection")

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    data, rate = sf.read(sample, dtype="float32")
    assert rate == 16000
    mix = 0.5 * (data[16000:48000] + data[7 * 16000 : 9 * 16000])
    sources = Separator(MODELS, "cpu")(mix)
    assert len(sources) == 2
    assert all(len(s) == len(mix) and np.isfinite(s).all() for s in sources)
    assert not np.allclose(sources[0], sources[1])
