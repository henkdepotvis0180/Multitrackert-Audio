# Wat moet ik per versie installeren?

**Huidige bronversie: 0.3.0.** Kijk op de website bij **Versie & installatie** om te zien
welke versie je daadwerkelijk draait, wat aanwezig is en wat nog ontbreekt.
Kies daar Windows, Linux of macOS en CPU of NVIDIA voor passende commando's.
De website installeert niets automatisch.

## Windows: alleen een installer downloaden

Download de **[Windows CPU-installer 0.3.0](https://github.com/henkdepotvis0180/Multitrackert-Audio/releases/download/v0.3.0/Multitrackert-Audio-Setup-0.3.0-CPU-x64.exe)** (circa 615 MB).
Andere versies vind je bij [GitHub Releases](https://github.com/henkdepotvis0180/Multitrackert-Audio/releases). De
installer bevat Python, FFmpeg, de bibliotheken en alle drie modellen. Je hoeft de
losse commando’s hieronder dan niet uit te voeren. Verschijnt er nog geen `.exe`,
dan is de Windows-build nog niet geslaagd. De installer is niet digitaal ondertekend.

Nieuwe installers vervangen de oude geïnstalleerde app. Je opnames en exports staan
buiten de installatiemap en blijven behouden, ook bij de-installatie. Een bestaande
standaardmap uit de Python-versie wordt hergebruikt. De website toont het opslagpad
en kan de lokale uitvoermap openen na een onderbroken browserdownload.

## Overzicht

| Versie | Nodig voor de basis | Extra voor muziek/radio en stemmen | Wat opnieuw installeren? |
| --- | --- | --- | --- |
| **0.1.0** | Python 3.12 (64-bit), FFmpeg + ffprobe, `requirements.lock`, basismodellen (~45 MB) | Oude optionele SpeechBrain/SepFormer-route | Bij nieuwe installatie alles in de basiskolom. Upgrade voor de nieuwere functies naar 0.3.0. |
| **0.2.0** | Dezelfde basis als 0.1.0; installeer de requirements uit de nieuwe broncode en werk het app-pakket bij | Voor muziek: PyTorch **2.8.0** + torchaudio **2.8.0**, HDemucs (~320 MB). Voor overlap: Conv-TasNet (~20 MB) | Vanaf 0.1: code bijwerken, requirements controleren, app bijwerken; alleen de gewenste extra's installeren. Bestaande basismodellen behouden. |
| **0.2.1** | Dezelfde basis als 0.2.0 | **Dezelfde** runtime en modellen als 0.2.0 | Vanaf 0.2.0: alleen broncode/app bijwerken; geen nieuwe modeldownloads. Deze versie voegt het versie- en installatieoverzicht toe. |
| **0.3.0 — Windows CPU-installer** | Alles inbegrepen in de `.exe` | Geen losse installatie nodig; CUDA blijft via de bronversie | Nieuwe `.exe` installeren: programmabestanden worden vervangen, projectdata blijft staan. |
| **0.3.0 — bronversie** | Dezelfde basis als 0.2.1 | Dezelfde extra modellen als 0.2 | Alleen code/app bijwerken; geen nieuwe modellen. |

**Muziek en radio zijn optioneel.** Zonder de extra's kun je de lokale website,
spreker-tijdlijn en achtergrond/rest-export gebruiken. Voor de radio-/muziekkeuzes
installeer je de audio-runtime en het muziekmodel. Voor stemmen die tegelijk praten
is daarnaast het overlapmodel nodig. Ook daarmee blijft perfecte stemisolatie onzeker.

De bestaande SpeechBrain-installatie hoef je niet te verwijderen. De nieuwe
Conv-TasNet-route heeft geen SpeechBrain, Hugging Face-account of token nodig.
Heb je nog torch/torchaudio 2.5.1 uit een oude installatie? Werk **beide** bij naar
2.8.0 met de commando's hieronder als je de nieuwe audiofuncties wilt gebruiken.

## Ik werk een bestaande broninstallatie bij

Stop de server met `Ctrl+C`. Haal de nieuwste code op met `git pull` als je de
repository hebt gecloned. Anders download je de nieuwste repository-ZIP van GitHub;
bewaar je bestaande `models/`, `.venv/` en je eigen opnames/datamap.
Voer daarna in de projectmap uit:

**Windows / PowerShell:**

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\start.bat
```

**Linux / macOS:**

```sh
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
./start.sh
```

Bestaande passende dependencies blijven aanwezig. **Voer de modeldownloaders niet
opnieuw uit als je die modellen al hebt.** Controleer na herstart bovenaan de website
of er **0.3.0** staat. Vernieuw de browserpagina; bij oude opmaak eventueel `Ctrl+F5`.

## Ik heb 0.1.0 en wil de muziek-/radiofuncties

Werk eerst de code en app bij zoals hierboven. Installeer vervolgens alleen de
extra's die nog ontbreken. De basismodellen van 0.1.0 blijven bruikbaar.

**Windows / PowerShell, CPU:**

```powershell
.\.venv\Scripts\python.exe -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe scripts/download_music_model.py
.\.venv\Scripts\python.exe scripts/download_overlap_model.py
.\start.bat
```

**Linux, CPU:**

```sh
.venv/bin/python -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python scripts/download_music_model.py
.venv/bin/python scripts/download_overlap_model.py
./start.sh
```

**macOS / Apple Silicon, CPU:** gebruik voor de runtime
`.venv/bin/python -m pip install torch==2.8.0 torchaudio==2.8.0` en dezelfde twee
downloadopdrachten. De extra modellen gebruiken hier CPU, geen Metal/MPS. PyTorch 2.8
biedt geen standaard macOS Intel-wheels; voor zo'n Mac is deze extra-modelconfiguratie
niet ondersteund. De basis zonder PyTorch staat daarvan los.

**NVIDIA op Windows/Linux:** kies op de website NVIDIA om het commando voor
`https://download.pytorch.org/whl/cu128` te zien. Daarvoor is een geschikte driver
nodig. Bij omschakelen tussen een bestaande CPU-/CUDA-build laat de website bewust
`--force-reinstall` zien zodat de gewenste build ook echt wordt geïnstalleerd.
Kies bij twijfel CPU; GPU-hardware is niet vereist. De GPU-route is nog niet op
GPU-hardware getest.

Oude exports moet je opnieuw analyseren om de nieuwe achtergrond-/muziektracks te
krijgen. De oorspronkelijke opname blijft je referentie. Er zijn geen nieuwe
basismodellen nodig.

## Ik installeer de tool voor het eerst

Volg [Basis installeren in README](README.md#basis-installeren). Die stappen maken
ook de `.venv` aan. Kies daarna de gewenste extra audiomodellen volgens die README
of het overzicht hierboven. De losse upgradecommando's werken pas als de basis en
virtuele omgeving bestaan.

## Hoe lees ik het overzicht op de website?

- **Aanwezig:** opnieuw installeren is niet nodig. Het commando staat ingeklapt als
  je het toch wilt bekijken.
- **Ontbreekt — nodig voor de basis:** installeer dit eerst.
- **Nog nodig voor deze optionele functie:** de basis werkt, maar de bijbehorende
  extra muziek-/stemfunctie nog niet. De runtime-rij toont ook afwijkende versies.
- Een modelbestand dat aanwezig is hoeft niet nogmaals te worden gedownload. Zijn
  checksum wordt bij gebruik gecontroleerd; aanwezigheid is geen integriteitscontrole.

Stop de server vóór installatie en start hem erna opnieuw, zodat de nieuwe
bibliotheken worden ingeladen. Internet is alleen voor installatie/download nodig;
je MP4 wordt niet naar een modelhost verstuurd. Windows/macOS-commando's zijn
beschreven, maar alleen Linux-installatie en browserflow zijn hier gevalideerd.
