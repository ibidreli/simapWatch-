day 2 - 28.02.2026

example_multimple_accepts.txt problem ist aktuell noch das wenn mehrer firmen den zuschlag bekommen nur für die oberste firma ein eintrag im data frame gemacht wurde ich möchte allerdings für jede firma die einen zuschlag auf eine auschreibung erhalten haben für jede firma eine eigene zeile im dataframe siehe das example das ich eingebunden habe https://www.simap.ch/de/project-detail/e2af7463-f5a5-4a07-aa7a-d0d6bb1ea0a5#zuschlag zudem geht es ehr lange bis die auschreibungen gesammelt werden  um das zu initialisieren sollen alle einträgge aus dem dataframe gelöscht werden und dann werde ich es von grund auf neu starten das alles stimmt zudem ist es aktuell sehr langsam gibt es eine möglich keit etwas schneller zu machen denke dabei an das test driven development


Worked for 9m 29s
Mehrfach-Zuschläge sind jetzt korrekt modelliert, die lokale DB ist geleert, und der Sync kann parallel laufen.

Geändert

Parser liefert jetzt mehrere Gewinnerzeilen pro Publikation:
detail_parser.py
neu: parse_award_details(...)
parse_award_detail(...) bleibt als Kompatibilitäts-Fallback auf die erste Zeile
Datenmodell erweitert um winner_position:
contracts.py
DB-Schema auf „eine Zeile pro Gewinner“ umgestellt:
sqlite_repository.py
neue technische ID: award_row_id = publication_number::winner_position
neue Methode: clear_all_data()
neue Methode: get_awards_by_publication_number(...)
Sync lädt Detailseiten jetzt parallel:
sync_service.py
max_workers konfigurierbar
CLI erweitert:
cli.py
--reset-db
--max-workers
README ergänzt:
README.md
Wichtiges Verhalten jetzt

Wenn 7 Firmen denselben Zuschlagseintrag teilen, entstehen 7 Zeilen in awards.
new_count und updated_count zählen jetzt Gewinner-Zeilen, nicht nur Publikationen.
Für dein Beispiel example_multimple_accepts.txt werden 7 Gewinner erkannt.
TDD-Status

neue Tests für:
mehrere Gewinner in HTML
mehrere Gewinner in API-JSON
mehrere DB-Zeilen pro Publikation
Reset
parallelen Detail-Fetch
Testlauf:
python.exe -m unittest discover -s tests -p "test_*.py"
Ergebnis: 19 tests OK
DB-Reset

Die bestehende lokale DB simapwatch.db wurde bereits geleert.
Verifiziert: count_awards() == 0
Neu starten

cd src
..\.venv\Scripts\python.exe -m simapwatch.cli --db-path simapwatch.db --reset-db --max-workers 12
Hinweis:

--reset-db loescht vor dem Lauf awards, sync_runs und parse_errors.
--max-workers 12 beschleunigt den langsamen Teil, also die Detailseiten.
Naechste sinnvolle Schritte:

Live-Sync einmal laufen lassen und die ersten echten Mehrfach-Zuschlaege in der DB pruefen.
Danach das Exportformat fuer dein DataFrame definieren, damit klar ist, welche Spalten direkt aus awards kommen sollen.

6 files changed
+231
-5
Undo

Review
README.md
src/simapwatch/cli.py
src/simapwatch/domain/contracts.py
src/simapwatch/parsers/__init__.py
tests/test_detail_parser.py
tests/test_sync_integration.py
okay noch eine letzte sache die workers sollten alle richtig beendet werden wen ich ctrl c klicke und ich möchte in der console updates wie viele auschreibungen es gemacht hat


Worked for 7m 26s
Implementiert.

Neu

Sauberer Interrupt-Pfad bei Ctrl+C
Laufende Fortschrittsausgabe in der Konsole
Tests fuer Progress und Interrupt-Shutdown
Geaenderte Dateien:

sync_service.py
init.py
cli.py
test_sync_integration.py
Was jetzt passiert

Beim Start bekommst du Progress-Zeilen wie:
progress processed=0/120 new=0 updated=0 errors=0
progress processed=1/120 new=1 updated=0 errors=0
progress processed=2/120 new=2 updated=0 errors=0
Am Ende kommt weiter die Zusammenfassung:
status=success overview=120 new=118 updated=2 errors=0
Bei Ctrl+C

