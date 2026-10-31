"""One-time explicit download; inference never calls a download API."""

import hashlib
import shutil
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from multitrack.config import MODELS  # noqa: E402
from multitrack.music import MODEL_NAME, MODEL_SHA256, MODEL_URL  # noqa: E402


def main():
    MODELS.mkdir(parents=True, exist_ok=True)
    temp = MODELS / (MODEL_NAME + ".tmp")
    try:
        print("Download Hybrid Demucs (ongeveer 320 MB) via HTTPS…", flush=True)
        with urllib.request.urlopen(MODEL_URL, timeout=180) as source, temp.open("wb") as target:
            shutil.copyfileobj(source, target)
        with temp.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != MODEL_SHA256:
                raise RuntimeError("Checksum verschilt; model wordt niet geïnstalleerd.")
        temp.replace(MODELS / MODEL_NAME)
    finally:
        temp.unlink(missing_ok=True)
    print("Muziekmodel gereed. Verwerking is vanaf nu volledig lokaal.")


if __name__ == "__main__":
    main()
