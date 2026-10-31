# Multitrackert Audio

Een lokale website om een MP4 om te zetten naar een **tijdlijn per spreker**.
Je opname blijft op de computer waarop je de app start. De website gebruikt geen
cloud-API, CDN, externe lettertypes of tracking. Nederlands is de interfacetaal;
sprekerherkenning werkt op stemkenmerken en maakt geen transcriptie.

**Status: geteste basis, geen garantie op perfecte stemisolatie.** Sprekerherkenning
(diarisatie: wie spreekt wanneer) en het scheiden van stemmen die tegelijk klinken
zijn verschillende taken. De basis maakt tijdvaste sprekertracks; daarin blijft
bij overlap de mix hoorbaar. De optionele SepFormer-stap probeert twee gelijktijdige
stemmen te scheiden. Deze adapter is experimenteel en kon in de ontwikkelcloud niet
met echte gewichten worden getest, omdat de modelhost geblokkeerd is. Hij staat
standaard uit. Zie [testresultaten](docs/VALIDATION.md).

## Wat je krijgt

- MP4-upload naar **je eigen lokale server**, maximaal 4 GiB / 60 minuten.
- Automatisch aantal sprekers, of zelf 1–12 opgeven; mono en stereo.
- Fasevoortgang, verstreken tijd, geschatte resterende tijd **voor de huidige fase**,
  annuleren en terugvinden/verwijderen van eerdere opdrachten.
- Hardwarecontrole: CPU-threads, vrij RAM, FFmpeg en optioneel een bruikbare CUDA-GPU.
- Een visuele spreker-tijdlijn met afspelen van het origineel en losse tracks.
- ZIP met beeld zonder audio, originele audiomix, volledige spreker-WAVs, genummerde
  fragmenten, CSV/JSON met tijdcodes en een experimenteel Premiere/FCP7-XML-project.
- Originele samplefrequentie en mono/stereo-indeling blijven behouden voor gewone
  spreekmomenten. WAV is 32-bit float; dit voorkomt extra verlies bij export, maar
  herstelt geen informatie die al door AAC/MP4-compressie verloren is gegaan.

## Installeren — eenmalig met internet

Benodigd: **Python 3.12 (64-bit)** en **FFmpeg inclusief ffprobe op PATH**.
Voor CPU-gebruik is geen account, API-sleutel of betaalde dienst nodig.
Reken op minimaal 8 GB RAM en voldoende vrije schijfruimte. Volledige WAV-tracks en
een ZIP kunnen veel groter zijn dan de MP4; de app controleert dit vooraf conservatief.

FFmpeg installeren, bijvoorbeeld:

