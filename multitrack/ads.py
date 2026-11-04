"""Local known-ad audio matching and reference subtraction, never text-based muting."""

import re

import numpy as np
import soundfile as sf
from scipy import signal

from .audio import resample, writer
from .radio import estimate_radio
from .state import read_json

SEARCH_RATE = 2000
MIN_SCORE = 0.70
MAX_REFERENCES = 32
MAX_REFERENCE_SECONDS = 90


def library_entries(root):
    if not root.exists():
        return []
    entries = []
    for folder in sorted(root.iterdir()):
        if re.fullmatch(r"[a-f0-9]{32}", folder.name) and (folder / "metadata.json").is_file():
            entries.append({"id": folder.name, **read_json(folder / "metadata.json")})
    return entries


def find_matches(source, reference, progress):
    """Search the entire recording in bounded, overlapping windows.

    Scores measure waveform correlation, not probability or semantic ad identity.
    Only full reference matches are considered; unrelated speech is not muted.
    """
    x, rate = sf.read(reference, dtype="float32", always_2d=True)
    if not 2 <= len(x) / rate <= MAX_REFERENCE_SECONDS:
        raise ValueError("Reclamevoorbeeld moet tussen 2 en 90 seconden duren.")
    x = resample(x.mean(axis=1), rate, SEARCH_RATE)
    sos = signal.butter(3, [100, 850], btype="bandpass", fs=SEARCH_RATE, output="sos")
    x = signal.sosfilt(sos, x)
    power = float(x @ x)
    if power < 1e-7 or not np.isfinite(x).all():
        raise ValueError("Reclamevoorbeeld bevat onvoldoende bruikbaar geluid.")
    matches = []
    with sf.SoundFile(source) as original:
        window = 120 * original.samplerate
        step = window - round(len(x) / SEARCH_RATE * original.samplerate)
        for start in range(0, len(original), step):
            progress.update("Bekende reclame zoeken", start / max(1, len(original)))
            original.seek(start)
            y = original.read(window, dtype="float32", always_2d=True).mean(axis=1)
            y = signal.sosfilt(sos, resample(y, original.samplerate, SEARCH_RATE))
            if len(y) < len(x):
                continue
            corr = signal.correlate(y, x, mode="valid", method="fft")
            energy = signal.convolve(y * y, np.ones(len(x)), mode="valid", method="fft")
            scores = np.abs(corr) / np.sqrt(np.maximum(energy * power, 1e-20))
            scores[energy < max(1e-12, float(energy.max()) * 1e-7)] = 0
            peaks, _ = signal.find_peaks(scores, height=MIN_SCORE, distance=len(x) * 0.8)
            # Endpoints are not returned by find_peaks.
            candidates = list(peaks)
            if scores[0] >= MIN_SCORE:
                candidates.append(0)
            if len(scores) > 1 and scores[-1] >= MIN_SCORE:
                candidates.append(len(scores) - 1)
            for peak in sorted(candidates, key=lambda p: -scores[p]):
                time = start / original.samplerate + peak / SEARCH_RATE
                if any(abs(time - m["start"]) < len(x) / SEARCH_RATE * 0.8 for m in matches):
                    continue
                matches.append(
                    {
                        "start": time,
                        "end": time + len(x) / SEARCH_RATE,
                        "score": float(min(1, scores[peak])),
                    }
                )
    return sorted(matches, key=lambda m: m["start"])


def reduce_known_ads(source, library, ids, folder, progress):
    entries = {e["id"]: e for e in library_entries(library)}
    if not ids or not set(ids) <= entries.keys():
        raise ValueError("Kies bestaande lokale reclamevoorbeelden.")
    candidates = []
    for ident in dict.fromkeys(ids):
        reference = library / ident / "reference.wav"
        for match in find_matches(source, reference, progress):
            candidates.append({**match, "reference_id": ident, "name": entries[ident]["name"]})
    # Prefer the strongest match where different examples cover the same audio.
    matches = []
    for match in sorted(candidates, key=lambda m: -m["score"]):
        if not any(
            min(match["end"], m["end"]) - max(match["start"], m["start"]) > 0.1 for m in matches
        ):
            matches.append(match)
    matches.sort(key=lambda m: m["start"])
    if not matches:
        return {
            "method": "known_ad_waveform",
            "matches": [],
            "applied": False,
            "note": "Geen sterke overeenkomst. De oorspronkelijke audio is behouden.",
        }
    with sf.SoundFile(source) as original:
        rate, channels, frames = original.samplerate, original.channels, len(original)
        with (
            writer(folder / "cleaned.wav", rate, channels, frames) as clean,
            writer(folder / "radio.wav", rate, channels, frames) as radio,
        ):
            position = 0

            def copy_until(stop):
                nonlocal position
                while position < stop:
                    progress.check()
                    original.seek(position)
                    block = original.read(
                        min(262144, stop - position), dtype="float32", always_2d=True
                    )
                    clean.write(block)
                    radio.write(np.zeros_like(block))
                    position += len(block)

            for match in matches:
                progress.update(
                    "Herkende reclame met referentie verminderen",
                    match["start"] * rate / max(1, frames),
                )
                start, stop = (
                    max(position, round(match["start"] * rate)),
                    min(frames, round(match["end"] * rate)),
                )
                copy_until(start)
                original.seek(start)
                mixed = original.read(stop - start, dtype="float32", always_2d=True)
                x, xr = sf.read(library / match["reference_id"] / "reference.wav", dtype="float32")
                x = resample(x, xr, rate)[: len(mixed)]
                x = np.pad(x, (0, max(0, len(mixed) - len(x))))
                estimate = estimate_radio(mixed, x, rate)
                # Keep transitions click-free; unestimated content remains in clean.
                fade = min(rate // 200, len(estimate) // 2)
                if fade:
                    ramp = np.linspace(0, 1, fade, dtype="float32")[:, None]
                    estimate[:fade] *= ramp
                    estimate[-fade:] *= ramp[::-1]
                clean.write(mixed - estimate)
                radio.write(estimate)
                position = stop
            copy_until(frames)
    return {
        "method": "known_ad_waveform",
        "matches": matches,
        "applied": True,
        "note": "Alleen sterk overeenkomende voorbeeld-audio is geschat en apart gezet. "
        "Nieuwe spots, andere montages en galm kunnen resten geven; controleer spraaklekkage.",
    }
