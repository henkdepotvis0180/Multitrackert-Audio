#!/usr/bin/env python3
"""Explicit one-time network installation. No uploaded media is ever used here."""

import hashlib
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from multitrack.config import MODELS  # noqa: E402

BASE = "https://github.com/k2-fsa/sherpa-onnx/releases/download/"
ASSETS = [
    (
        "speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2",
        "24615ee884c897d9d2ba09bb4d30da6bb1b15e685065962db5b02e76e4996488",
        "segmentation",
    ),
    (
        "speaker-recongition-models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx",
        "1a331345f04805badbb495c775a6ddffcdd1a732567d5ec8b3d5749e3c7a5e4b",
        "embedding",
    ),
]


def main():
    MODELS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for asset, expected, name in ASSETS:
            print(f"Download {name} via HTTPS…", flush=True)
            local = Path(tmp) / name
            with (
                urllib.request.urlopen(BASE + asset, timeout=120) as response,
                local.open("wb") as f,
            ):
                shutil.copyfileobj(response, f)
            with local.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != expected:
                raise RuntimeError(f"Checksum verschilt voor {name}; installatie gestopt.")
            if name == "segmentation":
                with tarfile.open(local) as archive:
                    # Extract only known files, never paths supplied by an archive.
                    for src, dest in [
                        ("model.onnx", "segmentation.onnx"),
                        ("LICENSE", "segmentation-LICENSE"),
                    ]:
                        with archive.extractfile(
                            f"sherpa-onnx-pyannote-segmentation-3-0/{src}"
                        ) as f:
                            with (MODELS / (dest + ".tmp")).open("wb") as output:
                                shutil.copyfileobj(f, output)
                        (MODELS / (dest + ".tmp")).replace(MODELS / dest)
            else:
                shutil.copyfile(local, MODELS / "embedding.onnx.tmp")
                (MODELS / "embedding.onnx.tmp").replace(MODELS / "embedding.onnx")
    print(f"Modellen gereed: {MODELS}")


if __name__ == "__main__":
    main()