- Windows: `winget install Gyan.FFmpeg` (open daarna een nieuwe terminal).
- macOS: `brew install ffmpeg`.
- Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y ffmpeg`.

Clone of download deze repository en open een terminal in de projectmap.

**Windows (PowerShell):**

```powershell
git clone https://github.com/henkdepotvis0180/Multitrackert-Audio.git
cd Multitrackert-Audio
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe scripts/download_models.py
.\start.bat
```

**Linux / macOS:**

```sh
git clone https://github.com/henkdepotvis0180/Multitrackert-Audio.git
cd Multitrackert-Audio
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python scripts/download_models.py
./start.sh
```

De modeldownload is ongeveer 45 MB, verifieert vaste SHA-256-checksums en haalt geen
gebruikersbestanden op. De checksums zijn vastgelegd na de eerste download vanaf de
officiële GitHub-release via HTTPS. De modellen worden niet met de repository meegestuurd.

Open vervolgens **http://127.0.0.1:8765** op dezelfde computer. Bij volgende starts
volstaat `start.bat` of `./start.sh`. Internet kan dan uit. Stoppen: `Ctrl+C` in de terminal.
Een andere poort kan met `.venv/bin/python -m multitrack.cli --port 8766` (op Windows de
Python in `.venv\Scripts` gebruiken).

De backend is in Linux getest; Windows/macOS-installatie-instructies zijn nog niet op
die besturingssystemen gevalideerd. Apple Silicon werkt via CPU; Metal/MPS wordt niet gebruikt.

## De tijdlijn in je editor zetten

1. Download de ZIP en pak **de hele map** uit.
2. Importeer `video.mp4` en alle bestanden in `speakers/`.
3. Plaats de video en **elke volledige speaker-WAV op tijdstip 00:00:00** in aparte tracks.
   Iedere WAV bevat de benodigde stilte en evenveel samples; je hoeft dus geen losse
   fragmenten terug te schuiven.
4. Gebruik `original.wav` alleen als referentie. Tegelijk afspelen met de sprekertracks
   verdubbelt geluid; ook niet-gescheiden overlap op meerdere tracks kan harder klinken.
5. Voor losse fragmenten: `clips/00001_speaker_01_...wav`, `00002_...`, enzovoort staan
   in chronologische volgorde. `segments.csv` en `timeline.json` geven de originele posities.
   **Losse clips achter elkaar plakken bewaart de stiltes/tijdposities niet.**

Premiere kan daarnaast `timeline.xml` proberen te importeren. Wijs bij ontbrekende media
de bestanden uit dezelfde uitgepakte map aan. XML-import is hier niet in Premiere
gevalideerd; stereo kanaalindeling en variabele framerate kunnen handmatige correcties
vragen. De volledige WAVs op tijdstip 0 zijn de primaire route. Clipchamp heeft geen
geteste XML-import; plaats daar de volledige tracks handmatig op 0. Ondersteunde
trackaantallen en WAV-import hangen ook van de editorversie af.

`timeline.json` vermeldt bij elke gedetecteerde overlap of die daadwerkelijk is gescheiden
(`separated_8khz`) of nog de originele mix bevat (`mixed`). Een ontbrekende overlapmelding
betekent **niet** dat er zeker geen overlap in de opname zit: de herkenner kan iets missen.

## Optioneel: twee overlappende stemmen scheiden

**Experimenteel / niet met echte modelgewichten gevalideerd in deze cloud.** Deze stap
is niet nodig voor de gewone tijdlijn-export. Je kunt de basis dus eerst gebruiken.

Installeer een bij elkaar passende PyTorch/torchaudio 2.8.0 build, daarna SpeechBrain.
Gebruik op Windows de Python in `.venv\Scripts` in plaats van `.venv/bin/python`.

CPU, ook zonder GPU:

```sh
.venv/bin/python -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r requirements-separation.txt
.venv/bin/python scripts/download_separator.py
```

NVIDIA, met geschikte driver voor CUDA 12.8:

```sh
.venv/bin/python -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
.venv/bin/python -m pip install -r requirements-separation.txt
.venv/bin/python scripts/download_separator.py
```

Voor een nieuwere GPU die niet door deze PyTorch-build wordt ondersteund: gebruik
voorlopig de CPU-build. De GPU-route is hier niet getest. Combineer geen verschillende
PyTorch- en torchaudio-versies. Herstart na installatie de server.

`download_separator.py` haalt alleen modelbestanden van
[`speechbrain/sepformer-wsj02mix`](https://huggingface.co/speechbrain/sepformer-wsj02mix),
controleert eerst of de modelkaart `apache-2.0` aangeeft en legt de exacte modelrevision
en gedownloade bestandschecksums lokaal vast. Er worden geen opnames verstuurd.
Voor deze optionele installatie zijn `huggingface.co` en mogelijk de downloadhost
`cas-bridge.xethub.hf.co` nodig. Tijdens verwerking staan Hugging Face en Transformers
in offline-modus; er is geen automatische download bij uploaden.

Werking en grenzen:

- De standaard ONNX-herkenner gebruikt CPU, ook op een pc met GPU. CUDA wordt voor de
  optionele zware scheidingsstap gebruikt als PyTorch die GPU kan gebruiken en er minimaal 4 GB VRAM vrij is.
  Met “CPU forceren” kun je een GPU met onvoldoende geheugen omzeilen.
- Alleen gedetecteerde regio's met **precies twee** actieve sprekers worden gescheiden.
- Schone spreekmomenten van minimaal 1 seconde dienen als stemreferenties. Zonder
  bruikbare referenties of bij een onduidelijke match blijft de mix behouden en krijgt
  het manifest een waarschuwing. Sprekers die altijd tegelijk praten kunnen dus niet
  betrouwbaar worden toegewezen.
- SepFormer is getraind op WSJ0-2Mix (Engelse, gesimuleerde mengsels), **8 kHz mono**.
  De gescheiden regio wordt naar de bronsamplefrequentie teruggerekend; dat maakt het
  geen echte 48 kHz-stemisolatie. Bij stereo staat die regio op beide kanalen.
- Het model kan ruis, muziek, galm, onbekende talen, korte stemmen en drie of meer
  gelijktijdige stemmen slecht behandelen. Verkeerde labels, stemlekkage en hoorbare
  artefacten blijven mogelijk. Drempels voor identiteit zijn heuristieken, geen
  gevalideerde zekerheidspercentages. Luister resultaten altijd na.
- Scheiding gebeurt in stukken van maximaal 8 seconden met extra context; daardoor
  blijft modelgeheugen begrensd. Overgangen tussen stukken kunnen hoorbaar zijn.
- Het origineel blijft beschikbaar, ook voor spraak die de modellen niet detecteren.

## Privacy, opslag en limieten

De server bindt uitsluitend op `127.0.0.1`. Geen account nodig. Alleen lokale clients en
verwachte hostnamen worden geaccepteerd; schrijfaanvragen vereisen een lokale header
zonder CORS-toestemming voor andere websites. Start **één serverproces**, geen meerdere
workers. Eén verwerking tegelijk voorkomt GPU-/RAM-concurrentie; er is geen wachtrij.

Uploads, exports en logs staan standaard in `~/.multitrackert/jobs/`. Verwijderen in
de website verwijdert de hele opdracht, inclusief bron en ZIP. Bij een serverherstart
worden onafgeronde opdrachten gemarkeerd als onderbroken; upload ze opnieuw. Annuleren
gebeurt bij het volgende controlepunt: een lopende FFmpeg- of modelstap kan eerst nog
even doorwerken. Er zijn geen automatische meldingen buiten de website; de pagina
toont duidelijk wanneer je download klaarstaat.

Optionele omgevingsvariabelen:

| Naam | Betekenis |
| --- | --- |
| `MULTITRACK_DATA` | Andere lokale datamap, liefst een absolute locatie |
| `MULTITRACK_MODELS` | Andere modelmap; standaard `models/` in deze checkout |
| `MULTITRACK_MAX_BYTES` | Uploadlimiet in bytes; standaard 4294967296 |
| `MULTITRACK_TEST_AUDIO` | WAV-fixture voor de echte modeltests |

MP4 gebruikt de eerste video- en audiostream; extra taaltracks worden niet gecombineerd.
Mono/stereo met 8–192 kHz wordt ondersteund. Media met meer kanalen moet je eerst zelf
naar de gewenste mix omzetten. GPU wordt niet gebruikt voor video: de videostream wordt
zonder herencoding gekopieerd. Volledige audiotracks worden blokgewijs geschreven;
voor herkenning staat de mono 16 kHz-analyse wel in RAM. De schijfruimtecontrole houdt
rekening met maximaal twaalf tracks, clips en ZIP; die is bewust ruim en kan een lange
opname afwijzen die met minder sprekers wel zou passen.

## Testen en ontwikkelen

```sh
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pytest -q -m 'not models'
# Echte inferentie en MP4 → API → ZIP, na de eenmalige modeldownload:
.venv/bin/python scripts/download_test_audio.py
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

