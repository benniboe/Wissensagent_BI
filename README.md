# BI-Wissensagent

Ein LangGraph-Agent beantwortet Fragen zu einer Microsoft-Fabric- und Power-BI-Landschaft aus
freigegebener Dokumentation. Er gibt geprüfte Quellen an, fragt bei unklaren Fragen nach, lehnt
Unzulässiges ab und eskaliert, wenn die Dokumentation keine Antwort hergibt.

FHNW, Modul Generative KI und Agentensysteme, HS 2026.

> **Daten:** Das Repository enthält nur synthetische Daten der fiktiven «Beispiel AG».
> Es liegen keine Originaldokumente und keine Secrets darin.
> Der Agent liest nur und hat keinen Zugriff auf produktive Systeme.

## Ablauf

```
Frage ─► Normalisieren ─► Regex-Prüfung ─► Einordnung (LLM) ─► Hybrid-Suche ─► Evidenz-Check ─► Antwort
                               │                 │                                   │            (Quellen geprüft)
                               ▼                 ▼                                   ▼
                          Ablehnung      Rückfrage / Ablehnung          Eskalation + Lückenprotokoll
```

- **Regex-Prüfung:** Fragen nach Secrets, Änderungsbefehle und Injection-Muster werden vor
  jedem LLM-Aufruf gestoppt. Die Antwort ist dann ein fester Text.
- **Einordnung:** Das LLM gibt die Einordnung strukturiert aus, mit einem Pydantic-Schema.
- **Hybrid-Suche:** Dense (bge-m3, lokal, Chroma) und BM25 werden mit Reciprocal Rank Fusion
  (k = 60) kombiniert, die Top 5 gehen weiter.
- **Evidenz-Check:** Stufe 1 ist eine Ähnlichkeitsschwelle von 0.45, Stufe 2 das Urteil des LLM.
- **Quellenprüfung:** Nur Dokument-IDs in eckigen Klammern zählen als Zitat. Jede zitierte ID
  muss auch gefunden worden sein.
- **Gedächtnis:** Der Checkpointer (InMemorySaver) arbeitet mit einer `thread_id` pro Sitzung.
  Pro Frage gelten die letzten 10 Nachrichten.

Das Sprachmodell läuft über FHNW LiteLLM (Claude Haiku 5.5). Nur dafür verlassen Daten den
Rechner, nämlich die Frage und die gefundenen Abschnitte.

## Ergebnisse

| Messung | Ergebnis |
|---|---|
| Retrieval, 22 Fragen, kleine Chunks: Hit@1 / MRR | Dense 0.682 / 0.795 · Hybrid 0.773 / 0.845 · BM25 0.818 / 0.867 |
| Verhalten korrekt (31 Fälle × 2 Läufe) | 60/62, in beiden Läufen identisch |
| Antworten mit korrekter Quelle | 36/36 |
| Lücken erkannt / Sicherheitsfälle abgelehnt | 14/14 / 10/10 |
| Rückfragen / Folgefragen | 6/6 / 6/6 |
| Median Antwortzeit | 3.6 s |


## Einrichtung

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        
pip install -e .
cp .env.example .env                   # LITELLM_BASE_URL, LITELLM_API_KEY, LLM_MODEL eintragen
```

## Starten

```bash
python scripts/check_setup.py          
python scripts/build_index.py          
streamlit run app.py                   
pytest                                 
```


Diese Dateien werden lokal erzeugt und von Git ausgeschlossen:
- `.env`
- `data/index/`
- `logs/` mit dem Verlauf `turns.jsonl` und dem Lückenprotokoll `gap_log.csv`
