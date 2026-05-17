# Entwicklungstagebuch simapWatch

## 1. Projektidee und Ziel

Das Projekt **simapWatch** entstand aus der Idee, öffentliche Beschaffungsdaten von `simap.ch` automatisch zu sammeln und journalistisch auswertbar zu machen. Der Ausgangspunkt war die Frage:

> Wer gewinnt, wenn der Staat einkauft?

Öffentliche Beschaffungen betreffen große Summen öffentlicher Gelder. Die Daten sind zwar öffentlich verfügbar, aber nicht besonders einfach zu durchsuchen, zu vergleichen oder über längere Zeit zu beobachten. Deshalb sollte ein Tool entstehen, das Zuschlagsentscheide automatisch lädt, strukturiert speichert und über ein Dashboard sichtbar macht.

Am Anfang war die technische Richtung noch offen. Klar war nur, dass zuerst ein Scraper entstehen sollte und dass die Entwicklung möglichst testgetrieben erfolgen sollte. Daraus entwickelte sich schrittweise eine vollständige Datenpipeline:

```text
SIMAP -> Parser -> SQLite -> Geocoding -> CSV -> Dashboard -> marimo
```

Das Ziel war nicht nur, Daten herunterzuladen. Wichtiger war, aus den Daten sinnvolle Fragen beantworten zu können:

- Welche Firmen gewinnen besonders häufig?
- Welche Auftraggeber vergeben besonders viel Volumen?
- Gibt es Zuschläge mit sehr wenig Wettbewerb?
- Welche Branchen bzw. CPV-Kategorien sind besonders relevant?
- Bleibt Geld im gleichen Kanton oder fließt es in andere Regionen?
- Wie verändern sich Zuschläge und Volumen über die Zeit?

## 2. Wichtigste Entwicklungsstrategie: klein starten, testen, erweitern

Eine der wichtigsten Entscheidungen war, das Projekt nicht als ein großes Skript zu bauen. Stattdessen wurde die Architektur in mehrere Schichten aufgeteilt:

- `fetcher`: lädt Daten von SIMAP.
- `parsers`: wandeln HTML oder JSON in strukturierte Daten um.
- `domain`: definiert Datenobjekte wie `OverviewEntry` und `AwardDetail`.
- `repository`: speichert Daten in SQLite.
- `services`: orchestriert Sync, Parsing und Speicherung.
- `analysis`: erzeugt Auswertungsdaten.
- `dashboard`: zeigt KPIs, Charts, Karte und Tabellen.
- `notebooks`: enthält das spätere marimo-Notebook.

Diese Trennung war sehr hilfreich, weil sich die Anforderungen während der Entwicklung stark verändert haben. SIMAP lieferte die Daten anders als zuerst angenommen, mehrere Firmen konnten denselben Zuschlag gewinnen, später kamen Adressen, Koordinaten, Karten und Dashboard-Filter hinzu. Durch die modulare Struktur musste nicht jedes Mal alles umgebaut werden.

Besonders wichtig war Test Driven Development. Zuerst wurden Tests für bekannte HTML-Beispiele geschrieben. Dann wurden die Parser so implementiert, dass diese Tests grün wurden. Später kamen Tests für JSON, Pagination, Mehrfachzuschläge, Datenbank-Upserts, inkrementelle Updates, Geocoding und Dashboard-Payloads dazu.

Die zentrale Erkenntnis daraus:

> Bei einem Scraping- und Analyseprojekt schützen Tests nicht nur vor Programmierfehlern, sondern auch vor falschen journalistischen Aussagen.

Wenn ein Betrag, ein Gewinner oder die Anzahl Angebote falsch extrahiert wird, entstehen im Dashboard falsche Schlüsse. Deshalb war es wichtig, kritische Logik testbar zu machen.

## 3. Erstes großes Problem: Tests grün, Live-Sync leer

Zu Beginn funktionierten die Parser mit den gespeicherten Beispiel-Dateien. Die Tests erkannten 20 Overview-Einträge und extrahierten aus Detailseiten Felder wie Gewinner, Betrag, Anzahl Angebote und CPV-Codes.

Beim ersten Live-Lauf passierte aber etwas Unerwartetes:

