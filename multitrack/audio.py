"""Bounded-memory, full-timeline audio helpers shared by the separation stages."""

import math

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


def resample(samples, source_rate, target_rate):
    if source_rate == target_rate:
        return samples
    divisor = math.gcd(source_rate, target_rate)
    return resample_poly(samples, target_rate // divisor, source_rate // divisor, axis=0)


def writer(path, rate, channels, frames):
    return sf.SoundFile(
        path,
        "w",
        samplerate=rate,
        channels=channels,
        subtype="FLOAT",
        format="RF64" if frames * channels * 4 > 4_000_000_000 else "WAV",
    )


def fit_length(samples, frames):
    return np.pad(samples[:frames], ((0, max(0, frames - len(samples))), (0, 0)))