Der Sync bricht kontrolliert ab.
Noch nicht gestartete Futures werden abgebrochen.
Der Executor wird mit shutdown(wait=False, cancel_futures=True) beendet.
Die CLI endet mit Exit-Code 130.
Es wird eine Abschlusszeile ausgegeben:
status=interrupted overview=120 new=37 updated=0 errors=1
Wichtige technische Grenze

Bereits laufende HTTP-Requests kann Python mit Threads nicht hart killen.
Sie laufen noch bis ihr Timeout oder Request-Ende erreicht ist.
Alles, was noch in der Queue war, wird aber sofort verworfen.
Genau deshalb ist --timeout-seconds weiter wichtig.
Teststatus

python.exe -m unittest discover -s tests -p "test_*.py"
Ergebnis: 21 tests OK
Dein Aufruf bleibt

cd src
..\.venv\Scripts\python.exe -m simapwatch.cli --db-path simapwatch.db --reset-db --max-workers 12
Wenn du willst, kann ich als naechstes noch eine kompaktere Progress-Ausgabe einbauen, z. B. nur alle 10 Eintraege statt nach jedem einzelnen.


3 files changed
+126
-7
Undo

Review
src/simapwatch/cli.py
src/simapwatch/services/__init__.py
tests/test_sync_integration.py
User attachment
irgendwie strtet es nicht


Worked for 2m 22s
Das Problem war real: der Prozess lief, aber vor der ersten Ausgabe wurde zuerst die komplette Overview eingesammelt. Dadurch sah es so aus, als starte nichts.

Ich habe das jetzt geändert.

Neu in der Konsole
Direkt nach dem Start kommt jetzt sofort:

starting overview_url=... db_path=simapwatch.db workers=12 reset=True
Schon waehrend des Einsammelns der Overview:

overview pages=1 discovered=20
overview pages=2 discovered=40
overview pages=3 discovered=60
Danach wie bisher der Detail-Fortschritt:

progress processed=1/240 new=1 updated=0 errors=0
progress processed=2/240 new=2 updated=0 errors=0
Am Ende:

status=success overview=240 new=240 updated=0 errors=0
Warum dein Screenshot komisch aussah

Der Umbruch nach simapwatch.db ist nur Zeilenumbruch im Terminal, nicht der Fehler.
Das eigentliche Problem war die fehlende fruehe Ausgabe.
Verifiziert

Tests: 22 OK
So startest du jetzt

cd src
..\.venv\Scripts\python.exe -m simapwatch.cli --db-path simapwatch.db --reset-db --max-workers 12
Wenn der alte Lauf noch offen ist:

Ctrl+C
Befehl noch einmal starten
Wenn du willst, kann ich als Nächstes noch ein --limit-pages einbauen, damit du zum Testen erst nur z. B. die ersten 3 Overview-Seiten lädst.


3 files changed
+117
-1
Undo

Review
src/simapwatch/cli.py
src/simapwatch/services/sync_service.py
tests/test_sync_integration.py
also es ist mir nicht so wichtig ob es anzeigt 100 von 10000 auschreibungen gesammelt wichtig ist das es eifach durchläuft und wichtig ist auch das wenn ich das script später starte nur die neuen auschreibungen zum data frame dazukommen

Dann ist die Regel klar:

--reset-db nur fuer einen kompletten Neuaufbau
fuer normale Folge-Laeufe ohne --reset-db starten
Wichtig fuer dein aktuelles System:

Die DB ist die Quelle der Wahrheit, nicht der temporäre Console-Progress.
Bereits vorhandene Eintraege werden nicht doppelt gespeichert.
Neue Ausschreibungen werden eingefuegt.
Bereits bekannte Ausschreibungen bleiben unveraendert oder werden bei Aenderungen aktualisiert.
Konkret:

cd src
..\.venv\Scripts\python.exe -m simapwatch.cli --db-path simapwatch.db --max-workers 12
Nicht verwenden fuer normale Updates:

--reset-db
Warum das funktioniert:

Jede Gewinner-Zeile hat einen stabilen Schluessel:
award_row_id = publication_number::winner_position
Dadurch macht der Lauf ein upsert:
neu -> INSERT
schon vorhanden -> kein Duplikat
geaendert -> UPDATE
Das heisst:

spaeterer Start fuegt nur neue Zeilen hinzu
bestehende Zeilen werden nicht nochmals dupliziert
Wichtiger Zusatz:

Aktuell durchsucht der Sync trotzdem noch die gesamte Overview und prueft dann per Upsert, ob etwas neu ist.
Fachlich ist das korrekt.
Performance-maessig ist es noch nicht optimal.
Der naechste sinnvolle technische Schritt waere:

echten inkrementellen Sync bauen
beim ersten bereits bekannten Eintrag abbrechen oder ab einer gespeicherten letzten Publikation weiterlaufen
Das wuerde dein eigentliches Ziel sauber treffen: nicht nur keine Duplikate, sondern auch deutlich schneller bei spaeteren Runs.

Wenn du willst, setze ich als naechstes genau diesen inkrementellen Sync um.


ja genau gerne

Ich setze jetzt den inkrementellen Sync um: Standardverhalten wird „nur neue Ausschreibungen einsammeln“, statt jedes Mal die komplette History erneut durchzuprüfen. Ich sichere das zuerst mit Tests ab, damit wir das Stopp-Kriterium sauber treffen und keine neuen Einträge übersehen.

Ran Get-Content -Path src/simapwatch/repository/sqlite_repository.py


Ran Get-Content -Path tests/test_sync_integration.py


Ran Get-Content -Path src/simapwatch/cli.py


Ran Get-Content -Path src/simapwatch/services/sync_service.py


Ich ziehe das jetzt auf die eigentliche Optimierung um: die Overview wird künftig abgebrochen, sobald der erste bereits bekannte Eintrag auftaucht. Das entspricht genau deinem Zielbild „spätere Runs sollen nur neue Ausschreibungen dazunehmen“ und spart den größten Teil der Zeit.