```text
status=success overview=0 new=0 updated=0 errors=0
```

Das sah zunächst aus, als würde das Programm funktionieren, aber keine Einträge finden. Die Ursache war, dass SIMAP die Overview-Daten live nicht mehr so im HTML auslieferte wie in den gespeicherten Beispieldateien. Die sichtbaren Einträge wurden über eine API nachgeladen.

Damit wurde klar:

> Die Parser waren für die Fixtures korrekt, aber nicht für den aktuellen Live-Zustand von SIMAP.

Die Lösung war, den Overview-Parser um JSON-Support zu erweitern und die SIMAP-API als Standardquelle zu nutzen:

```text
/api/publications/v2/project/project-search
```

Auch der Detail-Parser wurde erweitert, damit er nicht nur HTML, sondern auch JSON-Antworten verarbeiten kann.

Nach der Anpassung funktionierte der Live-Sync:

```text
status=success overview=20 new=20 updated=0 errors=0
```

Ein zweiter Lauf ergab:

```text
status=success overview=20 new=0 updated=0 errors=0
```

Das zeigte, dass die Daten nicht doppelt gespeichert wurden.

Die wichtigste Erkenntnis aus dieser Phase war:

> Fixture-Tests sind wichtig, aber bei Webscraping braucht es zusätzlich Live-Plausibilitätsprüfungen. Eine Website kann intern anders funktionieren, als sie im Browser aussieht.

## 4. Pagination: nicht nur die ersten 20 Einträge sammeln

Ein weiteres Problem war der Button **"Mehr Einträge laden"** auf SIMAP. Die erste API-Antwort enthielt nur 20 Einträge. Für ein Analyseprojekt wäre das viel zu wenig gewesen.

Wenn nur die ersten 20 Einträge gespeichert werden, sind alle späteren Auswertungen verzerrt:

- Top-Gewinner wären unvollständig.
- Zeitreihen wären falsch.
- Kantonsvergleiche wären nicht aussagekräftig.
- CPV-Verteilungen würden nur die neuesten Einträge abbilden.

Die API nutzt für weitere Seiten einen Cursor. In der Antwort steht ein Wert wie:

```text
pagination.lastItem
```

Dieser Wert muss beim nächsten Request als Parameter mitgegeben werden. Deshalb wurde der Sync-Service so erweitert, dass er API-Seiten nacheinander lädt, bis kein weiterer Cursor mehr vorhanden ist.

Vereinfacht läuft es so:

```text
1. erste Overview-Seite laden
2. Einträge speichern
3. lastItem auslesen
4. nächste Seite mit lastItem laden
5. wiederholen, bis keine nächste Seite existiert
```

Zur Sicherheit wurden auch Stop-Bedingungen eingebaut:

- bereits bekannte Detail-URLs werden übersprungen.
- bereits bekannte Cursor werden nicht erneut verarbeitet.
- eine maximale Seitenzahl verhindert Endlosschleifen.

Die Erkenntnis:

> Pagination ist kein UI-Detail, sondern entscheidet darüber, ob der Datensatz vollständig ist.

## 5. Mehrfachzuschläge: eine Publikation kann mehrere Gewinner haben

Eines der wichtigsten fachlichen Probleme entstand bei einer SIMAP-Seite mit mehreren Zuschlagsempfängern. Zuerst wurde nur die oberste Firma gespeichert. Das war falsch, weil eine Zuschlagspublikation mehrere Gewinner enthalten kann.

Das ursprüngliche Modell dachte vereinfacht:

```text
eine Publikation = ein Gewinner
```

Richtig ist aber:

```text
eine Publikation = ein oder mehrere Gewinner
```

Wenn nur der erste Gewinner gespeichert wird, sind viele spätere Analysen falsch:

- Gewinner-Rankings verlieren Firmen.
- Volumen pro Firma ist unvollständig.
- Geo-Flüsse sind unvollständig.
- Die Anzahl Zuschläge pro Kanton kann falsch sein.

Die Lösung war, eine eigene Zeile pro Gewinner zu speichern. Dafür wurde `winner_position` eingeführt. Die technische ID wurde:

