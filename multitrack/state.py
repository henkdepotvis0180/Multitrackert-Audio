import json
import os
import time
from pathlib import Path


def atomic_json(path: Path, value: dict):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class Progress:
    def __init__(self, folder: Path):
        self.folder = folder
        self.started = time.monotonic()
        self.phase = None
        self.phase_start = self.started

    def check(self):
        if (self.folder / "cancel").exists():
            raise InterruptedError("Verwerking geannuleerd.")

    def update(self, phase: str, fraction: float = 0, message: str = ""):
        self.check()
        now = time.monotonic()
        if self.phase != phase:
            self.phase, self.phase_start = phase, now
        elapsed = now - self.phase_start
        eta = elapsed * (1 - fraction) / fraction if 0.02 < fraction < 1 and elapsed > 2 else None
        atomic_json(
            self.folder / "status.json",
            {
                "state": "running",
                "phase": phase,
                "fraction": min(1, max(0, fraction)),
                "message": message,
                "elapsed_seconds": now - self.started,
                "phase_eta_seconds": eta,
                "updated_at": time.time(),
            },
        )
