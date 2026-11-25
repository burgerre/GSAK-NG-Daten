#!/usr/bin/env python3
"""
#1385 Den Abschnitt der Routing-Verbünde im Katalog pflegen: **mehrere Kontinente nebeneinander**.

Bis zum 25.11.2026 schrieb der Workflow `routing-verbund.yml` den Abschnitt mit `jq '.verbund = $v[0]'` – er **ersetzte** ihn also.
Damit hätte Nordamerika Europa verdrängt: Geräte mit geladenen Europa-Daten behielten die Dateien, aber die Länderliste hätte nur noch
Nordamerika gezeigt, und «Aktualisieren» hätte sich auf den neuen Verbund bezogen. Ein Kontinent ist ein Valhalla-Bau, und Kacheln
verschiedener Bauten passen nicht zusammen (docs/11-Mobile/Offline-Routing-Laender-442.md), darum gibt es mehrere Verbünde nebeneinander.

Dieses Skript schreibt deshalb:

* `verbuende` – die Liste aller Verbünde. Ein Eintrag mit demselben Namen wird ersetzt, fremde bleiben stehen.
* `verbund` – **unverändert der bisherige Eintrag**, als Rückfall für App-Stände vor #1385, die nur diesen einen lesen. Er wird nur
  angefasst, wenn genau dieser Verbund einen neuen Stand bekommt. Würde hier der neueste Kontinent landen, verlöre ein älterer
  App-Stand seinen geladenen Kontinent aus der Liste – genau der Rückschritt, den #1385 verhindern soll.

Zwei Dinge räumt das Skript am neuen Verbund auf, bevor er in den Katalog kommt:

* **Kontinent je Land.** `verbund/gebiete.py` kannte das Feld nicht; ohne es landen Kanada, Grönland, Mexiko und die USA in der App
  unter «Weitere Gebiete», sobald ein Stand die eingebaute Rückfalltabelle nicht kennt.
* **Regionen ohne Teil.** Der Nordamerika-Bau hat 66 statt 68 Gebiete erzeugt (Puerto Rico und die Amerikanischen Jungferninseln
  fehlen im Geofabrik-Kontinentauszug, siehe #1385 und #1555). Die Länderliste nannte trotzdem 53 US-Regionen – zwei davon ohne
  Teil. Die App zeigt sie nicht an, aber der Katalog soll nichts nennen, was es nicht gibt.

Aufruf (im Wurzelverzeichnis des Repositorys):
    python3 -I verbund/katalog.py out/verbund.json katalog.json
    python3 -I verbund/katalog.py out/verbund.json katalog.json --trockenlauf
"""

import json
import os
import sys
from datetime import datetime, timezone

FORMAT = 2


def kontinente_je_land():
    """Land → Kontinent, aus derselben Quelle wie der Bau (alle Kontinente, nicht nur der aus VERBUND)."""
    hier = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, hier)
    import gebiete                                     # noqa: PLC0415 – erst hier, der Pfad steht vorher nicht
    vorher = {k: os.environ.get(k) for k in ("VERBUND", "VERBUND_GEBIETE")}
    tabelle = {}
    try:
        for kontinent in sorted(gebiete.KONTINENTE):
            os.environ["VERBUND"] = kontinent
            os.environ.pop("VERBUND_GEBIETE", None)
            for land in gebiete.laender():
                tabelle.setdefault(land["id"], kontinent)
    finally:
        for k, v in vorher.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return tabelle


def aufraeumen(verbund, kontinente=None):
    """Kontinent je Land ergänzen und Regionen ohne Teil entfernen. Gibt eine neue Struktur zurück."""
    teile = {t.get("id") for t in verbund.get("teile", [])}
    kontinente = kontinente_je_land() if kontinente is None else kontinente
    laender = []
    for land in verbund.get("laender", []):
        neu = dict(land)
        if not neu.get("kontinent") and kontinente.get(neu.get("id")):
            neu["kontinent"] = kontinente[neu["id"]]
        if neu.get("regionen"):
            neu["regionen"] = [r for r in neu["regionen"] if r in teile]
        laender.append(neu)
    return dict(verbund, laender=laender)


def zusammenfuehren(katalog, verbund):
    """
    Den Verbund in den Katalog einhängen: `verbuende` ergänzen, `verbund` nur anfassen, wenn es derselbe ist.

    Gibt (neuer Katalog, Meldungen) zurück.
    """
    name = verbund.get("verbund")
    if not name:
        raise SystemExit("verbund.json nennt kein Feld «verbund»")
    if verbund.get("format") != FORMAT:
        raise SystemExit("verbund.json hat Format %r, erwartet %r" % (verbund.get("format"), FORMAT))

    neu = dict(katalog)
    liste = list(katalog.get("verbuende") or [])
    if not liste and katalog.get("verbund"):
        # Erster Lauf mit dem neuen Format: den bisherigen einzelnen Abschnitt in die Liste übernehmen.
        liste = [katalog["verbund"]]

    meldungen = []
    ersetzt = False
    for i, v in enumerate(liste):
        if v.get("verbund") == name:
            meldungen.append("Verbund «%s» ersetzt (Stand %s → %s)" % (name, v.get("osmDate"), verbund.get("osmDate")))
            liste[i] = verbund
            ersetzt = True
            break
    if not ersetzt:
        meldungen.append("Verbund «%s» neu aufgenommen (Stand %s)" % (name, verbund.get("osmDate")))
        liste.append(verbund)

    neu["verbuende"] = sorted(liste, key=lambda v: v.get("verbund") or "")
    behalten = katalog.get("verbund")
    if behalten and behalten.get("verbund") != name:
        meldungen.append("Rückfall «verbund» bleibt bei «%s» (für App-Stände vor #1385)" % behalten.get("verbund"))
    else:
        neu["verbund"] = verbund
        meldungen.append("Rückfall «verbund» zeigt auf «%s»" % name)
    neu["aktualisiert"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return neu, meldungen


def main(argv):
    trockenlauf = "--trockenlauf" in argv
    argv = [a for a in argv if not a.startswith("--")]
    if len(argv) != 2:
        raise SystemExit(__doc__.strip().splitlines()[-2].strip())
    quelle, ziel = argv

    with open(quelle, encoding="utf-8") as f:
        verbund = aufraeumen(json.load(f))
    with open(ziel, encoding="utf-8") as f:
        katalog = json.load(f)

    neu, meldungen = zusammenfuehren(katalog, verbund)
    for m in meldungen:
        print(m)
    namen = [v.get("verbund") for v in neu["verbuende"]]
    print("Katalog führt %d Verbünde: %s" % (len(namen), ", ".join(namen)))
    for v in neu["verbuende"]:
        print("  %-14s Stand %s, %d Länder, %d Teile" % (v.get("verbund"), v.get("osmDate"), len(v.get("laender", [])), len(v.get("teile", []))))

    if trockenlauf:
        print("Trockenlauf – nichts geschrieben.")
        return 0
    with open(ziel, "w", encoding="utf-8", newline="\n") as f:
        json.dump(neu, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("Geschrieben:", ziel)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