```text
award_row_id = publication_number::winner_position
```

Beispiel:

```text
#12345-01::1 -> Firma A
#12345-01::2 -> Firma B
#12345-01::3 -> Firma C
```

Auch der Parser wurde angepasst. Statt nur `parse_award_detail(...)` gibt es nun auch:

```text
parse_award_details(...)
```

Diese Funktion gibt mehrere Gewinner-Zeilen zurück.

Die wichtigste Erkenntnis:

> Für gute Analysen muss die Granularität des Datenmodells stimmen. In diesem Projekt ist die zentrale Zeile nicht nur eine Publikation, sondern eine Kombination aus Publikation und Gewinner.

## 6. Performance: parallele Detailseiten und sauberer Abbruch

Nachdem Pagination und Mehrfachzuschläge funktionierten, wurde der Sync deutlich langsamer. Das war logisch: Es mussten viele Overview-Seiten und sehr viele Detailseiten geladen werden.

Der langsamste Teil war nicht das Parsen, sondern das Laden der Detailseiten. Deshalb wurde der Sync parallelisiert. Über `ThreadPoolExecutor` können mehrere Detailseiten gleichzeitig geladen werden. Die Anzahl Worker ist konfigurierbar:

```powershell
--max-workers 12
```

Ein typischer Startbefehl wurde:

```powershell
.\.venv\Scripts\python.exe -m simapwatch.cli --db-path simapwatch.db --max-workers 12
```

Außerdem wurde eine Fortschrittsausgabe ergänzt, weil der Prozess sonst so wirkte, als würde er hängen:

```text
overview pages=1 discovered=20
overview pages=2 discovered=40
progress processed=10/240 new=10 updated=0 errors=0
```

Später wurde klar, dass die genaue Anzeige nicht der wichtigste Punkt ist. Wichtig ist vor allem, dass der Prozess zuverlässig durchläuft. Trotzdem hilft Progress beim Debugging.

Zusätzlich wurde `Ctrl+C` sauberer behandelt. Bei parallelen Threads können bereits laufende HTTP-Requests nicht sofort hart beendet werden. Aber noch nicht gestartete Jobs können abgebrochen werden:

```text
executor.shutdown(wait=False, cancel_futures=True)
```

Die Erkenntnis:

> Ein Tool ist nicht nur dann gut, wenn es technisch funktioniert. Es muss sich auch während langer Läufe verständlich und kontrollierbar anfühlen.

## 7. Inkrementeller Sync: nur neue Einträge nachladen

Ein besonders wichtiger Punkt war der spätere Regelbetrieb. Nach dem ersten großen Datenaufbau soll das Skript nicht jedes Mal die gesamte Vergangenheit neu laden. Es soll nur neue Ausschreibungen ergänzen.

Vorher war das System bereits idempotent:

```text
gleicher Eintrag -> kein Duplikat
```

Aber es war noch nicht wirklich inkrementell:

```text
alle alten Seiten werden trotzdem erneut geprüft
```

Der Unterschied ist wichtig:

```text
Idempotenz:
Es entstehen keine Duplikate.

Inkrementalität:
Der Sync hört früh auf, sobald bekannte Einträge erreicht werden.
```

Die Lösung war ein Stop-Kriterium: Wenn die Datenbank bereits Einträge enthält und der Sync in der Overview auf eine bekannte `project_url` trifft, stoppt er. Alles davor gilt als neu, alles danach als bereits bekannt.

Beispiel:

```text
1. neuer Eintrag
2. neuer Eintrag
3. bekannter Eintrag
4. alter Eintrag
```

Dann werden nur Eintrag 1 und 2 verarbeitet. Die Detailseite des bekannten Eintrags wird gar nicht mehr geladen.

Für Sonderfälle gibt es weiterhin:

```powershell
--full-sync
```

Damit kann man bewusst alle Einträge erneut prüfen.

Die Erkenntnis:

> Für den Alltag ist inkrementeller Sync sinnvoll. Für Datenqualität und Rechecks braucht es zusätzlich einen expliziten Full-Sync.

## 8. Adressen, Geocoding und Karte