De modeltests slaan over wanneer de modellen of spraakfixture ontbreken; een run met
skips is dus geen bewijs dat echte inferentie is getest. De fixture is een openbaar
voorbeeld van sherpa-onnx, geen gebruikersopname. Hij wordt niet in deze repository
opgenomen. GitHub Actions draait ook de echte modeltests.

Browsercontrole (optioneel): installeer `playwright`, daarna `python -m playwright install chromium`.
Start de server en voer `python scripts/browser_smoke.py pad/naar/spraak.mp4` uit. Voor
systeem-Chromium: `--chromium /usr/bin/chromium`. Dit test upload, resultaatweergave,
WAV-decoding, mobiel formaat en dat de pagina geen externe aanvragen doet.

## Gratis commercieel gebruiken

De eigen applicatiecode is **MIT**. De meegeleverde dependencykeuze en de basis-modellen
hebben licenties die commercieel gebruik toestaan, zonder abonnement of verwerkingstarief.
Behoud de licentieteksten en notices bij doorlevering. FFmpeg wordt apart geïnstalleerd;
de precieze LGPL/GPL-verplichtingen hangen af van jouw FFmpeg-build. Dat verbiedt op
zichzelf geen commercieel gebruik. De optionele scheider wordt alleen gedownload na
controle op Apache-2.0-modelmetadata. Zie [licenties en bronnen](docs/THIRD_PARTY.md).
