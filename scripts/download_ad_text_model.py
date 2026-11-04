#!/usr/bin/env python3
"""Explicit optional download. Never called while processing a user's recording."""

import hashlib
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from multitrack.ad_text import MODEL_FILES  # noqa: E402
from multitrack.config import MODELS  # noqa: E402

URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-small.tar.bz2"


def main():
    destination = MODELS / "whisper-small"
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        archive = Path(temp) / "whisper-small.tar.bz2"
        print("Download optioneel Whisper Small-tekstmodel via HTTPS…", flush=True)
        with urllib.request.urlopen(URL, timeout=180) as response, archive.open("wb") as out:
            shutil.copyfileobj(response, out)
        found = set()
        with tarfile.open(archive, "r|bz2") as bundle:
            for member in bundle:
                name = member.name.removeprefix("sherpa-onnx-whisper-small/")
                if name not in MODEL_FILES or not member.isfile():
                    continue
                target = Path(temp) / name
                with bundle.extractfile(member) as source, target.open("wb") as out:
                    shutil.copyfileobj(source, out)
                with target.open("rb") as f:
                    if hashlib.file_digest(f, "sha256").hexdigest() != MODEL_FILES[name]:
                        raise RuntimeError(f"Model-checksum verschilt: {name}")
                found.add(name)
        if found != MODEL_FILES.keys():
            raise RuntimeError("Het modelarchief mist bestanden.")
        for name in MODEL_FILES:
            shutil.copyfile(Path(temp) / name, destination / (name + ".tmp"))
            (destination / (name + ".tmp")).replace(destination / name)
    print(f"Optioneel tekstmodel gereed: {destination}")


if __name__ == "__main__":
    main()
