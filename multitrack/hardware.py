import importlib.util
import os
import shutil

import psutil


def inspect_hardware():
    # Sherpa's standard wheel is CPU-only. Never claim CUDA from nvidia-smi alone.
    cuda, gpu, vram, free_vram = False, None, None, None
    if importlib.util.find_spec("torch"):
        import torch

        cuda = torch.cuda.is_available()
        if cuda:
            p = torch.cuda.get_device_properties(0)
            gpu, vram = p.name, round(p.total_memory / 1024**3, 1)
            free_vram = round(torch.cuda.mem_get_info()[0] / 1024**3, 1)
    available = psutil.virtual_memory().available
    return {
        "cpu_threads": os.cpu_count() or 1,
        "inference_threads": max(1, min(4, os.cpu_count() or 1)),
        "ram_available_gb": round(available / 1024**3, 1),
        "cuda_available": cuda,
        "gpu": gpu,
        "vram_gb": vram,
        "vram_free_gb": free_vram,
        "diarization_device": "cpu",
        "separation_device": "cuda" if cuda and free_vram >= 4 else "cpu",
        "ffmpeg": bool(shutil.which("ffmpeg") and shutil.which("ffprobe")),
    }
