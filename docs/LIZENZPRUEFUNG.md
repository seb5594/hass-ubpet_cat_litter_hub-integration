# Herkunftsprüfung für 2026.11.18.1

Der HACS-Review [#13798](https://github.com/hacs/default/pull/13798#pullrequestreview-5928093514)
beanstandet zu Recht, dass die bisherige MIT-Angabe übernommenen Code ohne
nachgewiesene Freigabe einschloss. Die Antwort von `royalgardist` in
[CrazzyBerg/upet-hass#8](https://github.com/CrazzyBerg/upet-hass/issues/8)
ist keine belegte Freigabe des ursprünglichen Repository-Inhabers `CrazzyBerg`.
Für die weiteren recherchierten Forks wird ebenfalls keine Freigabe unterstellt.

Die Überarbeitung verfolgt den im Review genannten Weg einer neuen Umsetzung.
Es wird keine nachträgliche Genehmigung für ältere Veröffentlichungen behauptet.
Die bestehende Submission bleibt bis zur Prüfung und Veröffentlichung des
korrigierten Stands ein Entwurf; es wird kein weiterer HACS-PR eröffnet.

## Was ersetzt wurde

| Beanstandeter Bereich | Umsetzung im neuen Stand |
| --- | --- |
| Eigene Klassen für Auto-Clean, Geruchsblock und weitere Schalter | Ein `SettingSwitch` über einem gemeinsamen Einstellungsmodell. Lesen, Validierung, Schreibauftrag und Übernahme bestätigter Werte sind getrennt. |
| Sensor-Klassen, Statusattribute, Firmware- und Betriebsstatus-Auswertung | Ein Adapter für Box und Katze, ein Datenkatalog für Entitätsmetadaten und reine Projektionen in `readings.py`. Unbekannte REST-Statuscodes ergeben einen unbekannten Wert. |
| Zeitentitäten und verteilte Zeitplanänderungen | Ein `ScheduleTime` mit demselben Einstellungsmodell wie Schalter und Tagesauswahl. Unvollständige Zeitpläne werden nicht mit geratenen Mitternachtswerten überschrieben. |
| REST-Client und Signierung | `CloudHTTP` übernimmt ausschließlich den HTTP-Austausch. Der Account-Client verwaltet Anmeldung, erneute Anmeldung und Zwischenspeicher; Endpunkte sind separat deklarierte Protokolldaten. |
| Weitere geerbte Plattformstrukturen | Zahlen, Tagesauswahl und binäre Sensoren verwenden dieselben gemeinsamen Adapter. Die alten Entitätsbasen und Schreibpfade wurden entfernt. |

Die bereits projektseitig umgesetzten Bereiche bleiben erhalten: Anbieter- und
Regionsauswahl, Kontentrennung, Migrationsablauf, begrenzter Besuchsverlauf,
MQTT-Sitzungsverwaltung, neuer Binärcodec, Diagnosefilter, Kompatibilitätsbrücken,
Dashboard-Karten und eigenes SVG. Sie wurden in die Bestandsprüfung einbezogen.
Eine bloße Umbenennung vorhandener Upstream-Klassen ist nicht die Grundlage
dieser Änderung.

## Welche Informationen kompatibel bleiben

HTTP-Pfade, JSON-Feldnamen, Protobuf-Feldnummern, Prüfsummenparameter und
Hersteller-Statuswerte beschreiben das Protokoll. Entitätskennungen,
Übersetzungsschlüssel, Ereignisnamen und Speicherformate beschreiben die
Kompatibilität mit bestehenden Installationen. Deren Herkunft bleibt in
[SOURCES.md](SOURCES.md) sichtbar. Aus diesen Informationen wird keine Erlaubnis
zur Übernahme fremder Implementierungen abgeleitet.

Der synthetische Referenzbestand in
[2026.11.10.1-entity-contract.json](../.github/fixtures/2026.11.10.1-entity-contract.json)
enthält **95 Entitäten** über alle sieben Plattformen. Der Regressionstest prüft
Kennungen, Einheiten, Zustands- und Geräteklassen, Enum-Werte, Kategorien und
standardmäßige Aktivierung. Anzeigenamen können aus den aktuellen Übersetzungen
stammen. Es werden weder Konto-, Geräte- noch Katzendaten echter Benutzer als
Testdaten veröffentlicht.

Änderungen an demselben Zeitplan laufen je Box nacheinander. Erst nach einer
erfolgreichen REST-Antwort werden die bestätigten Felder übernommen. Eine
gleichzeitige Änderung des Endes überschreibt dadurch nicht den gerade
geänderten Anfang. Fehlgeschlagene Änderungen lassen den Zustand unverändert.
Bewegungsbefehle behalten ihre Anwesenheits- und Aktualitätsprüfung; Pause
wartet weiterhin nicht auf eine zusätzliche Statusabfrage.

## Nachvollziehbare Prüfung

- [sources.json](../.github/provenance/sources.json) hält **51 öffentliche
  Quellstände** aus elf fremden Repositories mit unveränderlichen Commit-SHAs
  fest. Dazu gehören auch die zuvor erfassten, inzwischen verschobenen Branches.
- [overlap-report.json](../.github/provenance/overlap-report.json) vergleicht den
  installierbaren Python-Code mit **152 unterschiedlichen Python-Dateiständen**.
  Kommentare und Formatierung zählen nicht als Unterschiede. Gemeldet werden
  gleiche Folgen ab 35 Tokens über mindestens vier Zeilen sowie identische
  Übersetzungstexte ab 50 Zeichen. Im geprüften Stand gab es keine Fundstellen
  nach diesen Kriterien.
- Diese Schwellenwerte sind **keine urheberrechtlichen Grenzen**. Der Vergleich
  beweist weder Urheberschaft noch Unabhängigkeit. Kürzere, umbenannte oder
  umgestellte Ableitungen müssen zusätzlich inhaltlich geprüft werden. Die
  Implementierung entstand mit Kenntnis der Quellen; es wird ausdrücklich kein
  organisatorisch getrenntes Clean-Room-Verfahren behauptet.
- [distribution.json](../.github/provenance/distribution.json) nennt jede Datei
  des installierbaren Bestands mit SHA-256 und Kategorie. Der normale
  `hass-workflows`-Lauf prüft diesen Bestand unverändert. Neue, fehlende oder
  geänderte Dateien erfordern eine bewusste Aktualisierung nach Herkunftsprüfung.
  Eine Prüfsumme ersetzt diese Prüfung nicht.

Reproduktion mit einem getrennten, nicht versionierten Quellen-Cache:

```bash
# Fetch public snapshots for analysis; the cache is never part of the release.
python tools/audit_sources.py --sources-root .research/sources --fetch --output .research/overlap.json

# Check the reviewed source inventory and the ZIP built by the existing engine.
python tools/provenance.py check
python .engine/.scripts/project.py package
python tools/provenance.py check --archive dist/ubpet_cat_litter_hub.zip
```

`record` ist kein automatischer CI-Schritt. Nach einer geprüften Änderung:

```bash
# Record only after reviewing all changed files and their origin.
python tools/provenance.py record --review docs/LIZENZPRUEFUNG.md
```

## Paket- und Lizenzumfang

Der MIT-Text im Repository und im Installationsordner ist identisch. Er gilt
für die Projektimplementierung und die selbst erstellten Grafiken dieses
Quellstands. Er erteilt keine Rechte an früher übernommenem Fremdcode, fremden
Apps, Herstellerdiensten oder Marken. Die frühere pauschale Aussage zur
Freigabe ab `2026.11.09.1` wurde berichtigt; die neue Prüfung repariert keine
bereits verteilten Archive rückwirkend.

Die vier PNGs stammen aus `assets/cat-litter-hub.svg`. Es werden keine
Herstellerlogos, Fotos oder zusätzlichen Schriftdateien eingebunden.
`paho-mqtt` wird als externe Laufzeitabhängigkeit installiert und nicht als
Quellcode mitgeliefert; seine eigene Lizenz bleibt maßgeblich.

`vendor_app_keys.json` und der automatische Bezug daraus wurden entfernt.
Neue Pakete enthalten keine dieser Hersteller-Signierwerte. Bestehende oder
migrierte Konten verwenden ihren lokal gespeicherten Schlüssel weiter. Bei
einer neuen Einrichtung ist ein zur Verwendung freigegebener Schlüssel für
die gewählte App und Region erforderlich. Beim Wechsel der App-Region wird
ein alter Schlüssel nicht automatisch für den neuen Kontext übernommen.
Eine allgemein verfügbare offizielle Ausgabestelle für Fremdintegrationen ist
nicht verifiziert. Ohne einen zulässig verwendbaren Schlüssel ist deshalb
keine neue Cloud-Verbindung möglich. Das ist eine separate Frage des
Dienstzugangs und kein Nachweis über die Lizenz des Integrationscodes.

## Vor erneuter HACS-Prüfung

1. Diesen Änderungsstand einschließlich des Herkunftsinventars prüfen. Offene
   Rechtefragen mit den tatsächlichen Rechteinhabern klären; gegebenenfalls
   fachkundigen rechtlichen Rat einholen. Der technische Bericht kann keine
   verbindliche rechtliche Freigabe geben.
2. Bestehenden C20-Eintrag mit Backup aktualisieren und den Ablauf aus
   [TESTING.md](TESTING.md) prüfen. Eine erfolgreiche Prüfung von
   `v2026.11.03.2` gilt nicht als Gerätetest dieses neuen Clients.
3. Nach Übernahme auf `main` Kompatibilität und den bestehenden strikten
   Marketplace-Lauf ausführen. Der normale gemeinsame CI-Lauf blendet die
   Katalogprüfungen `brands` und `topics` aus; er allein belegt die strikte
   HACS-Anforderung nicht. Im Marketplace-Lauf darf kein `ignore` gesetzt sein.
4. Erst nach den erfolgreichen Prüfungen eine neue vollständige Veröffentlichung
   über den bestehenden Tag-/Release-Workflow erstellen. ZIP und Inventar erneut
   vergleichen. Alte Release-Archive weder austauschen noch als korrigiert ausgeben.
5. Im bestehenden englischen PR #13798 die belegten Release- und Lauf-Links
   aktualisieren und erst dann erneut um Prüfung bitten. Keinen doppelten
   Submission-PR erstellen und keine ungeprüfte Checkliste abhaken.

Quellen zur Einordnung: [HACS-Aufnahmebedingungen](https://www.hacs.xyz/docs/publish/include/),
[GitHub zu nicht lizenziertem Code](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository),
[Richtlinie 2009/24/EG, insbesondere Artikel 1](https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32009L0024).
