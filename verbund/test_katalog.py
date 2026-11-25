"""#1385 Prüfungen zur Katalogpflege mehrerer Routing-Verbünde – ohne Netz.

Aufruf (im Wurzelverzeichnis des Repositorys):
    python3 -I -m unittest discover -s verbund -p "test_*.py"
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import katalog  # noqa: E402


def verbund(name, stand="2026-11-13", laender=None, teile=None):
    return {
        "format": 2, "engine": "valhalla", "engineVersion": "3.9.0", "verbund": name, "osmDate": stand,
        "laender": laender if laender is not None else [{"id": "ch", "name": {"de": "Schweiz", "en": "Switzerland"}, "regionen": []}],
        "teile": teile if teile is not None else [{"id": "basis", "typ": "basis", "datei": "basis.zip"},
                                                 {"id": "ch", "typ": "land", "land": "ch", "datei": "ch.zip"}],
    }


class Zusammenfuehren(unittest.TestCase):
    """Mehrere Kontinente nebeneinander – und der Rückfall darf keinen App-Stand aussperren."""

    def test_erster_lauf_uebernimmt_den_bisherigen_abschnitt(self):
        katalog_alt = {"verbund": verbund("europa", "2026-11-15")}
        neu, _ = katalog.zusammenfuehren(katalog_alt, verbund("nordamerika"))
        self.assertEqual(["europa", "nordamerika"], [v["verbund"] for v in neu["verbuende"]])

    def test_rueckfall_bleibt_beim_bisherigen_verbund(self):
        # Ein App-Stand vor #1385 liest nur «verbund». Stünde dort Nordamerika, verlöre er Europa aus der Liste.
        katalog_alt = {"verbund": verbund("europa", "2026-11-15")}
        neu, meldungen = katalog.zusammenfuehren(katalog_alt, verbund("nordamerika"))
        self.assertEqual("europa", neu["verbund"]["verbund"])
        self.assertTrue(any("bleibt bei" in m for m in meldungen))

    def test_gleicher_verbund_wird_ersetzt_und_der_rueckfall_mit(self):
        katalog_alt = {"verbund": verbund("europa", "2026-11-15"), "verbuende": [verbund("europa", "2026-11-15"), verbund("nordamerika")]}
        neu, _ = katalog.zusammenfuehren(katalog_alt, verbund("europa", "2026-11-25"))
        self.assertEqual(2, len(neu["verbuende"]))
        europa = [v for v in neu["verbuende"] if v["verbund"] == "europa"][0]
        self.assertEqual("2026-11-25", europa["osmDate"])
        self.assertEqual("2026-11-25", neu["verbund"]["osmDate"])        # derselbe Verbund, also mitgezogen
        self.assertEqual("2026-11-13", [v for v in neu["verbuende"] if v["verbund"] == "nordamerika"][0]["osmDate"])

    def test_fremde_abschnitte_bleiben(self):
        katalog_alt = {"karten": {"format": 1}, "hoehen": {"format": 1}, "verbund": verbund("europa")}
        neu, _ = katalog.zusammenfuehren(katalog_alt, verbund("nordamerika"))
        self.assertIn("karten", neu)
        self.assertIn("hoehen", neu)
        self.assertIn("aktualisiert", neu)

    def test_falsches_format_bricht_ab(self):
        with self.assertRaises(SystemExit):
            katalog.zusammenfuehren({}, dict(verbund("nordamerika"), format=1))
        with self.assertRaises(SystemExit):
            katalog.zusammenfuehren({}, dict(verbund("nordamerika"), verbund=""))


class Aufraeumen(unittest.TestCase):
    """Was der Bau liegen lässt: fehlender Kontinent und Regionen ohne Teil."""

    def test_kontinent_wird_ergaenzt(self):
        v = verbund("nordamerika", laender=[{"id": "us", "name": {"de": "USA", "en": "US"}, "regionen": []},
                                            {"id": "mx", "name": {"de": "Mexiko", "en": "Mexico"}, "regionen": []}])
        sauber = katalog.aufraeumen(v, {"us": "nordamerika", "mx": "nordamerika"})
        self.assertEqual(["nordamerika", "nordamerika"], [l["kontinent"] for l in sauber["laender"]])

    def test_vorhandener_kontinent_bleibt(self):
        v = verbund("europa", laender=[{"id": "ch", "name": {"de": "Schweiz", "en": "Switzerland"}, "kontinent": "europa", "regionen": []}])
        sauber = katalog.aufraeumen(v, {"ch": "etwas-anderes"})
        self.assertEqual("europa", sauber["laender"][0]["kontinent"])

    def test_regionen_ohne_teil_fallen_weg(self):
        # Der Nordamerika-Bau hat 66 statt 68 Gebiete erzeugt; Puerto Rico und die Jungferninseln haben keinen Teil (#1555).
        v = verbund("nordamerika",
                    laender=[{"id": "us", "name": {"de": "USA", "en": "US"},
                              "regionen": ["us-california", "us-puerto-rico", "us-us-virgin-islands"]}],
                    teile=[{"id": "basis", "typ": "basis"}, {"id": "us-california", "typ": "region", "land": "us"}])
        sauber = katalog.aufraeumen(v, {"us": "nordamerika"})
        self.assertEqual(["us-california"], sauber["laender"][0]["regionen"])

    def test_die_quelle_bleibt_unberuehrt(self):
        v = verbund("nordamerika", laender=[{"id": "us", "name": {"de": "USA", "en": "US"}, "regionen": ["us-texas"]}],
                    teile=[{"id": "basis", "typ": "basis"}])
        katalog.aufraeumen(v, {"us": "nordamerika"})
        self.assertEqual(["us-texas"], v["laender"][0]["regionen"])
        self.assertNotIn("kontinent", v["laender"][0])


class KontinenteJeLand(unittest.TestCase):
    def setUp(self):
        for k in ("VERBUND", "VERBUND_GEBIETE"):
            os.environ.pop(k, None)

    def test_alle_kontinente_ohne_umgebungsvariable(self):
        tabelle = katalog.kontinente_je_land()
        self.assertEqual("europa", tabelle["ch"])
        self.assertEqual("nordamerika", tabelle["us"])
        self.assertEqual("nordamerika", tabelle["gl"])

    def test_umgebung_bleibt_unveraendert(self):
        os.environ["VERBUND"] = "europa"
        katalog.kontinente_je_land()
        self.assertEqual("europa", os.environ.get("VERBUND"))


if __name__ == "__main__":
    unittest.main()