Später entstand der Wunsch, auf einer Karte zu sehen, von wo das Geld kommt und wer es bekommt. Dafür reichten Gewinnername und Auftraggebername nicht aus. Es brauchte Adressen und danach Koordinaten.

Zuerst wurden die Adressfelder ergänzt:

```text
winner_address
procurement_office_address
```

Die Daten kamen aus den SIMAP-Detail-JSONs:

```text
decision.vendors[].vendorAddress
project-info.procOfficeAddress
```

Danach wurde Geocoding integriert. Aus Adressen werden Koordinaten:

```text
Adresse -> GeoAdmin SearchServer -> lat/lon
```

Dafür wurden neue Datenbankfelder ergänzt:

```text
winner_lat
winner_lon
winner_geocode_query
winner_geocode_status

procurement_office_lat
procurement_office_lon
procurement_office_geocode_query
procurement_office_geocode_status
```

Wichtig war, Geocoding nicht bei jedem Lauf neu zu machen. Deshalb werden Query und Status gespeichert. Wenn eine Adresse bereits erfolgreich gefunden wurde, wird sie übersprungen. Wenn sie bereits `not_found` war, wird sie ebenfalls nicht bei jedem Lauf erneut abgefragt.

Das Geocoding wurde in den normalen Update-Lauf integriert:

```text
Sync -> Geocoding -> CSV Export
```

Der Standardbefehl wurde:

```powershell
.\.venv\Scripts\python.exe .\scripts\update_data.py
```

Die Erkenntnis:

> Eine Karte braucht mehr als Adressen. Sie braucht persistierte Koordinaten, Statusinformationen und eine Cache-Logik, damit das System zuverlässig bleibt.

## 9. Datenbankmigration: ein echter Fehler mit Mehrfachzuschlägen

Bei der Erweiterung um Geocoding-Spalten trat ein Datenbankfehler auf:

```text
sqlite3.IntegrityError: UNIQUE constraint failed: awards.publication_number, awards.winner_position
```

Die Ursache war eine Migration, die bestehende Mehrfachzuschläge nicht korrekt übernahm. Beim Umbau der Tabelle wurde `winner_position` teilweise wieder auf `1` gesetzt. Dadurch entstanden mehrere Zeilen mit derselben Kombination aus `publication_number` und `winner_position`.

Das war kritisch, weil bereits echte Daten in der Datenbank lagen. Ein einfacher Reset wäre zwar möglich gewesen, aber nicht sauber. Deshalb wurde die Migration korrigiert:

- vorhandene `award_row_id` übernehmen
- vorhandene `winner_position` übernehmen
- neue Geocoding-Spalten ergänzen
- bei Zwischenzustand aus `awards_legacy` wiederherstellen

Die echte DB konnte dadurch wiederhergestellt werden.

Die Erkenntnis:

> Schemaänderungen sind riskanter als normale Codeänderungen. Migrationen müssen echte alte Datenzustände berücksichtigen, nicht nur das ideale neue Modell.

## 10. Dashboard: von Daten zu verständlichen Analysen

Nach der Datenpipeline wurde das Dashboard immer wichtiger. Es sollte nicht nur eine Tabelle zeigen, sondern Muster sichtbar machen.

Wichtige Dashboard-Funktionen wurden:

- KPI-Karten
- Zeitreihe für Volumen und Anzahl
- Top-Gewinner
- Top-Auftraggeber
- CPV-Auswertung
- Kanton-Auswertung
- Geo-Flüsse
- Single-Bid-Analyse
- Wettbewerbsintensität
- Gewinnerprofile
- Filter nach Datum, Auftraggeber, Gewinner, CPV, Text und Betrag

Ein wichtiger Schritt war die serverseitige Filterlogik. Wenn ein Zeitraum oder CPV-Code gewählt wird, werden nicht nur einzelne Charts im Browser gefiltert, sondern der gesamte Payload wird passend neu berechnet. Dadurch bleiben KPIs, Charts und Tabellen konsistent.

Beispiel:

```text
Filter: letzte 30 Tage
```

Dann sollen nicht nur die Tabellenzeilen anders sein, sondern auch:

- Gesamtvolumen
- Anzahl Zuschläge
- Top-Gewinner
- Zeitreihe
- CPV-Verteilung

