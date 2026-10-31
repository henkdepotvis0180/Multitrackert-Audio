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

## Aanvulling 0.2.1: installatieoverzicht

Deze patch verandert de audioverwerking of dependencies niet. De 6 bestaande
API-tests zijn geslaagd. Het package is gebouwd en gecontroleerd op versie 0.2.1
en aanwezigheid van de installatiecode en websitebestanden. De versie komt nu uit
één bron (`multitrack.__version__`) voor package en website.

Chromium-controles: juiste actieve versie, zes installatiechecks, aanwezige en
ontbrekende onderdelen, Windows-/Linux-/macOS-commando's, CPU-/CUDA-keuze en mobiel
formaat. Ontbrekende modellen openen het overzicht; aanwezige modellen worden niet
opnieuw als vereiste download aangeboden. Geen JavaScript-fouten. Dit valideert de
weergave van de commando's, niet installatie op Windows/macOS of een GPU-machine.

## Aanvulling 0.3: zelfstandige app en blijvende lokale uitvoer

- **36 tests geslaagd** met de eigen minimale FFmpeg 7.1.5-build, inclusief echte
  modellen, MP4-verwerking en de drie nieuwe opslag-/hersteltests.
- Een nieuwe browsersessie vindt dezelfde volledige ZIP en bron-MP4 terug. Een
  ZIP-download is in twee HTTP Range-aanvragen gereconstrueerd. Projectnamen zijn
  metadata en kunnen geen andere bestandslocaties veroorzaken.
- Een bestaande standaarddatamap uit de bronversie wordt hergebruikt; de standaardmap
  van de Windows-installer staat buiten de programmamap. De code weigert expliciet
  een datamap binnen de standalone-installatiemap.
- De zelfstandige verpakking is lokaal daadwerkelijk gebouwd en uitgevoerd: modellen,
  verwerkingssubprocessen, mix, ZIP-integriteit, downloadhervatting, opgeslagen uitvoer,
  installerweergave in de browser en afsluiten via de website. Deze lokale frozen
  controle is Linux, niet Windows.
- De eerste native Windows-build publiceerde geen installer omdat de pakketcontrole
  een ontbrekende SciPy-module vond. Het pakket verzamelt nu ook de dynamische
  `scipy._external`-modules; de fout is lokaal gereproduceerd en opgelost.
- De Windows-workflow controleert daarnaast de werkelijke Windows-executable en
  installer: installeren, een lopende app bijwerken, oude programmabestanden opruimen,
  mediachecksums behouden en de-installeren zonder projectdata te verwijderen. Alleen
  een volledig geslaagde workflow publiceert een release-preview. Controleer de
  [actuele Windows-build](https://github.com/henkdepotvis0180/Multitrackert-Audio/actions/workflows/windows-installer.yml)
  voor het resultaat van die native checks.

De installer is CPU-only en niet digitaal ondertekend. De controle gebruikt een
GitHub-hosted Windows-machine, geen schone eigen Windows-pc zonder reeds aanwezige
Microsoft-runtime. CUDA blijft via de broninstallatie beschikbaar en is niet op een
GPU getest. De kwaliteitsgrenzen van muziek-/radio-/stemmenscheiding blijven gelden.

### Bevestigde Windows-release 0.3.0

De [native Windows-workflow](https://github.com/henkdepotvis0180/Multitrackert-Audio/actions/runs/41221439336)
is volledig geslaagd en heeft de Windows CPU-installer gepubliceerd. Dit omvat de
Windows-testsuite, echte gebundelde modellen, frozen verwerkingsprocessen, ZIP en
HTTP Range, installatie, een lopende app bijwerken, oude binaries verwijderen en
mediachecksums na update én de-installatie behouden. De installer en checksum staan
bij [release v0.3.0](https://github.com/henkdepotvis0180/Multitrackert-Audio/releases/tag/v0.3.0).

Een latere optimalisatie laat onnodige C++-ontwikkelheaders weg en gebruikt snellere
verliesloze installercompressie. De compacte verpakking is ook lokaal als echte
standalone-app met modellen en verwerkingssubprocessen getest. Bestaande gepubliceerde
releasebestanden worden nooit stilzwijgend overschreven.

## Aanvulling 0.3.1: Windows-statusbestanden en foutlogs

- Lokaal: **45 tests geslaagd, 2 Windows-specifieke tests overgeslagen**. De echte
  modeltests zijn uitgevoerd. Ook de HTTP-download van het foutlog is gecontroleerd
  op ZIP-integriteit, bestandsnaam en het uitsluiten van mediabestanden.
- De [native Windows-workflow](https://github.com/henkdepotvis0180/Multitrackert-Audio/actions/runs/41240362988)
  heeft de volledige testsuite en de werkelijke verpakte app succesvol uitgevoerd.
  De regressietests houden een leeshandle open tijdens vervanging, bootsen een
  tijdelijke Windows-blokkade na en laten meerdere threads en processen tegelijk
  status schrijven. Een blijvende schrijffout behoudt de vorige geldige status.
- Installeren, een draaiende app bijwerken, verouderde programmabestanden verwijderen
  en de-installeren zijn geslaagd. Opgeslagen WAV-, MP4- en ZIP-bestanden behielden
  hun SHA-256-checksums na update en de-installatie.

Dit controleert de Windows-bestandsvergrendelingsfout, niet iedere mogelijke oorzaak
van geweigerde toegang op een gebruikers-pc. Als Windows een bestand blijvend blokkeert,
kan het foutlog helpen de resterende oorzaak te onderzoeken.

De volledige Windows-workflow en publicatie zijn geslaagd. De gepubliceerde
[installer 0.3.1](https://github.com/henkdepotvis0180/Multitrackert-Audio/releases/tag/v0.3.1)
is opnieuw gedownload (850.787.017 bytes) en komt overeen met de gepubliceerde SHA-256:
`5bedc8e6083e23a7f9b175a7f1fcb4d28724292b176d03023c1e43fb3f574f4e`.
