"""Read-only installation guidance: no installation or downloads from the website."""

import importlib.metadata
import sys

from . import __version__
from .ad_text import ready as ad_text_ready
from .config import MODELS
from .diarize import model_ready
from .music import MODEL_NAME
from .separate import OVERLAP_NAME


def package_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def installation_status(ffmpeg_ready, cuda_available=False):
    windows = r".\.venv\Scripts\python.exe"
    posix = ".venv/bin/python"
    torch = package_version("torch")
    torchaudio = package_version("torchaudio")
    runtime_ok = all(v and v.split("+")[0] == "2.8.0" for v in [torch, torchaudio])
    checks = [
        {
            "name": "Optioneel: reclametekst herkennen (Whisper Small, Nederlands)",
            "installed": ad_text_ready(MODELS),
            "required": False,
            "detail": "Geeft tekstaanwijzingen; gezongen slogans kunnen verkeerd worden verstaan. Tekst wist geen audio.",
            "windows": f"{windows} scripts/download_ad_text_model.py",
            "posix": f"{posix} scripts/download_ad_text_model.py",
        },
        {
            "name": "Python 3.12 (64-bit)",
            "installed": sys.version_info[:2] == (3, 12) and sys.maxsize > 2**32,
            "required": True,
            "detail": f"Actief: {sys.version.split()[0]}.",
            "windows": "Installeer Python 3.12 (64-bit) en open daarna een nieuwe terminal.",
            "posix": "Installeer Python 3.12 via de pakketbeheerder van je besturingssysteem.",
        },
        {
            "name": "FFmpeg + ffprobe",
            "installed": ffmpeg_ready,
            "required": True,
            "detail": "Nodig om MP4-bestanden te lezen en audio/video te exporteren.",
            "windows": "winget install Gyan.FFmpeg",
            "posix": "sudo apt-get update && sudo apt-get install -y ffmpeg",
            "mac": "brew install ffmpeg",
        },
        {
            "name": "Basismodellen: sprekers herkennen",
            "installed": model_ready(MODELS),
            "required": True,
            "detail": "Eenmalig circa 45 MB; dezelfde modellen als in versie 0.1.",
            "windows": f"{windows} scripts/download_models.py",
            "posix": f"{posix} scripts/download_models.py",
        },
        {
            "id": "audio_runtime",
            "name": "Audio-runtime: PyTorch + torchaudio 2.8.0",
            "installed": runtime_ok,
            "required": False,
            "detail": f"Nodig voor muziek- en stemmenscheiding. PyTorch: {torch or 'ontbreekt'}; torchaudio: {torchaudio or 'ontbreekt'}.",
            "windows": f"{windows} -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cpu",
            "posix": f"{posix} -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cpu",
            "mac": f"{posix} -m pip install torch==2.8.0 torchaudio==2.8.0",
        },
        {
            "name": "Muziekmodel: Hybrid Demucs",
            "installed": (MODELS / MODEL_NAME).is_file(),
            "required": False,
            "detail": "Vanaf versie 0.2, circa 320 MB. Aanwezigheid van het bestand; checksum wordt bij verwerking gecontroleerd.",
            "windows": f"{windows} scripts/download_music_model.py",
            "posix": f"{posix} scripts/download_music_model.py",
        },
        {
            "name": "Stemmenscheider: Conv-TasNet",
            "installed": (MODELS / OVERLAP_NAME).is_file(),
            "required": False,
            "detail": "Vanaf versie 0.2, circa 20 MB. Aanwezigheid van het bestand; checksum wordt bij verwerking gecontroleerd.",
            "windows": f"{windows} scripts/download_overlap_model.py",
            "posix": f"{posix} scripts/download_overlap_model.py",
        },
    ]
    return {
        "version": __version__,
        "packaged": bool(getattr(sys, "frozen", False)),
        "cuda_available": cuda_available,
        "update_note": (
            "Windows CPU-editie: Python, FFmpeg en de modellen zijn inbegrepen. Je hoeft geen losse dependencies te installeren."
            if getattr(sys, "frozen", False)
            else "Versie 0.5 gebruikt dezelfde Python-pakketten. Alleen voor reclametekst is het nieuwe optionele Whisper Small-model nodig. De reclamebibliotheek werkt zonder dat model."
        ),
        "checks": checks,
    }
