import json
import os
import subprocess
from pathlib import Path

from .config import MAX_SECONDS


class MediaError(ValueError):
    pass


def run(args, timeout=600):
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if result.returncode:
        raise MediaError(result.stderr[-2000:] or "FFmpeg-opdracht mislukt.")
    return result.stdout


def probe(path: Path):
    raw = json.loads(
        run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
            timeout=30,
        )
    )
    video = next((s for s in raw["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in raw["streams"] if s["codec_type"] == "audio"), None)
    if not video or not audio:
        raise MediaError("Een MP4 met zowel beeld als geluid is vereist.")
    if not 8000 <= int(audio["sample_rate"]) <= 192000:
        raise MediaError("Ondersteunde bronfrequentie: 8 tot 192 kHz.")
    duration = float(raw["format"].get("duration", 0))
    if not 0 < duration <= MAX_SECONDS:
        raise MediaError(f"Duur moet tussen 0 en {MAX_SECONDS // 60} minuten liggen.")
    if int(audio["channels"]) > 2:
        raise MediaError("Deze versie ondersteunt mono en stereo; kies eerst de gewenste audiomix.")
    return {
        "duration": duration,
        "sample_rate": int(audio["sample_rate"]),
        "channels": int(audio["channels"]),
        "fps": video.get("avg_frame_rate", "25/1"),
        "width": video["width"],
        "height": video["height"],
        "audio_stream": audio["index"],
        "video_stream": video["index"],
    }


def extract(source: Path, folder: Path, info: dict):
    # copyts + start_at_zero preserves the relative video/audio offset. Padding to
    # container duration gives every audio track exactly the same timeline origin.
    common = [
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-y",
        "-copyts",
        "-start_at_zero",
        "-protocol_whitelist",
        "file,pipe",
        "-i",
        str(source),
    ]
    run(
        common
        + [
            "-map",
            f"0:{info['audio_stream']}",
            "-vn",
            "-af",
            "aresample=async=1:first_pts=0,apad",
            "-t",
            str(info["duration"]),
            "-c:a",
            "pcm_f32le",
            "-rf64",
            "auto",
            str(folder / "original.wav"),
        ]
    )
    run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-i",
            str(folder / "original.wav"),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_f32le",
            str(folder / "analysis.wav"),
        ]
    )
    run(
        common
        + ["-map", f"0:{info['video_stream']}", "-an", "-c:v", "copy", str(folder / "video.mp4")]
    )


def make_analysis(source, destination):
    run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-i",
            str(source),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_f32le",
            str(destination),
        ]
    )


def decode_reference(source, destination, rate):
    raw = json.loads(
        run(
            ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(source)],
            timeout=30,
        )
    )
    if not any(s["codec_type"] == "audio" for s in raw["streams"]):
        raise MediaError("Referentiebestand bevat geen audio.")
    duration = float(raw["format"].get("duration", 0))
    if not 1 <= duration <= 1800:
        raise MediaError("Radio-referentie moet tussen 1 seconde en 30 minuten duren.")
    run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-protocol_whitelist",
            "file,pipe",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(rate),
            "-c:a",
            "pcm_f32le",
            "-rf64",
            "auto",
            str(destination),
        ]
    )
