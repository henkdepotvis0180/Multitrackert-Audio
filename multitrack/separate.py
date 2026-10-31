"""Optional two-speaker separation. Never download models during a job."""

import os
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly


def ready(models: Path):
    import importlib.util

    return importlib.util.find_spec("speechbrain") is not None and all(
        (models / "sepformer" / name).is_file()
        for name in ["hyperparams.yaml", "encoder.ckpt", "decoder.ckpt", "masknet.ckpt"]
    )


class Separator:
    def __init__(self, models, device):
        import torch
        from speechbrain.inference.separation import SepformerSeparation

        torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
        self.torch = torch
        self.device = device
        local = str((models / "sepformer").resolve())
        self.model = SepformerSeparation.from_hparams(
            source=local,
            savedir=str(models / "sepformer-cache"),
            run_opts={"device": device},
            overrides={"pretrained_path": local},
        )

    def __call__(self, mono16):
        wave8 = resample_poly(mono16, 1, 2).astype(np.float32)
        with self.torch.inference_mode():
            tensor = self.torch.from_numpy(wave8).unsqueeze(0).to(self.device)
            result = self.model.separate_batch(tensor)[0].detach().cpu().numpy()
        # No per-source normalisation: retain model relative gains.
        return [resample_poly(result[:, i], 2, 1)[: len(mono16)] for i in range(2)]


def assign_sources(sources, references, embed):
    """Conservative identity assignment; ambiguous matches remain mixed."""
    vectors = [embed(s) for s in sources]
    if any(v is None for v in vectors) or len(references) != 2:
        return None
    scores = np.array([[float(v @ r) for r in references] for v in vectors])
    direct = scores[0, 0] + scores[1, 1]
    reverse = scores[0, 1] + scores[1, 0]
    indices = [0, 1] if direct >= reverse else [1, 0]
    if abs(direct - reverse) < 0.15 or min(scores[indices[j], j] for j in range(2)) < 0.25:
        return None
    return indices