Edited file
test_sync_integration.py
+105
-0

        self.mapping = mapping
        self.calls: list[str] = []

    def fetch_text(self, url: str) -> str:
        self.calls.append(url)
        return self.mapping[url]

    def test_incremental_sync_stops_when_first_known_entry_is_reached(self) -> None:
        overview_url = (
            "https://www.simap.ch/api/publications/v2/project/project-search"
            "?lang=de&newestPubTypes=award_tender"
        )
        page2_url = (
            "https://www.simap.ch/api/publications/v2/project/project-search"
            "?lang=de&newestPubTypes=award_tender&lastItem=cursor-1"
        )
        detail_url_new_1 = "https://www.simap.ch/api/publications/v1/project/proj-new-1/publication-details/pub-new-1?lang=de"
        detail_url_new_2 = "https://www.simap.ch/api/publications/v1/project/proj-new-2/publication-details/pub-new-2?lang=de"
        detail_url_known = "https://www.simap.ch/api/publications/v1/project/proj-known/publication-details/pub-known?lang=de"

        first_page = {
            "projects": [
                {
                    "id": "proj-new-1",
                    "publicationId": "pub-new-1",
                    "title": {"de": "Projekt Neu 1"},
                    "procOfficeName": {"de": "Amt 1"},
                    "pubType": "award",
                    "publicationDate": "2026-02-26",
                },
                {
                    "id": "proj-new-2",
                    "publicationId": "pub-new-2",
                    "title": {"de": "Projekt Neu 2"},
                    "procOfficeName": {"de": "Amt 2"},
                    "pubType": "award",
                    "publicationDate": "2026-02-25",
                },
                {
                    "id": "proj-known",
                    "publicationId": "pub-known",
                    "title": {"de": "Projekt Bekannt"},
                    "procOfficeName": {"de": "Amt 3"},
                    "pubType": "award",
                    "publicationDate": "2026-02-24",
                },
            ],
            "pagination": {"lastItem": "cursor-1", "itemsPerPage": 20},
        }
        second_page = {
            "projects": [
                {
                    "id": "proj-old",
                    "publicationId": "pub-old",
                    "title": {"de": "Projekt Alt"},
                    "procOfficeName": {"de": "Amt 4"},
                    "pubType": "award",
                    "publicationDate": "2026-02-23",
                }
            ],
            "pagination": {"itemsPerPage": 20},
        }

        detail_payload = lambda number, name: json.dumps(
            {
                "procurement": {"orderType": "construction"},
                "decision": {"vendors": [{"vendorName": name, "price": {"price": 10.0}}]},
                "base": {"publicationNumber": number, "publicationDate": "2026-02-25"},
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            repository = SqliteAwardRepository(db_path)
            repository.init_schema()

            bootstrap_fetcher = DictFetcher(
                {
                    "https://example.local/bootstrap": """
                    <article id="proj-known">
                        <h6 aria-label="Projekttitel: Project Known"></h6>
                        <p aria-label="Beschaffungsstelle: Office Known"></p>
                        <p aria-label="Publikationstyp: Zuschlag"></p>
                        <span aria-label="Publikationsdatum: 24.02.2026"></span>
                        <a href="/api/publications/v1/project/proj-known/publication-details/pub-known?lang=de"></a>
                    </article>
                    """,
                    detail_url_known: detail_payload("PUB-KNOWN", "Known Vendor"),
                }
            )
            SyncService(fetcher=bootstrap_fetcher, repository=repository).run_once("https://example.local/bootstrap")

            fetcher = DictFetcher(
                {
                    overview_url: json.dumps(first_page),
                    page2_url: json.dumps(second_page),
                    detail_url_new_1: detail_payload("PUB-NEW-1", "Vendor 1"),
                    detail_url_new_2: detail_payload("PUB-NEW-2", "Vendor 2"),
                    detail_url_known: detail_payload("PUB-KNOWN", "Known Vendor"),
                }
            )

            run = SyncService(fetcher=fetcher, repository=repository).run_once(overview_url)

            self.assertEqual(run.status, "success")
            self.assertEqual(run.overview_count, 2)
            self.assertEqual(run.new_count, 2)
            self.assertNotIn(page2_url, fetcher.calls)
            self.assertNotIn(detail_url_known, fetcher.calls)

    def test_sync_interrupt_shuts_down_executor_without_waiting(self) -> None:
Ran .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" for 3s


Die Red-Phase ist sauber: aktuell lädt der Sync trotz bekanntem Eintrag weiter. Ich ergänze jetzt den Known-Entry-Stopp in Repository und Service, ohne das Upsert-Verhalten anzufassen.

Edited file
sqlite_repository.py
+8
-0


    def has_project_url(self, project_url: str) -> bool:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM awards WHERE project_url = ? LIMIT 1",
                (project_url,),
            ).fetchone()
            return row is not None

    def get_award_by_row_id(self, award_row_id: str) -> Optional[dict[str, object]]:
Ich stelle den Abbruch jetzt direkt im Overview-Loop um. Dadurch bleibt die Logik lokal nachvollziehbar: sobald die DB nicht mehr leer ist und der erste bekannte Detail-Link auftaucht, wird der neue Lauf an genau dieser Grenze beendet.

Edited file
sync_service.py
+25
-1

        progress_callback: Optional[Callable[[SyncProgress], None]] = None,
        incremental: bool = True,
    ):
        self._progress_callback = progress_callback
        self._incremental = incremental

            raw = self._fetcher.fetch_text(overview_url)
            entries = parse_overview(raw)
            entries = self._filter_incremental_entries(parse_overview(raw))
            if entries:
            page_entries = parse_overview(raw)
            should_stop = False
            for entry in page_entries:
                    continue
                if self._should_stop_at_known_entry(entry.project_url):
                    should_stop = True
                    break
                seen_urls.add(entry.project_url)

            if should_stop:
                break

            last_item = extract_overview_pagination_last_item(raw)

    def _filter_incremental_entries(self, entries: list) -> list:
        filtered = []
        for entry in entries:
            if self._should_stop_at_known_entry(entry.project_url):
                break
            filtered.append(entry)
        return filtered

    def _should_stop_at_known_entry(self, project_url: str) -> bool:
        if not self._incremental:
            return False
        if self._repository.count_awards() == 0:
            return False
        return self._repository.has_project_url(project_url)

    def _fetch_and_parse_entry(self, entry) -> tuple[object, list]:
Ich ziehe noch eine kleine Korrektur nach: die Known-Entry-Prüfung soll nicht für jeden Eintrag erneut die ganze DB-Größe abfragen. Sonst gewinnen wir zwar funktional, aber verlieren wieder unnötig Zeit im Incremental-Pfad.

