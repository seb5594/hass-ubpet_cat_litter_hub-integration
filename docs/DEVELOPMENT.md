# Architektur und Erweiterungen

## Datenfluss

`providers.json` hält Anbieter, Regionen, Hosts und Regeln für die Vorauswahl. `providers.py` wertet diese Daten aus; es probiert keine anderen Regionen durch. `mobile_apps.json` beschreibt die bekannten Produkt- und App-Kennungen. Die bekannten App-Schlüssel sind in `vendor_app_keys.json` als getrennte Herstellerdaten vordefiniert. Explizite Eingabe, gespeicherter Eintragswert und ein eindeutig passender lokaler Wert haben Vorrang vor dem Standardprofil. `app_credentials.py` liest für die lokale Wiederverwendung nur Konfigurationsdaten derselben HTTPS-Origin, App- und Produktkennung; alte Implementierungen werden nicht importiert. Abweichende individuelle App-IDs erhalten keinen geratenen Standardschlüssel. Herkunft und begrenzter Lizenzumfang stehen in [APP_SCHLUESSEL.md](APP_SCHLUESSEL.md).

`cloud_http.py` tauscht signierte HTTP-Nachrichten aus und prüft die Antwortform. `http_profile.json` hält die bisherigen statischen Kompatibilitätsheader und den Timeout als Daten fest; darin stehen keine Signierschlüssel. `api.py` beschreibt die Endpunkte und verwaltet Account-Typen, gesperrte Zugangsdaten, die einmalige Erneuerung nach HTTP 401 und den begrenzten Zwischenspeicher optionaler Antworten. Die Anmeldung ist mit einem Lock geschützt. Pro Kontenabgleich laufen höchstens vier HTTP-Aufrufe gleichzeitig im Executor; fehlende optionale Endpunkte werden eine Stunde lang nicht erneut abgefragt.

`mqtt.py` ist der Binärcodec. `transport.py` verwaltet je Konfigurationseintrag genau eine TLS-Verbindung zu Paho für Meldungen und Befehle. Eine Broker-Bestätigung bedeutet keine Bestätigung einer Gerätebewegung. Nach einem Verbindungsaufbau muss erst wieder ein aktueller Gerätestatus eintreffen.

`coordinator.py` verbindet REST, MQTT und den Verlauf. Push-Meldungen verschieben nicht den regelmäßigen REST-Termin. Wiederholte Hinweise werden zu einer verzögerten Aktualisierung zusammengefasst. Beim Entladen werden Verbindungen, Warteaufgaben und geplante Aufrufe beendet.

`history.py` übernimmt Deduplizierung, Zeitnormalisierung, begrenzte Speicherung und Auswertungen ohne Home-Assistant-Abhängigkeit. Der Speicher heißt `ubpet_cat_litter_hub.<entry_id>.visit_analytics`; übernommene Einträge lesen beim ersten Start den bisherigen Speicher `ubpet.<old_entry_id>.visit_analytics`. Datensätze werden nach Gerät und Datenstrom unterschieden.

## Messwerte und Einstellungen

`metrics.json` enthält die Metadaten der Sensoren und binären Sensoren. `catalog.py` übersetzt diese in Home-Assistant-Beschreibungen. `readings.py` liefert die Werte und Zusatzattribute aus dem aktuellen Snapshot. Ein einziger Sensoradapter kann eine Box oder eine Katze darstellen. Fehlende und unbekannte Werte bleiben unbekannt; ein unbekannter REST-Statuscode wird nicht als laufende Reinigung ausgegeben.

`settings.py` kennt Einstellungen als Daten: Familie, Plattform, Quellfeld und Protokolloptionen. Lesen und Planen sind reine Operationen. `SettingWrite` beschreibt einen Auftrag mit Methode, Argumenten und den nach Erfolg zu übernehmenden Feldern. Die Plattformen für Schalter, Uhrzeit, Zahlen und Auswahl sind kleine Adapter auf dieses Modell. Der lokale Schätzschwellwert einer Katze wird weiterhin ausschließlich im Verlaufsspeicher geändert.