Die Erkenntnis:

> Filter sind nicht nur UI-Elemente. Sie verändern die analytische Grundgesamtheit und müssen deshalb überall konsistent angewendet werden.

## 11. Gute Visualisierungen brauchen passende Aggregation

Mehrere Dashboard-Probleme zeigten, dass Visualisierung nicht nur bedeutet, "einen Chart zu machen".

### Zeitraum und Zeitachse

Beim Filter "letzte 30 Tage" blieb der Chart zuerst auf Monatsbasis. Das war wenig sinnvoll, weil 30 Tage in einem Monatschart kaum sichtbar werden.

Die Lösung war eine dynamische Zeitauflösung:

```text
kurzer Zeitraum -> Tage
mittlerer Zeitraum -> Wochen
langer Zeitraum -> Monate
```

### Kantone pro 100'000 Einwohner

Bei "Zuschläge pro Kanton" wurde klar, dass absolute Zahlen unfair sind. Zürich hat viel mehr Einwohner als kleine Kantone. Deshalb wurde zusätzlich berechnet:

```text
Zuschläge pro 100'000 Einwohner
Volumen pro 100'000 Einwohner
```

Das macht Kantone besser vergleichbar.

### Geo-Flüsse aggregieren

Einzelne Linien auf der Karte sind anschaulich, aber bei vielen Daten schnell unübersichtlich. Deshalb wurden Flüsse zusätzlich nach Kantonen aggregiert:

```text
Buyer-Kanton -> Winner-Kanton
```

Mit Kennzahlen wie:

- Anzahl Zuschläge
- Gesamtvolumen
- Durchschnittsbetrag
- interkantonal oder innerkantonal

Die Erkenntnis:

> Eine gute Visualisierung hängt stark davon ab, ob die Aggregation zur Frage passt.

## 12. CPV-Codes: korrekt ist nicht automatisch verständlich

CPV-Codes sind für die Daten wichtig, aber als reine Zahlen schwer lesbar:

```text
45000000
72000000
```

Deshalb wurden CPV-Codes mit Klartext ergänzt, zum Beispiel:

```text
45000000 - Bauarbeiten
72000000 - IT-Dienste: Beratung, Software, Internet und Support
```

Zusätzlich wurde erkannt, dass unterschiedliche Codes teilweise dieselbe oder sehr ähnliche Bezeichnungen haben. Für manche Charts ist es deshalb sinnvoller, nach Kategorie bzw. Bezeichnung zu gruppieren.

Die Erkenntnis:

> Rohcodes sind für Maschinen gut. Für journalistische Analyse müssen sie übersetzt und sinnvoll gruppiert werden.

## 13. Nicht jede mögliche Analyse ist sinnvoll

Zwischendurch wurden viele zusätzliche Analyseideen diskutiert:

- Lorenz-Kurve
- Gini-Koeffizient
- Top-10-Gewinner vs. Rest
- Repeat Winners
- Wettbewerb vs. Preis
- Outlier Detection
- Risiko-Score
- Netzwerk-Analyse
- Budget-Rush

Technisch kann man viele Charts bauen. Aber ein Dashboard wird dadurch nicht automatisch besser. Manche Analysen brauchen mehr Kontext, als die vorhandenen Daten liefern. Ein "Risiko-Score" kann zum Beispiel schnell suggerieren, dass eine Beschaffung problematisch ist, obwohl es legitime Gründe geben kann:

- nur ein Anbieter wegen Spezialisierung
- hoher Betrag wegen Projektgröße
- wiederholter Gewinner wegen Rahmenvertrag

Deshalb wurde ein Teil der zusätzlichen Deep-Dive-Analysen wieder entfernt und das Dashboard auf die stärkeren, verständlicheren Kernanalysen fokussiert.

Die Erkenntnis:

> Ein gutes Dashboard ist kuratiert. Es soll Fragen sichtbar machen, aber nicht durch zu viele oder zu spekulative Analysen falsche Sicherheit erzeugen.

## 14. UI-Details sind Teil der Qualität

Mehrere kleinere UI-Probleme waren trotzdem wichtig.