Edited file
sync_service.py
+7
-8

    def _fetch_overview_entries(self, overview_url: str) -> list:
        incremental_boundary_active = self._incremental and self._repository.count_awards() > 0
        if not self._is_project_search_api(overview_url):
            raw = self._fetcher.fetch_text(overview_url)
            entries = self._filter_incremental_entries(parse_overview(raw))
            entries = self._filter_incremental_entries(parse_overview(raw), incremental_boundary_active)
            if entries:
                    continue
                if self._should_stop_at_known_entry(entry.project_url):
                if self._should_stop_at_known_entry(entry.project_url, incremental_boundary_active):
                    should_stop = True

    def _filter_incremental_entries(self, entries: list) -> list:
    def _filter_incremental_entries(self, entries: list, incremental_boundary_active: bool) -> list:
        filtered = []
        for entry in entries:
            if self._should_stop_at_known_entry(entry.project_url):
            if self._should_stop_at_known_entry(entry.project_url, incremental_boundary_active):
                break

    def _should_stop_at_known_entry(self, project_url: str) -> bool:
        if not self._incremental:
            return False
        if self._repository.count_awards() == 0:
    def _should_stop_at_known_entry(self, project_url: str, incremental_boundary_active: bool) -> bool:
        if not incremental_boundary_active:
            return False
Ich verifiziere jetzt den kompletten Pfad: bestehende Idempotenz, Mehrfach-Zuschläge, Progress, Interrupt und zusätzlich den neuen Incremental-Stop.

Ran .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" for 15s


Die Fehler sind scharf eingegrenzt: im HTML-Pfad wird ein „absichtlich leer wegen bekanntem Eintrag“ gerade noch mit „nichts geparst, also Fallback“ verwechselt. Ich korrigiere das jetzt an der Overview-Grenze, damit Incremental und Idempotenz beide stimmen.

Ran Get-Content -Path src/simapwatch/parsers/overview_parser.py


Ich löse das sauber in zwei Schritten: HTML-Fallback nur noch bei echtem Parse-Fehler, und der Incremental-Test bekommt einen bereits bekannten API-Eintrag direkt in die DB, damit er exakt den echten Lauf simuliert.

Edited file
sync_service.py
+3
-3

            raw = self._fetcher.fetch_text(overview_url)
            entries = self._filter_incremental_entries(parse_overview(raw), incremental_boundary_active)
            if entries:
                return entries
            parsed_entries = parse_overview(raw)
            if parsed_entries:
                return self._filter_incremental_entries(parsed_entries, incremental_boundary_active)
            fallback_url = (
Edited file
test_sync_integration.py
+25
-15

from simapwatch.repository import SqliteAwardRepository
from simapwatch.domain.contracts import AwardDetail, OverviewEntry
from simapwatch.services import SyncInterruptedError, SyncProgress, SyncService
            repository.init_schema()

            bootstrap_fetcher = DictFetcher(
                {
                    "https://example.local/bootstrap": """
                    <article id="proj-known">
                        <h6 aria-label="Projekttitel: Project Known"></h6>
                        <p aria-label="Beschaffungsstelle: Office Known"></p>
                        <p aria-label="Publikationstyp: Zuschlag"></p>
                        <span aria-label="Publikationsdatum: 24.02.2026"></span>
                        <a href="/api/publications/v1/project/proj-known/publication-details/pub-known?lang=de"></a>
                    </article>
                    """,
                    detail_url_known: detail_payload("PUB-KNOWN", "Known Vendor"),
                }
            repository.upsert_award(
                OverviewEntry(
                    project_id="proj-known",
                    project_url=detail_url_known,
                    title="Projekt Bekannt",
                    procurement_office="Amt 3",
                    publication_type="Zuschlag",
                    publication_date="24.02.2026",
                ),
                AwardDetail(
                    publication_number="PUB-KNOWN",
                    publication_date="24.02.2026",
                    related_notice_number=None,
                    winner_name="Known Vendor",
                    award_amount_chf=10.0,
                    vat_percent=None,
                    offers_count=None,
                    winner_position=1,
                    winner_address=None,
                    procurement_office_address=None,
                    cpv_codes=[],
                    procurement_type="Bauleistung",
                    source_url=detail_url_known,
                ),
            )
            SyncService(fetcher=bootstrap_fetcher, repository=repository).run_once("https://example.local/bootstrap")

Ich verifiziere jetzt noch einmal die komplette Suite. Wenn das grün ist, ist der inkrementelle Pfad funktional sauber und du kannst normale Folge-Läufe ohne Reset verwenden.

Ran .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" for 3s


Der verbleibende Konflikt ist fachlich logisch: im Incremental-Modus werden bekannte Einträge nicht mehr erneut geladen, daher können ältere Änderungen nicht mehr entdeckt werden. Ich halte den neuen Default trotzdem so und ergänze als sauberen Ausweg einen expliziten full sync-Modus für den seltenen Fall „bestehende Einträge erneut prüfen“.

Edited file
test_sync_integration.py
+2
-1


            run3 = service.run_once(overview_url)
            full_sync_service = SyncService(fetcher=fetcher, repository=repository, incremental=False)
            run3 = full_sync_service.run_once(overview_url)
            self.assertEqual(run3.status, "success")
Edited file
cli.py
+7
-1

    )
    parser.add_argument(
        "--full-sync",
        action="store_true",
        help="Fetch all overview pages instead of stopping at the first already known entry.",
    )
    return parser
        f"starting overview_url={args.overview_url} db_path={args.db_path} "
        f"workers={args.max_workers} reset={args.reset_db}",
        f"workers={args.max_workers} reset={args.reset_db} incremental={not args.full_sync}",
        file=sys.stdout,
        progress_callback=print_progress,
        incremental=not args.full_sync,
    )
