Wenn du willst, setze ich dir als nächsten Schritt direkt ein erstes interaktives Filter-Panel plus serverseitige Query-Parameter um.

gerne bitte mach es das es schönn ist sibolle charts usw
Thursday 3:40 PM


72 previous messages
Umgesetzt: Dashboard ist jetzt deutlich interaktiver, filterbar und chart-basiert.

Serverseitige Filter-Engine mit Query-Parametern (from, to, buyer, winner, cpv, procurement_type, text, min_amount, max_amount) in 
service.py (line 16)
 und 
service.py (line 256)
Neues Options-API für Filtervorschläge (/api/dashboard/options) in 
service.py (line 205)
Server-Routing mit Param-Bounds + neue JS-Route in 
server.py (line 62)
 und 
server.py (line 65)
Neues Filter-UI + Chart-Canvas-Struktur in 
index.html (line 46)
Neues interaktives Frontend mit:
Live-Fetch per Query-Params in 
dashboard.js (line 384)
 und 
dashboard.js (line 399)
Mixed Trend-Chart (Volumen + Anzahl) in 
dashboard.js (line 67)
CPV Doughnut, Gewinner-Chart, Beschaffungstyp-Chart
Sauberes Map-Redraw ohne Layer-Leaks in 
dashboard.js (line 279)
Visuelles Redesign (responsive, klarere Panels/Filter) in 
app.css (line 137)
Zusätzliche Tests für Filter & Options-Endpunkt in 
test_dashboard_service.py (line 171)
 und 
test_dashboard_server.py (line 91)
Getestet:

.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
Ergebnis: Ran 40 tests ... OK
Hinweis:

Altes 
app.js
 wurde durch 
dashboard.js
 ersetzt; /app.js wird serverseitig weiterhin kompatibel bedient.

simapWatch Dashboard
Website
Open
5 files changed
+566
-6
Undo
Review

src/simapwatch/dashboard/static/dashboard.js
src/simapwatch/dashboard/static/index.html
src/simapwatch/dashboard/server.py
tests/test_dashboard_service.py
tests/test_dashboard_server.py




Thursday 3:57 PM
User attachment
bei dem CPV codes wäre es gut wenn man die codierung übersetzen kann und zudem 


möchte ich das die anzeige oben hinein passt aktuell stimmt das pberhaubt nicht 
Thursday 4:03 PM


34 previous messages
Umgesetzt, beide Punkte sind drin.

CPV-Codes werden jetzt mit Klartext ausgeliefert (cpv_label, cpv_display) statt nur Zahlencode in 
service.py (line 490)
.
Die CPV-Filteroptionen enthalten ebenfalls Anzeige-Text (display) in 
service.py (line 343)
.
CPV-Chart zeigt jetzt lesbare Labels + volle Bezeichnung im Tooltip in 
dashboard.js (line 139)
.
KPI-Zahlen oben wurden für große CHF-Werte kompakt formatiert (Mio.) und die Karten sind robuster gegen Overflow in 
dashboard.js (line 54)
 und 
app.css (line 230)
.
Wichtig zur CPV-Übersetzung:

Standardmäßig läuft sie offline stabil über Divisionen (z. B. 45 -> Bauarbeiten) in 
service.py (line 33)
.
Optional für detailliertere Live-Auflösung pro Code kannst du vor dem Start setzen:
$env:SIMAPWATCH_CPV_REMOTE_LOOKUP='1'
Validierung:

Test-Suite läuft grün: Ran 40 tests ... OK (inkl. neuer CPV-Assertion in 
test_dashboard_service.py (line 152)
).
Wenn du willst, kann ich als nächsten Schritt noch die CPV-Anzeige auf „Code links, Bezeichnung rechts“ im Doughnut-Panel umbauen, damit die Legende noch cleaner wirkt.

4 files changed
+199
-17
Undo
Review

src/simapwatch/dashboard/service.py
src/simapwatch/dashboard/static/dashboard.js
src/simapwatch/dashboard/static/app.css
tests/test_dashboard_service.py




