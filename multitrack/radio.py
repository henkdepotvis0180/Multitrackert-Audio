"""Reference-based radio reduction. No voice identification or network/model access.

Requires the same recording/master of the song, not another performance. A local
linear acoustic estimate removes correlated reference content, including singing.
It cannot reconstruct speech that was masked or clipped in the recording.
"""

import numpy as np
import soundfile as sf
from scipy import signal

from .audio import fit_length, resample, writer


def locate_reference(recording, reference, progress, manual_offset=None):
    rate = 2000
    anchor = max(0.0, manual_offset - 5.0) if manual_offset is not None else 0.0
    with sf.SoundFile(recording) as f:
        f.seek(min(len(f), round(anchor * f.samplerate)))
        y = f.read(min(len(f) - f.tell(), f.samplerate * 90), dtype="float32", always_2d=True)[:, 0]
        y = resample(y, f.samplerate, rate)
    with sf.SoundFile(reference) as f:
        x = resample(f.read(dtype="float32"), f.samplerate, rate)
    if len(x) < rate or len(y) < rate:
        raise ValueError("Minimaal één seconde referentie en opname nodig.")
    progress.update("Radio-referentie uitlijnen")
    sos = signal.butter(3, [100, 850], btype="bandpass", fs=rate, output="sos")
    x, y = signal.sosfilt(sos, x), signal.sosfilt(sos, y)
    corr = signal.correlate(y, x, mode="full", method="fft")
    ey = signal.correlate(y * y, np.ones(len(x)), mode="full", method="fft")
    ex = signal.correlate(np.ones(len(y)), x * x, mode="full", method="fft")
    lags = signal.correlation_lags(len(y), len(x))
    overlap = np.maximum(0, np.minimum(len(y), len(x) + lags) - np.maximum(0, lags))
    scores = np.abs(corr) / np.sqrt(np.maximum(ey * ex, 1e-20))
    valid = overlap >= min(3 * rate, 0.5 * len(y), 0.5 * len(x))
    # FFT roundoff in silent tails must not create an artificially large score.
    valid &= (ey > max(1e-15, float(ey.max()) * 1e-7)) & (ex > max(1e-15, float(ex.max()) * 1e-7))
    if manual_offset is not None:
        valid &= np.abs(lags / rate + anchor - manual_offset) <= 0.1
    scores[~valid] = 0
    best = int(np.argmax(scores))
    if scores[best] < max(0.08, 6 / np.sqrt(max(1, overlap[best]))):
        raise ValueError(
            "Geen betrouwbare match met de radio-referentie. Gebruik exact dezelfde "
            "opname/versie, controleer de starttijd of laat de referentie weg. "
            "Automatisch zoeken gebruikt de eerste 90 seconden van de vergadering."
        )
    return float(lags[best] / rate + anchor), float(scores[best])


def read_aligned(reference, start, frames, offset):
    position = start - offset
    leading = min(frames, max(0, -position))
    result = np.zeros(frames, dtype="float32")
    position = max(0, position)
    if leading < frames and position < len(reference):
        reference.seek(position)
        block = reference.read(min(frames - leading, len(reference) - position), dtype="float32")
        result[leading : leading + len(block)] = block
    return result


def estimate_radio(mixture, reference, rate):
    """Estimate a coherent room/filter response; unrelated voices average out.

    Coherence shrinkage prevents amplification of reference-silent frequency bins.
    This remains a heuristic and can leak speech into the removed track.
    """
    size = min(4096, 2 ** int(np.floor(np.log2(max(128, rate // 20)))))
    if len(reference) < size:
        return np.zeros_like(mixture)
    _, _, x = signal.stft(reference, fs=rate, nperseg=size, noverlap=size * 3 // 4)
    power = np.mean(np.abs(x) ** 2, axis=1)
    floor = max(1e-14, float(power.max()) * 1e-4)
    result = np.zeros_like(mixture)
    for channel in range(mixture.shape[1]):
        _, _, y = signal.stft(mixture[:, channel], fs=rate, nperseg=size, noverlap=size * 3 // 4)
        cross = np.mean(y * x.conj(), axis=1)
        coherence = np.abs(cross) ** 2 / (power * np.mean(np.abs(y) ** 2, axis=1) + 1e-20)
        transfer = cross / (power + floor) * np.clip((coherence - 0.03) / 0.25, 0, 1)
        _, estimated = signal.istft(
            transfer[:, None] * x, fs=rate, nperseg=size, noverlap=size * 3 // 4
        )
        result[:, channel] = fit_length(estimated[:, None], len(mixture))[:, 0]
    return result


def reduce_radio(source, reference_path, folder, progress, manual_offset=None):
    offset_seconds, score = locate_reference(source, reference_path, progress, manual_offset)
    with sf.SoundFile(source) as original, sf.SoundFile(reference_path) as reference:
        rate, channels, frames = original.samplerate, original.channels, len(original)
        if reference.samplerate != rate or reference.channels != 1:
            raise ValueError("Referentie moet eerst op de bronfrequentie naar mono worden omgezet.")
        offset = round(offset_seconds * rate)
        core, fade = 4 * rate, max(1, rate // 10)
        step, pending = core - fade, None
        with (
            writer(folder / "cleaned.wav", rate, channels, frames) as cleaned,
            writer(folder / "radio.wav", rate, channels, frames) as radio,
        ):

            def emit(start, estimate):
                original.seek(start)
                mixed = original.read(len(estimate), dtype="float32", always_2d=True)
                radio.write(estimate)
                cleaned.write(mixed - estimate)

            for start in range(0, frames, step):
                progress.update("Radio met referentie verminderen", start / max(1, frames))
                stop = min(frames, start + core)
                left, right = max(0, start - 12 * rate), min(frames, stop + 12 * rate)
                original.seek(left)
                mixed = original.read(right - left, dtype="float32", always_2d=True)
                aligned = read_aligned(reference, left, right - left, offset)
                estimate = estimate_radio(mixed, aligned, rate)[start - left : stop - left]
                if pending is not None:
                    n = min(len(pending), len(estimate))
                    ramp = np.linspace(0, 1, n, dtype="float32")[:, None]
                    estimate[:n] = pending[:n] * (1 - ramp) + estimate[:n] * ramp
                if stop == frames:
                    emit(start, estimate)
                    break
                emit(start, estimate[:-fade])
                pending = estimate[-fade:].copy()
    return {
        "offset_seconds": offset_seconds,
        "alignment_score": score,
        "method": "local_reference_coherence_filter",
        "note": "Geschatte radiobijdrage, inclusief gecorreleerde zang. Controleer spraaklekkage; "
        "een andere master, radiospreker, reclames, klokdrift of galm kan de match beperken.",
    }
