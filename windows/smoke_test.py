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

import numpy as np
import soundfile as sf


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
    speech, rate = sf.read(".local-data/test-speech.wav", dtype="float32")
    speech = speech[: rate * 4]
    speech = speech / max(1e-7, float(np.sqrt(np.mean(speech * speech)))) * 0.02
    reference = np.random.default_rng(47).normal(0, 0.08, rate * 2).astype("float32")
    mixture = speech.copy()
    mixture[rate // 2 : rate // 2 + len(reference)] += reference
    sf.write(root / "reference.wav", reference, rate, subtype="FLOAT")
    sf.write(root / "mixed-speech.wav", mixture, rate, subtype="FLOAT")
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
            str(root / "mixed-speech.wav"),
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
        try:
            with opener.open(req, timeout=20) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            e.add_note(f"{path}: {e.read().decode('utf-8', errors='replace')[:2000]}")
            raise

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
        assert system["ad_text_ready"]
        request("/api/ad-library", (root / "reference.wav").read_bytes())
        job = json.loads(
            request(
                "/api/jobs?speakers=1&music=true&separate=true&known_ads=true&ad_text=true",
                source.read_bytes(),
            )
        )["id"]
        wait_job(job)
        timeline = json.loads(request("/api/jobs/" + job + "/timeline"))
        assert timeline["segments"], "Speech fixture must produce selectable fragments"
        assert timeline["processing"]["ad_detection"]["applied"]
        assert len(timeline["processing"]["ad_detection"]["matches"]) == 1
        assert not timeline["processing"]["ad_text"]["automatic_removal"]
        fragment = timeline["segments"][0]["fragment"]
        for attempt in range(30):
            try:
                request(
                    "/api/jobs/" + job + "/mix",
                    json.dumps({"mode": "remove_radio", "excluded_fragments": [fragment]}).encode(),
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
                "radio_voices.wav",
                "radio.wav",
            } <= set(z.namelist())
            manifest = json.loads(z.read("timeline.json"))
            assert manifest["mix"]["excluded_fragments"] == [fragment]
            assert manifest["mix_tracks"][0]["file"] == "radio_voices.wav"
            assert "mix-speakers/" in z.read("timeline.xml").decode("utf-8")
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
    try:
        main()
    except Exception:
        import traceback

        detail = traceback.format_exc()
        for path in Path("build/frozen-smoke").rglob("*.log"):
            detail += "\n" + str(path) + "\n" + path.read_text(errors="replace")[-6000:]
        encoded = detail[-14000:].replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print("::error title=Frozen application validation::" + encoded, flush=True)
        raise
