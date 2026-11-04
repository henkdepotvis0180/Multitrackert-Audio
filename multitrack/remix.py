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


def configure_mix(manifest, mode, excluded_speakers, excluded_fragments=()):
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
    fragments = {s.get("fragment"): s for s in manifest.get("segments", [])}
    if not set(excluded_fragments) <= fragments.keys():
        raise ValueError("Onbekend spreekfragment geselecteerd.")
    selected_regions(manifest, selected, set(excluded_fragments))
    has_reference = bool(manifest.get("processing", {}).get("radio"))
    if has_reference and mode in {"remove_music", "remove_vocals"}:
        raise ValueError(
            "Bij referentievermindering is de radio als geheel verwijderd. Analyseer zonder referentiebestand om muziek en zang apart te kiezen."
        )
    if (
        mode in {"remove_music", "remove_radio"}
        and not (mode == "remove_radio" and has_reference)
        and not any(t["id"] == "music" for t in tracks)
    ):
        raise ValueError("Analyseer opnieuw met “Muziek apart zetten” voor deze exportkeuze.")
    if (
        mode in {"remove_radio", "remove_vocals"}
        and not selected
        and not excluded_fragments
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


def selected_regions(manifest, speakers, fragments):
    """Merge selected intervals per stem; overlapping choices must not count twice."""
    regions = {}
    duration = manifest["media"]["duration"]
    for speaker in speakers:
        regions[speaker] = [(0, duration)]
    for segment in manifest.get("segments", []):
        if segment.get("fragment") in fragments and segment["speaker"] not in speakers:
            start, end = float(segment["start"]), float(segment["end"])
            if not 0 <= start < end <= duration:
                raise ValueError("Ongeldige fragmenttijd; analyseer dit project opnieuw.")
            regions.setdefault(segment["speaker"], []).append((start, end))
    for speaker, spans in regions.items():
        merged = []
        for start, end in sorted(spans):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((start, end))
        regions[speaker] = merged
    return regions


def remix(folder, mode, excluded_speakers, progress, excluded_fragments=()):
    output = folder / "export"
    manifest = read_json(output / "timeline.json")
    known, muted = configure_mix(manifest, mode, excluded_speakers, excluded_fragments)
    fragments = set(excluded_fragments) if mode in {"remove_radio", "remove_vocals"} else set()
    regions = selected_regions(manifest, muted, fragments)
    tracks = manifest["tracks"]
    readers = []
    derived = {}
    speaker_files = {}
    try:
        # Read muted stems too: their samples belong on the isolated radio track.
        inputs = [t for t in tracks if t["enabled"] or t["id"].startswith("speaker_")]
        readers = [sf.SoundFile(output / t["file"]) for t in inputs]
        with sf.SoundFile(output / "original.wav") as original:
            frames, rate, channels = len(original), original.samplerate, original.channels
            if any((len(r), r.samplerate, r.channels) != (frames, rate, channels) for r in readers):
                raise ValueError(
                    "Tracks hebben verschillende lengtes of audioformaten; analyseer opnieuw."
                )
            for speaker in regions.keys() - muted:
                target = output / "mix-speakers" / f"speaker_{speaker:02}.wav"
                target.parent.mkdir(exist_ok=True)
                derived[speaker] = writer(target.with_suffix(".next.wav"), rate, channels, frames)
                speaker_files[speaker] = target.relative_to(output).as_posix()
            with (
                writer(folder / "cleaned.next.wav", rate, channels, frames) as clean,
                writer(folder / "removed.next.wav", rate, channels, frames) as removed,
                writer(folder / "radio_voices.next.wav", rate, channels, frames) as radio,
            ):
                for start in range(0, frames, BLOCK):
                    progress.update("Gekozen mix maken", start / max(1, frames))
                    mixed = original.read(
                        min(BLOCK, frames - start), dtype="float32", always_2d=True
                    )
                    result = np.zeros_like(mixed)
                    voices = np.zeros_like(mixed)
                    for track, reader in zip(inputs, readers, strict=True):
                        samples = reader.read(len(mixed), dtype="float32", always_2d=True)
                        if track["id"].startswith("speaker_"):
                            speaker = int(track["id"].removeprefix("speaker_"))
                            mask = np.zeros(len(mixed), dtype="float32")
                            for a, b in regions.get(speaker, []):
                                left = max(0, round(a * rate) - start)
                                right = min(len(mixed), round(b * rate) - start)
                                if right > left:
                                    mask[left:right] = 1
                            chosen = samples * mask[:, None]
                            voices += chosen
                            samples = samples - chosen
                            if speaker in derived:
                                derived[speaker].write(samples)
                        if track["enabled"]:
                            result += samples
                    radio.write(voices)
                    clean.write(result)
                    removed.write(mixed - result)
        progress.check()
        for audio in derived.values():
            audio.close()
        for relative in speaker_files.values():
            target = output / relative
            target.with_suffix(".next.wav").replace(target)
        (folder / "cleaned.next.wav").replace(output / "cleaned.wav")
        (folder / "removed.next.wav").replace(output / "removed.wav")
        (folder / "radio_voices.next.wav").replace(output / "radio_voices.wav")
    finally:
        for reader in readers:
            reader.close()
        for audio in derived.values():
            audio.close()
        for relative in speaker_files.values():
            (output / relative).with_suffix(".next.wav").unlink(missing_ok=True)
        for name in ["cleaned.next.wav", "removed.next.wav", "radio_voices.next.wav"]:
            (folder / name).unlink(missing_ok=True)
    manifest["mix"] = {
        "mode": mode,
        "excluded_speakers": sorted(muted),
        "excluded_fragments": sorted(fragments),
        "speaker_files": {str(s): path for s, path in speaker_files.items()},
        "note": "Handmatige selectie van radio/reclame/zang per spreker of fragment. Niet herkende of onvoldoende gescheiden "
        "radiostemmen kunnen blijven; controleer ook of vergaderspraak is mee verwijderd.",
    }
    extra = [t for t in tracks if not t["id"].startswith("speaker_")]
    manifest["mix_tracks"] = (
        [
            {
                "id": "radio_voices",
                "name": "Geselecteerde radiostemmen en reclame",
                "file": "radio_voices.wav",
                "enabled": False,
            }
        ]
        if regions
        else []
    )
    atomic_json(output / "timeline.json", manifest)
    timeline_xml(
        output,
        manifest["media"],
        sorted(known),
        extra + manifest["mix_tracks"],
        muted,
        speaker_files,
    )
    with (output / "LEESMIJ.txt").open("a", encoding="utf-8") as f:
        f.write(
            f"\nNieuwe mix: {mode}. Gedempte sprekers: {sorted(muted)}. Radiofragmenten: {sorted(fragments)}.\n"
            "radio_voices.wav bevat de geselecteerde radiostemmen/reclame; originele sprekertracks blijven bewaard.\n"
            "mix-speakers/ bevat de sprekertracks na fragmentselectie; timeline.xml gebruikt deze waar nodig.\n"
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
        manifest = remix(
            folder,
            options["mode"],
            options["excluded_speakers"],
            progress,
            options.get("excluded_fragments", []),
        )
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