Thursday 4:10 PM
User attachment

ist immer noch etwas verschoben und ich bräuchte noch viel viel mehr charts und analysenenn die vielleicht nicht so offensichtlich sind aber viel aussagen oder gewinner pro kanton usw fände ich spannend
Thursday 4:13 PM


96 previous messages
Dashboard ist jetzt deutlich interaktiver und die obere KPI-Zeile wurde stabilisiert.

Was ich umgesetzt habe

KPI-Fix oben:
kompakteres CHF-Formatting ohne unschönen Umbruch (CH/F)
metric-value jetzt nowrap + ellipsis statt Wortzerlegung
responsiveres KPI-Grid für Desktop/Tablet/Mobile
Viele neue Analysen + Charts:
Gewinner pro Kanton
Auftraggeber-Volumen pro Kanton
Kanton-Flüsse (Buyer -> Gewinner)
Auftragsgrößen-Buckets (inkl. Volumenanteile)
Wettbewerbsintensität (Anzahl Angebote)
Gewinner-Konzentration (Pareto-Kurve)
Insight-Kacheln (Top-1/3/10, HHI, Interkantonal, Single-Bid, etc.)
Gewinner-Profile Tabelle (Kanton, Avg Angebote, Haupt-CPV, Volumenanteil)
Backend-Payload erweitert, damit alle neuen Panels serverseitig gerechnet werden.
Wichtige Dateien

Backend-Analytik: 
service.py (line 473)
KPI-/Chart-Rendering: 
dashboard.js (line 70)
Neue Dashboard-Sektionen: 
index.html (line 112)
KPI/Insights Layout-Fix: 
app.css (line 230)
Erweiterte Tests: 
test_dashboard_service.py (line 136)
Tests

.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
Ergebnis: Ran 40 tests ... OK
Wenn du willst, mache ich als nächsten Schritt noch echte Drilldown-Interaktionen (Klick auf Kanton/Chart setzt automatisch Filter).
Ich kann zusätzlich eine robustere Kanton-Erkennung für Winner bauen (z. B. PLZ->Kanton-Mapping), damit “Unbekannt” weiter sinkt.

simapWatch Dashboard
Website
Open
6 files changed
+1407
-561
Undo
Review

src/simapwatch/dashboard/service.py
src/simapwatch/dashboard/static/dashboard.js
src/simapwatch/dashboard/static/dashboard.js
src/simapwatch/dashboard/static/index.html
src/simapwatch/dashboard/static/app.css
tests/test_dashboard_service.py




Thursday 4:30 PM
User attachment
User attachment
Zuschlaege pro Kanton diese visualisierung wäre gut wenn es pro 100'000 einwohner wäre damit es im verhältnis zur bevölkerung ist 

zudem ist das Volumen und Anzahl pro Monat der graph veränderet sich nicht wenn man die letzten 30 tage ausgewählt hbae änderet sich unten die tage gar nicht ich möchte das es sich auf dem gewählten zeitraum angepasst wird 

bei der cpv code gibt es viele die einen anderen code haben aber die gleiche bezeichnung ich möchte das es zusammengefassst wird wennn der cpv code gleich bleibt 

auch der Geo-Fluss sollte etwas komplexer werden oder besser gesagt es soll etwas mehr ausgesagt werden 

Thursday 4:48 PM


44 previous messages
Die vier Punkte sind umgesetzt.

Zuschlaege pro Kanton ist jetzt relativ zur Bevölkerung:
Backend liefert awards_per_100k und volume_per_100k_chf je Kanton.
Chart zeigt nun primär Zuschlaege pro 100'000 Einwohner (plus absolute Linie).
Volumen und Anzahl passt sich jetzt dem gewählten Zeitraum an:
Mit Datumsfilter wird automatisch auf Tag/Woche/Monat umgestellt.
Bei 30 Tage bekommst du Tagesachsen statt fixer Monatsachsen.
CPV wird jetzt nach Bezeichnung gruppiert:
Gleich benannte Kategorien werden zusammengefasst, auch wenn mehrere Codes dahinterliegen.
Geo-Fluss ist jetzt aussagekräftiger:
Aggregierte Kanton-zu-Kanton-Flüsse mit Gewichtung (Linienstärke nach Count/Volumen) und besseren Popups (Count, Volumen, Avg, Anteil).
Wichtige Änderungen:

