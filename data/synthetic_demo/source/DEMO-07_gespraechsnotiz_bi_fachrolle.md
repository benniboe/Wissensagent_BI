---
doc_id: DEMO-07
title: Gesprächsnotiz mit der BI-Fachrolle
corpus: synthetic_demo
doc_type: interview_notes
domain: mixed
version: "0.1"
valid_from: 2026-11-12
last_reviewed: 2026-11-12
status: draft
supersedes: null
owner_role: BI-Fachrolle
sensitivity: S0
approval_id: null
language: de
synthetic: true
---

# Gesprächsnotiz mit der BI-Fachrolle

> Synthetisches Beispieldokument für ein Studienprojekt. Keine realen Daten. Die Beispiel AG ist frei erfunden.

**Status: Entwurf.** Diese Notiz gibt mündliche Aussagen aus einem Gespräch wieder. Die Inhalte sind nicht offiziell dokumentiert, nicht geprüft und nicht fachlich abgenommen. Sie ersetzen keine Dokumentation.

## 1. Anlass

Das Gespräch diente dazu, Wissen zu erfassen, das in den bestehenden Dokumenten fehlt. Gemäss BI-Fachrolle sind Architektur, Datenflüsse, Modelle und Deployment gut beschrieben. Kaum dokumentiert sind dagegen die fachlichen Definitionen der Kennzahlen, deren Berechnungslogik in DAX sowie das Vorgehen bei Störungen.

## 2. Aussagen zu Kennzahlen

- **Auftragseingang:** Gezählt wird nach Auftragsdatum, nicht nach Lieferdatum. Ein Auftrag vom 30. Juni mit Lieferung im Juli zählt also zum Juni.
- **Umsatz Netto:** Umsatz nach Rabatten und ohne Mehrwertsteuer. Gutschriften werden abgezogen.
- **Deckungsbeitrag:** Es gibt keine einheitliche Definition. Controlling und Verkauf rechnen unterschiedlich, deshalb ist der Deckungsbeitrag bisher in keinem Modell enthalten. Eine Klärung ist offen.
- Zu Maschinenauslastung und Ausschussquote konnte im Gespräch keine genaue Berechnung genannt werden. Die Logik steckt in den Measures von SM_Produktion und ist nicht beschrieben.

## 3. Tipps bei Störungen

Es gibt kein offizielles Troubleshooting-Handbuch. Die BI-Fachrolle nannte drei Erfahrungswerte:

1. Wenn die Aktualisierung eines semantischen Modells fehlschlägt oder alte Zahlen zeigt, zuerst prüfen, ob die Master-Pipeline PL_Master_Daily in der Nacht erfolgreich war. Meist liegt die Ursache dort und nicht im Modell.
2. Fehler beim Zugriff über das On-Premises-Datengateway nicht selbst beheben, sondern das BI-Plattformteam informieren.
3. Fehlen im Management-Cockpit am Monatsanfang die Budgetwerte, liegt die neue Planungsdatei meist noch nicht im SharePoint-Ordner «BI-Planung».

Für alle anderen Fehlermeldungen gibt es keine dokumentierten Lösungen. Solche Fälle sollen an das BI-Plattformteam gehen.

## 4. Offene Punkte

- Fachliche Kennzahlendefinitionen mit den Fachbereichen erarbeiten und dokumentieren.
- Ein Troubleshooting-Handbuch für die häufigsten Fehler erstellen.
- Zuständigkeiten pro Modell und Pipeline festlegen; heute sind sie nur grob geregelt.
