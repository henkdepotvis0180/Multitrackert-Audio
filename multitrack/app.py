import asyncio
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import config
from .diarize import model_ready
from .hardware import inspect_hardware
from .separate import ready
from .state import atomic_json, read_json

TERMINAL = {"done", "error", "cancelled", "interrupted"}


class Jobs:
    def __init__(self, root):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.active = None
        self.process = None
        for folder in root.iterdir():
            if folder.is_dir() and (folder / "status.json").is_file():
                if read_json(folder / "status.json")["state"] not in TERMINAL:
                    atomic_json(
                        folder / "status.json",
                        {"state": "interrupted", "message": "Server herstart. Upload opnieuw."},
                    )

    def reserve(self):
        with self.lock:
            if self.active is not None:
                raise HTTPException(
                    409, "Er wordt al een bestand verwerkt. Wacht of annuleer dit eerst."
                )
            ident = uuid.uuid4().hex
            self.active = ident
            folder = self.root / ident
            folder.mkdir()
            atomic_json(folder / "status.json", {"state": "uploading", "message": "Uploaden"})
            return ident, folder

    def release(self):
        with self.lock:
            self.active, self.process = None, None

    def start(self, folder):
        log = (folder / "worker.log").open("w")
        try:
            self.process = subprocess.Popen(
                [sys.executable, "-m", "multitrack.worker", str(folder)], stdout=log, stderr=log
            )
        finally:
            log.close()

        def wait():
            self.process.wait()
            status = read_json(folder / "status.json")
            if status["state"] not in TERMINAL:
                atomic_json(
                    folder / "status.json",
                    {
                        "state": "error",
                        "message": "Worker gestopt. Bekijk worker.log in je lokale datamap.",
                    },
                )
            self.release()

        threading.Thread(target=wait, daemon=True).start()

    def stop(self):
        # Terminate only this server's worker and its FFmpeg descendants.
        import psutil

        with self.lock:
            process = self.process
            if process is None or process.poll() is not None:
                return
            try:
                children = psutil.Process(process.pid).children(recursive=True)
            except psutil.NoSuchProcess:
                children = []
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            process.terminate()
            _, alive = psutil.wait_procs(children, timeout=3)
            for child in alive:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def create_app(data=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.jobs = Jobs(Path(data or config.DATA) / "jobs")
        yield
        app.state.jobs.stop()

    app = FastAPI(title="Multitrackert Audio", lifespan=lifespan)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"]
    )

    @app.middleware("http")
    async def local_only(request, call_next):
        if request.client and request.client.host not in {"127.0.0.1", "::1", "testclient"}:
            return JSONResponse({"detail": "Alleen lokaal beschikbaar."}, status_code=403)
        if request.method in {"POST", "DELETE"} and request.headers.get("x-multitrack") != "local":
            return JSONResponse({"detail": "Lokale aanvraagheader ontbreekt."}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        return response

    def job(request, ident):
        if not re.fullmatch(r"[a-f0-9]{32}", ident):
            raise HTTPException(404, "Onbekende opdracht.")
        folder = request.app.state.jobs.root / ident
        if not (folder / "status.json").is_file():
            raise HTTPException(404, "Onbekende opdracht.")
        return folder

    @app.get("/api/system")
    async def system():
        hardware = await asyncio.to_thread(inspect_hardware)
        return {
            **hardware,
            "models_ready": model_ready(config.MODELS),
            "separation_ready": ready(config.MODELS),
            "max_bytes": config.MAX_BYTES,
            "max_minutes": config.MAX_SECONDS // 60,
        }

    @app.get("/api/jobs")
    async def list_jobs(request: Request):
        return [
            {"id": p.name, **read_json(p / "status.json")}
            for p in sorted(request.app.state.jobs.root.iterdir(), reverse=True)
            if (p / "status.json").is_file()
        ]

    @app.post("/api/jobs", status_code=202)
    async def upload(
        request: Request, speakers: int = 0, separate: bool = False, device: str = "auto"
    ):
        if device not in {"auto", "cpu"}:
            raise HTTPException(422, "Kies auto of cpu als apparaat.")
        if not 0 <= speakers <= 12:
            raise HTTPException(422, "Kies 0 (automatisch) tot 12 sprekers.")
        if not model_ready(config.MODELS):
            raise HTTPException(
                503, "Modellen ontbreken. Voer eerst de modeldownload uit (README)."
            )
        if separate and not ready(config.MODELS):
            raise HTTPException(503, "De optionele scheidingsmodellen ontbreken.")
        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > config.MAX_BYTES:
            raise HTTPException(413, "Bestand is te groot.")
        manager = request.app.state.jobs
        ident, folder = manager.reserve()
        size = 0
        try:
            with (folder / "input.mp4").open("wb") as f:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > config.MAX_BYTES:
                        raise HTTPException(413, "Bestand is te groot.")
                    f.write(chunk)
            if size == 0:
                raise HTTPException(422, "Bestand is leeg.")
            atomic_json(
                folder / "options.json",
                {"speakers": speakers, "separate": separate, "device": device},
            )
            atomic_json(
                folder / "status.json",
                {"state": "queued", "message": "Verwerking starten", "created_at": time.time()},
            )
            manager.start(folder)
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            manager.release()
            raise
        return {"id": ident}

    @app.get("/api/jobs/{ident}")
    async def status(request: Request, ident: str):
        return read_json(job(request, ident) / "status.json")

    @app.post("/api/jobs/{ident}/cancel")
    async def cancel(request: Request, ident: str):
        folder = job(request, ident)
        if read_json(folder / "status.json")["state"] in TERMINAL:
            raise HTTPException(409, "Opdracht is al gestopt.")
        (folder / "cancel").touch()
        return {"message": "Annulering aangevraagd; de huidige modelstap wordt eerst afgerond."}

    @app.delete("/api/jobs/{ident}")
    async def delete(request: Request, ident: str):
        folder = job(request, ident)
        if request.app.state.jobs.active == ident:
            raise HTTPException(409, "Wacht tot de verwerking is gestopt.")
        shutil.rmtree(folder)
        return {"deleted": True}

    @app.get("/api/jobs/{ident}/download")
    async def download(request: Request, ident: str):
        folder = job(request, ident)
        if read_json(folder / "status.json")["state"] != "done":
            raise HTTPException(409, "Export is nog niet klaar.")
        return FileResponse(folder / "result.zip", filename="multitrackert-export.zip")

    @app.get("/api/jobs/{ident}/timeline")
    async def timeline(request: Request, ident: str):
        folder = job(request, ident)
        if read_json(folder / "status.json")["state"] != "done":
            raise HTTPException(409, "Analyse is nog niet klaar.")
        return read_json(folder / "export" / "timeline.json")

    @app.get("/api/jobs/{ident}/media/{name}")
    async def media(request: Request, ident: str, name: str):
        folder = job(request, ident)
        if read_json(folder / "status.json")["state"] != "done":
            raise HTTPException(409, "Analyse is nog niet klaar.")
        if name == "input.mp4":
            return FileResponse(folder / name, media_type="video/mp4")
        if not re.fullmatch(r"speaker_\d{2}\.wav", name):
            raise HTTPException(404)
        path = folder / "export" / "speakers" / name
        if not path.is_file():
            raise HTTPException(404)
        return FileResponse(path, media_type="audio/wav")

    app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True))
    return app


app = create_app()