Ein Beispiel waren KPI-Karten, bei denen große CHF-Werte nicht sauber hineinpassten. Dadurch entstanden unschöne Umbrüche. Die Lösung war kompakteres Formatting, zum Beispiel:

```text
1.2 Mio.
45.7 Mio.
```

Ein anderes Beispiel waren Umlaute. Begriffe wie "Zuschläge", "Flüsse" oder "Häufigkeit" sollten korrekt angezeigt werden und nicht als `ae`, `oe`, `ue`.

Auch ein externer Frontend-Fehler trat auf:

```text
ReferenceError: L is not defined
```

Die Ursache war ein falscher `integrity`-Hash bei Leaflet. Dadurch wurde das Karten-Script vom Browser blockiert. Der Hash wurde korrigiert und zusätzlich ein Schutz eingebaut, damit das Dashboard nicht komplett abstürzt, falls Leaflet einmal nicht lädt.

Die Erkenntnis:

> Datenqualität und UI-Qualität gehören zusammen. Wenn ein Dashboard optisch kaputt wirkt, sinkt auch das Vertrauen in die Daten.

## 15. marimo als Ergänzung zum Dashboard

Später wurde zusätzlich `marimo` integriert. Das ist ein reaktives Python-Notebook, das gut zu explorativen Analysen passt.

Das Dashboard ist eher für wiederkehrende, klare Auswertungen gedacht. marimo eignet sich dagegen für:

- experimentelle Analysen
- schnelles Ausprobieren von Filtern
- zusätzliche journalistische Deep Dives
- reproduzierbare Notebooks als Python-Dateien

Ergänzt wurden:

```text
notebooks/simapwatch_marimo.py
scripts/start_marimo.py
```

Ein Fehler beim ersten Start war:

```text
NameError: name 'mo' is not defined
```

Die Ursache war, dass `mo.md(...)` verwendet wurde, bevor `marimo` importiert war. Die Lösung war eine Import-Zelle:

```python
import marimo as mo
```

Die Erkenntnis:

> Das Dashboard sollte stabil und klar bleiben. Experimentelle Analysen passen besser in ein Notebook wie marimo.

## 16. Wichtigste technische Erkenntnisse

### 1. SIMAP ist keine stabile HTML-Quelle

Die erste Annahme war, HTML zu parsen. Live zeigte sich aber, dass viele Daten über APIs geladen werden. Deshalb muss der Scraper flexibel sein und sowohl HTML als auch JSON verstehen.

### 2. Vollständigkeit braucht Pagination

Ohne `lastItem`-Pagination wären nur die ersten 20 Einträge gesammelt worden. Das hätte alle Analysen verzerrt.

### 3. Mehrfachzuschläge müssen als mehrere Zeilen gespeichert werden

Eine Publikation kann mehrere Gewinner enthalten. Deshalb ist `winner_position` zentral.

### 4. Inkrementeller Sync ist mehr als Upsert

Upsert verhindert Duplikate. Inkrementeller Sync spart zusätzlich Zeit, weil alte Seiten gar nicht mehr verarbeitet werden.

### 5. Geocoding braucht Cache und Status

Koordinaten sind nicht garantiert. Deshalb müssen `ok`, `not_found`, Query und Koordinaten gespeichert werden.

### 6. Migrationen sind kritisch

Schemaänderungen können echte Daten beschädigen. Recovery-Logik und vorsichtige Migrationen sind wichtig.

### 7. Dashboard-Analysen müssen fachlich begründet sein

Nicht jeder Chart ist sinnvoll. Gute Analysen müssen zur Datenqualität und zur Fragestellung passen.

## 17. Wichtigste fachliche Erkenntnisse

Das Projekt zeigt, dass öffentliche Beschaffungsdaten viele spannende Fragen ermöglichen, aber vorsichtig interpretiert werden müssen.

Sinnvoll und robust sind zum Beispiel:

- Volumen über Zeit
- Anzahl Zuschläge über Zeit
- Top-Gewinner
- Top-Auftraggeber
- CPV-Verteilung
- Zuschläge pro Kanton
- Zuschläge pro 100'000 Einwohner
- Single-Bid-Anteil
- interkantonale Geldflüsse

