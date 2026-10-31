"""Windows entry point for the self-contained installer and its worker processes."""

import importlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

APP_URL = "http://127.0.0.1:8765"
MUTEX_NAME = r"Local\MultitrackertAudioServer"
_MUTEX = None


def prepare_environment():
    if getattr(sys, "frozen", False):
        resource_root = Path(sys._MEIPASS)
        ffmpeg = resource_root / "ffmpeg" / "bin"
        os.environ["PATH"] = str(ffmpeg) + os.pathsep + os.environ.get("PATH", "")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


def message(text):
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, "Multitrackert Audio", 0x10)
    else:
        print(text, file=sys.stderr)


def local_request(path, method="GET"):
    # Loopback never uses a user-configured Internet proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return opener.open(
        urllib.request.Request(APP_URL + path, method=method, headers={"X-Multitrack": "local"}),
        timeout=3,
    )


def single_instance():
    global _MUTEX
    if sys.platform != "win32":
        return True
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    handle = kernel.CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        raise OSError("Kan de appvergrendeling niet maken.")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(handle)
        return False
    _MUTEX = handle  # The OS releases this handle when the process exits.
    return True


def enable_log(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    log = path.open("a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = log


def self_test(destination):
    """Run the bundled models without a browser; used by native Windows build checks."""
    import numpy as np

    from . import __version__, config
    from .diarize import model_ready
    from .hardware import inspect_hardware
    from .music import MusicSeparator
    from .separate import Separator

    destination.mkdir(parents=True, exist_ok=True)
    hardware = inspect_hardware()
    assert hardware["ffmpeg"] and model_ready(config.MODELS)
    signal = np.random.default_rng(7).normal(0, 0.01, (44100, 2)).astype("float32")
    music = MusicSeparator(config.MODELS, hardware)(signal)
    voices = Separator(config.MODELS, "cpu")(signal[:16000, 0])
    assert music.shape == signal.shape and np.isfinite(music).all()
    assert len(voices) == 2 and all(len(v) == 16000 and np.isfinite(v).all() for v in voices)
    (destination / "self-test.json").write_text(
        json.dumps({"version": __version__, "models": "passed"})
    )


def main():
    import multiprocessing

    multiprocessing.freeze_support()
    prepare_environment()
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        # Never acquire the desktop mutex in a subprocess.
        module, folder = sys.argv[2], Path(sys.argv[3])
        if module not in {"multitrack.worker", "multitrack.remix"}:
            return 2
        enable_log(folder / "worker.log")
        return importlib.import_module(module).process(folder)
    if len(sys.argv) > 1 and sys.argv[1] == "--quit":
        try:
            with local_request("/api/app/quit", "POST"):
                pass
            return 0
        except (OSError, urllib.error.URLError):
            return 1
    if len(sys.argv) > 2 and sys.argv[1] == "--self-test":
        destination = Path(sys.argv[2])
        enable_log(destination / "self-test.log")
        try:
            self_test(destination)
            return 0
        except Exception:
            import traceback

            traceback.print_exc()
            return 1
    try:
        if not single_instance():
            if not os.environ.get("MULTITRACK_NO_BROWSER"):
                webbrowser.open(APP_URL)
            return 0
        from . import config

        enable_log(config.DATA / "server.log")
        try:
            with local_request("/api/health"):
                message(
                    "Poort 8765 wordt al gebruikt. Sluit een eventueel nog draaiende oude Python-versie en probeer opnieuw."
                )
                return 1
        except urllib.error.HTTPError:
            message("Poort 8765 wordt al gebruikt. Sluit de oude lokale server en probeer opnieuw.")
            return 1
        except (OSError, urllib.error.URLError):
            pass
        import uvicorn

        from .app import app

        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=8765, workers=1, use_colors=False)
        )
        app.state.shutdown_callback = lambda: setattr(server, "should_exit", True)

        def open_when_ready():
            for _ in range(120):
                if server.should_exit:
                    return
                try:
                    with local_request("/api/health") as response:
                        if json.load(response).get("app") == "Multitrackert Audio":
                            if not os.environ.get("MULTITRACK_NO_BROWSER"):
                                webbrowser.open(APP_URL)
                            return
                except (OSError, urllib.error.URLError):
                    pass
                time.sleep(0.5)

        threading.Thread(target=open_when_ready, daemon=True).start()
        server.run()
        return 0
    except Exception as e:
        import traceback

        traceback.print_exc()
        message(f"De app kon niet starten: {e}\nBekijk server.log in je lokale datamap.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
