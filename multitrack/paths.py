"""Keep user projects outside application binaries and preserve legacy data locations."""

from pathlib import Path


def default_data_dir(home, local_app_data=None, packaged_windows=False):
    legacy = Path(home) / ".multitrackert"
    if legacy.exists() or not packaged_windows:
        return legacy
    return Path(local_app_data or Path(home) / "AppData" / "Local") / "Multitrackert Audio" / "Data"
