---
doc_id: DEMO-02
title: Quellsysteme, Daten-Ingestion und Lineage
corpus: synthetic_demo
doc_type: data_flow
domain: data_sources
version: "2.2"
valid_from: 2026-03-01
last_reviewed: 2026-09-30
status: current
supersedes: null
owner_role: BI-Plattformteam
sensitivity: S0
approval_id: null
language: de
synthetic: true
---

# Quellsysteme, Daten-Ingestion und Lineage

> Synthetisches Beispieldokument für ein Studienprojekt. Keine realen Daten. Die Beispiel AG ist frei erfunden.

## 1. Zweck

Dieses Dokument beschreibt, welche Quellsysteme an die BI-Datenplattform angebunden sind, wie die Daten in die Bronze-Schicht geladen werden und wie sich der Weg der Daten bis zum Bericht nachverfolgen lässt (Lineage). Die Gesamtarchitektur steht in DEMO-01, der zeitliche Ablauf in DEMO-03.

## 2. Übersicht der Quellsysteme

| Kürzel | System | Inhalt | Standort | Anbindung |
|---|---|---|---|---|
| SRC_ERP | ERP | Aufträge, Rechnungen, Artikel, Lagerbestände | lokal im Rechenzentrum | On-Premises-Datengateway |
| SRC_CRM | CRM | Kunden, Verkaufschancen (Opportunities) | Cloud-Dienst | REST-API |
| SRC_PPS | Produktionsplanungssystem | Fertigungsaufträge, Maschinenzeiten, Ausschuss | lokal im Werk | On-Premises-Datengateway |
| SRC_PLAN | Planungsdateien (Excel) | Budget und Absatzplanung | SharePoint-Ordner «BI-Planung» | Dataflow Gen2 |

## 3. Ladeverfahren pro Quelle

### 3.1 ERP

Die Auftragsdaten stammen aus dem ERP. Sie werden durch die Pipeline PL_ERP_Orders_Daily geladen. Die Pipeline verwendet eine Copy Activity und greift über das On-Premises-Datengateway auf die ERP-Datenbank zu. Geladen wird inkrementell: Es werden nur Datensätze übernommen, deren Änderungsdatum nach dem letzten erfolgreichen Lauf liegt (Watermark-Verfahren). Die Pipeline startet um 02:00 Uhr und schreibt in die Tabellen erp_auftraege, erp_rechnungen, erp_artikel und erp_lager im Lakehouse LH_Bronze.

### 3.2 CRM

Die CRM-Daten werden mit dem Dataflow Gen2 DF_CRM_Daily über die REST-API des CRM abgerufen. Weil die API keine zuverlässigen Änderungsdaten liefert, wird jeden Tag eine Vollladung durchgeführt. Der Dataflow läuft um 03:00 Uhr und schreibt die Tabellen crm_kunden und crm_opportunities nach LH_Bronze.

### 3.3 PPS

Die Produktionsdaten lädt die Pipeline PL_PPS_Production_Daily. Wie beim ERP läuft der Zugriff über das On-Premises-Datengateway und inkrementell nach Änderungsdatum. Start ist um 02:30 Uhr. Ziel sind die Tabellen pps_fertigungsauftraege, pps_maschinenzeiten und pps_ausschuss in LH_Bronze.

### 3.4 Planungsdateien

Budget- und Absatzplanung pflegt das Controlling in Excel-Dateien im SharePoint-Ordner «BI-Planung». Der Dataflow Gen2 DF_Plan_Budget liest alle Dateien des Ordners und lädt sie vollständig nach LH_Bronze in die Tabelle plan_budget. Er läuft wöchentlich am Montag um 06:00 Uhr.

## 4. Schnittstellen

Alle Schnittstellen sind lesend. Die Plattform schreibt nie in ein Quellsystem zurück. Für die Anbindung gelten folgende Regeln:

- Lokale Systeme (ERP, PPS) werden ausschliesslich über das On-Premises-Datengateway angebunden.
- Zugangsdaten werden in den Verbindungseinstellungen von Fabric hinterlegt und nicht in Pipelines, Notebooks oder Dokumentationen festgehalten.
- Neue Quellen werden erst nach Prüfung durch das BI-Plattformteam angebunden.

## 5. Lineage: vom Quellsystem zum Bericht

Die folgende Tabelle zeigt, über welche Stationen die Daten bis zu den Berichten gelangen.

| Gold-Tabelle | Silver-Basis | Quellsystem | Semantisches Modell | Berichte |
|---|---|---|---|---|
| fact_verkauf | silver_auftraege, silver_rechnungen | ERP | SM_Verkauf | RPT_Verkaufsuebersicht, RPT_Kundenanalyse, RPT_Auftragseingang |
| fact_opportunity | silver_opportunities | CRM | SM_Verkauf | RPT_Kundenanalyse |
| dim_kunde | silver_kunden (ERP und CRM harmonisiert) | ERP, CRM | SM_Verkauf | alle Verkaufsberichte |
| dim_artikel | silver_artikel | ERP | SM_Verkauf, SM_Produktion | alle Berichte |
| fact_produktion | silver_fertigung, silver_maschinenzeiten | PPS | SM_Produktion | RPT_Produktionsleistung |
| fact_budget | silver_budget | Planungsdateien | SM_Verkauf | RPT_Verkaufsuebersicht, RPT_Management_Cockpit |
| dim_region | silver_regionen | ERP | SM_Verkauf | alle Verkaufsberichte |

Die Lineage-Ansicht in Fabric zeigt diese Abhängigkeiten auch grafisch. Sie ist im Workspace über die Schaltfläche «Lineage-Ansicht» erreichbar.

## 6. Datenqualität beim Laden

Beim Laden in Bronze werden keine Daten verworfen. Qualitätsprüfungen finden erst beim Übergang nach Silver statt: Datensätze ohne Pflichtfeld werden markiert, aber nicht gelöscht. Die Anzahl markierter Datensätze pro Lauf protokolliert das Notebook NB_Silver_Transform.
