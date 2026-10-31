# Validatie van versie 0.1

Uitgevoerd op 31 oktober 2026 in Linux x86_64, Python 3.12.14, FFmpeg 7.1.5,
5 CPU-threads (2–4 inferentiethreads), geen CUDA-GPU. Dit is functionele validatie,
geen nauwkeurigheidsbenchmark voor sprekers of stemisolatie.

## Geslaagd

- Installatie vanuit `requirements-dev.lock` in een nieuwe virtuele omgeving, gevolgd
  door `pip install --no-deps -e .`. Ook installatie zonder PyTorch/SpeechBrain werkt.
- De gedocumenteerde basismodeldownload, herhaald met vaste SHA-256-controle.
- **16 pytest-tests geslaagd, 1 overgeslagen** in de volledige suite:
  - lokale host-/clientbeperking, schrijfheader, ontbrekende modellen, uploadlimieten,
    lege uploads, ongeldige spreker-aantallen en afscherming van bestanden;
  - één actieve opdracht, annuleringssignaal en herstel van onafgeronde opdrachten
    na serverherstart;
  - echte FFmpeg-demux met audio die pas 0,5 seconde na de video begint: de vertraging
    blijft behouden in de volledige WAV; de video-export bevat geen audiostream;
  - ongeldige MP4 en video zonder audio worden afgewezen;
  - sample-exacte tracks en stiltes op een stereo testbron van 48 kHz, juiste
    overlappingsmarkering, clips, ZIP-integriteit en chronologische manifesten;
  - conservatieve toewijzing van twee bronnen aan sprekerreferenties en het weigeren
    van een ambigue toewijzing (hier zijn deterministische testdubbels gebruikt);
  - echte ONNX-inferentie op de officiële `0-four-speakers-zh.wav` fixture,
    een bestand zonder spraak, en een kunstmatig mengsel van twee echte stemmen;
  - echte MP4-upload via de API naar een workerproces, vier gevraagde clusters,
    veertien spreekfragmenten, volledige ZIP-download en afspelen via HTTP Range;
  - echte inferentie met Python-netwerkverbindingen geblokkeerd.
- Chromium-browser: upload van een H.264/AAC MP4, voortgang naar resultaat,
  sprekertracks, fragmententabel, decoderen van de float-WAV in de audio-player,
  mobiel formaat van 390 pixels zonder horizontaal overlopen.
- Geen JavaScript-fouten of externe aanvragen in de succesvolle browserrun.
- Ruff en JavaScript-syntaxcontrole geslaagd.
- PyTorch 2.8.0+cpu, torchaudio 2.8.0+cpu en SpeechBrain 1.0.3 importeren samen.

De vier clusters zijn expliciet opgegeven in de fixturetest; dit bewijst geen
foutloze automatische telling of identiteit. Automatisch tellen maakte bij een
andere gecodeerde variant van deze opname zeven clusters: automatische oversegmentatie
is dus een bekende beperking. Geef het werkelijke aantal op wanneer je het kent.
Het gemengde fragment leverde enkele echte overlapregio's op, maar niet ieder gemengd
moment werd als overlap herkend. De interface en manifesten waarschuwen hiervoor.

## Niet geclaimd als getest

- **Echte SepFormer-inferentie: 1 test overgeslagen.** De cloudproxy weigert de modelhost
  `huggingface.co` met HTTP 403. Daarom ontbreken de optionele gewichten. De runtime
  importeert en de scheidings-/toewijzingslogica heeft deterministische tests, maar
  scheidingskwaliteit of echte end-to-end modelcompatibiliteit is hiermee niet bewezen.
- CUDA-inferentie / snelheid / VRAM-gebruik: geen GPU beschikbaar.
- Installatie op Windows of macOS, Apple Silicon of specifieke NVIDIA-drivers.
- Import van XML of WAV-bestanden in Premiere/Clipchamp zelf; die editors zijn hier
  niet beschikbaar. Het XML-bestand heeft relatieve mediapaden en kan relinken vereisen.
- Nauwkeurigheid op Nederlandse vergaderingen, muziek, galm, rumoer, veel sprekers,
  lange opnames of meer dan twee stemmen tegelijk; daarvoor ontbreekt een gelabelde
  representatieve testset.
- GitHub Actions is toegevoegd; een geslaagde remote Actions-run is pas bevestigd
  wanneer GitHub die uitvoert. De hierboven genoemde tests zijn lokaal in de cloud gedraaid.

Er is één upstream deprecatiewaarschuwing van Starlette over HTTPX in de tests.
SpeechBrain geeft op torchaudio 2.8 daarnaast een deprecatiewaarschuwing voor
`list_audio_backends`; daarom is torchaudio bewust niet naar 2.9 opgehoogd.

## Herhalen

Zie de README voor installatie en testcommando's. De spraakfixture wordt apart
met checksum gedownload via `scripts/download_test_audio.py`; geen opgenomen audio
of modelgewichten staan in Git. `test_real_separator_local_inference` wordt alleen
gedraaid wanneer ook het optionele model lokaal is geïnstalleerd.
