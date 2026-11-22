# Zeitplan der Datenverarbeitung

> Synthetisches Beispieldokument für ein Studienprojekt. Keine realen Daten. Die Beispiel AG ist frei erfunden.

Version 1.0, Stand Juni 2025.

## Täglicher Ablauf

Die Master-Pipeline PL_Master_Daily startet täglich um 01:00 Uhr. Sie lädt nacheinander die Daten aus ERP, PPS und CRM und baut danach die Silver- und Gold-Schicht auf. Die Verarbeitung ist erfahrungsgemäss um 04:00 Uhr abgeschlossen.

## Aktualisierung der Modelle

| Modell | Geplante Aktualisierung |
|---|---|
| SM_Verkauf | täglich 05:00 |
| SM_Produktion | täglich 05:30 |

## Fehler

Bei einem Fehler wird das BI-Plattformteam per E-Mail informiert. Automatische Wiederholungen sind nicht eingerichtet.
