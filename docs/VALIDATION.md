# Validatie van versie 0.2

Uitgevoerd op 31 oktober 2026 in Linux x86_64, Python 3.12.14, FFmpeg 7.1.5,
5 CPU-threads (maximaal 4 modelthreads), geen CUDA-GPU. Functionele tests zijn geen
nauwkeurigheidsbenchmark voor radioherkenning of bewijs dat een artiest is geïsoleerd.

## Resultaten

- **33 pytest-tests geslaagd**, inclusief echte modellen; geen modeltests overgeslagen
  in de volledig geïnstalleerde testomgeving.
- De basis blijft werken zonder PyTorch. De gedocumenteerde extra installatie is
  vervolgens in een schone basisomgeving uitgevoerd: PyTorch 2.8.0+cpu en torchaudio
  2.8.0+cpu, zonder SpeechBrain. Beide nieuwe downloaders zijn daadwerkelijk uitgevoerd
  met checksumcontrole. Modelbestanden staan buiten Git.
- Echte **HDemucs**-inferentie op spraak met toegevoegd instrumentaal testsignaal,
  48 kHz stereo: eindige vocals-/muziek-uitvoer, oorspronkelijke samplefrequentie,
  kanalen en lengte behouden. Vocals plus muziek reconstrueren de bron binnen 1e-7.
  Deze test bewijst geen perfecte isolatie van gezongen tekst uit een vergadering.
- Echte **Conv-TasNet**-inferentie op een mengsel van twee stemmen: twee verschillende
  eindige bronnen met de juiste lengte. Beide nieuwe modellen laden alleen lokale
  gewichten; Python-netwerkverbindingen waren tijdens deze inferentietests verboden.
- Achtergrond/rest blijft behouden bij stilte in de sprekerdetectie en tussen
  spreekmomenten. Bij niet-gescheiden overlap wordt de mix over sprekers verdeeld,
  zodat die niet dubbel wordt opgeteld. Alle bronstems samen reconstrueren de originele mix.
- Alle vier exportkeuzes zijn op bekende stems gecontroleerd, inclusief uit/aan-keuzes
  in het XML-project, `cleaned.wav`, `removed.wav`, ZIP-integriteit, herhaald wijzigen
  en terugkeren naar de oorspronkelijke mix zonder model-inferentie.
- Een lege radiostem-selectie wordt geweigerd als “volledige radio weglaten” zou worden
  gekozen zonder referentie. Ontbrekende modellen en onbekende labels geven duidelijke fouten.
- De optionele referentieroute is getest met een bekende synthetische akoestische
  menging (echo + onafhankelijke stemachtige ruis): meer dan 6 dB verbetering tegen de
  bekende bron, en `cleaned + radio == original` binnen float-afronding. Verkeerde
  referenties worden afgewezen; negatieve offsets en handmatig opgegeven starts ná
  de eerste 90 seconden zijn getest. Geen echte vergadering/radio-opname gebruikt.
- Upload van een optionele referentie, lege upload, annuleren vóór ontvangst en
  vrijgeven van de verwerkingsplek zijn getest.
- Alle bestaande MP4-/sprekerfunctionaliteit blijft getest: host/header-beveiliging,
  bestandstoegang, uploadlimieten, ongeldige media, video zonder audio, herstart,
  annuleringssignaal, echte 0,5 seconde audio-offset, vier gevraagde sprekerclusters,
  echte overlapdetectie met twee gemengde stemmen, geen verzonnen sprekers bij stilte,
  volledige MP4 → worker → ZIP en HTTP Range voor audioplayers.
- **Chromium end-to-end:** H.264/AAC MP4 van ongeveer 12 seconden uploaden, echte
  muziekscheiding en sprekeranalyse, cluster 2 expliciet als radio aanwijzen,
  “Volledige radio weglaten”, nieuwe worker-mix en Premiere-download, afspelen van de
  float-WAV, `removed.wav` aanwezig, mobiel formaat 390 px zonder horizontale overflow.
  Geen JavaScript-fouten en geen externe aanvragen door de pagina.
- Ruff, Python- en JavaScript-syntaxcontrole geslaagd.

In de browsertest is cluster 2 door de test gekozen. Dat is **geen automatische
herkenning van een zanger** en geen bewijs dat de stem van Michael Jackson in jouw
opname van de vergadering kan worden gescheiden. Die specifieke opname is niet
geanalyseerd. Een stem die met andere stemmen op dezelfde track blijft, kan niet
zonder verlies van die andere stemmen simpelweg worden weggemute.

## Grenzen / niet getest

- Radio- of muziekverwijdering op jouw eigen vergadering; luister `cleaned.wav` en
  `removed.wav` na en behoud het origineel. Niet-herkende zang en radio kunnen in de
  achtergrond/rest of op vergadertracks blijven zitten.
- CUDA-snelheid, VRAM-gebruik, Windows/macOS, Apple Silicon en specifieke GPU-drivers.
- Daadwerkelijke XML-/WAV-import in Premiere of Clipchamp. XML-structuur, mediapaden en
  mute-keuzes zijn gecontroleerd; desktopeditors waren hier niet beschikbaar.
- Objectieve nauwkeurigheid op Nederlands, radiovervorming, muziek met zang, galm,
  langdurige overlap, meer dan twee stemmen tegelijk of urenlange bestanden.
- Echte SpeechBrain/SepFormer-gewichten (oudere fallback). De nieuwe Conv-TasNet-route
  heeft geen Hugging Face-toegang nodig en is wel met gewichten getest.
- De bijgewerkte GitHub Actions-workflows staan in de repository; remote CI-succes
  wordt pas geclaimd na een daadwerkelijk waargenomen run. De resultaten hierboven
  zijn van de lokale cloudmachine.

Automatisch tellen kan extra clusters maken. In een eerdere gecodeerde variant van de
vier-sprekers-fixture werden zeven clusters gevonden; geef het werkelijke aantal op
wanneer je het weet. Kunstmatig gemengde stemmen leverden echte overlapregio's op,
maar niet alle gemengde momenten werden herkend. Drempels zijn heuristieken, geen
gevalideerde zekerheidspercentages.

Er is een upstream Starlette-deprecatiewaarschuwing over HTTPX in de tests. Optioneel
SpeechBrain meldt op torchaudio 2.8 ook een backend-deprecatiewaarschuwing; daarom zijn
torch en torchaudio bewust samen op 2.8.0 gehouden.

## Herhalen

Installeer de basis en beide extra modellen volgens README, download de openbare
spraakfixture via `scripts/download_test_audio.py` en voer `python -m pytest -q` uit.
Bij ontbrekende runtime, modellen of fixture worden de betreffende tests overgeslagen;
een run met skips bewijst dus niet dat echte modelinferentie is getest. Zie ook
`scripts/browser_smoke.py --help` voor de browsercontrole.
