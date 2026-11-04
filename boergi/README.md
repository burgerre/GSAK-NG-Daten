# Börgi-Wissen

Signiertes Paket mit zusätzlichen Formulierungen für Börgi, den Assistenten in GSAK-NG ([#602](https://github.com/burgerre/GSAK-NG/issues/602)).
Die App lädt es über die Börgi-Meldestelle und übernimmt es nur mit gültiger Signatur und höherer Version.

- `wissen.json`: das Paket (Format 1)
- `wissen.sig`: die Signatur (ECDSA P-256, SHA-256) über die genauen Bytes von `wissen.json`

Nicht von Hand ändern: Jede Änderung macht die Signatur ungültig. Gepflegt und signiert wird das Paket im Hauptrepository unter
`tools/boergi-wissen/`.
