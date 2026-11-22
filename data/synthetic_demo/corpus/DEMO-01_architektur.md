# Architektur der BI-Datenplattform

> Synthetisches Beispieldokument für ein Studienprojekt. Keine realen Daten. Die Beispiel AG ist frei erfunden.

## 1. Zweck und Geltungsbereich

Dieses Dokument beschreibt die Architektur der BI-Datenplattform der Beispiel AG. Die Plattform stellt Daten aus den operativen Systemen für Analysen und Berichte bereit. Sie basiert auf Microsoft Fabric für Datenhaltung und Verarbeitung sowie auf Power BI für semantische Modelle und Berichte.

Das Dokument richtet sich an das BI-Plattformteam, an Report-Entwicklerinnen und -Entwickler sowie an Key User in den Fachbereichen. Details zur Datenanbindung stehen in DEMO-02, zum Zeitplan in DEMO-03, zu den Modellen in DEMO-04 und zu Workspaces und Deployment in DEMO-05.

## 2. Überblick

Die Plattform folgt der Medallion-Architektur mit drei Schichten: Bronze, Silver und Gold. Daten fliessen nur in eine Richtung, von den Quellsystemen über Bronze und Silver nach Gold. Berichte greifen ausschliesslich auf Gold zu, nie direkt auf Bronze oder Silver und nie direkt auf ein Quellsystem.

Ablauf in Kurzform:

1. Pipelines und Dataflows laden Daten aus vier Quellsystemen in die Bronze-Schicht.
2. Notebooks bereinigen und vereinheitlichen die Daten in der Silver-Schicht.
3. Stored Procedures bauen daraus das Sternschema der Gold-Schicht.
4. Semantische Modelle in Power BI lesen die Gold-Tabellen.
5. Berichte, Dashboards und Apps nutzen die semantischen Modelle.

## 3. Die drei Schichten

| Schicht | Fabric-Element | Typ | Inhalt | Erzeugt durch |
|---|---|---|---|---|
| Bronze | LH_Bronze | Lakehouse | Rohdaten 1:1 wie geliefert | Pipelines, Dataflows Gen2 |
| Silver | LH_Silver | Lakehouse | bereinigte, typisierte, deduplizierte Daten | Notebooks NB_Silver_* |
| Gold | WH_Gold | Warehouse | Sternschema für das Reporting | Stored Procedures SP_Gold_* |

### 3.1 Bronze

Die Bronze-Schicht speichert die Daten so, wie sie aus dem Quellsystem kommen. Es findet keine fachliche Transformation statt. Ergänzt werden nur zwei technische Spalten: `_load_ts` mit dem Ladezeitpunkt und `_source` mit dem Kürzel des Quellsystems. Alle Tabellen liegen im Delta-Format. Die Bronze-Schicht dient der Nachvollziehbarkeit: Wenn eine Zahl im Bericht unplausibel ist, lässt sich der Rohzustand prüfen.

### 3.2 Silver

In der Silver-Schicht werden die Daten bereinigt und vereinheitlicht, aber noch nicht aggregiert. Typische Schritte sind Datentypen setzen, Dubletten entfernen, leere Pflichtfelder markieren und Schlüssel harmonisieren. Ein Kunde aus dem CRM und derselbe Kunde aus dem ERP erhalten in Silver einen gemeinsamen Kundenschlüssel. Spaltennamen werden auf Deutsch vereinheitlicht. Die Transformationen laufen in den Notebooks NB_Silver_ERP, NB_Silver_CRM, NB_Silver_PPS und NB_Silver_Plan; orchestriert werden sie über das Notebook NB_Silver_Transform.

### 3.3 Gold

Die Gold-Schicht ist das Fabric Warehouse WH_Gold. Es enthält ein Sternschema mit Fakten- und Dimensionstabellen:

- Faktentabellen: fact_verkauf, fact_opportunity, fact_produktion, fact_budget
- Dimensionstabellen: dim_kunde, dim_artikel, dim_datum, dim_werk, dim_region

Die Gold-Tabellen werden täglich durch die Stored Procedures SP_Gold_Load neu befüllt. Nur die Gold-Schicht ist für Berichte freigegeben.

## 4. Quellsysteme

Die Plattform bindet vier Quellsysteme an: das ERP (Kürzel SRC_ERP), das CRM (SRC_CRM), das Produktionsplanungssystem PPS (SRC_PPS) und die Planungsdateien in Excel (SRC_PLAN). Art der Anbindung, Ladezeitpunkte und Ladeverfahren sind in DEMO-02 beschrieben.

## 5. Komponenten in Power BI

Auf der Gold-Schicht bauen zwei semantische Modelle auf: SM_Verkauf für Verkauf und Kunden sowie SM_Produktion für die Werke. Die Berichte werden über drei Power-BI-Apps verteilt: App Verkauf, App Produktion und App Management. Einzelheiten stehen in DEMO-04 und im Report-Katalog DEMO-06.

## 6. Architekturprinzipien

- **Einbahnstrasse:** Daten fliessen nur von Bronze über Silver nach Gold.
- **Eine Wahrheit für Berichte:** Berichte lesen nur aus semantischen Modellen, die semantischen Modelle nur aus Gold.
- **Nur lesend:** Die Plattform schreibt nie in Quellsysteme zurück.
- **Trennung der Stufen:** Entwicklung, Test und Produktion liegen in getrennten Workspaces (DEMO-05).
- **Nachvollziehbarkeit:** Jede Zeile in Bronze trägt Ladezeitpunkt und Quelle.

## 7. Zuständigkeiten

Die Zuständigkeiten sind auf Ebene der Plattform geregelt, nicht pro Workspace, Modell oder Pipeline.

| Bereich | Zuständig | Aufgaben |
|---|---|---|
| Fachlich | Fachbereiche: Verkaufsleitung für Verkauf, Produktionsleitung für Produktion | Anforderungen, fachliche Inhalte, Abnahme in der Teststufe |
| Technisch | BI-Plattformteam | Plattform, Pipelines, Modelle, Deployment, Betrieb |
| Erste Anlaufstelle | BI-Fachrolle | Fragen zur Plattform und Weiterleitung |

Eine Zuordnung einzelner Workspaces, Modelle oder Pipelines zu bestimmten Personen ist in diesem Dokument nicht enthalten.

## 8. Änderungshistorie

| Version | Datum | Änderung |
|---|---|---|
| 3.1 | 2026-10-20 | Zuständigkeiten ergänzt |
| 3.0 | 2026-03-01 | Gold-Schicht von Lakehouse auf Warehouse WH_Gold umgestellt |
| 2.0 | 2025-09-15 | Planungsdateien als viertes Quellsystem aufgenommen |