Backend-Logik: 
service.py (line 88)
, 
service.py (line 380)
, 
service.py (line 745)
, 
service.py (line 1030)
Frontend-Charts/Map: 
dashboard.js (line 156)
, 
dashboard.js (line 227)
, 
dashboard.js (line 355)
, 
dashboard.js (line 681)
Trend-Titel angepasst: 
index.html (line 119)
Tests erweitert: 
test_dashboard_service.py (line 158)
Verifiziert:

.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
Ergebnis: Ran 40 tests ... OK
Wenn du willst, mache ich als nächsten Schritt noch eine Toggle-Option im Kanton-Chart: absolut vs. pro 100k.
Ich kann zusätzlich offizielle BFS-Bevölkerungswerte als kleine Datei einbinden (statt statischer Werte im Code), damit es jährlich sauber aktualisierbar ist.

simapWatch Dashboard
Website
Open
4 files changed
+318
-46
Undo
Review

src/simapwatch/dashboard/service.py
src/simapwatch/dashboard/static/dashboard.js
src/simapwatch/dashboard/static/index.html
tests/test_dashboard_service.py




Thursday 4:54 PM
Kanton-Abdeckung
98.60%
Anteil Zuschlaege mit Kanton fuer Buyer und Winner.

das kannst du löschen 

dann werde ü ä ö nich angezeigt sondern als ue oe ae das ist unnötig 

zudem möchte ich noch weitere analysen überlege welche sinnvoll sein können mit den daten die ich habe 
Thursday 5:05 PM


52 previous messages
Kanton-Abdeckung ist entfernt, Umlaute sind korrigiert, und ich habe zusätzliche Analysen eingebaut.

Geändert

Insight Kanton-Abdeckung entfernt (wird nicht mehr gerendert), inkl. Testabsicherung.

service.py (line 1009)


test_dashboard_service.py (line 167)
Umlaute statt ae/oe/ue in UI-Texten und CPV-Bezeichnungen (z. B. Häufigkeit, Zuschläge, Flüsse, Großauftragsanteil, CPV-Labels).

index.html (line 151)


dashboard.js (line 722)


service.py (line 33)
Neue sinnvolle Analysen

Single-Bid je Beschaffungstyp (inkl. Anteil und Ø Angebote).
Backend: 
service.py (line 825)

Frontend-Chart: 
dashboard.js (line 523)

Canvas: 
index.html (line 232)
Interkantonale Quote im Zeitverlauf (pro Zeitbucket mit Fallzahl).
Backend: 
service.py (line 919)

Frontend-Chart: 
dashboard.js (line 663)

Canvas: 
index.html (line 242)
Verifiziert

.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
Ergebnis: Ran 40 tests ... OK
Wenn du willst, ergänze ich als Nächstes noch eine Drilldown-Logik (Klick auf Beschaffungstyp/Kanton setzt direkt Filter).
Ich kann zusätzlich eine Anomalie-Analyse bauen (auffällige Ausreißer bei Volumen vs. Anzahl Angebote je CPV/Beschaffungstyp).

simapWatch Dashboard
Website
Open
4 files changed
+200
-26
Undo
Review

src/simapwatch/dashboard/service.py
src/simapwatch/dashboard/static/index.html
src/simapwatch/dashboard/static/dashboard.js
tests/test_dashboard_service.py




Thursday 5:12 PM
🔥 1. Konzentration & Macht (sehr stark!)

👉 Wer bekommt das Geld wirklich?

💡 Visualisierung:
Lorenz-Kurve + Gini-Koeffizient
oder: „Top 10 Gewinner vs. Rest“