Ich verifiziere jetzt noch den Abschlusszustand mit dem neuen Default incremental=True und dem expliziten Ausweichpfad --full-sync.

Ran .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" for 3s


Ich ergänze noch die Bedienung knapp im README, damit der normale Folge-Lauf und der seltene Vollabgleich sauber getrennt sind.

Edited file
c:\Users\elias\Desktop\FHNW\KIP\simapWatch-\README.md
+14
-0

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
Worked for 3m 43s
Der inkrementelle Sync ist jetzt umgesetzt.

Was sich geändert hat

Standardverhalten ist jetzt: beim ersten bereits bekannten Eintrag in der Overview stoppen.
Dadurch werden spätere Runs auf neue Ausschreibungen begrenzt, statt jedes Mal die ganze History erneut durchzugehen.
Für Sonderfälle gibt es jetzt zusätzlich --full-sync.
Geänderte Dateien:

sync_service.py
sqlite_repository.py
cli.py
test_sync_integration.py
README.md
Neue Logik

DB leer:
kompletter Initiallauf
DB hat schon Daten:
Overview wird von oben nach unten gelesen
sobald ein bereits bekannter project_url auftaucht, stoppt der Overview-Scan
nur die davor liegenden neuen Einträge werden verarbeitet
Warum das zu deinem Ziel passt

Normale Folge-Läufe fügen nur neue Ausschreibungen hinzu
Bereits vorhandene Einträge werden nicht doppelt geladen
Laufzeit wird deutlich besser, weil alte Seiten nicht mehr komplett durchlaufen werden
Wichtig

Dieses neue Default-Verhalten priorisiert „nur neue Einträge“.
Wenn du alte Einträge absichtlich nochmals komplett prüfen willst, nimm:
--full-sync
Normale Nutzung ab jetzt
Für spätere Updates:

cd src
..\.venv\Scripts\python.exe -m simapwatch.cli --db-path simapwatch.db --max-workers 12
Für kompletten Neuaufbau:

cd src
..\.venv\Scripts\python.exe -m simapwatch.cli --db-path simapwatch.db --reset-db --max-workers 12
Für vollständigen Recheck aller Einträge:

cd src
..\.venv\Scripts\python.exe -m simapwatch.cli --db-path simapwatch.db --full-sync
Teststatus

python.exe -m unittest discover -s tests -p "test_*.py"
Ergebnis: 23 tests OK
Naechster sinnvoller Schritt:

einmal echten Initiallauf mit --reset-db
danach ein zweiter Normal-Lauf ohne --reset-db, um den inkrementellen Stop live zu verifizieren