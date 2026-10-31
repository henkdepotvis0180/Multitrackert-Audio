# Windows CPU-installer bouwen en controleren

De workflow `Windows installer` bouwt en test op native Windows 2022. Alleen na
succesvolle verificatie verschijnt de `.exe` als GitHub-release-preview. Een aangepast
workflowbestand of succesvolle Linux-test bewijst nog geen geslaagde Windows-build.

De installer bundelt Python 3.12, de CPU-versies van PyTorch/torchaudio, alle drie
modeldownloads, een eigen minimale FFmpeg/ffprobe-build en de Microsoft C++ runtime.
De Microsoft-download wordt op Authenticode-handtekening gecontroleerd. De app-installer
zelf is nog niet digitaal ondertekend en kan een onbekende uitgever tonen.

FFmpeg wordt uit vastgepinde officiële broncode gebouwd, zonder GPL/nonfree of netwerk-
protocollen, met alleen lokale codecs/filters/formats die de app gebruikt. De exacte
broncode en het bouwscript gaan mee als releaseattachment voor de LGPL-verplichtingen.
Python-/dependency-/modelllicenties worden met de app geïnstalleerd.

## Update en bestanden behouden

- De vaste Inno Setup AppId blijft gelijk bij nieuwe versies.
- Updates sluiten de bestaande desktop-app af en vervangen alleen de executable en
  `_internal` (libraries, ingebouwde modellen en app-resources).
- De programmamap is standaard `C:\Program Files\Multitrackert Audio`.
- De projectmap is standaard `%LOCALAPPDATA%\Multitrackert Audio\Data\jobs`.
- Bestaat `%USERPROFILE%\.multitrackert` al van een broninstallatie, dan wordt die
  locatie automatisch hergebruikt. `MULTITRACK_DATA` blijft een expliciete override.
- Data binnen de programmamap wordt geweigerd. De uninstaller verwijdert geen projecten.
- Onbekende oude Python-/broncode-mappen worden niet automatisch verwijderd: die kunnen
  gebruikersbestanden bevatten. Stop een oude `.bat`-server voordat je de desktop-app opent.

## Verificatie

`windows/smoke_test.py` start de werkelijke frozen executable, laadt de muziek- en
stemmodellen, verwerkt een MP4 in een subprocess, maakt een mix/ZIP en hervat een
ZIP-download met HTTP Range. `windows/verify_install.ps1` installeert de app, genereert
projecten, installeert opnieuw, controleert verwijdering van oude programmabestanden,
verwijdert de app en controleert de checksums van bewaarde mediabestanden.

Dezelfde versie wordt bij deze installercontrole twee keer geïnstalleerd; een vaste
AppId en een verouderd testbestand verifiëren dat de update dezelfde installatielocatie
vervangt. Het is geen test van elke historische Windows-versie of van een schone pc
zonder bestaande Microsoft-runtime.

Voor een release de versie verhogen in `multitrack/__init__.py`. Bestaande release-
installers worden niet overschreven. Voor CUDA blijft voorlopig de broninstallatie
beschikbaar; de installer wordt bewust als CPU-editie aangeduid.
