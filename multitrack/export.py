import csv
import json
import math
import time
import zipfile
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from .diarize import Embedder, intervals
from .separate import Separator, assign_sources

BLOCK = 262144


def write_region(source, writers, start, stop, active, replacements=None, progress=None):
    source.seek(start)
    for offset in range(start, stop, BLOCK):
        if progress:
            progress.check()
        n = min(BLOCK, stop - offset)
        original = source.read(n, dtype="float32", always_2d=True)
        if len(original) < n:
            original = np.pad(original, ((0, n - len(original)), (0, 0)))
        silence = np.zeros_like(original)
        for speaker, writer in writers.items():
            samples = original if speaker in active else silence
            if replacements and speaker in replacements:
                mono = replacements[speaker][offset - start : offset - start + n]
                samples = np.repeat(mono[:, None], source.channels, axis=1)
            writer.write(samples)


def render(folder, info, segments, analysis, models, hardware, separate, progress):
    output = folder / "export"
    output.mkdir()
    tracks = output / "speakers"
    tracks.mkdir()
    rate = info["sample_rate"]
    regions = list(intervals(segments, info["duration"]))
    speakers = sorted({s.speaker for s in segments})
    embed, separator, refs = None, None, {}
    if separate and any(len(active) == 2 for _, _, active in regions):
        progress.update("Stemmen voorbereiden", 0)
        embed = Embedder(models, hardware["inference_threads"])
        for speaker in speakers:
            clean = [
                analysis[round(a * 16000) : round(b * 16000)]
                for a, b, active in regions
                if active == (speaker,) and b - a >= 1.0
            ]
            if clean:
                refs[speaker] = embed(np.concatenate(clean)[:160000])
        separator = Separator(models, hardware["separation_device"])
    overlap = []
    with sf.SoundFile(folder / "original.wav") as original:
        frames = len(original)
        writers = {
            s: sf.SoundFile(
                tracks / f"speaker_{s:02}.wav",
                "w",
                samplerate=rate,
                channels=original.channels,
                subtype="FLOAT",
                format=("RF64" if frames * original.channels * 4 > 4_000_000_000 else "WAV"),
            )
            for s in speakers
        }
        try:
            for i, (a, b, active) in enumerate(regions):
                progress.update(
                    "Audiotracks maken",
                    i / max(1, len(regions)),
                    f"{a:.1f} / {info['duration']:.1f} seconden",
                )
                # Bound separation memory: at most 8 seconds per model invocation.
                steps = max(1, math.ceil((b - a) / 8)) if separator and len(active) == 2 else 1
                for k in range(steps):
                    progress.check()
                    left, right = a + (b - a) * k / steps, a + (b - a) * (k + 1) / steps
                    start, stop = round(left * rate), min(frames, round(right * rate))
                    replacements = None
                    method = "mixed"
                    reason = "Scheiding uitgeschakeld of meer dan twee actieve sprekers."
                    if (
                        separator
                        and len(active) == 2
                        and all(refs.get(s) is not None for s in active)
                    ):
                        pad_a = max(0, round((left - 0.25) * 16000))
                        pad_b = min(len(analysis), round((right + 0.25) * 16000))
                        sources = separator(analysis[pad_a:pad_b])
                        assignment = assign_sources(sources, [refs[s] for s in active], embed)
                        if assignment is not None:
                            replacements = {}
                            for j, speaker in enumerate(active):
                                full = resample_poly(
                                    sources[assignment[j]],
                                    rate // math.gcd(rate, 16000),
                                    16000 // math.gcd(rate, 16000),
                                )
                                cut = start - round(pad_a * rate / 16000)
                                chunk = full[cut : cut + stop - start]
                                replacements[speaker] = np.pad(
                                    chunk, (0, max(0, stop - start - len(chunk)))
                                )
                            method, reason = (
                                "separated_8khz",
                                "Experimenteel; controleer stemidentiteit en artefacten.",
                            )
                        else:
                            reason = "Stemtoewijzing onzeker; originele mix behouden."
                    elif separate and len(active) == 2:
                        reason = "Geen voldoende lange, schone referentie voor beide stemmen; mix behouden."
                    write_region(original, writers, start, stop, active, replacements, progress)
                    if len(active) > 1:
                        overlap.append(
                            {
                                "start": left,
                                "end": right,
                                "speakers": list(active),
                                "method": method,
                                "note": reason,
                            }
                        )
        finally:
            for writer in writers.values():
                writer.close()
    return output, overlap


