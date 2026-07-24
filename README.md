# ÖH WG-Zimmer Watcher

Schickt dir eine Push-Nachricht aufs Handy, sobald ein neues WG-Zimmer-Inserat
auf der ÖH-Wohnungsbörse (wohnen.oehweb.at) erscheint.

## Wie es funktioniert

- Alle 30 Minuten ruft eine GitHub Action `watch_oeh.py` auf.
- Das Skript holt sich https://wohnen.oehweb.at/kategorie/wg/, erkennt darauf
  die einzelnen Inserate und vergleicht sie mit `seen.json` (was schon bekannt ist).
- Für jedes neue Inserat schickt es eine Push-Nachricht über den kostenlosen
  Dienst [ntfy.sh](https://ntfy.sh).
- **Nur Innsbruck-Stadt**: Inserate aus "Innsbruck Umgebung", "Umland" oder
  "Anderswo" werden herausgefiltert (erkannt am Text bzw. den Stadtteil-Namen
  wie Wilten, Pradl, Hötting, ...). Die Liste der Stadtteile steht ganz oben
  in `watch_oeh.py` (`INNSBRUCK_DISTRICTS`) - falls mal ein Inserat ohne
  erkennbaren Stadtteil durchrutscht oder fälschlich rausgefiltert wird,
  einfach dort anpassen.
- Inserate, deren Text Hinweise auf Oktober oder "ab 15. September" enthalten,
  werden als "möglich relevant" markiert (Priorität hoch) - alle anderen
  Innsbruck-Treffer kommen trotzdem, nur mit normaler Priorität, damit dir
  nichts entgeht (die Texterkennung ist nicht perfekt, z.B. bei "ab September"
  ohne genaues Datum).

## Einrichtung (5–10 Minuten)

### 1. ntfy-App installieren und Topic wählen
- Lade die App **ntfy** heruntergeladen (iOS App Store / Google Play), oder
  nutze https://ntfy.sh im Browser.
- Denk dir einen **eindeutigen, schwer erratbaren Topic-Namen** aus, z.B.
  `katia-oeh-wg-4k29xz` (Topics bei ntfy.sh sind öffentlich erreichbar über
  ihren Namen - je zufälliger, desto sicherer vor Fremdzugriff).
- In der App: "+" → Topic hinzufügen → deinen Topic-Namen eingeben → abonnieren.

### 2. GitHub-Repo anlegen
- Neues (privates oder öffentliches) Repo erstellen, z.B. `oeh-wg-watcher`.
- Diese Dateien hochladen (per GitHub Desktop, `git push`, oder Web-Upload).

### 3. Topic-Namen als Secret hinterlegen
- Im Repo: Settings → Secrets and variables → Actions → "New repository secret"
- Name: `NTFY_TOPIC`
- Wert: dein Topic-Name (z.B. `katia-oeh-wg-4k29xz`)

### 4. Actions aktivieren
- Tab "Actions" im Repo öffnen, Workflows bestätigen/aktivieren.
- Optional: einmal manuell über "Run workflow" starten, um zu testen.

Danach läuft es automatisch alle 30 Minuten und du bekommst eine
Push-Nachricht, sobald ein neues Inserat auftaucht.

## Wenn's nicht klappt

Falls das Skript "Keine Inserate gefunden" meldet, hat sich vermutlich die
HTML-Struktur der Seite geändert (Themes/Plugins werden ab und zu
aktualisiert). Öffne dann https://wohnen.oehweb.at/kategorie/wg/ im Browser,
Rechtsklick auf ein Inserat → "Untersuchen", und schick mir ein Stück vom
HTML - dann passe ich die Erkennung in `watch_oeh.py` an.

## Ein Hinweis zur Fairness gegenüber der ÖH-Seite

Die Seite bittet in ihrer robots.txt darum, nicht automatisiert abgerufen zu
werden. Dieses Skript ruft deshalb bewusst nur EINE Seite ab (nicht die ganze
Website) und das nur alle 30 Minuten, nicht öfter - ähnlich wie ein Mensch,
der die Seite gelegentlich manuell aktualisiert. Wenn du es lieber noch
zurückhaltender willst, erhöhe einfach das Intervall in
`.github/workflows/check.yml` (z.B. auf `*/60 * * * *` für stündlich).

## Lokal testen (ohne GitHub)

```bash
pip install -r requirements.txt
export NTFY_TOPIC="dein-topic-name"   # optional, sonst nur Konsolenausgabe
python watch_oeh.py
```
