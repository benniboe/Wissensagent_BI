---
doc_id: DEMO-04
title: Semantische Modelle und Power-BI-Nutzung
corpus: synthetic_demo
doc_type: semantic_model
domain: reports_models
version: "1.4"
valid_from: 2026-03-01
last_reviewed: 2026-09-10
status: current
supersedes: null
owner_role: BI-Plattformteam
sensitivity: S0
approval_id: null
language: de
synthetic: true
---

# Semantische Modelle und Power-BI-Nutzung

> Synthetisches Beispieldokument für ein Studienprojekt. Keine realen Daten. Die Beispiel AG ist frei erfunden.

## 1. Zweck

Dieses Dokument beschreibt die semantischen Modelle der Beispiel AG und die Regeln für die Nutzung von Power BI. Es nennt Tabellen und Measures je Modell. Die Berechnungslogik der Measures (DAX) ist nicht Teil dieses Dokuments.

## 2. Übersicht

| Modell | Workspace | Speichermodus | Datenquelle | Zeilenebenen-Sicherheit |
|---|---|---|---|---|
| SM_Verkauf | BI Verkauf | Direct Lake | WH_Gold | ja, nach Verkaufsregion |
| SM_Produktion | BI Produktion | Import | WH_Gold | nein |

## 3. Semantisches Modell SM_Verkauf

SM_Verkauf ist das zentrale Modell für Verkauf, Kunden und Verkaufschancen. Es liest im Speichermodus Direct Lake direkt aus dem Warehouse WH_Gold.

Tabellen:

- fact_verkauf: Auftrags- und Rechnungspositionen
- fact_opportunity: Verkaufschancen aus dem CRM
- fact_budget: Budgetwerte aus den Planungsdateien
- dim_kunde, dim_artikel, dim_datum, dim_region

Measures:

| Measure | Kurzbeschreibung |
|---|---|
| Umsatz Netto | Netto-Umsatz der Rechnungspositionen |
| Umsatz Vorjahr | Umsatz Netto in der Vergleichsperiode des Vorjahres |
| Auftragseingang | Wert der eingegangenen Aufträge |
| Anzahl Aufträge | Anzahl eindeutiger Aufträge |
| Pipeline-Volumen | Summe der offenen Verkaufschancen |
| Budget Umsatz | geplanter Umsatz gemäss Planungsdateien |

Zeilenebenen-Sicherheit (RLS): Das Modell enthält die Rollen «Region Nord», «Region Mitte» und «Region Süd». Mitglieder einer Rolle sehen nur die Verkaufsdaten ihrer Region. Die Geschäftsleitung und das Controlling sind keiner Rolle zugeordnet und sehen alle Regionen. Die Rollenmitgliedschaft wird über Gruppen gesteuert.

## 4. Semantisches Modell SM_Produktion

SM_Produktion enthält die Kennzahlen der beiden Werke. Es nutzt den Import-Modus, weil einige Berechnungen auf Maschinenzeiten im Direct-Lake-Modus zu langsam waren.

Tabellen:

- fact_produktion: Fertigungsaufträge und Maschinenzeiten
- dim_werk, dim_artikel, dim_datum

Measures:

| Measure | Kurzbeschreibung |
|---|---|
| Produktionsmenge | produzierte Stückzahl |
| Maschinenauslastung | Verhältnis von Laufzeit zu verfügbarer Zeit |
| Ausschussquote | Anteil fehlerhafter Teile an der Produktionsmenge |

Zeilenebenen-Sicherheit ist nicht eingerichtet; alle Berechtigten sehen beide Werke.

## 5. Nutzung von Power BI

- **Zugang über Apps:** Endnutzerinnen und Endnutzer greifen über die Apps «App Verkauf», «App Produktion» und «App Management» auf Berichte zu, nicht direkt über die Workspaces.
- **Eigene Berichte:** Key User dürfen eigene Berichte auf Basis von SM_Verkauf und SM_Produktion erstellen. Eigene semantische Modelle neben den zentralen Modellen sind nicht vorgesehen. Einzige Ausnahme ist RPT_Management_Cockpit: ein zusammengesetztes Modell, das SM_Verkauf und SM_Produktion per DirectQuery verbindet und vom BI-Plattformteam gepflegt wird.
- **Analyse in Excel:** Das Controlling darf SM_Verkauf über «In Excel analysieren» nutzen. Für andere Gruppen ist die Funktion nicht freigegeben.
- **Export:** Der Export zugrunde liegender Daten aus Berichten ist deaktiviert. Erlaubt ist der Export zusammengefasster Daten.
- **Teilen:** Berichte werden nicht einzeln geteilt, sondern über die App-Zielgruppen verteilt.

## 6. Änderungen an Modellen

Änderungen an SM_Verkauf und SM_Produktion entwickelt das BI-Plattformteam im DEV-Workspace und stellt sie über die Bereitstellungspipelines bereit (siehe DEMO-05). Fachliche Anforderungen an neue Measures reichen die Fachbereiche bei der BI-Fachrolle ein.
