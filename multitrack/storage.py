import os
import shutil
import subprocess
import sys
import time
from urllib.parse import unquote

from .state import atomic_json, read_json


def save_project(folder, encoded_filename):
    name = unquote(encoded_filename or "opname.mp4").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(c for c in name if c.isprintable())[:200] or "opname.mp4"
    atomic_json(folder / "project.json", {"name": name, "created_at": time.time()})


def project_info(folder):
    path = folder / "project.json"
    return (
        read_json(path)
        if path.is_file()
        else {"name": f"Opname {folder.name[:8]}", "created_at": None}
    )


def storage_info(folder):
    return {
        "project_dir": str(folder.resolve()),
        "output_dir": str((folder / "export").resolve()),
        "source": str((folder / "input.mp4").resolve()),
        "zip": str((folder / "result.zip").resolve()),
        "output_exists": (folder / "export").is_dir(),
        "zip_exists": (folder / "result.zip").is_file(),
    }


def open_folder(path):
    path = path.resolve()
    if not path.is_dir():
        raise ValueError("Deze map bestaat nog niet.")
    if sys.platform == "win32":
        os.startfile(str(path))
    else:
        command = "open" if sys.platform == "darwin" else "xdg-open"
        if not shutil.which(command):
            raise ValueError("Geen bestandsbeheerder beschikbaar. Gebruik het getoonde lokale pad.")
        subprocess.Popen([command, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
