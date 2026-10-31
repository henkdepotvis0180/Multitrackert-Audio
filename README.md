# Multitrackert Audio

Lokale MP4-verwerking met een tijdlijn per spreker, behoud van achtergrondgeluid,
optionele muziekscheiding en een instelbare Premiere-export. **Opnames blijven op je
computer.** Alleen de eenmalige installatie/modeldownload heeft internet nodig.

## Nieuw in 0.3: Windows-installer en lokale opslag

**[Download Windows CPU-installer 0.3.1 (.exe, circa 851 MB)](https://github.com/henkdepotvis0180/Multitrackert-Audio/releases/download/v0.3.1/Multitrackert-Audio-Setup-0.3.1-CPU-x64.exe)**

[Release, checksum en FFmpeg-broncode](https://github.com/henkdepotvis0180/Multitrackert-Audio/releases/tag/v0.3.1). De Windows-installatie-, update- en gegevensbehoudcontroles zijn geslaagd; de gepubliceerde download is op SHA-256 gecontroleerd.

De Windows CPU-installer bevat Python, FFmpeg en de modellen. Eenmalig de `.exe`
installeren; daarna opent de lokale website en zijn geen losse pip-/modelinstallaties
nodig. Alleen succesvolle, op Windows gecontroleerde builds worden als release geplaatst.
Staat er nog geen `.exe` bij Releases, dan is die build nog niet succesvol afgerond.
Deze preview is niet digitaal ondertekend; Windows kan een onbekende uitgever tonen.

Updates vervangen de oude programmabestanden, niet je opnames. Standaard bewaart de
installer projecten buiten de installatiemap in `%LOCALAPPDATA%\Multitrackert Audio\Data`.
Een bestaande `%USERPROFILE%\.multitrackert` wordt automatisch hergebruikt. Onbekende
oude broncode-/Python-mappen worden niet verwijderd, omdat daar gebruikersbestanden in
kunnen staan. Sluit de oude `.bat`-server vóór je de desktop-app opent.

De website toont **Open lokale opslagmap**, **Open lokale uitvoermap** en per opdracht
**Map**. De bron-MP4, video, WAVs en ZIP staan daar ook als een browserdownload afbreekt.
Je kunt de ZIP later opnieuw downloaden; HTTP Range ondersteunt gedeeltelijk hervatten.
De browser moet hervatten zelf ondersteunen; anders download je opnieuw of kopieer je
het reeds complete ZIP-bestand uit de lokale uitvoer-/projectmap.

```text
Projectenmap/
  jobs/
    <opdracht-id>/
      project.json          # oorspronkelijke bestandsnaam en aanmaakmoment
      input.mp4             # jouw bronopname
      result.zip            # complete download, onafhankelijk van de browser
      export/
        video.mp4
        original.wav
        background.wav
        music.wav           # als muziekscheiding aan stond
        speakers/*.wav
        cleaned.wav         # na het kiezen van een mix
        removed.wav
        timeline.xml
        timeline.json
        clips/*.wav
```

De uninstaller verwijdert de programmabestanden, **niet** deze projecten. Alleen de
knop “Verwijder” bij een opdracht verwijdert de bijbehorende opname en exports.
Installeer een update nadat de lopende verwerking klaar is: bijwerken sluit de app af.
Complete exports blijven behouden; een onderbroken verwerking kun je opnieuw uitvoeren.
De desktop-app stop je via **App afsluiten** op de website. Deze installer is CPU-only;
voor NVIDIA/CUDA blijft onderstaande broninstallatie beschikbaar.

## Nieuw in 0.2.1: installatie per versie

**[Wat moet ik per versie installeren? → INSTALLATIE.md](INSTALLATIE.md)**

De website toont nu de actieve versie en een installatiecheck met commando’s voor
Windows, Linux/macOS en CPU/NVIDIA. Versie 0.2.1 gebruikt dezelfde dependencies en
modellen als 0.2.0; voor deze update zijn geen nieuwe modeldownloads nodig.

## Nieuw in 0.2: muziek behouden of radio weglaten

De eerste versie exporteerde alleen herkende spreekmomenten. Daardoor ontbrak geluid
buiten die momenten. Versie 0.2 bewaart altijd **`background.wav`**, met niet-toegewezen
geluid en restverschillen. In combinatie met alle sprekertracks en optionele
muziek-/radiotracks is de originele mix weer te vormen, op float-afronding na.
Bij niet-gescheiden overlap wordt de mix verdeeld over de actieve sprekers, zodat die
niet meer dubbel zo hard wordt wanneer je alle tracks samen afspeelt.

Met de optionele Hybrid Demucs-muziekscheider komt **`music.wav`** erbij, ook onder
spreekmomenten. De website laat je daarna kiezen:

| Exportkeuze | Wat blijft aan? |
| --- | --- |
| Alles behouden | Alle sprekertracks, achtergrond en muziek |
| Alleen instrumentale muziek weglaten | Sprekertracks en achtergrond; zang kan blijven |
| **Volledige radio weglaten** (standaardkeuze) | Vergaderstemmen en achtergrond; muziek en door jou aangewezen radiostemmen staan uit |
| Alleen aangewezen radiostem/zang weglaten | Overige stemmen, achtergrond én muziek |

**Een radiozanger wordt niet automatisch op naam herkend.** Beluister na de analyse
de stemtracks en vink aan welke bij de radio/zang horen. De laatste twee keuzes
hebben die selectie nodig. De app weigert een lege selectie als “volledige radio
verwijderd” te behandelen. Voor alleen instrumentale muziek is die selectie niet nodig.
Je kunt de keuze later veranderen zonder opnieuw te analyseren.

Zang en vergaderstemmen kunnen samen op een track staan, vooral als ze door elkaar
praten. Die hele track verwijderen zou ook de vergadering verwijderen. Laat hem dan
aan en probeer opnieuw met de optionele stemmenscheider. Blijft het model die stemmen
mengen, dan is volledige radioverwijdering met deze opname **niet betrouwbaar gelukt**.
Ook achtergrond/rest kan gemiste zang of vergaderspraak bevatten. De tool belooft geen
perfecte isolatie van bijvoorbeeld Michael Jackson uit een vergadering.

## Bestaande installatie bijwerken

Stop eerst de server. Werk de broncode bij (`git pull` als je Git gebruikt; anders de
nieuwe repository-ZIP downloaden). Bewaar je eigen `models/` en datamap.
Start vervolgens opnieuw. Voor alleen behoud van achtergrond zijn geen nieuwe modellen
nodig. **Oude exports moet je opnieuw analyseren**: hun ontbrekende restgeluid kan niet
uit alleen de oude sprekertracks worden teruggehaald; de oude `original.wav` is wel volledig.

Voor muziek/radio: volg hieronder de eenmalige installatie van de extra audiomodellen.

## Basis installeren

Benodigd: **Python 3.12, 64-bit**, en **FFmpeg + ffprobe op PATH**.
Minimaal 8 GB RAM voor de basis; voor de optionele zware modellen liever 16 GB of meer.
Voldoende schijfruimte is belangrijk: volledige WAV-tracks, clips en ZIP zijn veel
groter dan de gecomprimeerde MP4. De app controleert ruimte en RAM vooraf.

FFmpeg installeren:

- Windows: `winget install Gyan.FFmpeg`, daarna een nieuwe terminal openen.
- macOS: `brew install ffmpeg`.
- Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y ffmpeg`.

Windows / PowerShell, in de projectmap:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe scripts/download_models.py
.\start.bat
```

Linux / macOS, in de projectmap:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python scripts/download_models.py
./start.sh
```

Open **http://127.0.0.1:8765** op dezelfde computer. Volgende keren volstaat `start.bat`
of `./start.sh`. Stop met `Ctrl+C`. De basismodeldownload is circa 45 MB en verifieert
vaste SHA-256-checksums. Geen account, token, cloud-API of betaalde dienst nodig.

De backend en browserflow zijn in Linux getest. Windows/macOS-installatie is nog niet
op die systemen gevalideerd. Apple Silicon gebruikt CPU; Metal/MPS is niet geïmplementeerd.

## Muziek en overlappende stemmen scheiden — extra modellen

De basis werkt zonder PyTorch. Voor muziek/radio en de nieuwe Conv-TasNet-stemmenscheider
installeer je eenmaal PyTorch/torchaudio en download je twee modellen. Dit vervangt de
noodzaak om het oude optionele SpeechBrain-model via Hugging Face op te halen.

**Windows, CPU (geen NVIDIA nodig):**

```powershell
.\.venv\Scripts\python.exe -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe scripts/download_music_model.py
.\.venv\Scripts\python.exe scripts/download_overlap_model.py
```

**Linux/macOS, CPU:**

```sh
.venv/bin/python -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python scripts/download_music_model.py
.venv/bin/python scripts/download_overlap_model.py
```

**NVIDIA, passende driver voor CUDA 12.8:** vervang bij de eerste opdracht de index
`https://download.pytorch.org/whl/cpu` door `https://download.pytorch.org/whl/cu128`.
Gebruik bij Windows de Python in `.venv\Scripts`. Herstart de server na installatie.
De GPU-route is nog niet op echte GPU-hardware getest; CPU-inferentie is wel uitgevoerd.

- Muziekmodel: circa 320 MB, `HDEMUCS_HIGH_MUSDB`, 44,1 kHz stereo.
- Stemmodel: circa 20 MB, `CONVTASNET_BASE_LIBRI2MIX`, twee stemmen, 8 kHz mono.
- Downloads alleen via de officiële PyTorch-host, met vaste SHA-256-checksums.
- Geen modeldownload tijdens een upload/verwerking. Weights laden alleen vanaf schijf;
  beide modellen worden vóór laden op checksum gecontroleerd.
- Standaard worden de extra opties aangevinkt als hun modellen lokaal gereed zijn.
  Je kunt ze uitzetten om sneller alleen een tijdlijn te maken.
- De ONNX-sprekerherkenner gebruikt CPU (maximaal vier modelthreads). De zware
  muziekscheiding en stemmenscheiding gebruiken CUDA als dat bruikbaar is met minimaal
  4 GB vrij VRAM, anders CPU. “CPU forceren” omzeilt een GPU met onvoldoende geheugen.
- Muziekverwerking gebruikt blokken van acht seconden met extra context; de volledige
  opname hoeft daarvoor niet tegelijk door het model. Langere verwerking op CPU is normaal.
- De bestaande optionele SpeechBrain/SepFormer-backend blijft als fallback ondersteund;
  Conv-TasNet krijgt voorrang als beide zijn geïnstalleerd. Zie `requirements-separation.txt`
  en `scripts/download_separator.py`. De SpeechBrain-gewichten zijn hier niet getest.

## Jouw vergadering: volledige radio proberen weg te laten

1. Kies de MP4. Zet **Muziek apart zetten** aan, en bij overlap ook **Overlappende stemmen scheiden**.
2. Kies zo mogelijk het werkelijke aantal verschillende stemmen, **inclusief de radiostem**.
   Automatisch tellen kan extra of te weinig clusters maken.
3. Start de analyse. De pagina toont de fase, verstreken tijd en een geschatte resterende
   tijd voor die fase. Volgende fases komen daarna; dit is geen exacte eindtijd.
4. Beluister de gevonden stemtracks. Vink alleen de radiostem/zang aan.
5. Kies **Volledige radio weglaten** en klik **Gekozen mix en Premiere-export maken**.
6. Luister naar `cleaned.wav` én `removed.wav`. Staat er vergaderspraak in wat is
   weggelaten, of blijft er zang over, pas de selectie aan of behoud het origineel.
7. Download de nieuwe ZIP of direct de gekozen mix. Andere exportkeuzes kun je daarna
   proberen zonder nieuwe inferentie; de oorspronkelijke losse stems blijven behouden.

Muziekscheiding maakt geen onderscheid tussen een zanger en vergaderstemmen. De
sprekerherkenner en stemmenscheider proberen die stemmen te onderscheiden, maar dat
werkt niet altijd, vooral bij voortdurend gelijktijdige stemmen, galm en radiovervorming.
Een stem die geen schone referentiemomenten in de opname heeft, kan bij overlap bewust
als mix blijven staan. De achtergrondtrack bewaart dan die rest in plaats van die weg te gooien.

## Weer samenvoegen in Premiere

De eenvoudigste route na het kiezen van een mix:

1. Pak de hele ZIP uit.
2. Plaats `video.mp4` op tijdstip **00:00:00**.
3. Plaats **alleen `cleaned.wav`** als volledige audiotrack ook op **00:00:00**.

Zo hoef je geen fragmenten te schuiven. Voor afzonderlijke bewerkbare sprekers probeer
je `timeline.xml`: de gekozen radio-/muziektracks staan daarin uit. Mogelijk vraagt
Premiere om de uitgepakte bestanden opnieuw te koppelen. De XML-structuur en mute-keuzes
zijn getest, **import in Premiere zelf niet**; stereo/VFR kan handmatige correctie vragen.

Handmatig met losse tracks: zet `speakers/*.wav`, `background.wav` en optioneel
`music.wav` allemaal op aparte tracks vanaf **00:00:00**. Zet radio-/zangtracks en muziek
uit volgens je keuze. `radio.wav` bestaat alleen bij gebruik van een referentiebestand.

**Speel `original.wav`, `cleaned.wav` of `removed.wav` niet dubbel met de losse tracks af.**
`original.wav` is de ongewijzigde gedecodeerde mix; `cleaned.wav` is de gekozen mix;
`removed.wav` laat juist horen wat is weggelaten. Zet je alle bronstems weer aan, dan
vormen die samen het origineel (op float-afronding na).

`clips/` bevat genummerde spreekfragmenten, zonder de tussenliggende stiltes. Plaats je
die los, gebruik dan `segments.csv` / `timeline.json` voor de oorspronkelijke posities.
Die clips achter elkaar plakken bewaart de timing niet. De volledige WAVs doen dat wel.
Ook in Clipchamp kun je de volledige `cleaned.wav` vanaf 0 onder de video plaatsen;
Clipchamp zelf is hier niet getest.

## Optioneel: je hebt wél het oorspronkelijke radiobestand

Dit is **niet nodig** voor de workflow hierboven. Als je exact dezelfde opname/master
van het nummer hebt, kun je onder de extra radio-optie een lokaal WAV/MP3/FLAC/M4A
referentiebestand kiezen. De app zoekt een uitlijning en schat welk gecorreleerd geluid
van de radio komt, inclusief zang. Die schatting komt in `radio.wav`; de mix erna in
`cleaned.wav`. Er wordt geen artiest op naam herkend en niets naar een muziekdienst gestuurd.

Automatisch zoeken gebruikt de eerste 90 seconden. Optioneel kun je opgeven wanneer
het begin van het referentiebestand op de vergadertijdlijn ligt: `-30` betekent dat de
opname dertig seconden ná het begin van het nummer start. Een slechte match wordt
geweigerd, niet stilzwijgend toegepast. Referentie maximaal 30 minuten / 512 MiB.
Deze experimentele DSP-route is getest op een synthetische bekende akoestische menging,
niet op jouw radio-opname. Een andere master, reclames, radio-DJ, galm, clipping of
klokdrift kan voor resten of spraaklekkage zorgen. Luister de verwijderde track na.

## Kwaliteit, privacy en grenzen

- Verwerking is offline na installatie. Geen CDN, externe scripts, tracking of API.
- De server bindt op `127.0.0.1`; alleen lokale clients en verwachte hosts worden
  toegelaten. Schrijfaanvragen vereisen een lokale header, zonder cross-origin toestemming.
- Eén serverproces, één actieve verwerking. Annuleren bij het volgende controlepunt;
  een lopende model- of FFmpeg-stap kan eerst nog even doorwerken.
- Eerdere opdrachten en bestanden blijven lokaal tot je ze via de website verwijdert.
  Standaard datamap: `~/.multitrackert/jobs/`. Herstart markeert onvoltooide opdrachten
  als onderbroken; upload die opnieuw. Mixkeuzes op complete analyses zijn herhaalbaar.
- MP4: eerste audio-/videostream, maximaal 4 GiB / 60 minuten, mono/stereo, 8–192 kHz.
  De ruimtecontrole is conservatief en houdt rekening met veel stems, clips en ZIP.
- Bronfrequentie, kanalen en videostream blijven behouden. Export is 32-bit float WAV;
  dit veroorzaakt geen extra verlies, maar herstelt geen door AAC verloren informatie.
- De muziekscheider rekent op 44,1 kHz stereo en zet terug naar het bronformaat. De
  overlap-stemmenscheider werkt op **8 kHz mono**; die stukken krijgen daardoor minder
  bandbreedte en bij stereo dezelfde stem op beide kanalen. Dit is geen 48 kHz-stemisolatie.
- Overgangen, stemlekkage en verkeerde labels blijven mogelijk. Geen gevalideerde
  nauwkeurigheidspercentages en geen bewijs van identiteit. Lees [validatie](docs/VALIDATION.md).

| Omgevingsvariabele | Betekenis |
| --- | --- |
| `MULTITRACK_DATA` | Andere lokale datamap |
| `MULTITRACK_MODELS` | Andere modelmap; standaard `models/` in de checkout |
| `MULTITRACK_MAX_BYTES` | Uploadlimiet in bytes; standaard 4294967296 |
| `MULTITRACK_TEST_AUDIO` | Spraakfixture voor de modeltests |

## Ontwikkelen en testen

```sh
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pytest -q -m 'not models'
.venv/bin/python scripts/download_test_audio.py
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

Echte modeltests slaan over als de betreffende gewichten, runtime of spraakfixture
ontbreken; skips zijn geen bewijs van geteste inferentie. De fixture is een openbaar
sherpa-onnx-voorbeeld, geen gebruikersopname, en wordt niet in Git opgenomen.

Browser (optioneel): installeer `playwright`, daarna `python -m playwright install chromium`.
Start de server en voer `python scripts/browser_smoke.py gesprek.mp4` uit. Voor de volledige
nieuwe flow: `--speakers 2 --radio-speaker 2` op een passende testopname, en eventueel
`--chromium /usr/bin/chromium`. Dit wijst in de test expliciet cluster 2 aan; het bewijst
geen automatische herkenning van radio/zang.

## Gratis commercieel gebruik

De eigen code is **MIT**. De gekozen basiscomponenten, Demucs en torchaudio hebben
licenties die commercieel gebruik toestaan; er is geen abonnement of verwerkingstarief.
Modeldownloads gaan via de officiële bronnen en blijven buiten Git. Behoud de
licentieteksten/notices bij herdistributie. FFmpeg wordt apart geïnstalleerd; de
LGPL/GPL-verplichtingen hangen af van die build. Zie [bronnen en licenties](docs/THIRD_PARTY.md).

## Update 0.3.1: Windows-statusbestand en foutlogs

Deze update verhelpt een reproduceerbare Windows-bestandsvergrendeling bij
`status.tmp → status.json`: statuslezers staan nu atomisch vervangen toe, schrijvers
hebben unieke tijdelijke bestanden en wachten op elkaar, ook tussen processen.
Tijdelijke Windows-vergrendelingen krijgen begrensde herhaalpogingen. Echte blijvende
toegangsproblemen blijven een fout geven; er worden geen rechten omzeild en geen
bestaande audiobestanden verwijderd.

De website heeft **Download foutlog**. Dit ZIP bevat technische logregels, versies
en lokale paden, geen audio/video en geen procesomgeving. Het wordt niet automatisch
naar iemand verstuurd. Deel het alleen als je hulp nodig hebt.

Een nieuwe installer gebruikt dezelfde installatie-ID en vervangt de oude geïnstalleerde
app. Historische Python-versies opnieuw verpakken als installer is niet nodig voor
opruimen of logs. Onbekende bronmappen worden niet automatisch gewist, omdat daarin
projecten of andere gebruikersbestanden kunnen staan. Je bestaande standaarddatamap
wordt hergebruikt; complete audio-/video-exports blijven behouden.
