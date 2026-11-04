from dataclasses import dataclass
from pathlib import Path

import numpy as np
import sherpa_onnx


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    speaker: int


def model_ready(models: Path):
    return all((models / name).is_file() for name in ["segmentation.onnx", "embedding.onnx"])


def diarize(audio, models, speakers, threads, progress):
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=str(models / "segmentation.onnx"), window_shift_ratio=0.1
            ),
            num_threads=threads,
            provider="cpu",
        ),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(models / "embedding.onnx"), num_threads=threads, provider="cpu"
        ),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=speakers or -1, threshold=0.5),
        min_duration_on=0.25,
        min_duration_off=0.25,
    )
    if not config.validate():
        raise ValueError("Ongeldige modellen. Voer python scripts/download_models.py uit.")
    sd = sherpa_onnx.OfflineSpeakerDiarization(config)

    def callback(done, total):
        progress.update("Sprekers herkennen", done / max(1, total))
        return 0

    result = sd.process(audio, callback=callback).sort_by_start_time()
    # IDs are anonymous clusters. Stable renumbering follows first appearance.
    ids = {}
    segments = []
    for item in result:
        a, b = max(0.0, item.start), min(len(audio) / 16000, item.end)
        if b > a:
            ids.setdefault(item.speaker, len(ids) + 1)
            segments.append(Segment(a, b, ids[item.speaker]))
    return segments


def bound_voice_tracks(segments, limit=12):
    """Keep bounded individual tracks; other voices remain in the audio residual.

    This is an export/storage limit, not an assertion about who is radio or a person.
    The original segments are recorded as metadata for the grouped voices.
    """
    durations = {}
    for segment in segments:
        durations[segment.speaker] = durations.get(segment.speaker, 0) + segment.end - segment.start
    if len(durations) <= limit:
        return segments, None
    keep = set(sorted(durations, key=lambda s: (-durations[s], s))[:limit])
    track_ids = {group: i for i, group in enumerate(sorted(keep), 1)}
    return [Segment(s.start, s.end, track_ids[s.speaker]) for s in segments if s.speaker in keep], {
        "detected_groups": len(durations),
        "individual_tracks": limit,
        "individual_source_groups": [
            {"track": track, "source_group": group} for group, track in track_ids.items()
        ],
        "grouped_segments": [
            {"start": s.start, "end": s.end, "group": s.speaker}
            for s in segments
            if s.speaker not in keep
        ],
        "note": "Meer dan 12 geschatte stemgroepen. De 12 groepen met de meeste spreektijd "
        "hebben losse tracks; overige stemmen blijven in achtergrond/rest en kunnen "
        "bij overlap ook in andere tracks zitten. Dit is geen herkenning van radio versus gesprek.",
    }


class Embedder:
    def __init__(self, models, threads):
        self.extractor = sherpa_onnx.SpeakerEmbeddingExtractor(
            sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                model=str(models / "embedding.onnx"), num_threads=threads, provider="cpu"
            )
        )

    def __call__(self, audio):
        stream = self.extractor.create_stream()
        stream.accept_waveform(sample_rate=16000, waveform=np.asarray(audio, dtype=np.float32))
        stream.input_finished()
        if not self.extractor.is_ready(stream):
            return None
        vector = np.asarray(self.extractor.compute(stream))
        return vector / max(float(np.linalg.norm(vector)), 1e-8)


def intervals(segments, duration):
    """Disjoint regions with the complete set of active speakers, including silence."""
    events = {0.0: [], duration: []}
    for s in segments:
        a, b = max(0.0, s.start), min(duration, s.end)
        if b > a:
            events.setdefault(a, []).append((s.speaker, 1))
            events.setdefault(b, []).append((s.speaker, -1))
    counts = {}
    times = sorted(events)
    for i, start in enumerate(times[:-1]):
        for speaker, delta in events[start]:
            counts[speaker] = counts.get(speaker, 0) + delta
        yield start, times[i + 1], tuple(sorted(k for k, v in counts.items() if v > 0))
