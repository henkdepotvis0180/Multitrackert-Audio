import json
import zipfile
from xml.etree import ElementTree as ET

import numpy as np
import pytest
import soundfile as sf
from scipy.signal import lfilter

from multitrack.diarize import Segment
from multitrack.export import package, render
from multitrack.radio import locate_reference, reduce_radio
from multitrack.state import Progress


def test_music_present_during_silence_and_overlap_reconstructs_original(tmp_path):
    rate = 16000
    t = np.arange(rate * 5) / rate
    music = (0.1 * np.sin(2 * np.pi * 220 * t)).astype("float32")
    original = np.stack([music, music * 0.8], axis=1)
    original[rate : 4 * rate] += np.random.default_rng(2).normal(0, 0.07, (3 * rate, 2))
    sf.write(tmp_path / "original.wav", original, rate, subtype="FLOAT")
    (tmp_path / "video.mp4").write_bytes(b"fixture")
    info = dict(duration=5, sample_rate=rate, channels=2, fps="25/1", width=160, height=90)
    progress = Progress(tmp_path)
    segments = [Segment(1, 3, 1), Segment(2, 4, 2)]
    output, overlaps = render(tmp_path, info, segments, music, tmp_path, {}, False, progress)
    background, _ = sf.read(output / "background.wav", dtype="float32")
    a, _ = sf.read(output / "speakers/speaker_01.wav", dtype="float32")
    b, _ = sf.read(output / "speakers/speaker_02.wav", dtype="float32")
    assert len(background) == len(a) == len(b) == len(original)
    np.testing.assert_array_equal(background[:rate], original[:rate])
    np.testing.assert_array_equal(background[4 * rate :], original[4 * rate :])
    np.testing.assert_allclose(a + b + background, original, atol=1e-7)
    assert not np.any(background[2 * rate : 3 * rate])  # mixed overlap isn't duplicated
    manifest = package(tmp_path, output, info, segments, overlaps, progress, {})
    assert manifest["version"] == 2
    assert any(t["file"] == "background.wav" for t in manifest["tracks"])
    xml = ET.parse(output / "timeline.xml")
    assert any(f.text == "background.wav" for f in xml.findall(".//pathurl"))
    with zipfile.ZipFile(tmp_path / "result.zip") as archive:
        assert "background.wav" in archive.namelist()
        assert archive.testzip() is None


def test_no_speakers_preserves_all_music_in_background(tmp_path):
    source = np.random.default_rng(0).normal(0, 0.1, (16000, 1)).astype("float32")
    sf.write(tmp_path / "original.wav", source, 16000, subtype="FLOAT")
    output, _ = render(
        tmp_path,
        {"duration": 1, "sample_rate": 16000},
        [],
        np.zeros(16000),
        tmp_path,
        {},
        False,
        Progress(tmp_path),
    )
    actual, _ = sf.read(output / "background.wav", always_2d=True, dtype="float32")
    np.testing.assert_array_equal(actual, source)


def test_reference_cancels_correlated_audio_preserving_unrelated_speech(tmp_path):
    rate, duration, offset = 16000, 18, 1.25
    rng = np.random.default_rng(9)
    reference = lfilter([1.0, 0.3], [1.0, -0.7], rng.normal(0, 0.08, rate * duration)).astype(
        "float32"
    )
    radio = np.zeros(rate * duration, dtype="float32")
    aligned = np.pad(reference, (round(offset * rate), 0))[: len(radio)]
    # Linear acoustic path with a 5 ms echo.
    taps = np.zeros(81)
    taps[0], taps[-1] = 0.7, 0.15
    radio[:] = lfilter(taps, [1], aligned)
    speech = lfilter([1], [1, -0.3], rng.normal(0, 0.035, len(radio))).astype("float32")
    mixed = (radio + speech).astype("float32")
    sf.write(tmp_path / "original.wav", mixed, rate, subtype="FLOAT")
    sf.write(tmp_path / "reference.wav", reference, rate, subtype="FLOAT")
    result = reduce_radio(
        tmp_path / "original.wav", tmp_path / "reference.wav", tmp_path, Progress(tmp_path)
    )
    assert abs(result["offset_seconds"] - offset) < 0.003
    clean, _ = sf.read(tmp_path / "cleaned.wav", dtype="float32")
    removed, _ = sf.read(tmp_path / "radio.wav", dtype="float32")
    assert len(clean) == len(removed) == len(mixed)
    np.testing.assert_allclose(clean + removed, mixed, atol=1e-7)
    # Actual improvement against a known ground truth, not just finite outputs.
    before = np.mean((mixed - speech) ** 2)
    after = np.mean((clean - speech) ** 2)
    improvement_db = 10 * np.log10(before / after)
    assert improvement_db > 6, improvement_db


