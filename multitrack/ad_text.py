"""Optional offline Dutch speech-to-text clues. Text never authorizes audio removal."""

import hashlib
import re
import unicodedata

import numpy as np
import soundfile as sf

from .audio import resample

MODEL_FILES = {
    "small-encoder.int8.onnx": "4cbe7b22fa9026b843b60a68640c747de05bafb1a11b57edc0e66c232d9f33a9",
    "small-decoder.int8.onnx": "acad50b5c782696e91b55914cc5ab4f756f1532f76e22aa6fc615f39fb69a8ee",
    "small-tokens.txt": "b34b360dbb493e781e479794586d661700670d65564001f23024971d1f2fa126",
}
# Short identifying phrases, not copied advertising scripts or a complete ad list.
PHRASES = (
    (
        "Albert Heijn",
        "dat is het lekkere van albert heijn",
        "https://nieuws.ah.nl/albert-heijn-start-nieuwe-campagne/",
    ),
    ("Kruidvat", "steeds verrassend altijd voordelig", "https://www.kruidvat.be/nl/winkelformule"),
    (
        "Lidl",
        "de hoogste kwaliteit voor de laagste prijs",
        "https://www.lidl.nl/c/huismerken/s10023965",
    ),
)


def ready(models):
    return all((models / "whisper-small" / name).is_file() for name in MODEL_FILES)


def normalized(text):
    text = "".join(
        c for c in unicodedata.normalize("NFKD", text).casefold() if not unicodedata.combining(c)
    )
    return " ".join(re.findall(r"[a-z0-9]+", text))


def phrase_hits(text, custom=()):
    text = " " + normalized(text) + " "
    phrases = list(PHRASES) + [("Eigen herkenningszin", p, None) for p in custom]
    return [
        {"label": label, "phrase": phrase, "source": source}
        for label, phrase, source in phrases
        if len(normalized(phrase).split()) >= 3 and " " + normalized(phrase) + " " in text
    ]


def scan_text(source, models, progress, custom=(), threads=2):
    import sherpa_onnx

    root = models / "whisper-small"
    for name, expected in MODEL_FILES.items():
        with (root / name).open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() != expected:
                raise ValueError("Checksum tekstmodel verschilt. Download het opnieuw.")
    recognizer = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(root / "small-encoder.int8.onnx"),
        decoder=str(root / "small-decoder.int8.onnx"),
        tokens=str(root / "small-tokens.txt"),
        language="nl",
        num_threads=threads,
    )
    clues = []
    with sf.SoundFile(source) as reader:
        # Overlap covers phrases crossing a window boundary. These are review
        # windows, not precise word boundaries and never automatic mute regions.
        for start in range(0, len(reader), reader.samplerate * 12):
            progress.update("Mogelijke reclametekst zoeken", start / max(1, len(reader)))
            reader.seek(start)
            block = reader.read(reader.samplerate * 16, dtype="float32", always_2d=True).mean(
                axis=1
            )
            if len(block) < reader.samplerate or np.sqrt(np.mean(block * block)) < 0.001:
                continue
            stream = recognizer.create_stream()
            stream.accept_waveform(16000, resample(block, reader.samplerate, 16000))
            recognizer.decode_stream(stream)
            text = stream.result.text.strip()
            hits = phrase_hits(text, custom)
            if hits:
                clues.append(
                    {
                        "start": start / reader.samplerate,
                        "end": (start + len(block)) / reader.samplerate,
                        "text": text,
                        "matches": hits,
                    }
                )
    return {
        "method": "whisper_small_nl_phrase_clues",
        "candidates": clues,
        "automatic_removal": False,
        "note": "Tekst is een aanwijzing, geen bewijs van reclame. Vensters zijn maximaal "
        "16 seconden; gezongen of overstemde tekst kan ontbreken. Audio wordt hier niet gewist.",
    }
