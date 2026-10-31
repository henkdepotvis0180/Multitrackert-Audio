# Licenties en herkomst

Geen modelgewichten of FFmpeg-binaries worden in Git opgenomen. Eigen code: MIT.
Installatie gebruikt onderstaande bronnen. Dit is geen claim dat spraakherkenning
foutloos werkt of dat een stemcluster een bewezen identiteit is.

| Onderdeel | Licentie / bron | Gebruik |
| --- | --- | --- |
| sherpa-onnx 2.0.1 | Apache-2.0, [repository](https://github.com/k2-fsa/sherpa-onnx) | Lokale ONNX-diarisatie, CPU |
| pyannote segmentation-3.0 ONNX | MIT; `LICENSE` in de [officiële geconverteerde modelrelease](https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-segmentation-models), gebaseerd op [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0) | Spraak-/overlapsegmentatie |
| 3D-Speaker ERes2Net base | Apache-2.0, [3D-Speaker](https://github.com/modelscope/3D-Speaker), ONNX-bestand uit [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-recongition-models) | Spreker-embeddings, geen herkenning van namen |
| FastAPI | MIT | Lokale HTTP-server |
| Uvicorn | BSD-3-Clause | HTTP-runtime |
| NumPy / SciPy | BSD-3-Clause | Audio-arrayverwerking en resampling |
| SoundFile / libsndfile | BSD-3-Clause / LGPL-2.1-or-later | WAV lezen/schrijven |
| psutil | BSD-3-Clause | Hardwarecontrole |
| FFmpeg (apart installeren) | LGPL-2.1-or-later of GPL, afhankelijk van build | Media demux/decoding; commercieel gebruik toegestaan met toepasselijke voorwaarden |
| Optioneel: PyTorch / torchaudio | BSD-style | CPU/CUDA-inferentie |
| Optioneel: SpeechBrain | Apache-2.0 | SepFormer-runtime |
| Optioneel: speechbrain/sepformer-wsj02mix gewichten | Verwacht Apache-2.0; downloader controleert actuele modelkaart vóór download | Twee-stemmen-scheiding; metadata/gewichten konden vanuit deze cloud niet worden opgehaald |

Het MIT-bestand van de segmentatierelease en de Apache-2.0-tekst van de
3D-Speaker-repository zijn onder `docs/licenses/` bewaard. De oorspronkelijke
modelgewichten en trainingsdatasets worden niet verder verspreid in deze repository.
Datasets hebben eigen voorwaarden; deze app vereist of distribueert de trainingsdata niet.
Bij herdistributie van dependencies/binaries moeten ook hun eigen notices behouden blijven.

De optionele modeldownload legt een exact Hugging Face commit-ID en lokale SHA-256
bestandschecksums vast. De twee basismodeldownloads zijn vastgepind op checksums in
`scripts/download_models.py`; een afwijking stopt installatie, zonder verificatie uit
te schakelen of andere gewichten stilzwijgend te accepteren.
