#!/usr/bin/env python3
"""Optional explicit network step; refuses models without Apache-2.0 metadata."""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from multitrack.config import MODELS  # noqa: E402


def main():
    from huggingface_hub import HfApi, snapshot_download

    model = "speechbrain/sepformer-wsj02mix"
    info = HfApi().model_info(model)
    if not info.card_data or info.card_data.get("license") != "apache-2.0":
        raise RuntimeError("Apache-2.0 modellicentie niet bevestigd; download gestopt.")
    folder = MODELS / "sepformer"
    snapshot_download(
        repo_id=model,
        revision=info.sha,
        local_dir=folder,
        allow_patterns=["hyperparams.yaml", "*.ckpt", "README.md", "LICENSE*"],
    )
    manifest = {"repository": model, "revision": info.sha, "license": "apache-2.0", "sha256": {}}
    for f in folder.iterdir():
        if f.is_file():
            with f.open("rb") as stream:
                manifest["sha256"][f.name] = hashlib.file_digest(stream, "sha256").hexdigest()
    (folder / "download-manifest.json").write_text(json.dumps(manifest, indent=2))
    print("Scheider lokaal opgeslagen. Vanaf nu is voor verwerking geen internet nodig.")


if __name__ == "__main__":
    main()
