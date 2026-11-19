# Geräte- und Kompatibilitätstests

Der Maintainer hat [`v2026.11.03.2`](https://github.com/seb5594/hass-ubpet_cat_litter_hub-integration/releases/tag/v2026.11.03.2)
an einem UBPet C20 getestet. **Der Gerätetest des überarbeiteten Clients in
`2026.11.19.1` steht noch aus.** Der frühere Test bestätigt diesen neuen Client
nicht. Beim Robotail-Testgerät muss die genaue Modellbezeichnung noch am
Typenschild oder in der App geprüft werden.

## Bestehende Installation prüfen

1. Eine Home-Assistant-Sicherung erstellen und die bisherigen Entity-IDs oder
   deren Anzahl festhalten. Der Screenshot der bisherigen Installation zeigt
   54 Entitäten für zwei Katzen und eine Box; die Anzahl ist geräteabhängig.
2. Bei einem Umstieg von der alten Domain `ubpet` den Ordner
   `<config>/custom_components/ubpet` entfernen. Das neue Paket nach
   `<config>/custom_components/ubpet_cat_litter_hub` entpacken. Bestehende
   Konfigurationseinträge und `.storage` nicht manuell ändern.
3. Home Assistant neu starten und über **Integration hinzufügen → Cat Litter
   Hub → Bestehende UPET-Einrichtung übernehmen** den alten Eintrag übernehmen.
   Danach Entity-IDs, Automationen, Katzen, Besuchsverlauf und individuelle
   Dauerschwellen vergleichen. Bei einem bereits bestehenden Cat-Litter-Hub-
   Eintrag ist keine erneute Übernahme nötig.
4. Anbieter, Kontoregion und Registrierungsland mit der App vergleichen. Bei
   einem neuen Eintrag reichen die Kontodaten; ein App-Schlüssel muss für die
   bekannten Profile nicht manuell beschafft werden. Gespeicherte oder bewusst
   überschriebene Werte sollen erhalten bleiben.
5. Gewicht, Firmware, Behälterzähler, Geruchsblock und Onlinezustand mit der App
   vergleichen. Ein berechneter Behälterstand ist keine bestätigte physische
   Füllstandsmessung.

## Besuche und Schalter

1. Zunächst einen normalen Katzenbesuch abwarten. Anwesenheit, letzter Besuch,
   Dauer und 24-Stunden-Zähler vergleichen. Mehrere Besuche zwischen zwei
   REST-Abgleichen dürfen nicht zu einem Besuch zusammenfallen.
2. Home Assistant neu starten. Besuche dürfen nicht doppelt erscheinen;
   Dauerschwellen müssen erhalten bleiben.
3. Die Reinigungsverzögerung bei ausgeschalteter automatischer Reinigung
   ändern. Die automatische Reinigung muss ausgeschaltet bleiben. Danach den
   alten Wert wiederherstellen.
4. Nicht-stören-Zeitplan und Leerungserinnerung mit den Möglichkeiten des
   eigenen Geräts prüfen. Beim Schalten müssen Uhrzeiten und nicht geänderte
   Wochentage erhalten bleiben. Die tatsächliche Übernahme in der App prüfen.
5. An einem leeren, betriebsbereiten Gerät einen bekannten Reinigungsvorgang
   mit Start, Pause und Fortsetzen prüfen. Während eines Katzenbesuchs dürfen
   Startbefehle nicht freigegeben sein. Eine zur Wartung geöffnete Abdeckung
   darf nicht als Katzenbesuch erscheinen.
6. Die Hersteller-App normal anmelden. Verdrängt diese die Sitzung, soll die
   Integration mit Wartezeiten zurücktreten und sich ohne fortlaufende
   Anmeldemeldungen erholen.

Urin und Kot werden ausschließlich anhand der Besuchsdauer geschätzt. Eine
geänderte Schwelle klassifiziert gespeicherte Besuche neu; sie misst keine
Ausscheidungsart. Streurechen-Befehle sind auf neuen Installationen zunächst
deaktiviert und nur an passender Hardware zu prüfen.

## Weitere Werte und Konten

- Besuche und Reinigungen heute mit der Tagesansicht der App vergleichen.
  Maßgeblich ist die Home-Assistant-Zeitzone; der nächste REST-Abgleich nach
  Mitternacht aktualisiert die Tageswerte.
- Nach einem Behälterreset und einer Reinigung den Wert **Reinigungen seit
  Behälterreset** prüfen. Er dient als Alternative zu einem stehen gebliebenen
  Herstellerzähler.
- Zuletzt benutzende Katze, Gewicht beim letzten Besuch und geplante
  Reinigungen mit bekannten Ereignissen beziehungsweise App-Zeitplänen prüfen.
- Einen weiteren Konfigurationseintrag mit **Robotail** anlegen. Der Nachbar
  gibt seine Zugangsdaten selbst ein. Das erste Konto muss weiterlaufen;
  gleiche numerische Katzen-IDs dürfen die Konten nicht vermischen.

## Automatisierte Prüfung

Die deklarierte Mindestversion ist **Core 2023.6.0**. Sie bildet auch die
Untergrenze der gemeinsamen `hass-workflows`-Kompatibilitätsmatrix. Der
[Compatibility-Workflow](https://github.com/seb5594/hass-ubpet_cat_litter_hub-integration/actions/workflows/compat.yml)
dokumentiert die tatsächlich geprüften Versionen je Commit.

Die Tests in `.github/tests` und `.github/ha_tests` verwenden synthetische
Daten und simulierten Cloud-Verkehr. Sie prüfen unter anderem Einrichtung,
Registrierungsübernahme, Kontentrennung, MQTT, Verlauf und Schreibfehler.
Der [Schaltervergleich](SCHALTER.md) prüft 16 Schalter mit jeweils Ein und Aus
gegen 32 festgehaltene bisherige HTTP-Befehle. Das ersetzt keinen Gerätetest.

```bash
python -m pytest -c .github/dev/pyproject.toml --rootdir . .github/tests .github/ha_tests
```

Für lokale Tests Home Assistant mit passender Python-Version und
`paho-mqtt==2.1.0` in einer eigenen virtuellen Umgebung installieren. Die
vollständigen Einrichtungs- und Registrierungstests benötigen zusätzlich eine
zur Core-Version passende Version von `pytest-homeassistant-custom-component`;
ohne sie werden diese Module übersprungen. Die gemeinsamen CI-Workflows führen
sie mit dem passenden Plugin aus.

Für Rückmeldungen bitte Modell, Firmware, App, Anbieter, Kontoregion,
Registrierungsland, Core-Version und den konkreten Unterschied zwischen App
und Entität nennen. Geschwärzte Integrationsdiagnosen sind hilfreich.
Passwörter, Tokens oder rohe Cloud-Mitschnitte gehören nicht in Issues.
