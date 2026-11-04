Windows 10/11 x64 CPU-installer. Download de `.exe` en voer die uit; Python, FFmpeg en de drie lokale modellen zijn inbegrepen. Na installatie opent de website op deze computer. Voor deze editie hoef je geen losse Python-pakketten of modelbestanden te installeren.

Versie 0.4.0 maakt radiopraat, reclame en zang selecteerbaar per spreekfragment of hele spreker. Beluister een stemfragment, markeer de radiofragmenten en maak de gekozen mix. De selectie komt in `radio_voices.wav` op een aparte, standaard gedempte Premiere-track. De oorspronkelijke sprekertracks blijven bewaard; de nieuwe tijdlijn gebruikt aangepaste tracks voor de fragmentselectie. Je kunt de selectie wijzigen en de oorspronkelijke mix herstellen zonder nieuwe analyse. Radiostemmen apart zetten werkt ook zonder muziekscheiding.

Deze versie voegt handmatige precisie toe, geen automatische herkenning van radiopresentatoren. Bij gemengde overlap kan gesprek meekomen; de app toont dit bij het fragment. Beluister de radiostemtrack en de gekozen mix. Voor twee gelijktijdige stemmen blijft de bestaande optionele stemmenscheiding beschikbaar.

Ook de reparatie uit 0.3.1 blijft aanwezig: deze verhelpt Windows-conflicten bij het bijwerken van `status.json` (`WinError 5`). Gelijktijdige schrijvers wachten op elkaar; statuslezers houden het bestand niet meer onnodig geblokkeerd. Tijdelijke blokkades worden kort opnieuw geprobeerd. Een geblokkeerde status van een oude opdracht verhindert geen nieuwe upload. Met **Download foutlog** kun je een lokale ZIP met diagnostiek opslaan, zonder je opnames.

Updates vervangen de oude programmabestanden. Opnames, audio, MP4 en ZIP staan buiten de installatiemap en blijven ook bij de-installatie bewaard. Gebruik “Open lokale opslagmap” of “Open lokale uitvoermap” om ze terug te vinden na een afgebroken browserdownload.

De build controleert op native Windows: echte modellen, de bevroren app en subprocessen, MP4 → muziek-/sprekertracks → ZIP, een hervatbare download, installatie, opnieuw installeren en verwijderen met behoud van data. Dit is nog geen test op jouw eigen Windows-pc.

Dit is een niet digitaal ondertekende preview; Windows kan een onbekende uitgever tonen. De CPU-editie gebruikt geen CUDA. De broninstallatie met CUDA blijft beschikbaar. Perfecte radio-/zangisolatie is niet gegarandeerd.

De `.sha256` hoort bij de installer. Het FFmpeg-broncodearchief bevat de exacte LGPL-broncode en het bouwscript voor de meegeleverde mediabinaries. Licenties van de app, modellen en dependencies worden meegeleverd.