👉 Insight:

„10 Firmen erhalten 40% aller Aufträge“

👉 Das ist Gold für Journalismus.

🧠 2. Repeat Winners / Abhängigkeiten

👉 Gewinnen immer die gleichen Firmen?

💡 Visualisierung:
Sankey: Auftraggeber → Gewinner
oder:
Heatmap: Auftraggeber × Gewinner (Top 20)

👉 Insight:

„Kanton X vergibt 60% seiner Aufträge an dieselben 3 Firmen“

⚠️ 3. Wettbewerb vs. Preis (sehr spannend)

👉 Führt mehr Wettbewerb zu günstigeren Preisen?

💡 Visualisierung:
Scatterplot:
x = Anzahl Angebote
y = Zuschlagspreis / erwarteter Preis

👉 Insight:

„Ab 5 Angeboten sinken Preise signifikant“

🕵️ 4. Auffällige Beschaffungen (Outlier Detection)

👉 Wo könnte etwas „komisch“ sein?

💡 Visualisierung:
Boxplot oder Z-Score-Highlighting
Filter:
extrem hohe Preise
nur 1 Angebot
trotzdem hoher Betrag

👉 Insight:

„30 Mio. Auftrag mit nur einem Anbieter“

📉 5. Preisentwicklung über Zeit (Inflation / Trends)

👉 Werden Beschaffungen teurer?

💡 Visualisierung:
Medianpreis pro CPV über Zeit

👉 Insight:

„IT-Projekte sind in 3 Jahren um 25% teurer geworden“

🏗️ 6. Branchenanalyse (CPV deep dive)

👉 Wo fliesst das Geld hin?

💡 Visualisierung:
Treemap (Volumen nach CPV)
oder gestapelte Zeitreihe

👉 Insight:

„70% des Volumens geht in Bauprojekte“

🌍 7. Regionaler Bias / Heimvorteil

👉 Gewinnen Firmen eher im eigenen Kanton?

💡 Visualisierung:
Matrix: Auftraggeber-Kanton → Gewinner-Kanton
oder:
% „lokale Gewinner“

👉 Insight:

„80% der Aufträge bleiben im selben Kanton“

🔁 8. Wettbewerbsintensität je Auftraggeber

👉 Wer macht offene vs. eingeschränkte Verfahren?

💡 Visualisierung:
Bar Chart: Anteil Verfahrenstyp pro Auftraggeber

👉 Insight:

„Kanton X nutzt viel häufiger freihändige Vergaben“

📊 9. „Kosten pro Zuschlag“

👉 Wie teuer sind einzelne Beschaffungen im Schnitt?

💡 Visualisierung:
Volumen / Anzahl Zuschläge pro Monat

👉 Insight:
→ erklärt genau deinen Oktober-Peak besser

🧩 10. Netzwerk-Analyse (passt perfekt zu dir 🔥)

👉 Du nutzt ja bereits networkx/Gephi!

💡 Visualisierung:
Graph:
Knoten: Auftraggeber + Firmen
Kanten: Zuschläge
Gewicht: Volumen

👉 Insight:

„Cluster von Firmen dominieren bestimmte Regionen“

🚨 11. Risiko-Score (super Story)

👉 Kombiniere mehrere Faktoren:

wenig Angebote
hoher Preis
gleiche Gewinner
freihändiges Verfahren
💡 Visualisierung:
Ampelsystem / Score

👉 Insight:

„Diese 5% der Beschaffungen sind besonders kritisch“

🧠 12. Timing / „Budget Rush“

👉 Dein Oktober-Thema weiter ausbauen

💡 Visualisierung:
Anteil Jahresvolumen pro Monat

👉 Insight:

„30% der Ausgaben passieren im letzten Quartal“

💥 Was dir aktuell NOCH fehlt (wichtig!)

Du hast viel „Was passiert“
👉 aber noch wenig „Warum ist das relevant/problematisch?“

