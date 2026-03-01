# simapWatch-
Transparenz-Dashboard fuer oeffentliche Beschaffungszuschlaege in der Schweiz

## Local Test

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

## Run One Sync

Option 1 (empfohlen)
```powershell
cd src
..\.venv\Scripts\python.exe -m simapwatch.cli --db-path simapwatch.db
```

Option 2 (aus Projektroot)
```powershell
$env:PYTHONPATH="src"
.venv\Scripts\python.exe -m simapwatch.cli --db-path simapwatch.db
```

## Reset And Rebuild

Bestehende Eintraege vor einem kompletten Neuaufbau loeschen:
```powershell
cd src
..\.venv\Scripts\python.exe -m simapwatch.cli --db-path simapwatch.db --reset-db
```

Schnellerer Lauf mit parallelen Detail-Requests:
```powershell
cd src
..\.venv\Scripts\python.exe -m simapwatch.cli --db-path simapwatch.db --max-workers 12
```

## Incremental Sync

Normale Folge-Laeufe stoppen beim ersten bereits bekannten Eintrag und laden damit nur neue Ausschreibungen:
```powershell
cd src
..\.venv\Scripts\python.exe -m simapwatch.cli --db-path simapwatch.db --max-workers 12
```

Kompletter Vollabgleich ueber alle Overview-Seiten:
```powershell
cd src
..\.venv\Scripts\python.exe -m simapwatch.cli --db-path simapwatch.db --full-sync
```

## Analysis Export

Analyse-CSV aus der SQLite-Datenbank erzeugen:
```powershell
cd src
..\.venv\Scripts\python.exe -m simapwatch.analysis_cli --db-path simapwatch.db --csv-path analysis.csv
```

`pandas.DataFrame`-Export steht im Code ueber `load_analysis_dataframe(...)` bereit.
Dafuer muss `pandas` installiert sein:
```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Update Script

Ein Befehl fuer den Regelbetrieb: inkrementeller Sync plus Analyse-CSV-Refresh.

Python-Skript:
```powershell
.\.venv\Scripts\python.exe .\scripts\update_data.py
```

Direkt ueber Python-API:
```powershell
$env:PYTHONPATH="src"
.venv\Scripts\python.exe -c "from simapwatch import run_update, default_progress_printer; run_update(db_path='src/simapwatch.db', csv_path='src/analysis.csv', max_workers=12, progress_callback=default_progress_printer)"
```

Konfiguration fuer das Skript steht direkt in [update_data.py](C:/Users/elias/Desktop/FHNW/KIP/simapWatch-/scripts/update_data.py):
- `DB_PATH`
- `CSV_PATH`
- `MAX_WORKERS`
- `RESET_DB`
- `FULL_SYNC`
- `SKIP_CSV`
