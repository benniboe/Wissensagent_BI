---
doc_id: DEMO-05
title: Workspaces und Deployment
corpus: synthetic_demo
doc_type: architecture
domain: architecture
version: "1.2"
valid_from: 2026-03-01
last_reviewed: 2026-08-25
status: current
supersedes: null
owner_role: BI-Plattformteam
sensitivity: S0
approval_id: null
language: de
synthetic: true
---

# Workspaces und Deployment

> Synthetisches Beispieldokument für ein Studienprojekt. Keine realen Daten. Die Beispiel AG ist frei erfunden.

## 1. Zweck

Dieses Dokument beschreibt, wie die Fabric- und Power-BI-Workspaces der Beispiel AG aufgebaut sind und wie Änderungen von der Entwicklung in die Produktion gelangen.

## 2. Workspace-Struktur

Workspaces sind nach Bereich und Stufe getrennt. Jeder Bereich hat drei Workspaces mit den Stufen DEV, TEST und PROD. Das Namensschema lautet `<Bereich> [Stufe]`, zum Beispiel «BI Verkauf [PROD]».

| Bereich | Inhalt |
|---|---|
| BI Plattform | LH_Bronze, LH_Silver, WH_Gold, alle Pipelines, Dataflows und Notebooks |
| BI Verkauf | SM_Verkauf und die Verkaufsberichte |
| BI Produktion | SM_Produktion und RPT_Produktionsleistung |
| BI Management | RPT_Management_Cockpit (Management-Cockpit) |

Die Apps werden ausschliesslich aus den PROD-Workspaces veröffentlicht. Das Management-Cockpit liegt im Workspace «BI Management [PROD]» und wird über die App Management verteilt.

## 3. Rollen in den Workspaces

| Workspace-Stufe | Administrator | Mitglied / Mitwirkender | Betrachter |
|---|---|---|---|
| DEV | BI-Plattformteam | Report-Entwicklung | – |
| TEST | BI-Plattformteam | – | Key User der Fachbereiche |
| PROD | BI-Plattformteam | – | – (Zugriff nur über Apps) |

## 4. Versionsverwaltung

Nur die DEV-Workspaces sind mit Git verbunden. Das Repository liegt in Azure DevOps. Änderungen an Modellen, Berichten, Notebooks und Pipelines werden in DEV entwickelt und dort committet. TEST und PROD sind nicht mit Git verbunden; sie werden ausschliesslich über Bereitstellungspipelines befüllt.

## 5. Deployment-Prozess

Änderungen gelangen über die Bereitstellungspipelines (Deployment Pipelines) von Fabric von DEV über TEST nach PROD. Pro Bereich gibt es eine Bereitstellungspipeline: DP_Plattform, DP_Verkauf, DP_Produktion und DP_Management.

Ablauf einer Änderung, zum Beispiel an einem Bericht:

1. Entwicklung und Commit im DEV-Workspace.
2. Bereitstellung von DEV nach TEST durch das BI-Plattformteam.
3. Fachabnahme in TEST durch die Key User des Fachbereichs.
4. Nach erfolgter Abnahme Bereitstellung von TEST nach PROD durch das BI-Plattformteam.
5. Aktualisierung der betroffenen App, damit die Änderung bei den Nutzerinnen und Nutzern sichtbar wird.

Ohne Fachabnahme wird nichts nach PROD bereitgestellt. Ausnahmen bei dringenden Korrekturen entscheidet das BI-Plattformteam und informiert den Fachbereich nachträglich.

## 6. Bereitstellungsregeln

Bereitstellungsregeln stellen beim Deployment automatisch um, worauf ein Element zeigt. So verweist SM_Verkauf in DEV auf das Warehouse in «BI Plattform [DEV]» und in PROD auf das Warehouse in «BI Plattform [PROD]». Dadurch muss beim Deployment nichts manuell angepasst werden.

## 7. Was nicht über Deployment läuft

- Zugangsdaten und Gateway-Verbindungen werden pro Stufe separat eingerichtet.
- App-Zielgruppen werden in PROD direkt gepflegt.
- Zeitpläne der Modellaktualisierung werden nach dem ersten Deployment in PROD einmalig gesetzt (siehe DEMO-03).