🚀 Meine Empfehlung (Top 3 für dich)

Wenn du nur wenig Zeit hast, mach diese:

Top Gewinner Konzentration
Wettbewerb vs. Preis
Outlier / suspicious contracts

👉 Das gibt dir sofort journalistische Schlagzeilen.


kannst du solche plots implementieren aber nur die die sinn machen 

Show more
Thursday 5:36 PM


30 previous messages
Umgesetzt, und zwar genau die Teile aus deiner Liste, die mit euren vorhandenen Daten wirklich belastbar sind.

Was ich geändert habe

Kanton-Abdeckung Insight entfernt.
Umlaute sauber korrigiert (kein ae/oe/ue mehr in UI-Texten).
Neue starke Analysen implementiert:
Konzentration & Macht:
Lorenz-Kurve
Gini-Koeffizient
Top 10 Gewinner vs Rest
Repeat Winners / Abhängigkeiten:
Auftraggeber -> Gewinner Top-Paare nach Volumen
Wettbewerb vs Preis:
Scatterplot Anzahl Angebote vs Zuschlagspreis
Zusatzlinie: Medianpreis je Angebotszahl
Auffällige Beschaffungen:
Risiko-Score pro Auftrag (u.a. Single-Bid, hoher Betrag, Ausreißer, Repeat-Paar)
Tabelle Verdächtige Beschaffungen
Wichtige Stellen

Backend-Analysen: 
service.py (line 616)
, 
service.py (line 1025)
, 
service.py (line 1074)
, 
service.py (line 1269)
Neue Charts/Renderlogik: 
dashboard.js (line 605)
, 
dashboard.js (line 669)
, 
dashboard.js (line 703)
, 
dashboard.js (line 734)
, 
dashboard.js (line 884)
Neue Panels im Layout: 
index.html (line 232)
, 
index.html (line 242)
, 
index.html (line 254)
, 
index.html (line 264)
, 
index.html (line 338)
Validierung

.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
Ergebnis: Ran 40 tests ... OK
Nicht umgesetzt habe ich bewusst:

Sankey (zusätzliche Plugin-Abhängigkeit)
„Preis / erwarteter Preis“ (erwarteter Preis ist in euren Daten aktuell nicht vorhanden)
Wenn du willst, baue ich als Nächstes noch eine echte Heatmap Auftraggeber × Gewinner (Top-N Matrix) als zusätzliche Abhängigkeits-Visualisierung.
Ich kann den Risiko-Score noch transparent als einblendbare Formel pro Treffer ausgeben (für journalistische Nachvollziehbarkeit).

simapWatch Dashboard
Website
Open
5 files changed
+1707
-1364
Undo
Review

src/simapwatch/dashboard/service.py
src/simapwatch/dashboard/static/index.html
src/simapwatch/dashboard/static/index.html
src/simapwatch/dashboard/static/dashboard.js
src/simapwatch/dashboard/static/dashboard.js




Thursday 5:46 PM
vorher war besser kannst du es auf den letzen stand zurücksetzen 
Thursday 5:50 PM


40 previous messages
Zurückgesetzt auf den letzten stabilen Stand vor den zuletzt eingebauten Deep-Dive-Analysen.

index.html bereinigt und neu sauber aufgebaut (inkl. interaktivem Filter-Panel, ohne Merge-Konfliktmarker): 
index.html
Die zuletzt ergänzten Zusatz-Outputs im Backend entfernt (Lorenz/Gini/Outlier/Scatter/Buyer→Winner-Dependency), der vorherige Kern bleibt erhalten: 
service.py
Verifikation: unittest läuft grün (Ran 5 tests ... OK).
Wenn du willst, setze ich als Nächstes noch einen exakten visuellen “Pixel-Fix” für die oberen KPI-Karten um (damit nichts mehr verschoben wirkt).


simapWatch Dashboard
Website
Open
3 files changed
+308
-533
Undo
Review

src/simapwatch/dashboard/static/index.html
src/simapwatch/dashboard/static/index.html
src/simapwatch/dashboard/service.py




