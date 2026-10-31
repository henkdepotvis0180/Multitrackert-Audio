"""Local Hybrid Demucs vocals/music separation, preserving a reconstruction residual."""

import hashlib
import importlib.util

import numpy as np
import soundfile as sf

from .audio import fit_length, resample, writer

MODEL_NAME = "hdemucs.pt"
MODEL_URL = "https://download.pytorch.org/torchaudio/models/hdemucs_high_musdbhq_only.pt"
MODEL_SHA256 = "85ce4420e0852344b816487b4c4bb821bd406376b93bf684b2b76aa56404c46a"


def ready(models):
    return (models / MODEL_NAME).is_file() and all(
        importlib.util.find_spec(name) is not None for name in ["torch", "torchaudio"]
    )


class MusicSeparator:
    def __init__(self, models, hardware):
        import torch
        from torchaudio.models import hdemucs_high

        with (models / MODEL_NAME).open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() != MODEL_SHA256:
                raise ValueError("Muziekmodel-checksum verschilt. Download het model opnieuw.")
        torch.set_num_threads(hardware["inference_threads"])
        self.torch, self.device = torch, hardware["separation_device"]
        self.model = hdemucs_high(sources=["drums", "bass", "other", "vocals"])
        self.model.load_state_dict(
            torch.load(models / MODEL_NAME, map_location="cpu", weights_only=True)
        )
        self.model.eval().to(self.device)

    def __call__(self, stereo44):
        torch = self.torch
        waveform = torch.from_numpy(np.ascontiguousarray(stereo44.T)).float().to(self.device)
        mean, scale = waveform.mean(), waveform.std().clamp_min(1e-8)
        with torch.inference_mode():
            vocals = self.model(((waveform - mean) / scale)[None])[0, 3] * scale
        return vocals.detach().cpu().numpy().T


def separate_music(source, folder, models, hardware, progress):
    separator = MusicSeparator(models, hardware)
    with sf.SoundFile(source) as original:
        rate, channels, frames = original.samplerate, original.channels, len(original)
        with (
            writer(folder / "working.wav", rate, channels, frames) as voice_out,
            writer(folder / "music.wav", rate, channels, frames) as music_out,
        ):
            core, pad = rate * 8, rate
            for start in range(0, frames, core):
                progress.update("Muziek en stemmen scheiden", start / max(1, frames))
                stop = min(frames, start + core)
                left, right = max(0, start - pad), min(frames, stop + pad)
                original.seek(left)
                context = original.read(right - left, dtype="float32", always_2d=True)
                stereo = np.repeat(context, 2, axis=1) if channels == 1 else context
                vocals = separator(resample(stereo, rate, 44100))
                vocals = fit_length(resample(vocals, 44100, rate), len(context))
                if channels == 1:
                    vocals = vocals.mean(axis=1, keepdims=True)
                vocals = vocals[start - left : stop - left]
                voice_out.write(vocals)
                # Residual, rather than independently normalised stems: no sound is discarded.
                music_out.write(context[start - left : stop - left] - vocals)
    return {
        "model": "torchaudio HDEMUCS_HIGH_MUSDB",
        "model_sample_rate": 44100,
        "note": "Instrumentale muziek en modelrest. Zang en vergaderstemmen kunnen samen in de stemmix blijven.",
    }
