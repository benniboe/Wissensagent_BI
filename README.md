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

## Ergebnisse (synthetischer Korpus, 20.11.2026)

| Messung | Ergebnis |
|---|---|
| Retrieval, 22 Fragen, kleine Chunks: Hit@1 / MRR | Dense 0.682 / 0.795 · Hybrid 0.773 / 0.845 · BM25 0.818 / 0.867 |
| Verhalten korrekt (31 Fälle × 2 Läufe) | 60/62, in beiden Läufen identisch |
| Antworten mit korrekter Quelle | 36/36 |
| Lücken erkannt / Sicherheitsfälle abgelehnt | 14/14 / 10/10 |
| Rückfragen / Folgefragen | 6/6 / 6/6 |
| Median Antwortzeit | 3.6 s |

BM25 liegt beim Retrieval nur eine Frage vor Hybrid. Das Testset begünstigt exakte Namen, weil
Fragen und Korpus vom selben Autor stammen. Hybrid ist deshalb Standard.

**Grenzen:**
- Die Stichprobe ist klein: Ein Fall entspricht 3 bis 6 Prozentpunkten.
- Regex erkennt nur bekannte Formate.
- Es gibt keine Berechtigungsprüfung.
- Das Modell läuft nur mit Temperatur 1.

## Einrichtung (macOS, Python 3.12)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        # einige Minuten (PyTorch)
pip install -e .
cp .env.example .env                   # LITELLM_BASE_URL, LITELLM_API_KEY, LLM_MODEL eintragen
```

## Starten

```bash
python scripts/check_setup.py          # Umgebung prüfen
python scripts/build_index.py          # Index bauen (einmalig, lädt beim ersten Mal bge-m3)
streamlit run app.py                   # Oberfläche im Browser
pytest                                 # 101 Tests, ohne Netzwerk
```

## Skripte

| Skript | Zweck |
|---|---|
| `check_setup.py` | prüft Python, Pakete, `.env` und den Git-Ausschluss von `.env` |
| `check_llm.py` | testet die Verbindung zu LiteLLM (`--list` zeigt die verfügbaren Modelle) |
| `build_synthetic_corpus.py` | erzeugt den Demo-Korpus aus `data/synthetic_demo/source/` |
| `build_index.py` | zerlegt den Korpus in Chunks, bettet sie ein und baut die Indizes |
| `inspect_chunks.py` | zeigt Chunk-Statistik oder alle Chunks eines Dokuments |
| `search.py` | Suche ohne LLM, zeigt Ränge und Scores (`--mode dense\|sparse\|hybrid`) |
| `ask.py` | einfache RAG-Kette ohne Agent, zum Vergleich |
| `chat.py` | Chat mit dem Agenten im Terminal (`--debug` zeigt den Pfad) |
| `evaluate_retrieval.py` | misst Hit@k, MRR und P@5 für 3 Verfahren × 2 Chunk-Grössen |
| `calibrate_threshold.py` | zeigt die Ähnlichkeiten je Testfrage, um die Schwelle zu wählen |
| `evaluate_agent.py` | schickt alle Testfälle durch den Agenten und prüft das Verhalten automatisch |
| `scan_sensitive.py` | sucht in Dokumenten nach Secrets und Personendaten (maskierter Bericht) |

## Struktur

| Ordner | Inhalt |
|---|---|
| `src/bi_agent/` | Paket: `agent/` (State, Nodes, Graph, Guardrails), `retrieval/`, `ingestion/`, `llm/`, `evaluation/`, `utils/` |
| `config/` | Parameter, Prompts, Guardrail-Regeln, Suchmuster, ohne Secrets |
| `scripts/` | Kommandozeilen-Werkzeuge (Tabelle oben) |
| `tests/` | Pytest; der Graph wird mit Fakes getestet, ohne LLM |
| `data/synthetic_demo/` | Faktenblatt der fiktiven Firma, Quellen (Markdown) und generierter Korpus |
| `data/evaluation/` | 31 Testfälle mit Ground Truth, aufgeteilt in Dev und Test |

Diese Dateien werden lokal erzeugt und von Git ausgeschlossen:
- `.env`
- `data/index/`
- `logs/` mit dem Verlauf `turns.jsonl` und dem Lückenprotokoll `gap_log.csv`
