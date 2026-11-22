---
doc_id: DEMO-03
title: Pipelines und Scheduling
corpus: synthetic_demo
doc_type: operations
domain: operations
version: "2.0"
valid_from: 2026-03-01
last_reviewed: 2026-10-15
status: current
supersedes: DEMO-08
owner_role: BI-Plattformteam
sensitivity: S0
approval_id: null
language: de
synthetic: true
---

# Pipelines und Scheduling

> Synthetisches Beispieldokument für ein Studienprojekt. Keine realen Daten. Die Beispiel AG ist frei erfunden.

Version 2.0, gültig ab 1. März 2026. Diese Version ersetzt den Zeitplan der Version 1.0 (DEMO-08).

## 1. Zweck

Dieses Dokument beschreibt den täglichen Ablauf der Datenverarbeitung: welche Pipelines in welcher Reihenfolge laufen, wann die semantischen Modelle aktualisiert werden und was bei einem Fehler automatisch passiert.

## 2. Tagesablauf

Die Verarbeitung wird von der Master-Pipeline PL_Master_Daily gesteuert. Sie startet jeden Tag um 02:00 Uhr und ruft die folgenden Schritte nacheinander auf. Ein Schritt startet erst, wenn der vorherige erfolgreich war.

| Schritt | Element | Typ | Geplanter Start | Ergebnis |
|---|---|---|---|---|
| 1 | PL_ERP_Orders_Daily | Pipeline | 02:00 | ERP-Daten in LH_Bronze |
| 2 | PL_PPS_Production_Daily | Pipeline | 02:30 | PPS-Daten in LH_Bronze |
| 3 | DF_CRM_Daily | Dataflow Gen2 | 03:00 | CRM-Daten in LH_Bronze |
| 4 | NB_Silver_Transform | Notebook | ca. 03:30 | bereinigte Daten in LH_Silver |
| 5 | SP_Gold_Load | Stored Procedures | ca. 04:30 | Sternschema in WH_Gold |

Die Startzeiten der Schritte 4 und 5 sind Erfahrungswerte; sie hängen von der Laufzeit der vorherigen Schritte ab.

## 3. Aktualisierung der semantischen Modelle

Die semantischen Modelle haben eigene geplante Aktualisierungen in Power BI:

| Modell | Speichermodus | Geplante Aktualisierung |
|---|---|---|
| SM_Verkauf | Direct Lake | täglich 06:30 |
| SM_Produktion | Import | täglich 07:00 |

Für SM_Verkauf bewirkt die Aktualisierung im Direct-Lake-Modus, dass das Modell auf den neuesten Stand der Gold-Tabellen verweist. SM_Produktion lädt die Daten im Import-Modus vollständig neu.

Der Puffer zwischen dem Ende von SP_Gold_Load und der Modellaktualisierung ist bewusst gewählt. In Version 1.0 lag die Aktualisierung von SM_Verkauf zu früh und lief mehrmals auf unvollständige Gold-Daten.

## 4. Weitere Zeitpläne

| Element | Zeitplan |
|---|---|
| DF_Plan_Budget | wöchentlich, Montag 06:00 |
| Bereinigung alter Bronze-Daten | monatlich, erster Sonntag 04:00 |

## 5. Verhalten bei Fehlern

Jede Pipeline-Aktivität ist so eingestellt, dass sie bei einem Fehler zweimal wiederholt wird, jeweils im Abstand von 15 Minuten. Schlägt auch die zweite Wiederholung fehl, gilt:

1. Die Master-Pipeline PL_Master_Daily bricht ab. Nachgelagerte Schritte werden nicht ausgeführt.
2. Eine automatische E-Mail geht an die Verteilerliste des BI-Plattformteams.
3. Die Gold-Tabellen bleiben auf dem Stand des Vortags. Berichte zeigen weiterhin die Daten des Vortags.
4. Die Aktualisierung der semantischen Modelle läuft trotzdem zur geplanten Zeit, findet aber keine neuen Daten vor.

Fällt zum Beispiel PL_ERP_Orders_Daily endgültig aus, laufen PPS-, CRM-, Silver- und Gold-Schritte an diesem Tag nicht.

## 6. Überwachung

Das BI-Plattformteam prüft den Status der Läufe im Überwachungshub (Monitoring Hub) von Fabric. Die Lauf-Historie wird 30 Tage aufbewahrt. Eine manuelle Wiederholung eines fehlgeschlagenen Laufs nimmt ausschliesslich das BI-Plattformteam vor.
