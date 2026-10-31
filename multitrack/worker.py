import os
import sys
import time
from pathlib import Path

# Inference is strictly local, including optional Hugging Face libraries.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

from . import config  # noqa: E402
from .diarize import diarize, model_ready  # noqa: E402
from .export import package, render  # noqa: E402
from .hardware import inspect_hardware  # noqa: E402
from .media import extract, probe  # noqa: E402
from .state import Progress, atomic_json, read_json  # noqa: E402


def process(folder):
    import shutil

    import soundfile as sf

    from .separate import ready

    progress = Progress(folder)
    try:
        options = read_json(folder / "options.json")
        if not model_ready(config.MODELS):
            raise ValueError("Modellen ontbreken. Voer python scripts/download_models.py uit.")
        if options["separate"] and not ready(config.MODELS):
            raise ValueError("Optionele scheider ontbreekt. Zie README: overlap scheiden.")
        hardware = inspect_hardware()
        if options.get("device") == "cpu":
            hardware["separation_device"] = "cpu"
        progress.update("MP4 controleren")
        info = probe(folder / "input.mp4")
        # Original + speaker tracks + clips + uncompressed ZIP, conservative worst case.
        estimate = info["duration"] * info["sample_rate"] * info["channels"] * 4 * 60
        if shutil.disk_usage(folder).free < estimate + 512 * 1024**2:
            raise ValueError("Onvoldoende vrije schijfruimte voor verliesvrije tracks en ZIP.")
        if info["duration"] * 16000 * 4 * 12 > hardware["ram_available_gb"] * 1024**3:
            raise ValueError("Onvoldoende vrij RAM voor deze opname; gebruik kortere fragmenten.")
        progress.update("Audio en video uitpakken")
        extract(folder / "input.mp4", folder, info)
        progress.check()
        analysis, _ = sf.read(folder / "analysis.wav", dtype="float32")
        progress.update("Sprekers herkennen")
        segments = diarize(
            analysis, config.MODELS, options["speakers"], hardware["inference_threads"], progress
        )
        output, overlaps = render(
            folder, info, segments, analysis, config.MODELS, hardware, options["separate"], progress
        )
        manifest = package(folder, output, info, segments, overlaps, progress, hardware)
        progress.check()
        atomic_json(
            folder / "status.json",
            {
                "state": "done",
                "phase": "Klaar",
                "fraction": 1,
                "elapsed_seconds": time.monotonic() - progress.started,
                "phase_eta_seconds": 0,
                "message": f"{len(segments)} spreekfragmenten gevonden.",
                "speakers": sorted({s.speaker for s in segments}),
                "overlap_count": len(manifest["overlaps"]),
                "unseparated_overlap_count": sum(o["method"] == "mixed" for o in overlaps),
                "updated_at": time.time(),
            },
        )
    except Exception as e:
        atomic_json(
            folder / "status.json",
            {
                "state": "cancelled" if isinstance(e, InterruptedError) else "error",
                "phase": "Gestopt",
                "message": str(e),
                "updated_at": time.time(),
            },
        )
        return 1
    finally:
        # Retain input for local video review; clean analysis and partial output on errors.
        (folder / "analysis.wav").unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(process(Path(sys.argv[1])))
