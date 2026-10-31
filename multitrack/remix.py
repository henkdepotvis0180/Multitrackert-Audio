"""Build a new Premiere mix from user-selected stems; never identify an artist by name."""

import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from .audio import writer
from .export import BLOCK, make_zip, timeline_xml
from .state import Progress, atomic_json, read_json

MODES = {"keep_all", "remove_music", "remove_radio", "remove_vocals"}


def configure_mix(manifest, mode, excluded_speakers):
    tracks = manifest.get("tracks", [])
    if not tracks:
        raise ValueError(
            "Maak eerst een nieuwe analyse met versie 0.2 om alle restgeluiden te bewaren."
        )
    if mode not in MODES:
        raise ValueError("Onbekende exportkeuze.")
    known = {
        int(t["id"].removeprefix("speaker_")) for t in tracks if t["id"].startswith("speaker_")
    }
    selected = set(excluded_speakers)
    if not selected <= known:
        raise ValueError("Onbekende spreker geselecteerd.")
    has_reference = bool(manifest.get("processing", {}).get("radio"))
    if has_reference and mode in {"remove_music", "remove_vocals"}:
        raise ValueError(
            "Bij referentievermindering is de radio als geheel verwijderd. Analyseer zonder referentiebestand om muziek en zang apart te kiezen."
        )
    if (
        mode != "keep_all"
        and not (mode == "remove_radio" and has_reference)
        and not any(t["id"] == "music" for t in tracks)
    ):
        raise ValueError("Analyseer opnieuw met “Muziek apart zetten” voor deze exportkeuze.")
    if (
        mode in {"remove_radio", "remove_vocals"}
        and not selected
        and not manifest.get("processing", {}).get("radio")
    ):
        raise ValueError(
            "Beluister de stemtracks en vink aan welke radio/zang bevatten. Zonder die keuze "
            "wordt alleen instrumentale muziek verminderd; de zanger kan blijven."
        )
    muted = selected if mode in {"remove_radio", "remove_vocals"} else set()
    for track in tracks:
        if track["id"].startswith("speaker_"):
            track["enabled"] = int(track["id"].removeprefix("speaker_")) not in muted
        elif track["id"] == "music":
            track["enabled"] = mode not in {"remove_music", "remove_radio"}
        elif track["id"] == "radio":
            track["enabled"] = mode == "keep_all"
        else:
            track["enabled"] = True
    return known, muted


def remix(folder, mode, excluded_speakers, progress):
    output = folder / "export"
    manifest = read_json(output / "timeline.json")
    known, muted = configure_mix(manifest, mode, excluded_speakers)
    tracks = manifest["tracks"]
    readers = []
    try:
        readers = [sf.SoundFile(output / t["file"]) for t in tracks if t["enabled"]]
        with sf.SoundFile(output / "original.wav") as original:
            frames, rate, channels = len(original), original.samplerate, original.channels
            if any((len(r), r.samplerate, r.channels) != (frames, rate, channels) for r in readers):
                raise ValueError(
                    "Tracks hebben verschillende lengtes of audioformaten; analyseer opnieuw."
                )
            with (
                writer(folder / "cleaned.next.wav", rate, channels, frames) as clean,
                writer(folder / "removed.next.wav", rate, channels, frames) as removed,
            ):
                for start in range(0, frames, BLOCK):
                    progress.update("Gekozen mix maken", start / max(1, frames))
                    mixed = original.read(
                        min(BLOCK, frames - start), dtype="float32", always_2d=True
                    )
                    result = np.zeros_like(mixed)
                    for reader in readers:
                        result += reader.read(len(mixed), dtype="float32", always_2d=True)
                    clean.write(result)
                    removed.write(mixed - result)
        progress.check()
        (folder / "cleaned.next.wav").replace(output / "cleaned.wav")
        (folder / "removed.next.wav").replace(output / "removed.wav")
    finally:
        for reader in readers:
            reader.close()
        for name in ["cleaned.next.wav", "removed.next.wav"]:
            (folder / name).unlink(missing_ok=True)
    manifest["mix"] = {
        "mode": mode,
        "excluded_speakers": sorted(muted),
        "note": "Handmatige selectie van radio/zang. Niet herkende of onvoldoende gescheiden "
        "radiostemmen kunnen blijven; controleer ook of vergaderspraak is mee verwijderd.",
    }
    atomic_json(output / "timeline.json", manifest)
    extra = [t for t in tracks if not t["id"].startswith("speaker_")]
    timeline_xml(output, manifest["media"], sorted(known), extra, muted)
    with (output / "LEESMIJ.txt").open("a", encoding="utf-8") as f:
        f.write(
            f"\nNieuwe mix: {mode}. Gedempte sprekers: {sorted(muted)}.\n"
            "cleaned.wav is de gekozen volledige mix. removed.wav is wat is weggelaten.\n"
            "Voor Premiere: importeer de nieuwe timeline.xml, of zet alleen cleaned.wav op tijdstip 0 onder video.mp4.\n"
            "Speel cleaned.wav niet samen met de losse tracks af. Controleer op radio- en spraaklekkage.\n"
        )
    make_zip(folder, output, progress)
    return manifest


def process(folder):
    progress = Progress(folder)
    try:
        options = read_json(folder / "remix-options.json")
        manifest = remix(folder, options["mode"], options["excluded_speakers"], progress)
        atomic_json(
            folder / "status.json",
            {
                "state": "done",
                "phase": "Mix klaar",
                "fraction": 1,
                "elapsed_seconds": time.monotonic() - progress.started,
                "updated_at": time.time(),
                "message": "Nieuwe mix en Premiere-tijdlijn gereed. Luister het resultaat na.",
                "speakers": sorted({s["speaker"] for s in manifest["segments"]}),
                "unseparated_overlap_count": sum(
                    o["method"] == "mixed" for o in manifest["overlaps"]
                ),
                "mix": manifest["mix"],
            },
        )
    except Exception as e:
        atomic_json(
            folder / "status.json",
            {
                "state": "cancelled" if isinstance(e, InterruptedError) else "error",
                "message": str(e),
                "updated_at": time.time(),
            },
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(process(Path(sys.argv[1])))
