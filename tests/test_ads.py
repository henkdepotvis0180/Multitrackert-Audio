import io

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient
from scipy.signal import lfilter

from multitrack.ad_text import phrase_hits
from multitrack.ads import find_matches, reduce_known_ads
from multitrack.app import create_app
from multitrack.diarize import Segment, bound_voice_tracks
from multitrack.state import Progress, atomic_json


def put_reference(root, audio, rate=16000, ident="a" * 32):
    folder = root / ident
    folder.mkdir(parents=True)
    sf.write(folder / "reference.wav", audio, rate, subtype="FLOAT")
    atomic_json(folder / "metadata.json", {"name": "Test reference", "duration": len(audio) / rate})
    return ident


def test_repeated_reference_cancellation_preserves_speech_and_timeline(tmp_path):
    rate = 16000
    rng = np.random.default_rng(8)
    reference = lfilter([1, 0.3], [1, -0.6], rng.normal(0, 0.09, 3 * rate)).astype("float32")
    speech = lfilter([1], [1, -0.25], rng.normal(0, 0.025, (16 * rate, 2)), axis=0).astype(
        "float32"
    )
    ad = np.zeros_like(speech)
    for start in [2 * rate, 10 * rate]:
        ad[start : start + len(reference), 0] = reference * 0.9
        ad[start : start + len(reference), 1] = reference * 0.6
    mixture = speech + ad
    path = tmp_path / "original.wav"
    sf.write(path, mixture, rate, subtype="FLOAT")
    ident = put_reference(tmp_path / "library", reference)
    result = reduce_known_ads(path, tmp_path / "library", [ident], tmp_path, Progress(tmp_path))
    assert [round(m["start"], 2) for m in result["matches"]] == [2, 10]
    cleaned, _ = sf.read(tmp_path / "cleaned.wav", dtype="float32")
    removed, _ = sf.read(tmp_path / "radio.wav", dtype="float32")
    np.testing.assert_allclose(cleaned + removed, mixture, atol=1e-7)
    np.testing.assert_array_equal(cleaned[: 2 * rate], speech[: 2 * rate])
    np.testing.assert_array_equal(cleaned[5 * rate : 10 * rate], speech[5 * rate : 10 * rate])
    before = np.mean((mixture - speech) ** 2)
    after = np.mean((cleaned - speech) ** 2)
    assert 10 * np.log10(before / after) > 10


def test_search_covers_late_audio_and_window_boundaries(tmp_path):
    rate = 8000
    rng = np.random.default_rng(10)
    reference = rng.normal(0, 0.1, 3 * rate).astype("float32")
    mixture = rng.normal(0, 0.01, 135 * rate).astype("float32")
    for second in [0, 118, 132]:
        mixture[second * rate : second * rate + len(reference)] += reference
    sf.write(tmp_path / "source.wav", mixture, rate, subtype="FLOAT")
    sf.write(tmp_path / "reference.wav", reference, rate, subtype="FLOAT")
    matches = find_matches(tmp_path / "source.wav", tmp_path / "reference.wav", Progress(tmp_path))
    assert [round(m["start"]) for m in matches] == [0, 118, 132]


def test_nonmatch_does_not_change_audio_or_create_a_fake_cleaned_result(tmp_path):
    rng = np.random.default_rng(12)
    source = tmp_path / "source.wav"
    sf.write(source, rng.normal(0, 0.1, 80000), 16000, subtype="FLOAT")
    original = source.read_bytes()
    ident = put_reference(tmp_path / "library", rng.normal(0, 0.1, 48000))
    result = reduce_known_ads(source, tmp_path / "library", [ident], tmp_path, Progress(tmp_path))
    assert result["matches"] == [] and not result["applied"]
    assert source.read_bytes() == original
    assert not (tmp_path / "cleaned.wav").exists()


def test_text_clues_are_specific_and_not_brand_name_only():
    assert not phrase_hits("Ik ga straks naar Albert Heijn en daarna naar Lidl.")
    hits = phrase_hits("DAT IS HET LEKKERE VAN ALBERT HEIJN!")
    assert [h["label"] for h in hits] == ["Albert Heijn"]
    assert not phrase_hits("hallo jumbo", ["hallo jumbo"])  # too short to be specific
    assert phrase_hits("héérlijk vers brood voor iedereen", ["heerlijk vers brood"])


def test_voice_group_overflow_is_bounded_without_merging_people_into_two_ids():
    segments = [Segment(i, i + 1, i + 1) for i in range(15)]
    visible, overflow = bound_voice_tracks(segments)
    assert len({s.speaker for s in visible}) == 12
    assert overflow["detected_groups"] == 15
    assert len(overflow["grouped_segments"]) == 3
    assert {s.speaker for s in visible} == set(range(1, 13))
    # All original time ranges and group IDs remain represented in the metadata.
    assert [s.start for s in visible] + [s["start"] for s in overflow["grouped_segments"]] == list(
        range(15)
    )


def test_library_upload_list_delete_and_invalid_audio(tmp_path):
    buffer = io.BytesIO()
    sf.write(buffer, np.random.default_rng(5).normal(0, 0.1, 48000), 16000, format="WAV")
    with TestClient(create_app(tmp_path)) as client:
        h = {"X-Multitrack": "local", "X-Filename": "Test%20advertentie.wav"}
        response = client.post("/api/ad-library", content=buffer.getvalue(), headers=h)
        assert response.status_code == 201, response.text
        ident = response.json()["id"]
        assert client.get("/api/ad-library").json()[0]["name"] == "Test advertentie.wav"
        assert client.post("/api/ad-library", content=b"not audio", headers=h).status_code == 422
        assert len(client.get("/api/ad-library").json()) == 1
        assert client.delete("/api/ad-library/" + ident, headers=h).status_code == 200
        assert client.get("/api/ad-library").json() == []
        assert client.delete("/api/ad-library/not-an-id", headers=h).status_code == 404


def test_extra_voice_audio_is_preserved_in_residual_when_track_limit_is_exceeded(tmp_path):
    from multitrack.export import render

    rate = 8000
    original = np.random.default_rng(99).normal(0, 0.04, (rate * 15, 1)).astype("float32")
    sf.write(tmp_path / "original.wav", original, rate, subtype="FLOAT")
    segments, overflow = bound_voice_tracks([Segment(i, i + 1, i + 1) for i in range(15)])
    output, _ = render(
        tmp_path,
        {"sample_rate": rate, "duration": 15},
        segments,
        np.zeros(15 * 16000, dtype="float32"),
        None,
        {},
        False,
        Progress(tmp_path),
    )
    background, _ = sf.read(output / "background.wav", dtype="float32", always_2d=True)
    np.testing.assert_array_equal(background[12 * rate :], original[12 * rate :])
    reconstructed = background.copy()
    for path in (output / "speakers").glob("*.wav"):
        reconstructed += sf.read(path, dtype="float32", always_2d=True)[0]
    np.testing.assert_allclose(reconstructed, original, atol=1e-7)
    assert len(overflow["grouped_segments"]) == 3


def test_longest_groups_are_renumbered_to_playable_track_ids():
    segments = [Segment(i, i + 0.1, i + 1) for i in range(110)]
    segments.append(Segment(200, 220, 110))
    visible, overflow = bound_voice_tracks(segments)
    assert {s.speaker for s in visible} == set(range(1, 13))
    assert any(m["source_group"] == 110 for m in overflow["individual_source_groups"])
    assert any(s.start == 200 for s in visible)
