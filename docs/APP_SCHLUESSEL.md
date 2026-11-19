# Vordefinierte App-Schlüssel

Die Einrichtung der bekannten Anbieter benötigt keine manuelle Beschaffung
eines App-Schlüssels. Nach der Wahl von App, Kontoregion und Kontoland meldet
sich der Nutzer mit seinen Kontodaten an. Die benötigten Anwendungswerte werden
über das passende Profil ausgewählt.

## Auswahl und Erhalt bestehender Einträge

Die Reihenfolge ist:

1. ausdrücklich eingegebener Wert aus den erweiterten Optionen;
2. gespeicherter Wert des bearbeiteten Eintrags, wenn dessen App-Profil erhalten bleibt;
3. eindeutiger lokal gespeicherter Wert mit gleicher HTTPS-Origin, App- und Produktkennung;
4. vordefinierter Wert für das ausgewählte Standardprofil.

Die normalen Formulare zeigen kein App-Schlüsselfeld. In den erweiterten
Optionen bleibt eine leere Überschreibung möglich. Gespeicherte Werte werden
dabei nicht an den Browser zurückgegeben. Für eine abweichende, individuell
konfigurierte App-ID wird kein Schlüssel eines Standardprofils geraten.

`providers.json` enthält die Anbieter- und Regionszuordnung. UPET/UBPet nutzt
abhängig von der Region das UPET- oder AIR-PET-Profil. AIR PET/AIRROBO und
Meowant verwenden das AIR-PET-Profil; Robotail verwendet ein eigenes Profil.
Die drei bekannten Vorgaben liegen als Daten in `vendor_app_keys.json`.
Weder Kontopasswörter noch Sitzungstokens gehören in diese Datei.

## Herkunft und Lizenzumfang

Die Werte wurden unverändert aus dem bereits öffentlichen Projektstand
[`79d669d`](https://github.com/seb5594/hass-ubpet_cat_litter_hub-integration/commit/79d669d84335328e6d6171e57807169639df62d4)
wiederhergestellt. [vendor-data.json](../.github/provenance/vendor-data.json)
nennt Quell-Commit, Datei, Git-Blob und Prüfsummen. Die Paketprüfung stellt
sicher, dass diese festgehaltenen Werte ausgeliefert werden.

Die Projekt-MIT-Lizenz betrifft die eigene Implementierung und die eigenen
Grafiken. Für die Herstellerwerte in `vendor_app_keys.json` wird durch das
Projekt keine eigene Lizenz erteilt; dies steht auch im mitgelieferten
`LICENSE-SCOPE.txt` und im Dateiinventar. Eine veröffentlichte Quelle, getrennte
Datei oder Prüfsumme schafft keine zusätzliche Nutzungserlaubnis. Eine
Herstellerfreigabe für diese Werte oder die Integration ist nicht verifiziert.

Die Rechte an fremdem Quellcode und die Bedingungen des Herstellerdienstes
sind getrennt zu prüfen. Die veröffentlichten
[UBPet-Websitebedingungen](https://www.ubpet.com/pages/terms-conditions)
enthalten Einschränkungen für automatisierte Zugriffe. Welche Bedingungen für
jedes der App- und API-Profile gelten, wurde nicht abschließend festgestellt.
Die mitgelieferten Werte werden daher nicht als rechtlich abschließend
freigegeben dargestellt. Ihre Herkunft und der begrenzte Lizenzumfang bleiben
für die Prüfung der bestehenden HACS-Submission sichtbar.
