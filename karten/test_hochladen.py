"""#1386 Prüfungen zum Katalogteil von karten/hochladen.py – ohne Netz und ohne R2.

Aufruf (im Wurzelverzeichnis des Repositorys):
    python3 -I -m unittest discover -s karten -p "test_*.py"
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hochladen  # noqa: E402


class GebieteTabelle(unittest.TestCase):
    """Die Zuordnung Datei → Gebiet muss Regionen mitnehmen, sonst bliebe Nordamerika ganz liegen."""

    def test_europa_ueber_geofabrik_pfad(self):
        os.environ["VERBUND"] = "europa"
        tabelle, laender = hochladen.gebiete_tabelle()
        self.assertIn("switzerland", tabelle)                       # «europe/switzerland» → «switzerland.pmtiles»
        gid, land, de, en, typ = tabelle["switzerland"]
        self.assertEqual(("ch", "ch", "land"), (gid, land, typ))
        self.assertEqual("Schweiz", de)
        self.assertEqual([], laender["ch"]["regionen"])

    def test_nordamerika_regionen(self):
        os.environ["VERBUND"] = "nordamerika"
        tabelle, laender = hochladen.gebiete_tabelle()
        self.assertIn("us-california", tabelle)                     # Dateiname = Gebiets-Id
        gid, land, de, en, typ = tabelle["us-california"]
        self.assertEqual(("us-california", "us", "region"), (gid, land, typ))
        self.assertIn("us-california", laender["us"]["regionen"])
        self.assertGreater(len(laender["us"]["regionen"]), 40)       # 53 US-Gebiete
        self.assertEqual([], laender["mx"]["regionen"])              # Mexiko bleibt ein Teil

    def test_beide_kontinente_ohne_umgebungsvariable(self):
        """
        Ohne gesetzte Variable muss die Tabelle **beide** Kontinente kennen.

        Am 25.11.2026 hat der Upload-Trockenlauf alle 68 Nordamerika-Dateien als "kein Gebiet bekannt" uebersprungen:
        `gebiete.gebiete()` liefert die Tabellen aus `VERBUND` (Standard europa), und der Workflow setzt die Variable nicht.
        Die beiden Pruefungen darueber haben das nicht gemerkt, weil sie `VERBUND` selbst setzen.
        """
        for k in ("VERBUND", "VERBUND_GEBIETE"):
            os.environ.pop(k, None)
        tabelle, laender = hochladen.gebiete_tabelle()
        self.assertIn("switzerland", tabelle)
        self.assertIn("us-california", tabelle)
        self.assertIn("ca-quebec", tabelle)
        self.assertIn("mx", tabelle)
        self.assertIn("ch", laender)
        self.assertIn("us", laender)

    def test_eingeschraenkter_bau_beschneidet_die_zuordnung_nicht(self):
        # VERBUND_GEBIETE schraenkt einen Valhalla-Bau ein; fuer die Zuordnung der Kartendateien darf das nichts aendern.
        os.environ["VERBUND"] = "europa"
        os.environ["VERBUND_GEBIETE"] = "ch"
        tabelle, laender = hochladen.gebiete_tabelle()
        self.assertIn("us-california", tabelle)
        self.assertIn("us", laender)

    def test_umgebung_bleibt_unveraendert(self):
        os.environ["VERBUND"] = "europa"
        hochladen.gebiete_tabelle()
        self.assertEqual("europa", os.environ.get("VERBUND"))
        self.assertIsNone(os.environ.get("VERBUND_GEBIETE"))

    def tearDown(self):
        os.environ.pop("VERBUND", None)
        os.environ.pop("VERBUND_GEBIETE", None)


class AbschnittZusammenfuehren(unittest.TestCase):
    """Ergänzen statt ersetzen: Europa darf nicht verschwinden, wenn Nordamerika dazukommt."""

    @staticmethod
    def _abschnitt(stand, laender, dateien):
        return {"format": 1, "schema": "openmaptiles", "stand": stand, "laender": laender, "dateien": dateien}

    def test_fremde_eintraege_bleiben(self):
        alt = self._abschnitt("2026-11-17", [{"id": "ch", "name": {"de": "Schweiz", "en": "Switzerland"}}],
                              [{"land": "ch", "datei": "switzerland.pmtiles", "groesse": 1}])
        neu = self._abschnitt("2026-11-20", [{"id": "us", "name": {"de": "Vereinigte Staaten", "en": "United States"}, "regionen": ["us-california"]}],
                              [{"id": "us-california", "land": "us", "datei": "us-california.pmtiles", "groesse": 2}])
        zusammen = hochladen.abschnitt_zusammenfuehren(alt, neu)
        self.assertEqual(["ch", "us"], sorted(l["id"] for l in zusammen["laender"]))
        self.assertEqual(["switzerland.pmtiles", "us-california.pmtiles"], sorted(d["datei"] for d in zusammen["dateien"]))
        self.assertEqual("2026-11-20", zusammen["stand"])            # der neueste Stand gilt für den Abschnitt

    def test_gleiche_id_wird_ersetzt(self):
        alt = self._abschnitt("2026-11-17", [{"id": "us", "name": {"de": "Vereinigte Staaten", "en": "United States"}}],
                              [{"id": "us-california", "land": "us", "datei": "us-california.pmtiles", "groesse": 1}])
        neu = self._abschnitt("2026-11-20", [{"id": "us", "name": {"de": "Vereinigte Staaten", "en": "United States"}, "regionen": ["us-california"]}],
                              [{"id": "us-california", "land": "us", "datei": "us-california.pmtiles", "groesse": 999}])
        zusammen = hochladen.abschnitt_zusammenfuehren(alt, neu)
        self.assertEqual(1, len(zusammen["dateien"]))
        self.assertEqual(999, zusammen["dateien"][0]["groesse"])
        self.assertEqual(1, len(zusammen["laender"]))
        self.assertEqual(["us-california"], zusammen["laender"][0]["regionen"])

    def test_anderes_format_wird_nicht_gemischt(self):
        alt = {"format": 0, "schema": "anderes", "laender": [], "dateien": []}
        neu = self._abschnitt("2026-11-20", [], [])
        self.assertIs(neu, hochladen.abschnitt_zusammenfuehren(alt, neu))
        self.assertIs(neu, hochladen.abschnitt_zusammenfuehren(None, neu))


class LeereKarten(unittest.TestCase):
    def test_schwelle_unter_einem_megabyte(self):
        # Puerto Rico und die Amerikanischen Jungferninseln ergaben 0 B; eine echte Karte ist immer deutlich grösser.
        self.assertLess(hochladen.MIN_KARTE, 1024 * 1024)
        self.assertGreater(hochladen.MIN_KARTE, 0)


class GebieteOhneDaten(unittest.TestCase):
    """
    #1386 Gebiete, die im Kontinentauszug fehlen, duerfen nicht in den Katalog - und sind an der Groesse nicht erkennbar.

    Am 25.11.2026 stand Puerto Rico (442 KB, leer) im geschriebenen Katalog, waehrend Monaco (410 KB) eine richtige Karte ist.
    Eine Schwelle, die Puerto Rico faengt, haette Monaco aus dem Katalog geworfen.
    """

    def test_bekannte_gebiete_sind_benannt(self):
        self.assertIn("us-puerto-rico", hochladen.OHNE_DATEN)
        self.assertIn("us-us-virgin-islands", hochladen.OHNE_DATEN)
        for grund in hochladen.OHNE_DATEN.values():
            self.assertIn("#1555", grund)          # die Folgeaufgabe, die den eigenen Auszug baut

    def test_schwelle_wirft_monaco_nicht_weg(self):
        monaco = 410 * 1024                        # gemessen im Katalog vom 17.11.2026
        puerto_rico = 442 * 1024                   # leer, aber groesser als Monaco
        self.assertLess(hochladen.MIN_KARTE, monaco)
        self.assertLess(monaco, puerto_rico)       # darum entscheidet Wissen, nicht die Groesse

    def test_regionen_ohne_daten_stehen_nicht_im_land(self):
        for k in ("VERBUND", "VERBUND_GEBIETE"):
            os.environ.pop(k, None)
        _, laender = hochladen.gebiete_tabelle()
        # Die Gebietstabelle fuehrt sie weiter (das Routing braucht sie), der Katalog darf sie nicht nennen.
        self.assertIn("us-puerto-rico", laender["us"]["regionen"])
        gefiltert = [r for r in laender["us"]["regionen"] if r not in hochladen.OHNE_DATEN]
        self.assertNotIn("us-puerto-rico", gefiltert)
        self.assertNotIn("us-us-virgin-islands", gefiltert)
        self.assertEqual(51, len(gefiltert))       # 53 Gebiete der Tabelle minus die zwei ohne Daten


class KontinentImKatalog(unittest.TestCase):
    """#1386 Der Kontinent gehoert je Land in den Katalog, sonst landen neue Gebiete in der App unter "Weitere Gebiete"."""

    def test_jedes_land_nennt_seinen_kontinent(self):
        for k in ("VERBUND", "VERBUND_GEBIETE"):
            os.environ.pop(k, None)
        _, laender = hochladen.gebiete_tabelle()
        self.assertEqual("europa", laender["ch"]["kontinent"])
        self.assertEqual("nordamerika", laender["us"]["kontinent"])
        self.assertEqual("nordamerika", laender["mx"]["kontinent"])
        self.assertTrue(all(l.get("kontinent") for l in laender.values()))


if __name__ == "__main__":
    unittest.main()