def test_reference_mismatch_is_rejected(tmp_path):
    rng = np.random.default_rng(4)
    sf.write(tmp_path / "mix.wav", rng.normal(0, 0.1, 320000), 16000, subtype="FLOAT")
    sf.write(tmp_path / "ref.wav", rng.normal(0, 0.1, 320000), 16000, subtype="FLOAT")
    with pytest.raises(ValueError, match="Geen betrouwbare match"):
        locate_reference(tmp_path / "mix.wav", tmp_path / "ref.wav", Progress(tmp_path))


def test_reference_radio_xml_is_muted_and_all_stems_are_in_zip(tmp_path):
    rate, frames = 16000, 16000
    rng = np.random.default_rng(7)
    voice, music, radio = [rng.normal(0, 0.03, (frames, 1)).astype("float32") for _ in range(3)]
    sf.write(tmp_path / "original.wav", voice + music + radio, rate, subtype="FLOAT")
    sf.write(tmp_path / "working.wav", voice, rate, subtype="FLOAT")
    sf.write(tmp_path / "music.wav", music, rate, subtype="FLOAT")
    sf.write(tmp_path / "radio.wav", radio, rate, subtype="FLOAT")
    sf.write(tmp_path / "cleaned.wav", voice + music, rate, subtype="FLOAT")
    (tmp_path / "video.mp4").write_bytes(b"fixture")
    info = dict(duration=1, sample_rate=rate, channels=1, fps="25/1", width=160, height=90)
    progress = Progress(tmp_path)
    output, overlaps = render(
        tmp_path,
        info,
        [Segment(0.1, 0.9, 1)],
        np.zeros(frames),
        tmp_path,
        {},
        False,
        progress,
        tmp_path / "working.wav",
    )
    manifest = package(
        tmp_path,
        output,
        info,
        [Segment(0.1, 0.9, 1)],
        overlaps,
        progress,
        {},
        {"radio": {"method": "reference"}, "music": {"model": "test"}},
    )
    reconstructed = np.zeros((frames, 1), dtype="float32")
    for track in manifest["tracks"]:
        audio, _ = sf.read(output / track["file"], dtype="float32", always_2d=True)
        reconstructed += audio
    original, _ = sf.read(output / "original.wav", dtype="float32", always_2d=True)
    np.testing.assert_allclose(reconstructed, original, atol=1e-7)
    xml = ET.parse(output / "timeline.xml")
    radio_item = next(
        i for i in xml.findall(".//clipitem") if i.findtext("file/pathurl") == "radio.wav"
    )
    assert radio_item.findtext("enabled") == "FALSE"
    assert not next(t for t in manifest["tracks"] if t["id"] == "radio")["enabled"]
    with zipfile.ZipFile(tmp_path / "result.zip") as archive:
        assert {"background.wav", "music.wav", "radio.wav", "cleaned.wav"} <= set(
            archive.namelist()
        )
        assert json.loads(archive.read("timeline.json"))["processing"]["radio"]


@pytest.mark.parametrize("offset", [-3.25, 95.25])
def test_reference_offsets_can_be_negative_or_beyond_initial_search_window(tmp_path, offset):
    rate = 4000
    rng = np.random.default_rng(81)
    ref = rng.normal(0, 0.1, rate * 12).astype("float32")
    duration = 20 if offset < 0 else 115
    mix = np.zeros(rate * duration, dtype="float32")
    start = round(offset * rate)
    left, right = max(0, start), min(len(mix), start + len(ref))
    mix[left:right] = ref[left - start : right - start]
    sf.write(tmp_path / "mix.wav", mix, rate, subtype="FLOAT")
    sf.write(tmp_path / "ref.wav", ref, rate, subtype="FLOAT")
    found, score = locate_reference(
        tmp_path / "mix.wav",
        tmp_path / "ref.wav",
        Progress(tmp_path),
        offset if offset > 0 else None,
    )
    assert abs(found - offset) < 0.002
    assert score > 0.5
