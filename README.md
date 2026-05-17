# simapWatch-
Transparenz-Tool fuer oeffentliche Beschaffungszuschlaege in der Schweiz.

simapWatch- laedt Ausschreibungs- und Zuschlagsdaten aus SIMAP, speichert sie in SQLite, geocodiert fehlende Koordinaten und exportiert eine Auswertungs-CSV. Darauf aufbauend gibt es ein Web-Dashboard und ein reaktives `marimo`-Notebook.

## Projekteinleitung

Das Projekt automatisiert die Beobachtung von SIMAP-Daten. Statt Ausschreibungen manuell zu durchsuchen, holt sich das Tool die oeffentlichen SIMAP-Infos regelmaessig ab, verarbeitet die Detailseiten und legt die Ergebnisse strukturiert ab.

Im Kern passiert dabei Folgendes:

- Neue oder geaenderte Zuschlagsdaten werden aus SIMAP eingelesen.
- Die Daten werden in einer lokalen SQLite-Datenbank gespeichert.
- Fehlende Ortsinformationen werden automatisch ueber Geocoding ergaenzt.
- Aus der Datenbank wird eine Analyse-CSV erzeugt.
- Das Dashboard und das Notebook machen die Ergebnisse durchschaubar und auswertbar.

Damit deckt das Projekt den ganzen Weg ab: Daten holen, verarbeiten, anreichern, speichern und sichtbar machen.

## Projektuebersicht

- [src/simapwatch/cli.py](src/simapwatch/cli.py) fuehrt einen einzelnen Sync-Lauf aus.
- [src/simapwatch/update_runner.py](src/simapwatch/update_runner.py) kombiniert Sync, Geocoding und CSV-Export.
- [src/simapwatch/analysis_cli.py](src/simapwatch/analysis_cli.py) erzeugt die Analyse-CSV aus der SQLite-Datenbank.
- [src/simapwatch/dashboard/server.py](src/simapwatch/dashboard/server.py) startet den lokalen Dashboard-Server.
- [src/simapwatch/dashboard/service.py](src/simapwatch/dashboard/service.py) bereitet die Dashboard-Daten auf.
- [scripts/update_data.py](scripts/update_data.py) ist der empfohlene Regelbetrieb fuer einen kompletten Update-Lauf.
- [scripts/start_dashboard.py](scripts/start_dashboard.py) startet das Dashboard mit den Standardwerten.
- [scripts/start_marimo.py](scripts/start_marimo.py) startet das Notebook im Editor oder als App.

Die wichtigsten Artefakte sind:

- `src/simapwatch.db` fuer die SQLite-Datenbank
- `src/analysis.csv` fuer den Export

## Voraussetzungen

- Windows mit PowerShell
- Python 3 mit aktiviertem `venv`-Support
- Internetzugang fuer SIMAP, Geocoding und das Laden der Detailseiten

Die Projekt-Tools werden lokal in einer virtuellen Umgebung installiert. Die folgenden Beispiele gehen davon aus, dass du im Projektroot arbeitest.

## Setup Von Null

1. Virtuelle Umgebung anlegen, falls noch keine vorhanden ist:
   ```powershell
   py -m venv .venv
   ```

2. Virtuelle Umgebung aktivieren:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Abhaengigkeiten installieren:
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. Optional die Tests ausfuehren:
   ```powershell
   python -m unittest discover -s tests -p "test_*.py"
   ```

Wenn PowerShell das Aktivieren der Umgebung blockiert, kann fuer die aktuelle Sitzung dieses Kommando helfen:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

## Erster Datenaufbau

Der einfachste Einstieg ist der kombinierte Update-Lauf. Er holt neue Daten, geocodiert fehlende Koordinaten und erzeugt die Analyse-CSV.

```powershell
.\.venv\Scripts\python.exe .\scripts\update_data.py
```

Was dabei passiert:

- Die SQLite-Datenbank wird unter `src/simapwatch.db` gepflegt.
- Die Analyse-CSV wird unter `src/analysis.csv` geschrieben.
- Fehlende Koordinaten werden automatisch geocodiert.
- Bereits bekannte oder als `not_found` markierte Adressen werden nicht bei jedem Lauf neu angefragt.

