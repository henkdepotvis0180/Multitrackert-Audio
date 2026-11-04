from xml.etree import ElementTree as ET

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from multitrack.app import create_app
from multitrack.remix import configure_mix, remix
from multitrack.state import Progress, atomic_json, read_json


def fixture(folder):
    export = folder / "export"
    (export / "speakers").mkdir(parents=True)
    rng = np.random.default_rng(15)
    tracks = []
    for ident, path in [
        ("speaker_01", "speakers/speaker_01.wav"),
        ("speaker_02", "speakers/speaker_02.wav"),
        ("music", "music.wav"),
        ("background", "background.wav"),
    ]:
        sf.write(
            export / path, rng.normal(0, 0.05, (16000, 2)).astype("float32"), 16000, subtype="FLOAT"
        )
        tracks.append({"id": ident, "name": ident, "file": path, "enabled": True})
    original = sum(sf.read(export / t["file"], dtype="float32")[0] for t in tracks)
    sf.write(export / "original.wav", original, 16000, subtype="FLOAT")
    (export / "LEESMIJ.txt").write_text("Test\n")
    (export / "video.mp4").write_bytes(b"fixture")
    manifest = {
        "version": 2,
        "tracks": tracks,
        "media": {
            "duration": 1,
            "sample_rate": 16000,
            "channels": 2,
            "fps": "25/1",
            "width": 160,
            "height": 90,
        },
        "segments": [{"speaker": 1}, {"speaker": 2}],
        "overlaps": [],
        "processing": {},
    }
    atomic_json(export / "timeline.json", manifest)
    atomic_json(folder / "status.json", {"state": "done"})
    return manifest


@pytest.mark.parametrize(
    "mode,selected,enabled",
    [
        ("keep_all", [], {"speaker_01", "speaker_02", "music", "background"}),
        ("remove_music", [], {"speaker_01", "speaker_02", "background"}),
        ("remove_radio", [2], {"speaker_01", "background"}),
        ("remove_vocals", [2], {"speaker_01", "music", "background"}),
    ],
)
def test_mix_modes_are_reversible_and_preserve_all_source_stems(tmp_path, mode, selected, enabled):
    manifest = fixture(tmp_path)
    originals = {
        t["id"]: sf.read(tmp_path / "export" / t["file"], dtype="float32")[0]
        for t in manifest["tracks"]
    }
    result = remix(tmp_path, mode, selected, Progress(tmp_path))
    clean, _ = sf.read(tmp_path / "export/cleaned.wav", dtype="float32")
    expected = sum(originals[s] for s in enabled)
    np.testing.assert_allclose(clean, expected, atol=1e-7)
    removed, _ = sf.read(tmp_path / "export/removed.wav", dtype="float32")
    original, _ = sf.read(tmp_path / "export/original.wav", dtype="float32")
    np.testing.assert_allclose(clean + removed, original, atol=1e-7)
    assert {t["id"] for t in result["tracks"] if t["enabled"]} == enabled
    for t in manifest["tracks"]:
        np.testing.assert_array_equal(
            sf.read(tmp_path / "export" / t["file"], dtype="float32")[0], originals[t["id"]]
        )
    if mode in {"remove_radio", "remove_vocals"}:
        xml = ET.parse(tmp_path / "export/timeline.xml")
        item = next(
            i
            for i in xml.findall(".//clipitem")
            if i.findtext("file/pathurl") == "speakers/speaker_02.wav"
        )
        assert item.findtext("enabled") == "FALSE"
    # Change the selection without rerunning any model; return to the original mix.
    remix(tmp_path, "keep_all", [], Progress(tmp_path))
    restored, _ = sf.read(tmp_path / "export/cleaned.wav", dtype="float32")
    np.testing.assert_allclose(restored, original, atol=1e-7)


def test_cannot_claim_full_radio_removal_without_selecting_its_voice(tmp_path):
    manifest = fixture(tmp_path)
    with pytest.raises(ValueError, match="Beluister"):
        configure_mix(manifest, "remove_radio", [])
    with pytest.raises(ValueError, match="Onbekende spreker"):
        configure_mix(manifest, "remove_radio", [8])
    manifest["tracks"] = [t for t in manifest["tracks"] if t["id"] != "music"]
    with pytest.raises(ValueError, match="Muziek apart zetten"):
        configure_mix(manifest, "remove_radio", [2])


