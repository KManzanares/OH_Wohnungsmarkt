#!/usr/bin/env python3
"""
Beobachtet die ÖH-Wohnungsbörse (WG-Zimmer-Kategorie) auf neue Inserate
und schickt bei neuen Treffern eine Push-Nachricht via ntfy.sh aufs Handy.

Funktionsweise:
1. Seite abrufen (ganz normaler HTTP-GET, wie ein Browser)
2. Alle Inserate heuristisch erkennen (über "[mehr]"/"Details"-Links)
3. Vergleich mit seen.json (bereits gesehene Inserate)
4. Für jedes neue Inserat: Push-Notification schicken
5. seen.json aktualisieren

WICHTIG:
- Diese Seite verbietet in ihrer robots.txt automatisiertes Crawling.
  Das Skript läuft deshalb bewusst selten (alle 30-60 Min, nicht im Sekundentakt)
  und ruft nur EINE Seite ab (die WG-Zimmer-Übersicht), nicht die ganze Website.
  Wäge selbst ab, ob du damit einverstanden bist.
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://wohnen.oehweb.at/kategorie/wg/"
SEEN_FILE = Path(__file__).parent / "seen.json"

# Aus GitHub Secrets / Umgebungsvariable gelesen (siehe README)
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Schlüsselwörter, die auf einen für dich relevanten Zeitraum hindeuten
# (ab 15. September oder ab Oktober). Rein informativ, wird NICHT zum
# Herausfiltern benutzt, sondern nur zur Hervorhebung in der Nachricht.
RELEVANT_HINTS = [
    "oktober", "1.10", "01.10", "1. 10", "ab okt",
    "15. september", "15.09", "15.9", "mitte september",
]

# --- Ortsfilter: nur Innsbruck-Stadt, nicht "Umgebung"/"Umland"/"Anderswo" ---
# Die ÖH-Seite taggt Inserate meist mit "<Stadtteil>, Innsbruck" (z.B.
# "Hötting, Innsbruck"). Diese Liste kannst du bei Bedarf anpassen/erweitern,
# falls ein Stadtteil fehlt oder die Seite ihre Taxonomie ändert.
INNSBRUCK_DISTRICTS = [
    "allerheiligen", "amras", "arzl", "dreiheiligen", "hötting west",
    "höttinger au", "hötting", "hungerburg", "igls", "vill", "innenstadt",
    "mariahilf", "mühlau", "olympisches dorf", "pradl", "reichenau",
    "roßau", "saggen", "sieglanger", "mentelberg", "st. nikolaus",
    "st.nikolaus", "wilten", "technik",
]

# Begriffe, die anzeigen "das ist NICHT Innsbruck-Stadt", auch wenn
# "Innsbruck" im Text vorkommt (z.B. "Innsbruck Umgebung").
EXCLUDE_LOCATION_TERMS = ["innsbruck umgebung", "umland", "anderswo"]


def is_innsbruck_city(snippet: str) -> bool:
    text = snippet.lower()
    if any(term in text for term in EXCLUDE_LOCATION_TERMS):
        # Trotzdem prüfen, ob ein echter Stadtteil-Name auftaucht (falls der
        # Text z.B. "Innsbruck Umgebung" nur als Kategorie-Filterliste zeigt,
        # das eigentliche Inserat aber in der Stadt liegt) - im Zweifel lieber
        # einmal zu viel benachrichtigen als ein Zimmer verpassen.
        if any(d in text for d in INNSBRUCK_DISTRICTS):
            return True
        return False
    if "innsbruck" in text:
        return True
    if any(d in text for d in INNSBRUCK_DISTRICTS):
        return True
    return False


def fetch_listings():
    resp = requests.get(URL, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    listings = {}

    # Primäre Methode: WpResidence-Theme packt pro Inserat ein Element mit
    # class="listing_wrapper" und den Attributen data-listid / data-modal-title
    # / data-modal-link - das ist zuverlässiger als Text-Heuristiken.
    for div in soup.select("div.listing_wrapper[data-listid]"):
        listid = (div.get("data-listid") or "").strip()
        title = (div.get("data-modal-title") or "").strip()
        link = (div.get("data-modal-link") or "").strip()
        if not listid or not link:
            continue
        full_text = re.sub(r"\s+", " ", div.get_text(" ", strip=True))
        snippet = f"{title} - {full_text}"[:400] if title else full_text[:400]
        listings[listid] = {"title": title, "link": link, "snippet": snippet}

    if listings:
        return listings

    # Fallback (falls sich die Seitenstruktur mal ändert): alte Heuristik
    # über "[mehr]"/"Details"-Links.
    print("Primäre Erkennung fand nichts - falle auf Fallback-Heuristik zurück.")
    for a in soup.find_all("a", href=True):
        text = (a.get_text() or "").strip().lower()
        if text not in ("mehr", "[mehr]", "details"):
            continue
        href = a["href"]
        container = a.find_parent(["article", "li", "div"]) or a.parent
        snippet = container.get_text(" ", strip=True) if container else a.get_text(strip=True)
        snippet = re.sub(r"\s+", " ", snippet)[:400]
        if href not in listings or len(snippet) > len(listings.get(href, {}).get("snippet", "")):
            listings[href] = {"title": "", "link": href, "snippet": snippet}
    return listings


def load_seen():
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text(encoding="utf-8"))
    return {}


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")


def send_push(title, snippet, link):
    if not NTFY_TOPIC:
        print("Kein NTFY_TOPIC gesetzt - überspringe Push, gebe nur auf der Konsole aus.")
        print(f"NEU: {title}\n{snippet}\n{link}")
        return

    is_relevant = any(hint in snippet.lower() for hint in RELEVANT_HINTS)
    push_title = "Neues WG-Zimmer (moeglich relevant!)" if is_relevant else "Neues WG-Zimmer"
    body = f"{title}\n{link}" if title else snippet

    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=body.encode("utf-8"),
            headers={
                "Title": push_title,  # ASCII-Titel, damit HTTP-Header nicht zickt
                "Click": link,
                "Priority": "high" if is_relevant else "default",
                "Tags": "house" if is_relevant else "eyes",
            },
            timeout=15,
        )
    except requests.RequestException as e:
        print(f"Push fehlgeschlagen: {e}", file=sys.stderr)


def main():
    try:
        listings = fetch_listings()
    except requests.RequestException as e:
        print(f"Konnte Seite nicht abrufen: {e}", file=sys.stderr)
        sys.exit(0)  # kein harter Fehler, GitHub Action soll nicht rot werden

    if not listings:
        print("Keine Inserate gefunden - evtl. hat sich die Seitenstruktur geaendert.")
        return

    seen = load_seen()
    new_count = 0
    notified_count = 0
    for listid, data in listings.items():
        if listid not in seen:
            new_count += 1
            if is_innsbruck_city(data["snippet"]):
                notified_count += 1
                send_push(data["title"], data["snippet"], data["link"])
            else:
                print(f"Neu, aber nicht Innsbruck-Stadt - ignoriert: {data['snippet'][:80]}...")
            seen[listid] = data["snippet"]  # trotzdem merken, egal ob Innsbruck oder nicht

    save_seen(seen)
    print(
        f"Fertig. {len(listings)} Inserate insgesamt gesehen, {new_count} neu, "
        f"{notified_count} davon in Innsbruck-Stadt (benachrichtigt)."
    )


if __name__ == "__main__":
    main()