Thursday 5:55 PM
(index):1 Failed to find a valid digest in the 'integrity' attribute for resource 'https://unpkg.com/leaflet
leaflet.js
' with computed SHA-256 integrity '20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo='. The resource has been blocked.
dashboard.js:973 ReferenceError: L is not defined
    at ensureMap (dashboard.js:774:18)
    at renderMap (dashboard.js:788:3)
    at loadDashboard (dashboard.js:968:5)
    at async boot (dashboard.js:1046:3)
Thursday 5:56 PM


10 previous messages
Fehlerursache war genau das, was dein Log zeigt: ein falscher integrity-Hash bei Leaflet hat das Script blockiert, dadurch war L nicht definiert.

Ich habe es direkt gefixt:

Leaflet-Hash korrigiert in 
index.html (line 302)
 (...qIjJZ... statt ...qIjZ...).
Schutz eingebaut, damit das Dashboard nicht mehr mit ReferenceError crasht, falls Leaflet/CDN mal trotzdem fehlt: 
dashboard.js (line 769)
.
Kurztest ausgeführt: tests.test_dashboard_server läuft OK.
Bitte einmal hart neu laden (Ctrl+F5).
Wenn du willst, kann ich als Nächstes Leaflet lokal ausliefern (statt CDN), dann bist du komplett unabhängig von externen Ladeproblemen.


simapWatch Dashboard
Website
Open
2 files changed
+30
-17
Undo
Review

src/simapwatch/dashboard/static/index.html
src/simapwatch/dashboard/static/dashboard.js




Thursday 5:57 PM
Skip to content
logo


Search
 
 marimo-team/marimo
0.23.4
20.7k
1.1k
marimo
Getting Started
User Guide
Examples
API Reference
Commands
FAQ
Readings & Videos
Community
Changelog
Integrations
Security
Table of contents
Highlights
A reactive programming environment
Quickstart
Questions?
Learn more
Contributing
Community
Inspiration ✨

Copy page
marimo: The Reactive Python Notebook¶
marimo - reactive Python notebook

marimo is an open-source reactive Python notebook: run a cell or interact with a UI element, and marimo automatically runs dependent cells (or marks them as stale), keeping code and outputs consistent and preventing bugs before they happen. Every marimo notebook is stored as pure Python (Git-friendly), executable as a script, and deployable as an app; while stored as Python, marimo notebooks also have native support for SQL.

Built from the ground up

marimo was built from the ground up to solve well-known problems associated with traditional notebooks.

Get started instantly with molab, our free online notebook. Or get started locally by installing marimo with your favorite package manager:


install with pip
install with uv
install with conda

pip install marimo && marimo tutorial intro

Developer experience is core to marimo, with an emphasis on reproducibility, maintainability, composability, and shareability.

Highlights¶
🚀 batteries-included: replaces jupyter, streamlit, jupytext, ipywidgets, papermill, and more
⚡️ reactive: run a cell, and marimo reactively runs all dependent cells or marks them as stale
🖐️ interactive: bind sliders, tables, plots, and more to Python — no callbacks required
🐍 git-friendly: stored as .py files
🛢️ designed for data: query dataframes, databases, warehouses, and lakehouses with SQL; filter and search dataframes
🤖 AI-native: connect agent CLIs like Claude Code to notebooks, or use our editor's built-in AI features
🔬 reproducible: no hidden state, deterministic execution, built-in package management
🏃 executable: execute as a Python script, parameterized by CLI args
🛜 shareable: deploy as an interactive web app or slides, run in the browser via WASM
🧩 reusable: import functions and classes from one notebook to another
🧪 testable: run pytest on notebooks
⌨️ a modern editor: GitHub Copilot, AI assistants, vim keybindings, variable explorer, and more
🧑‍💻 use your favorite editor: run in VS Code or Cursor, or edit in neovim, Zed, or any other text editor
A reactive programming environment¶
marimo guarantees your notebook code, outputs, and program state are consistent. This solves many problems associated with traditional notebooks like Jupyter.

