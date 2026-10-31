"""Optional real-speech test fixture from the official sherpa-onnx release."""

import hashlib
import shutil
import urllib.request
from pathlib import Path


def main():
    target = Path(__file__).resolve().parents[1] / ".local-data" / "test-speech.wav"
    target.parent.mkdir(exist_ok=True)
    url = (
        "https://github.com/k2-fsa/sherpa-onnx/releases/download/"
        "speaker-segmentation-models/0-four-speakers-zh.wav"
    )
    temp = target.with_suffix(".tmp")
    try:
        with urllib.request.urlopen(url, timeout=120) as response, temp.open("wb") as f:
            shutil.copyfileobj(response, f)
        with temp.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        if digest != "bedf036caed208386c67b4ef4b11f83d74dd0d420b102163a1c33cd09cde7010":
            raise RuntimeError("Testaudio-checksum verschilt; bestand niet gebruiken.")
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)
    print(target)


if __name__ == "__main__":
    main()
