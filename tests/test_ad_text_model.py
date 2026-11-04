import hashlib
import socket

import pytest
import soundfile as sf

from multitrack.ad_text import ready, scan_text
from multitrack.config import MODELS, ROOT
from multitrack.state import Progress


@pytest.mark.models
@pytest.mark.skipif(not ready(MODELS), reason="Optional Whisper Small model not installed")
def test_real_text_model_is_offline_and_never_edits_source_audio(tmp_path, monkeypatch):
    fixture = ROOT / ".local-data/test-speech.wav"
    if not fixture.is_file():
        pytest.skip("Real speech fixture missing")
    speech, rate = sf.read(fixture, dtype="float32")
    source = tmp_path / "speech.wav"
    sf.write(source, speech[: rate * 4], rate, subtype="FLOAT")
    before = hashlib.sha256(source.read_bytes()).hexdigest()

    def forbidden(*args, **kwargs):
        raise AssertionError("Text inference attempted network access")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    result = scan_text(source, MODELS, Progress(tmp_path))
    assert result["method"] == "whisper_small_nl_phrase_clues"
    assert result["automatic_removal"] is False
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert not (tmp_path / "cleaned.wav").exists()
    assert not (tmp_path / "radio.wav").exists()