A reactive programming environment. Run a cell and marimo reacts by automatically running the cells that reference its variables, eliminating the error-prone task of manually re-running cells. Delete a cell and marimo scrubs its variables from program memory, eliminating hidden state.


Compatible with expensive notebooks. marimo lets you configure the runtime to be lazy, marking affected cells as stale instead of automatically running them. This gives you guarantees on program state while preventing accidental execution of expensive cells.

Synchronized UI elements. Interact with UI elements like sliders, dropdowns, dataframe transformers, and chat interfaces, and the cells that use them are automatically re-run with their latest values.

Interactive dataframes. Page through, search, filter, and sort millions of rows blazingly fast, no code required.

Generate cells with data-aware AI. Collaborate on marimo notebooks with your favorite agent, such as Claude Code, Codex, or OpenCode, using marimo pair. Or, generate code in the marimo editor with an AI assistant that is highly specialized for working with data, with context about your variables in memory. Customize the system prompt, bring your own API keys, or use local models.

Query data with SQL. Build SQL queries that depend on Python values and execute them against dataframes, databases, lakehouses, CSVs, Google Sheets, or anything else using our built-in SQL engine, which returns the result as a Python dataframe.

SQL cell in marimo querying a dataframe

Your notebooks are still pure Python, even if they use SQL.

Dynamic markdown. Use markdown parametrized by Python variables to tell dynamic stories that depend on Python data.

Built-in package management. marimo has built-in support for all major package managers, letting you install packages on import. marimo can even serialize package requirements in notebook files, and auto install them in isolated venv sandboxes.

Deterministic execution order. Notebooks are executed in a deterministic order, based on variable references instead of cells' positions on the page. Organize your notebooks to best fit the stories you'd like to tell.

Performant runtime. marimo runs only those cells that need to be run by statically analyzing your code.

Batteries-included. marimo comes with GitHub Copilot, AI assistants, Ruff code formatting, HTML export, fast code completion, a VS Code extension, an interactive dataframe viewer, and many more quality-of-life features.

Quickstart¶
The marimo concepts playlist on our YouTube channel gives an overview of many features.

Installation. In a terminal, run


pip install marimo  # or conda install -c conda-forge marimo
marimo tutorial intro
To install with additional dependencies that unlock SQL cells, AI completion, and more, run


pip install marimo[recommended]
Create notebooks.

Create or edit notebooks with


marimo edit
Run apps. Run your notebook as a web app, with Python code hidden and uneditable:


marimo run your_notebook.py
Execute as scripts. Execute a notebook as a script at the command line:


python your_notebook.py
Automatically convert Jupyter notebooks. Automatically convert Jupyter notebooks to marimo notebooks with the CLI


marimo convert your_notebook.ipynb > your_notebook.py
or use our web interface.

Tutorials. List all tutorials:


marimo tutorial --help
Share cloud-based notebooks. Use molab, a cloud-based marimo notebook service similar to Google Colab, to create and share notebook links.

Questions?¶
See our FAQ.

Learn more¶
marimo is easy to get started with, with lots of room for power users. For example, here's an embedding visualizer made in marimo (try the notebook live on molab!):

Check out our guides, usage examples, and our gallery to learn more.

Tutorial	Inputs	Plots	Layout
Open in molab	Open in molab	Open in molab	Open in molab
Contributing¶
We appreciate all contributions! You don't need to be an expert to help out. Please see CONTRIBUTING.md for more details on how to get started.

Questions? Reach out to us on Discord.

Community¶
We're building a community. Come hang out with us!

🌟 Star us on GitHub
💬 Chat with us on Discord
📧 Subscribe to our Newsletter
☁️ Join our Cloud Waitlist
✏️ Start a GitHub Discussion
💬 Follow us on Bluesky
🐦 Follow us on Twitter
🎥 Subscribe on YouTube
💬 Follow us on Mastodon
🤖 Follow us on Reddit
🕴️ Follow us on LinkedIn
A NumFOCUS affiliated project. marimo is a core part of the broader Python ecosystem and is a member of the NumFOCUS community, which includes projects such as NumPy, SciPy, and Matplotlib.

