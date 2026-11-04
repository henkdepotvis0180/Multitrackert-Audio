"""Reproducible controlled mix, not a claim about real room recordings.

python scripts/evaluate_ad_reference.py --reference my-ad.mp3 --output work/ad-check
Requires the optional real-speech fixture from scripts/download_test_audio.py.
User references and generated audio stay in the requested local output directory.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import lfilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from multitrack.ads import reduce_known_ads  # noqa: E402
from multitrack.config import ROOT  # noqa: E402
from multitrack.media import decode_reference  # noqa: E402
from multitrack.state import Progress, atomic_json  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--speech", type=Path, default=ROOT / ".local-data/test-speech.wav")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True)  # Never overwrite an existing evaluation folder.
    root = args.output
    library = root / "library"
    ident = "a" * 32
    target = library / ident
    target.mkdir(parents=True)
    rate = 16000
    decode_reference(args.reference, target / "reference.wav", rate, 90)
    reference, _ = sf.read(target / "reference.wav", dtype="float32")
    duration = len(reference) / rate
    speech, speech_rate = sf.read(args.speech, dtype="float32")
    if speech_rate != rate or speech.ndim != 1:
        raise ValueError("Use a mono 16 kHz real-speech fixture.")
    starts = [2, duration + 6, 2 * duration + 10]
    frames = round((3 * duration + 12) * rate)
    speech = np.tile(speech, int(np.ceil(frames / len(speech))))[:frames]
    speech = speech / max(1e-7, float(np.sqrt(np.mean(speech * speech)))) * 0.025
    radio = np.zeros(frames, dtype="float32")
    for second in starts:
        start = round(second * rate)
        radio[start : start + len(reference)] += reference * 0.8
    radio = lfilter([0.8] + [0] * 79 + [0.12], [1], radio).astype("float32")
    mixed = (speech + radio).astype("float32")
    sf.write(root / "original.wav", mixed, rate, subtype="FLOAT")
    sf.write(root / "clean-speech-ground-truth.wav", speech, rate, subtype="FLOAT")
    atomic_json(target / "metadata.json", {"name": "Local reference", "duration": duration})
    result = reduce_known_ads(root / "original.wav", library, [ident], root, Progress(root))
    cleaned = sf.read(root / "cleaned.wav", dtype="float32")[0] if result["applied"] else mixed
    before = float(np.mean((mixed - speech) ** 2))
    after = float(np.mean((cleaned - speech) ** 2))
    metrics = {
        "case": "Controlled mixture with unrelated real speech and a 5 ms echo; not a field recording",
        "inserted_starts_seconds": starts,
        "matches": result["matches"],
        "error_reduction_db": float(10 * np.log10(max(before, 1e-20) / max(after, 1e-20))),
        "error_relative_to_speech_rms": float(
            np.sqrt(after / max(float(np.mean(speech**2)), 1e-20))
        ),
    }
    atomic_json(root / "metrics.json", metrics)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
