import os
import sys
from pathlib import Path

from .paths import default_data_dir

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = default_data_dir(
    Path.home(),
    os.environ.get("LOCALAPPDATA"),
    sys.platform == "win32" and getattr(sys, "frozen", False),
)
DATA = Path(os.environ.get("MULTITRACK_DATA", str(DEFAULT_DATA))).resolve()
if getattr(sys, "frozen", False) and DATA.is_relative_to(Path(sys.executable).resolve().parent):
    raise ValueError(
        "De projectmap moet buiten de installatiemap staan, zodat updates je opnames behouden."
    )
MODELS = Path(os.environ.get("MULTITRACK_MODELS", str(ROOT / "models")))
MAX_BYTES = int(os.environ.get("MULTITRACK_MAX_BYTES", str(4 * 1024**3)))
MAX_SECONDS = 3600
