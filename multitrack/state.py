import json
import os
import sys
import tempfile
import time
from pathlib import Path


def replace_file(source, destination):
    if sys.platform != "win32" or not destination.exists():
        return os.replace(source, destination)
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.ReplaceFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    kernel.ReplaceFileW.restype = wintypes.BOOL
    if not kernel.ReplaceFileW(str(destination), str(source), None, 0, None, None):
        raise ctypes.WinError(ctypes.get_last_error())


def atomic_json(path: Path, value: dict):
    # Every writer owns its temp file. Readers may poll while another process writes.
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix="." + path.name + ".",
            suffix=".tmp",
            delete=False,
        ) as f:
            tmp = Path(f.name)
            json.dump(value, f, ensure_ascii=False, indent=2)
        for attempt in range(12):
            try:
                replace_file(tmp, path)
                return
            except OSError as e:
                # Windows scanners and legacy readers can briefly deny replacement.
                if getattr(e, "winerror", None) not in {5, 32, 33} or attempt == 11:
                    raise
                time.sleep(min(0.25, 0.02 * 2**attempt))
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def open_shared_text(path: Path, errors="strict"):
    if sys.platform != "win32":
        return path.open(encoding="utf-8", errors=errors)
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    # FILE_SHARE_DELETE is essential: a JSON reader must not lock out atomic updates.
    handle = kernel.CreateFileW(str(path), 0x80000000, 1 | 2 | 4, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        kernel.CloseHandle(handle)
        raise
    return os.fdopen(fd, "r", encoding="utf-8", errors=errors)


def read_json(path: Path):
    with open_shared_text(path) as f:
        return json.load(f)


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
