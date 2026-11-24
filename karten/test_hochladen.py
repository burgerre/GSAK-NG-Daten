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

    def tearDown(self):
        os.environ.pop("VERBUND", None)


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


if __name__ == "__main__":
    unittest.main()