`HubEntity` bindet Beschreibung, Ziel und Kontonamensraum zusammen. `HubSettingEntity` führt Schreibaufträge je Box nacheinander aus und übernimmt erst nach Erfolg die bestätigten Felder in den neuesten Snapshot. Fehlende Zeitplanfelder führen zum Abbruch; sie werden nicht durch Standarduhrzeiten ersetzt. Die Geräte- und Entitätsregistrierung wird nicht wegen eines vorübergehend fehlenden Werts gelöscht. Bereits registrierte Einstellungen werden auch bei aktuell fehlenden Feldern wieder angelegt.

`legacy.py` übernimmt zuerst Geräte und Entitäten in den neuen Eintrag und löst danach die alte Zuordnung. Sonst könnte Home Assistant die Entitäten beim Entfernen des alten Eintrags löschen. Der `namespace` bleibt bei einer Übernahme die alte Eintrags-ID. Katzengeräte sind je Konto getrennt. `compat.py` kapselt Unterschiede der unterstützten Core-Versionen.

## Neue Anbieter und Sensoren

1. Einen Anbieter mit belegtem App-Profil und Regionen in `providers.json` eintragen. Regionale Abweichungen gehören in `hosts` oder `region_apps`. Eine neue App-Kennung muss als Protokollbefund belegt sein; keine fremden Implementierungen übernehmen; Herkunft und Rechtsstatus neuer Anwendungswerte gesondert dokumentieren.
2. Für einen Messwert Quelle, Einheit, unbekannten Zustand und Wertebereich festlegen. Metadaten in `metrics.json` ergänzen; die Projektion kommt nach `readings.py`. Gleitende Zähler verwenden `measurement`, weil sie auch ohne Reset sinken können.
3. Für eine Einstellung eine Definition und gegebenenfalls eine neue Familie in `settings.py` ergänzen. Auftrag und Erhalt anderer Felder mit synthetischen Daten testen.
4. Neue Übersetzungsschlüssel in `strings.json` und allen `translations/*.json` ergänzen. Englische Kommentare und Docstrings beibehalten. Die Oberfläche folgt der HA-Benutzersprache; ältere Core-Versionen können bei Ausnahmen nur englischen Ersatztext zeigen.
5. Herkunft prüfen, Bericht aktualisieren und den Paketbestand bewusst neu erfassen. Der Vergleich mit fremdem Code ersetzt keine Rechteprüfung: siehe [LIZENZPRUEFUNG.md](LIZENZPRUEFUNG.md).

Auswertungen für Besuche, Reinigungen und Gewichte stammen aus gespeicherten Herstellerdatensätzen. Ereignistyp 31 für abgeschlossene Reinigung ist ein Forschungsbefund, nicht für jede Firmware bestätigt. Unbekannte Warncodes, medizinische Interpretationen, OTA-Befehle und Kamerabilder werden nicht als gesicherte Funktionen ergänzt.

## Dashboard und Übersetzungen

`frontend/ubpet-cards.js` enthält eigene Custom Elements ohne Build-Schritt. `frontend.py` registriert sie einmal pro HA-Lauf und verwendet eine Versionskennung zum Cache-Wechsel. Die Karten finden Entitäten über Gerät und Übersetzungsschlüssel. Texte, die HA selbst nicht übersetzen kann, stehen in `TEXTS`; Entitätsnamen, Zustände und Einheiten liefert HA.

## Tests und Paketprüfung

```bash
# Run project tests without vendor credentials.
python -m pip install -r .github/dev/requirements-dev.txt
python -m pytest -c .github/dev/pyproject.toml --rootdir . .github/tests
python .github/checks/project.py
python tools/provenance.py check
```

Mit echtem Core zusätzlich `.github/ha_tests` ausführen. Vollständige Setup- und Registry-Tests benötigen die passende HA-Testbibliothek und werden im vorhandenen Compatibility-Workflow ausgeführt. Core 2023.6.0 bleibt das deklarierte Minimum. Die bestehende private Engine wird anhand des Pins in den Workflow-Dateien wiederverwendet.