def test_mix_api_validation_does_not_damage_existing_export(tmp_path):
    ident = "a" * 32
    folder = tmp_path / "jobs" / ident
    fixture(folder)
    with TestClient(create_app(tmp_path)) as client:
        h = {"X-Multitrack": "local"}
        assert (
            client.post(
                f"/api/jobs/{ident}/mix",
                headers=h,
                json={"mode": "remove_radio", "excluded_speakers": []},
            ).status_code
            == 422
        )
        assert (
            client.post(f"/api/jobs/{ident}/mix", headers=h, json={"mode": "unknown"}).status_code
            == 422
        )
        assert read_json(folder / "status.json")["state"] == "done"


@pytest.mark.parametrize("mode", ["remove_radio", "remove_vocals"])
def test_radio_fragments_preserve_rest_and_have_a_separate_premiere_track(
    tmp_path, mode, monkeypatch
):
    import multitrack.remix as module

    # Exercise selection across multiple streaming blocks, including overlapping
    # selections on the same speaker; samples must only be removed once.
    monkeypatch.setattr(module, "BLOCK", 1800)
    manifest = fixture(tmp_path)
    manifest["segments"] = [
        {"fragment": 1, "speaker": 2, "start": 0.2, "end": 0.55},
        {"fragment": 2, "speaker": 2, "start": 0.45, "end": 0.75},
        {"fragment": 3, "speaker": 2, "start": 0.8, "end": 0.95},
    ]
    atomic_json(tmp_path / "export/timeline.json", manifest)
    original_stem, rate = sf.read(tmp_path / "export/speakers/speaker_02.wav", dtype="float32")
    original, _ = sf.read(tmp_path / "export/original.wav", dtype="float32")
    music, _ = sf.read(tmp_path / "export/music.wav", dtype="float32")
    result = remix(tmp_path, mode, [], Progress(tmp_path), [1, 2])
    radio, _ = sf.read(tmp_path / "export/radio_voices.wav", dtype="float32")
    expected = np.zeros_like(original_stem)
    expected[round(0.2 * rate) : round(0.75 * rate)] = original_stem[
        round(0.2 * rate) : round(0.75 * rate)
    ]
    np.testing.assert_array_equal(radio, expected)
    retained, _ = sf.read(tmp_path / "export/mix-speakers/speaker_02.wav", dtype="float32")
    np.testing.assert_allclose(retained + radio, original_stem, atol=1e-7)
    clean, _ = sf.read(tmp_path / "export/cleaned.wav", dtype="float32")
    np.testing.assert_allclose(
        clean, original - radio - (music if mode == "remove_radio" else 0), atol=1e-7
    )
    assert result["mix"]["excluded_fragments"] == [1, 2]
    xml = ET.parse(tmp_path / "export/timeline.xml")
    files = {i.findtext("file/pathurl"): i.findtext("enabled") for i in xml.findall(".//clipitem")}
    assert files["mix-speakers/speaker_02.wav"] == "TRUE"
    assert files["radio_voices.wav"] == "FALSE"
    np.testing.assert_array_equal(
        sf.read(tmp_path / "export/speakers/speaker_02.wav", dtype="float32")[0], original_stem
    )
    # A whole speaker selection plus the same fragment must not double the radio.
    remix(tmp_path, "remove_vocals", [2], Progress(tmp_path), [1, 2])
    np.testing.assert_array_equal(
        sf.read(tmp_path / "export/radio_voices.wav", dtype="float32")[0], original_stem
    )
    remix(tmp_path, "keep_all", [], Progress(tmp_path))
    np.testing.assert_allclose(
        sf.read(tmp_path / "export/cleaned.wav", dtype="float32")[0], original, atol=1e-7
    )


def test_radio_speech_can_be_selected_without_a_music_model(tmp_path):
    manifest = fixture(tmp_path)
    manifest["tracks"] = [t for t in manifest["tracks"] if t["id"] != "music"]
    known, muted = configure_mix(manifest, "remove_vocals", [2])
    assert known == {1, 2} and muted == {2}
    with pytest.raises(ValueError, match="Onbekend spreekfragment"):
        configure_mix(manifest, "remove_vocals", [], [100])


def test_unknown_radio_fragment_is_rejected_before_starting_worker(tmp_path):
    ident = "a" * 32
    folder = tmp_path / "jobs" / ident
    fixture(folder)
    with TestClient(create_app(tmp_path)) as client:
        response = client.post(
            f"/api/jobs/{ident}/mix",
            headers={"X-Multitrack": "local"},
            json={"mode": "remove_vocals", "excluded_fragments": [999]},
        )
        assert response.status_code == 422
        assert read_json(folder / "status.json")["state"] == "done"