Die wichtigsten Schalter fuer den Regelbetrieb stehen direkt in [scripts/update_data.py](scripts/update_data.py):

- `DB_PATH`
- `CSV_PATH`
- `MAX_WORKERS`
- `TIMEOUT_SECONDS`
- `RESET_DB`
- `FULL_SYNC`
- `SKIP_CSV`
- `GEOCODE_MISSING`

## Sync Einzelner Lauf

Wenn du nur die Rohdaten synchronisieren willst, nutze die CLI direkt.

```powershell
.\.venv\Scripts\python.exe -m simapwatch.cli --db-path src/simapwatch.db
```

Wichtige Optionen:

- `--reset-db` loescht alte Awards, Sync-Laeufe und Parse-Fehler vor dem Lauf.
- `--full-sync` liest alle Overview-Seiten statt beim ersten bekannten Eintrag zu stoppen.
- `--max-workers` steuert die parallelen Detail-Requests.
- `--timeout-seconds` legt den HTTP-Timeout fest.

Wenn du nur die Datenbasis neu aufbauen willst, ist dieser Befehl typisch:

```powershell
.\.venv\Scripts\python.exe -m simapwatch.cli --db-path src/simapwatch.db --reset-db --full-sync
```

## Analyse-Export

Die Analyse-CSV kann auch separat erzeugt werden, falls die Datenbank bereits vorhanden ist.

```powershell
.\.venv\Scripts\python.exe -m simapwatch.analysis_cli --db-path src/simapwatch.db --csv-path src/analysis.csv
```

Das ist nuetzlich, wenn du nur den Export erneuern willst, ohne einen neuen Sync auszufuehren.

## Dashboard Starten

Das Dashboard zeigt die Daten lokal im Browser und nutzt die geocodierten Koordinaten aus der Datenbank.

```powershell
.\.venv\Scripts\python.exe .\scripts\start_dashboard.py
```

Danach im Browser oeffnen:

```text
http://127.0.0.1:8050
```

Standardwerte fuer den Dashboard-Start stehen in [scripts/start_dashboard.py](scripts/start_dashboard.py):

- `DB_PATH`
- `HOST`
- `PORT`

## Marimo Notebook

Zusatzlich zum Web-Dashboard gibt es ein reaktives Notebook fuer Exploration und Analyse.

Notebook im Editor oeffnen:

```powershell
.\.venv\Scripts\python.exe .\scripts\start_marimo.py
```

Oder als App starten:

```powershell
.\.venv\Scripts\python.exe -m marimo run .\notebooks\simapwatch_marimo.py
```

Die Startlogik steht in [scripts/start_marimo.py](scripts/start_marimo.py). Dort kannst du zwischen diesen Modi wechseln:

- `edit` fuer die Notebook-Ansicht im Editor
- `run` fuer die App-Ansicht

## Typische Arbeitsablaeufe

1. Einmalig Umgebung einrichten und Abhaengigkeiten installieren.
2. Mit [scripts/update_data.py](scripts/update_data.py) einen kompletten Datenlauf ausfuehren.
3. Das Dashboard mit [scripts/start_dashboard.py](scripts/start_dashboard.py) starten und im Browser pruefen.
4. Fuer manuelle Analysen das Notebook mit [scripts/start_marimo.py](scripts/start_marimo.py) oeffnen.
5. Bei Aenderungen an der Datenlogik die Tests erneut laufen lassen.

## Tests

Die Tests laufen direkt mit der aktivierten virtuellen Umgebung:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Wenn ein einzelner Bereich geprueft werden soll, sind die Tests in [tests/](tests/) nach Funktion getrennt, zum Beispiel fuer Dashboard, Parser, Geocoding und Sync.

## Hinweis Zur Datenhaltung

Die Datenbank und die CSV sind Laufzeit-Artefakte. Wenn du sie loeschen willst, kannst du den Update-Lauf mit `--reset-db` starten oder die Dateien manuell entfernen und anschliessend den Update-Workflow erneut ausfuehren.
