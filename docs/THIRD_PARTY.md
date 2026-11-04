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

## Toegevoegd in 0.2

- **Hybrid Demucs / HDEMUCS_HIGH_MUSDB**: Demucs is MIT ([officiële licentie](https://github.com/facebookresearch/demucs/blob/main/LICENSE)); een kopie staat in `docs/licenses/demucs-MIT.txt`. De implementatie/fabriek komt uit BSD-gelicentieerd torchaudio 2.8.0. De officiële PyTorch-pipeline publiceert `hdemucs_high_musdbhq_only.pt` via `download.pytorch.org/torchaudio/models/`. Model en sample-rate volgen de [pipeline-definitie](https://github.com/pytorch/audio/blob/v2.8.0/src/torchaudio/pipelines/_source_separation_pipeline.py). Het model is getraind op MUSDB-HQ; de trainingsdata worden niet verspreid of voor installatie vereist.
- **Conv-TasNet / CONVTASNET_BASE_LIBRI2MIX**: implementatie en officiële gewichten uit dezelfde torchaudio-pipeline, BSD-style. Model: `conv_tasnet_base_libri2mix.pt`, 8 kHz, twee bronnen. De trainingsdata worden niet verspreid. Dit is de nieuw aanbevolen stemmenscheider; SpeechBrain/SepFormer is een optionele oudere fallback.
- Beide modelbestanden hebben vaste SHA-256-checksums in de app en downloader. HTTPS-, checksum- en packageverificatie blijven ingeschakeld. Verwerking doet geen modeldownloads; de lokale state dictionaries worden met `torch.load(..., weights_only=True)` geladen.
- De referentie-radiofilter is eigen MIT-code met NumPy/SciPy. Geen modelgewichten, muziekdienst of artiestdatabase. Het referentiebestand levert de gebruiker zelf lokaal aan.

De MIT/BSD-softwarelicenties geven geen nieuwe rechten op muziek of opnames die je
zelf verwerkt of doorlevert. Dat staat los van de gratis commerciële inzet van deze app.

## Windows-distributie vanaf 0.3

De CPU-installer bundelt Python (PSF-licentie), de CPU-runtime en modellen, en een eigen
minimale FFmpeg 7.1.5-build zonder GPL/nonfree-opties of netwerkprotocollen. De volledige
FFmpeg-broncode, configuratie, bouwscript en LGPL-licentie worden in de app én als
releaseattachment aangeboden. Build-toolchain-notices worden bewaard. De app spreekt
FFmpeg als afzonderlijk lokaal proces aan.

Inno Setup staat commercieel gebruik toe onder zijn eigen permissieve licentie;
zie `docs/licenses/inno-setup.txt`. De Microsoft C++ runtime wordt als ongewijzigde,
digitaal ondertekende redistributable gebundeld en blijft onder de Microsoft-voorwaarden.
Dependency- en runtime-licenties worden automatisch verzameld in de geïnstalleerde
`_internal/notices`-map. De eigen applicatiecode blijft MIT.

## Toegevoegd in 0.5

- **Whisper Small**: optionele lokale Nederlandse tekstherkenning via sherpa-onnx.
  De modellen zijn de INT8-ONNX-conversies uit de officiële sherpa-onnx-release
  `sherpa-onnx-whisper-small.tar.bz2`. De geselecteerde bestanden zijn gepind op
  SHA-256 in `multitrack/ad_text.py`; de downloader controleert elk bestand.
  Whisper-code en -gewichten zijn MIT: https://github.com/openai/whisper/blob/main/LICENSE.
  Een kopie staat in `docs/licenses/whisper-MIT.txt`. De trainingsdata worden niet meegeleverd.
- De korte herkenningszinnen en hun bronverwijzingen staan in `multitrack/ad_text.py`.
  Het is een beperkte lijst herkenningsaanwijzingen, geen archief van complete reclamescripts.
- Audio in de lokale reclamebibliotheek wordt door de gebruiker toegevoegd. De app
  publiceert die voorbeelden niet en bevat geen audio uit de uploads van deze chatsessie.
