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
from .media import decode_reference, extract, make_analysis, probe  # noqa: E402
from .music import ready as music_ready  # noqa: E402
from .music import separate_music  # noqa: E402
from .radio import reduce_radio  # noqa: E402
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
        if options.get("music") and not music_ready(config.MODELS):
            raise ValueError("Muziekmodel ontbreekt. Zie README: muziek apart zetten.")
        hardware = inspect_hardware()
        if options.get("device") == "cpu":
            hardware["separation_device"] = "cpu"
        progress.update("MP4 controleren")
        info = probe(folder / "input.mp4")
        # Original + speaker tracks + clips + uncompressed ZIP, conservative worst case.
        estimate = info["duration"] * info["sample_rate"] * info["channels"] * 4 * 70
        if shutil.disk_usage(folder).free < estimate + 512 * 1024**2:
            raise ValueError("Onvoldoende vrije schijfruimte voor verliesvrije tracks en ZIP.")
        if info["duration"] * 16000 * 4 * 12 > hardware["ram_available_gb"] * 1024**3:
            raise ValueError("Onvoldoende vrij RAM voor deze opname; gebruik kortere fragmenten.")
        progress.update("Audio en video uitpakken")
        extract(folder / "input.mp4", folder, info)
        progress.check()
        source = folder / "original.wav"
        processing = {}
        if options.get("reference"):
            progress.update("Radio-referentie voorbereiden")
            decode_reference(
                folder / "reference.upload", folder / "reference.wav", info["sample_rate"]
            )
            processing["radio"] = reduce_radio(
                source, folder / "reference.wav", folder, progress, options.get("reference_offset")
            )
            source = folder / "cleaned.wav"
        if options.get("music"):
            processing["music"] = separate_music(source, folder, config.MODELS, hardware, progress)
            source = folder / "working.wav"
        if source.name != "original.wav":
            progress.update("Stemmen voorbereiden voor herkenning")
            make_analysis(source, folder / "analysis.wav")
        analysis, _ = sf.read(folder / "analysis.wav", dtype="float32")
        progress.update("Sprekers herkennen")
        segments = diarize(
            analysis, config.MODELS, options["speakers"], hardware["inference_threads"], progress
        )
        output, overlaps = render(
            folder,
            info,
            segments,
            analysis,
            config.MODELS,
            hardware,
            options["separate"],
            progress,
            source,
        )
        manifest = package(folder, output, info, segments, overlaps, progress, hardware, processing)
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
        # Keep original uploads for review; remove derived intermediate audio.
        for name in ["analysis.wav", "working.wav", "reference.wav"]:
            (folder / name).unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(process(Path(sys.argv[1])))