NumFOCUS affiliated project

Inspiration ✨¶
marimo is a reinvention of the Python notebook as a reproducible, interactive, and shareable Python program, instead of an error-prone JSON scratchpad.

We believe that the tools we use shape the way we think — better tools, for better minds. With marimo, we hope to provide the Python community with a better programming environment to do research and communicate it; to experiment with code and share it; to learn computational science and teach it.

Our inspiration comes from many places and projects, especially Pluto.jl, ObservableHQ, and Bret Victor's essays. marimo is part of a greater movement toward reactive dataflow programming. From IPyflow, streamlit, TensorFlow, PyTorch, JAX, and React, the ideas of functional, declarative, and reactive programming are transforming a broad range of tools for the better.

marimo logo

April 30, 2026
 Back to top
Next
Getting Started
© marimo 2026



ich möchte zusätzlich noch das implementieren hassst du eine idee wie das geht und wie ich das implementieren kann 



Show more
Thursday 6:09 PM


71 previous messages
Sehr gute Idee, ich habe dir marimo jetzt direkt ins Projekt integriert.

Umgesetzt

Neues reaktives Notebook mit Filtern + KPI + Charts + Tabelle:

notebooks/simapwatch_marimo.py
Start-Skript fuer marimo:

scripts/start_marimo.py
Dependencies ergaenzt:

requirements.txt
README um Startanleitung erweitert:

README.md (line 112)
So startest du es

.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\scripts\start_marimo.py
Oder direkt als App:

.\.venv\Scripts\python.exe -m marimo run .\notebooks\simapwatch_marimo.py
Validierung

py_compile fuer Notebook + Startskript: ok
unittest (test_dashboard_service, test_dashboard_server): ok
marimo check: ok, nur 1 reine Style-Warnung (nicht funktional)
Wenn du willst, baue ich dir als naechsten Schritt genau deine journalistischen Deep-Dive-Plots auch ins marimo-Notebook ein (Lorenz/Gini, Outlier-Score, Buyer→Winner-Abhaengigkeiten) mit denselben Filtern.


README.md
Document · MD

Open

5 files changed
+380
-17
Undo
Review

notebooks/simapwatch_marimo.py
scripts/start_marimo.py
requirements.txt
README.md
notebooks/simapwatch_marimo.py




Thursday 6:18 PM



4ms

NameError
name 'mo' is not defined.

The marimo module (imported as mo) is required for Markdown, SQL, and UI elements.

Fix: Add 'import marimo as mo'


Traceback (most recent call last):
  File "C:\Users\elias\Desktop\FHNW\KIP\simapWatch-\.venv\Lib\site-packages\marimo\_runtime\executor.py", line 139, in execute_cell
    return eval(cell.last_expr, glbls)
  Cell 
marimo://C:\Users\elias\Desktop\FHNW\KIP\simapWatch-\notebooks\simapwatch_marimo.py#cell=cell-0

, line 1, in <module>
    mo.md("""
    ^^
NameError: name 'mo' is not defined

Show more
Thursday 7:24 PM



4 previous messages
Super erkannt, genau das war der Punkt.

Ich habe das Notebook gefixt:

Es gibt jetzt ganz oben eine eigene marimo-Cell mit import marimo as mo und return (mo,) in 
simapwatch_marimo.py
.
marimo check läuft jetzt ohne Fehler.
Bitte einfach neu starten:

.\.venv\Scripts\python.exe .\scripts\start_marimo.py
Wenn du willst, gehe ich als Nächstes direkt an die Deep-Dive-Plots dort (Lorenz/Gini, Outlier, Buyer→Winner-Abhängigkeit).

1 file changed
Undo
Review

notebooks/simapwatch_marimo.py