def timeline_xml(output, info, speakers):
    """FCP7 interchange for Premiere. Editors may require relinking relative paths."""
    rate = Fraction(info["fps"]) if info["fps"] != "0/0" else Fraction(25)
    timebase = round(float(rate))
    ntsc = abs(float(rate) - timebase * 1000 / 1001) < 0.01
    length = math.ceil(info["duration"] * float(rate))
    root = ET.Element("xmeml", version="5")
    seq = ET.SubElement(root, "sequence", id="sequence-1")
    ET.SubElement(seq, "name").text = "Multitrackert"
    ET.SubElement(seq, "duration").text = str(length)
    r = ET.SubElement(seq, "rate")
    ET.SubElement(r, "timebase").text = str(timebase)
    ET.SubElement(r, "ntsc").text = str(ntsc).upper()
    media = ET.SubElement(seq, "media")

    def clip(track, name, path, ident, audio=False):
        item = ET.SubElement(track, "clipitem", id=f"clip-{ident}")
        for key, val in [
            ("name", name),
            ("duration", length),
            ("start", 0),
            ("end", length),
            ("in", 0),
            ("out", length),
        ]:
            ET.SubElement(item, key).text = str(val)
        item.append(ET.fromstring(ET.tostring(r)))
        f = ET.SubElement(item, "file", id=f"file-{ident}")
        ET.SubElement(f, "name").text = Path(path).name
        ET.SubElement(f, "pathurl").text = path
        f.append(ET.fromstring(ET.tostring(r)))
        ET.SubElement(f, "duration").text = str(length)
        fm = ET.SubElement(f, "media")
        kind = ET.SubElement(fm, "audio" if audio else "video")
        sc = ET.SubElement(kind, "samplecharacteristics")
        if audio:
            ET.SubElement(sc, "depth").text = "32"
            ET.SubElement(sc, "samplerate").text = str(info["sample_rate"])
            ET.SubElement(kind, "channelcount").text = str(info["channels"])
            source = ET.SubElement(item, "sourcetrack")
            ET.SubElement(source, "mediatype").text = "audio"
            ET.SubElement(source, "trackindex").text = "1"
        else:
            ET.SubElement(sc, "width").text = str(info["width"])
            ET.SubElement(sc, "height").text = str(info["height"])

    video = ET.SubElement(media, "video")
    clip(ET.SubElement(video, "track"), "Video", "video.mp4", "video")
    audio = ET.SubElement(media, "audio")
    for speaker in speakers:
        clip(
            ET.SubElement(audio, "track"),
            f"Spreker {speaker}",
            f"speakers/speaker_{speaker:02}.wav",
            str(speaker),
            True,
        )
    ET.indent(root)
    ET.ElementTree(root).write(output / "timeline.xml", encoding="utf-8", xml_declaration=True)


def package(folder, output, info, segments, overlaps, progress, hardware):
    import shutil

    for name in ["original.wav", "video.mp4"]:
        shutil.move(str(folder / name), output / name)
    clips = output / "clips"
    clips.mkdir()
    records = []
    for i, segment in enumerate(segments, 1):
        progress.update("Fragmenten exporteren", i / max(1, len(segments)))
        name = f"{i:05}_speaker_{segment.speaker:02}_{segment.start:010.3f}s.wav"
        source = output / "speakers" / f"speaker_{segment.speaker:02}.wav"
        with sf.SoundFile(source) as reader:
            start, stop = (
                round(segment.start * reader.samplerate),
                round(segment.end * reader.samplerate),
            )
            reader.seek(start)
            with sf.SoundFile(
                clips / name,
                "w",
                samplerate=reader.samplerate,
                channels=reader.channels,
                subtype="FLOAT",
                format="WAV",
            ) as writer:
                remaining = stop - start
                while remaining > 0:
                    progress.check()
                    block = reader.read(min(BLOCK, remaining), dtype="float32", always_2d=True)
                    if not len(block):
                        break
                    writer.write(block)
                    remaining -= len(block)
        records.append({"fragment": i, **asdict(segment), "file": f"clips/{name}"})
    manifest = {
        "version": 1,
        "time_origin_seconds": 0,
        "media": info,
        "segments": records,
        "overlaps": overlaps,
        "hardware": hardware,
        "warnings": [
            "Sprekers zijn geschatte anonieme clusters, geen vastgestelde personen.",
            "Zonder geslaagde scheiding bevatten overlappen dezelfde mix op meerdere tracks.",
            "Gescheiden overlap is mono, 8 kHz modelbandbreedte, teruggesampled naar de bronfrequentie.",
            "Niet-gedetecteerde spraak blijft altijd aanwezig in original.wav.",
            "Variabele framerate: gebruik WAV-tracks op tijdstip 0 voor sample-nauwkeurige audio.",
        ],
    }
    (output / "timeline.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (output / "segments.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["fragment", "start", "end", "speaker", "file"])
        w.writeheader()
        w.writerows(records)
    speakers = sorted({s.speaker for s in segments})
    timeline_xml(output, info, speakers)
    (output / "LEESMIJ.txt").write_text(
        "Importeer video.mp4 en speakers/*.wav in aparte tracks, ALLEMAAL op tijdstip 0.\n"
        "De volledige WAVs hebben evenveel samples; stilte houdt alle posities intact.\n"
        "original.wav is de originele gedecodeerde mix, NIET tegelijk afspelen met de sprekertracks.\n"
        "Premiere: probeer timeline.xml; wijs ontbrekende media aan in deze uitgepakte map.\n"
        "Clipchamp: importeer de volledige WAVs en plaats elk bestand aan het begin.\n"
        "clips/ bevat chronologische fragmenten; tussenliggende stilte ontbreekt daar!\n"
        "Gebruik CSV/JSON tijdcodes als je fragmenten los op de tijdlijn plaatst.\n"
        "Lees timeline.json voor waarschuwingen en niet-gescheiden overlappingen.\n"
        "De XML-import is niet getest in Premiere/Clipchamp; de WAV-methode is de basis.\n",
        encoding="utf-8",
    )
    files = [f for f in sorted(output.rglob("*")) if f.is_file()]
    total_bytes = sum(f.stat().st_size for f in files)
    written, last_update = 0, 0.0
    with zipfile.ZipFile(
        folder / "result.zip", "w", compression=zipfile.ZIP_STORED, allowZip64=True
    ) as z:
        for path in files:
            with (
                path.open("rb") as source,
                z.open(
                    str(path.relative_to(output)).replace("\\", "/"), "w", force_zip64=True
                ) as destination,
            ):
                while block := source.read(8 * 1024**2):
                    progress.check()
                    destination.write(block)
                    written += len(block)
                    now = time.monotonic()
                    if now - last_update >= 0.4 or written == total_bytes:
                        progress.update("ZIP maken", written / max(1, total_bytes))
                        last_update = now
    return manifest
