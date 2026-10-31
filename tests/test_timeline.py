import json
import zipfile

import numpy as np
import soundfile as sf

from multitrack.diarize import Segment, intervals
from multitrack.export import package, render
from multitrack.separate import assign_sources
from multitrack.state import Progress


def test_overlapping_same_speaker_and_clamping():
    regions = list(intervals([Segment(-1, 2, 1), Segment(1, 3, 1), Segment(2, 8, 2)], 5))
    assert regions == [(0.0, 1, (1,)), (1, 2, (1,)), (2, 3, (1, 2)), (3, 5, (2,))]


def test_sample_exact_export_and_mixed_overlap(tmp_path):
    rate = 48000
    original = np.random.default_rng(7).uniform(-0.4, 0.4, (rate * 4, 2)).astype("float32")
    sf.write(tmp_path / "original.wav", original, rate, subtype="FLOAT")
    # Packaging only copies this file, real muxing is exercised by integration tests.
    (tmp_path / "video.mp4").write_bytes(b"test")
    segments = [Segment(0.25, 2, 1), Segment(1.5, 3, 2), Segment(3.5, 3.75, 1)]
    info = dict(duration=4, sample_rate=rate, channels=2, fps="25/1", width=160, height=90)
    progress = Progress(tmp_path)
    output, overlaps = render(
        tmp_path, info, segments, np.zeros(64000), tmp_path, {}, False, progress
    )
    a, _ = sf.read(output / "speakers/speaker_01.wav", dtype="float32")
    b, _ = sf.read(output / "speakers/speaker_02.wav", dtype="float32")
    assert len(a) == len(b) == len(original)
    np.testing.assert_array_equal(a[12000:72000], original[12000:72000])
    np.testing.assert_array_equal(a[72000:96000], original[72000:96000] / 2)
    assert not np.any(a[:12000]) and not np.any(a[96000:168000])
    np.testing.assert_array_equal(b[72000:96000], original[72000:96000] / 2)
    np.testing.assert_array_equal(b[96000:144000], original[96000:144000])
    assert overlaps == [
        {
            "start": 1.5,
            "end": 2,
            "speakers": [1, 2],
            "method": "mixed",
            "note": "Scheiding uitgeschakeld of meer dan twee actieve sprekers.",
        }
    ]
    package(tmp_path, output, info, segments, overlaps, progress, {})
    with zipfile.ZipFile(tmp_path / "result.zip") as z:
        assert {
            "original.wav",
            "video.mp4",
            "timeline.xml",
            "timeline.json",
            "segments.csv",
        } <= set(z.namelist())
        manifest = json.loads(z.read("timeline.json"))
        assert [s["fragment"] for s in manifest["segments"]] == [1, 2, 3]
        assert len([n for n in z.namelist() if n.startswith("clips/")]) == 3
        assert z.testzip() is None
    first, _ = sf.read(output / manifest["segments"][0]["file"], dtype="float32")
    np.testing.assert_array_equal(first, a[12000:96000])


def test_ambiguous_sources_are_not_silently_assigned():
    refs = [np.array([1.0, 0.0]), np.array([0.0, 1.0])]
    assert assign_sources([refs[1], refs[0]], refs, lambda a: a) == [1, 0]
    assert assign_sources([np.array([0.7, 0.7]), np.array([0.7, 0.7])], refs, lambda a: a) is None


def test_silence_has_no_invented_speaker_tracks(tmp_path):
    sf.write(tmp_path / "original.wav", np.zeros(16000), 16000, subtype="FLOAT")
    output, overlaps = render(
        tmp_path,
        {"duration": 1, "sample_rate": 16000},
        [],
        np.zeros(16000),
        tmp_path,
        {},
        False,
        Progress(tmp_path),
    )
    assert not list((output / "speakers").iterdir())
    assert overlaps == []


def test_separated_overlap_is_assigned_to_references(tmp_path, monkeypatch):
    import multitrack.export as module

    rate = 16000
    original = np.full((rate * 6, 1), 0.5, dtype="float32")
    sf.write(tmp_path / "original.wav", original, rate, subtype="FLOAT")
    segments = [Segment(0, 4, 1), Segment(2, 6, 2)]

    class FakeEmbedder:
        def __init__(self, *args):
            pass

        def __call__(self, audio):
            return np.array([1.0, 0.0]) if audio.mean() > 0 else np.array([0.0, 1.0])

    class FakeSeparator:
        def __init__(self, *args):
            pass

        def __call__(self, audio):
            # Reverse source order deliberately: assignment must correct it.
            return [np.full(len(audio), -0.2), np.full(len(audio), 0.3)]

    monkeypatch.setattr(module, "Embedder", FakeEmbedder)
    monkeypatch.setattr(module, "Separator", FakeSeparator)
    analysis = np.concatenate([np.ones(rate * 3), -np.ones(rate * 3)])
    output, overlap = render(
        tmp_path,
        {"duration": 6, "sample_rate": rate},
        segments,
        analysis,
        tmp_path,
        {"inference_threads": 2, "separation_device": "cpu"},
        True,
        Progress(tmp_path),
    )
    first, _ = sf.read(output / "speakers/speaker_01.wav")
    second, _ = sf.read(output / "speakers/speaker_02.wav")
    np.testing.assert_allclose(first[rate * 2 : rate * 4], 0.3, atol=1e-7)
    np.testing.assert_allclose(second[rate * 2 : rate * 4], -0.2, atol=1e-7)
    assert overlap[0]["method"] == "separated_8khz"