Vorsichtiger sind:

- Risiko-Scores
- Verdachtslisten
- Gini-Interpretationen
- Outlier ohne Kontext
- Aussagen über "zu wenig Wettbewerb"

Ein einzelnes Angebot ist nicht automatisch problematisch. Ein hoher Betrag ist nicht automatisch auffällig. Ein wiederholter Gewinner kann auf Abhängigkeit hindeuten, aber auch auf Spezialisierung.

Die Daten liefern also vor allem Recherchehinweise. Sie ersetzen keine journalistische Einordnung.

## 18. Reflexion zum KI-Einsatz

Die Entwicklung war stark KI-unterstützt, aber nicht automatisch. Die Chatlogs zeigen, dass die Qualität vor allem durch die Iteration entstanden ist:

- Fehler wurden durch echte Ausgaben erkannt.
- Anforderungen wurden nachgeschärft.
- UI wurde anhand von Screenshots bewertet.
- Zu große Lösungen wurden zurückgenommen.
- Fachliche Prioritäten wurden neu gesetzt.

KI war besonders hilfreich bei:

- Architekturvorschlägen
- TDD-Struktur
- Parser-Code
- Repository-Logik
- Tests
- Dashboard-Aggregationen
- Debugging von Stacktraces
- Integration von marimo

Entscheidend waren aber die menschlichen Rückmeldungen:

- "Warum updated es nicht?"
- "Mehr Einträge laden."
- "Mehrere Firmen sollen eigene Zeilen haben."
- "Später sollen nur neue Ausschreibungen dazukommen."
- "Die Karte soll echte Koordinaten haben."
- "Vorher war besser."

Die wichtigste Erkenntnis zum KI-Einsatz:

> KI kann sehr gut beim Umsetzen helfen, aber die fachliche Kontrolle, Priorisierung und Bewertung der Ergebnisse bleibt entscheidend.

## 19. Offene nächste Schritte

Sinnvolle nächste Schritte wären:

- eine Methodikseite im Dashboard ergänzen
- Entity Resolution für Firmen- und Auftraggebernamen verbessern
- Geocoding-Qualität genauer klassifizieren
- Dashboard-Drilldowns einbauen, z.B. Klick auf Kanton oder CPV setzt Filter
- Leaflet lokal ausliefern, damit das Dashboard weniger abhängig vom CDN ist
- experimentelle Deep-Dive-Analysen ins marimo-Notebook verschieben

Besonders wichtig wäre eine Methodikseite. Dort sollte erklärt werden:

- welche Daten von SIMAP geladen werden
- wie Mehrfachzuschläge gezählt werden
- was fehlende Beträge bedeuten
- wie Geocoding funktioniert
- welche Grenzen die Daten haben
- wie Kennzahlen wie Single-Bid-Anteil oder Kantonflüsse zu verstehen sind

## 20. Schlussfazit

simapWatch entwickelte sich von einer ersten Scraper-Idee zu einer funktionierenden kleinen Datenplattform. Die wichtigsten Fortschritte waren nicht nur neue Features, sondern vor allem bessere Datenmodellierung und bessere Interpretation:

- von HTML-Fixtures zur SIMAP-API
- von 20 Einträgen zu vollständiger Pagination
- von einem Gewinner pro Publikation zu mehreren Gewinnerzeilen
- von manuellem Lauf zu inkrementellem Update
- von Adressen zu geocodierten Kartenflüssen
- von Rohdaten zu Dashboard-Analysen
- von Dashboard zu zusätzlichem marimo-Notebook

Die wichtigste Gesamterkenntnis ist:

> Bei datenjournalistischen Tools ist technische Korrektheit nur die Grundlage. Entscheidend ist, ob die Daten vollständig, nachvollziehbar modelliert und vorsichtig interpretiert werden.

Das Projekt ist deshalb nicht nur ein Scraper, sondern ein Beispiel für iterative, KI-unterstützte Entwicklung: Anforderungen wurden sichtbar, Fehler wurden ernst genommen, Lösungen wurden getestet, und überladene Ideen wurden wieder reduziert. Genau dadurch wurde das Tool Schritt für Schritt besser und verständlicher.
