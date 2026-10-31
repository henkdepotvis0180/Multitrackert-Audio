"""Native Windows check of the actual frozen app and its subprocess workers."""

import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


def main():
    exe = Path(sys.argv[1]).resolve()
    root = Path("build/frozen-smoke").resolve()
    root.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "MULTITRACK_DATA": os.environ.get("MULTITRACK_DATA", str(root / "data")),
        "MULTITRACK_NO_BROWSER": "1",
    }
    # Validate that frozen Torch and both optional models actually load.
    result = subprocess.run([str(exe), "--self-test", str(root)], env=env, timeout=180)
    if result.returncode or not (root / "self-test.json").exists():
        raise RuntimeError(
            "Bundled model test failed: " + (root / "self-test.log").read_text(errors="replace")
        )
    ffmpeg = exe.parent / "_internal/ffmpeg/bin/ffmpeg.exe"
    source = root / "speech.mp4"
    subprocess.run(
        [
            str(ffmpeg),
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=s=160x90:r=25",
            "-i",
            ".local-data/test-speech.wav",
            "-t",
            "4",
            "-c:v",
            "mpeg4",
            "-c:a",
            "aac",
            str(source),
        ],
        check=True,
    )
    process = subprocess.Popen([str(exe)], env=env)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    url = "http://127.0.0.1:8765"

    def request(path, body=None):
        req = urllib.request.Request(
            url + path,
            data=body,
            headers={
                "X-Multitrack": "local",
                "Content-Type": "application/json"
                if body and body.startswith(b"{")
                else "video/mp4",
            },
        )
        with opener.open(req, timeout=20) as response:
            return response.read()

    def wait_job(ident):
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            status = json.loads(request("/api/jobs/" + ident))
            if status["state"] in {"done", "error", "cancelled"}:
                assert status["state"] == "done", status
                return status
            time.sleep(0.5)
        raise TimeoutError("Frozen worker did not finish")

    try:
        for _ in range(120):
            try:
                assert json.loads(request("/api/health"))["desktop"]
                break
            except (OSError, urllib.error.URLError):
                time.sleep(0.5)
        else:
            raise RuntimeError(
                "Frozen webserver did not start; inspect " + str(root / "data/server.log")
            )
        system = json.loads(request("/api/system"))
        assert system["models_ready"] and system["music_ready"] and system["separation_ready"]
        assert system["installation"]["packaged"]
        job = json.loads(
            request("/api/jobs?speakers=1&music=true&separate=true", source.read_bytes())
        )["id"]
        wait_job(job)
        for attempt in range(30):
            try:
                request(
                    "/api/jobs/" + job + "/mix",
                    json.dumps({"mode": "keep_all", "excluded_speakers": []}).encode(),
                )
                break
            except urllib.error.HTTPError as e:
                if e.code != 409 or attempt == 29:
                    raise
                time.sleep(0.2)
        wait_job(job)
        data = request("/api/jobs/" + job + "/download")
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            assert {
                "original.wav",
                "video.mp4",
                "background.wav",
                "music.wav",
                "cleaned.wav",
                "removed.wav",
            } <= set(z.namelist())
            assert z.testzip() is None
        # Simulate an interrupted browser download and request a byte range again.
        req = urllib.request.Request(
            url + "/api/jobs/" + job + "/download", headers={"Range": "bytes=0-31"}
        )
        with opener.open(req) as response:
            assert response.status == 206 and response.read() == data[:32]
        storage = json.loads(request("/api/jobs/" + job + "/storage"))
        assert Path(storage["zip"]).exists() and Path(storage["source"]).exists()
        (root / "result.json").write_text(
            json.dumps({"passed": True, "job": job, "storage": storage}, indent=2)
        )
    finally:
        try:
            request("/api/app/quit", b"{}")
        except OSError:
            pass
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
