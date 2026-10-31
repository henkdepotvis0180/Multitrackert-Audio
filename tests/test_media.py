import subprocess

import numpy as np
import pytest
import soundfile as sf

from multitrack.media import MediaError, extract, probe


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *map(str, args)], check=True)


def test_real_mp4_extract_preserves_delayed_audio(tmp_path):
    # Audio begins at .5s; extracted audio must keep that offset, not slide to zero.
    audio = tmp_path / "tone.wav"
    sf.write(
        audio, 0.2 * np.sin(2 * np.pi * 440 * np.arange(16000) / 16000), 16000, subtype="FLOAT"
    )
    path = tmp_path / "input.mp4"
    ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "color=s=160x90:r=25:d=2",
        "-itsoffset",
        "0.5",
        "-i",
        audio,
        "-c:v",
        "mpeg4",
        "-c:a",
        "aac",
        "-t",
        "2",
        path,
    )
    info = probe(path)
    extract(path, tmp_path, info)
    data, rate = sf.read(tmp_path / "original.wav")
    assert len(data) == round(info["duration"] * rate)
    assert np.max(np.abs(data[: int(0.3 * rate)])) < 0.001
    assert np.max(np.abs(data[int(0.6 * rate) : int(0.8 * rate)])) > 0.1
    streams = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(tmp_path / "video.mp4")],
        text=True,
    )
    assert '"codec_type": "audio"' not in streams


def test_invalid_and_silent_video(tmp_path):
    source = tmp_path / "invalid.mp4"
    source.write_bytes(b"not a video")
    with pytest.raises(MediaError):
        probe(source)
    ffmpeg("-f", "lavfi", "-i", "color=s=160x90:r=25:d=1", "-an", "-c:v", "mpeg4", source)
    with pytest.raises(MediaError, match="zowel beeld als geluid"):
        probe(source)
