import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("MULTITRACK_DATA", str(Path.home() / ".multitrackert")))
MODELS = Path(os.environ.get("MULTITRACK_MODELS", str(ROOT / "models")))
MAX_BYTES = int(os.environ.get("MULTITRACK_MAX_BYTES", str(4 * 1024**3)))
MAX_SECONDS = 3600
