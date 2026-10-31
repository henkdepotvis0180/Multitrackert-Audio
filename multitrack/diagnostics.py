"""User-initiated local log export; recordings and process environment are excluded."""

import io
import platform
import zipfile

from . import __version__
from .state import open_shared_text


def log_bundle(data_dir):
    stream = io.BytesIO()
    files = [data_dir / "server.log"]
    jobs = data_dir / "jobs"
    if jobs.exists():
        logs = sorted(jobs.glob("*/worker.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        for log in logs:
            files.extend([log, log.parent / "status.json"])
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "systeem.txt",
            f"Multitrackert Audio {__version__}\n{platform.system()} {platform.release()}\nPython {platform.python_version()}\n",
        )
        for path in files:
            if path.is_file():
                try:
                    with open_shared_text(path, errors="replace") as f:
                        f.seek(0, 2)
                        f.seek(max(0, f.tell() - 128 * 1024))
                        content = f.read()
                except (OSError, UnicodeError) as e:
                    content = f"Logbestand kon niet worden gelezen: {e}"
                archive.writestr(path.relative_to(data_dir).as_posix(), content)
    return stream.getvalue()
