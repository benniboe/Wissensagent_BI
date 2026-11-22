---
doc_id: DEMO-06
title: Report-Katalog
corpus: synthetic_demo
doc_type: report_catalog
domain: reports_models
version: "2.0"
valid_from: 2026-03-01
last_reviewed: 2026-10-01
status: current
supersedes: null
owner_role: BI-Plattformteam
sensitivity: S0
approval_id: null
language: de
synthetic: true
---

# Report-Katalog

> Synthetisches Beispieldokument für ein Studienprojekt. Keine realen Daten. Die Beispiel AG ist frei erfunden.

## 1. Zweck

Der Report-Katalog listet alle produktiven Berichte der Beispiel AG mit ihrem Zweck, ihrer Zielgruppe und ihrem semantischen Modell. Er hilft, den richtigen Bericht für eine Frage zu finden.

## 2. Übersicht

| Bericht | Semantisches Modell | Zielgruppe | App |
|---|---|---|---|
| RPT_Verkaufsuebersicht | SM_Verkauf | Verkaufsleitung | App Verkauf |
| RPT_Kundenanalyse | SM_Verkauf | Aussendienst | App Verkauf |
| RPT_Auftragseingang | SM_Verkauf | Verkaufsinnendienst | App Verkauf |
| RPT_Produktionsleistung | SM_Produktion | Produktionsleitung | App Produktion |
| RPT_Management_Cockpit (Management-Cockpit) | SM_Verkauf und SM_Produktion | Geschäftsleitung | App Management |

## 3. Berichte im Einzelnen

### 3.1 RPT_Verkaufsuebersicht

Zweck: tägliche Sicht auf die Umsatzentwicklung nach Region und Artikelgruppe, mit Vergleich zum Vorjahr und zum Budget. Zielgruppe ist die Verkaufsleitung. Wichtigste Kennzahlen: Umsatz Netto, Umsatz Vorjahr, Budget Umsatz. Dank Zeilenebenen-Sicherheit sehen regionale Verkaufsleitungen nur ihre Region.

### 3.2 RPT_Kundenanalyse

Zweck: Entwicklung des Umsatzes pro Kunde und Überblick über offene Verkaufschancen. Zielgruppe ist der Aussendienst, der den Bericht zur Vorbereitung von Kundenbesuchen nutzt. Der Bericht kombiniert Umsatzdaten aus dem ERP mit Verkaufschancen aus dem CRM. Wichtigste Kennzahlen: Umsatz Netto, Pipeline-Volumen.

### 3.3 RPT_Auftragseingang

Zweck: wöchentliche Auswertung des Auftragseingangs nach Kalenderwoche, Region und Artikelgruppe. Zielgruppe ist der Verkaufsinnendienst. Wichtigste Kennzahlen: Auftragseingang, Anzahl Aufträge.

### 3.4 RPT_Produktionsleistung

Zweck: Überwachung der Produktion pro Werk. Zielgruppe ist die Produktionsleitung. Wichtigste Kennzahlen: Produktionsmenge, Maschinenauslastung, Ausschussquote. Der Bericht zeigt Werk Nord und Werk Süd nebeneinander.

### 3.5 RPT_Management_Cockpit (Management-Cockpit)

Zweck: monatliche Gesamtsicht auf Verkauf und Produktion für die Geschäftsleitung, inklusive Vergleich mit dem Budget. Der Bericht wird über die App Management verteilt. Als einziger Bericht nutzt er zwei semantische Modelle: Er ist ein zusammengesetztes Modell, das SM_Verkauf und SM_Produktion per DirectQuery verbindet. Wichtigste Kennzahlen: Umsatz Netto, Budget Umsatz, Produktionsmenge, Ausschussquote. Die Budgetwerte stammen aus fact_budget (Planungsdateien).

## 4. Welcher Bericht für welche Frage?

| Frage | Bericht |
|---|---|
| Wie entwickelt sich der Umsatz in meiner Region? | RPT_Verkaufsuebersicht |
| Was hat ein bestimmter Kunde dieses Jahr gekauft? | RPT_Kundenanalyse |
| Wie viele Aufträge sind diese Woche eingegangen? | RPT_Auftragseingang |
| Wie ausgelastet sind die Maschinen im Werk Süd? | RPT_Produktionsleistung |
| Wie steht das Unternehmen im Monat gesamthaft da? | Management-Cockpit |

## 5. Stillgelegte Berichte

Der frühere Bericht «Umsatz klassisch» wurde im März 2026 durch RPT_Verkaufsuebersicht ersetzt und ist nicht mehr verfügbar.
