Windows 10/11 x64 CPU-installer. Download de `.exe` en voer die uit. Python, FFmpeg, muziek-/stemmodellen en het optionele Whisper Small-tekstmodel zijn inbegrepen. De app verwerkt je opnames lokaal.

Nieuw in 0.5.0:

- Lokale reclamebibliotheek: voeg één keer een schoon reclamefragment van 2–90 seconden toe. De app zoekt sterke geluidsmatches in de hele opname, ook bij herhaling, en schat die reclame op een aparte, standaard gedempte `radio.wav`-track. Het resultaat staat in `cleaned.wav`; origineel en restgeluid blijven bewaard.
- Optionele Nederlandse tekstherkenning met korte herkenningszinnen van AH, Kruidvat en Lidl en eigen zinnen. Die geeft aanwijzingen bij fragmenten. Tekst alleen verwijdert geen audio: ook een gesprek kan een slogan noemen en gezongen reclames worden soms verkeerd verstaan.
- Meer dan 12 geschatte stemgroepen veroorzaakt geen afgebroken analyse meer. De 12 groepen met de meeste spreektijd krijgen losse tracks; de rest blijft in achtergrond/rest. Tijden en uitleg staan in `reclame-analyse.json`.
- De radioselectie per fragment en de Windows-statusreparaties uit 0.4 blijven aanwezig.

Dit is geen universele herkenning of gegarandeerde verwijdering van alle radioreclames. Geluidsvergelijking vereist voldoende overeenkomst met een toegevoegd voorbeeld; dezelfde stem met andere woorden is daarvoor geen match. Controleer altijd `radio.wav` en `cleaned.wav` op resten en eventuele spraaklekkage. Het eigen AH-voorbeeld uit de chatsessie wordt niet in de app verspreid.

Bij een gecontroleerde mix van de aangeleverde AH-slogan met onafhankelijke echte testspraak en een korte echo zijn drie ingevoegde slogans gevonden. De fout ten opzichte van de schone testspraak daalde circa 25,7 dB. Dat is geen meting op jouw echte kamer-/gespreksopname. De kleine én grotere tekstherkenner misten de gezongen slogan; geluidsvergelijking is daarvoor de werkende route in deze test.

Updates vervangen de programmabestanden. Opnames, reclamebibliotheek en exports staan buiten de installatiemap en blijven bewaard. Sluit de oude app voor installatie. De Windows-build controleert echte modellen, de verpakte app, reclamebibliotheek → geluidsmatch → aparte track → ZIP, installatie, bijwerken en gegevensbehoud.

Deze CPU-preview is niet digitaal ondertekend. De `.sha256` hoort bij de installer; licenties en bijbehorende FFmpeg-broncode worden meegeleverd.
