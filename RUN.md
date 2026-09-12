# RUN.md — Kivi review instructions

## Primary review method

**Local browser application:** FastAPI + SQLite.

## Requirements

- Python 3.11+
- No external database required
- Optional: `OPENAI_API_KEY` for LLM-backed extraction/answering

## Install

```bash
cd kivi_submission
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment

Copy `.env.example` to `.env`.

Required only for LLM mode:

```text
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5-mini
```

## Create, migrate, and seed

```bash
python scripts/manage.py init
python scripts/manage.py seed
```

Seed creates the deterministic demo history and 500-record evaluation corpus if not already present.

## Start

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Primary interactions to try

1. Open **Hey Kivi** and ask:
   - `What format do I prefer for meeting notes?`
   - `What happened with the Atlas launch?`
   - `What should I remember about the design review?`
2. Ask an unsupported question:
   - `What is my mother's birthday?`
   The system should abstain because the history contains no supporting evidence.
3. Open **Memory** and inspect source interactions, confidence, and rationale.
4. Use **Forget** on a memory and repeat the corresponding Hey Kivi query.
5. Import a JSONL corpus from the Memory page or through the API.

## Candidate evaluation

Run the included evaluation:

```bash
python scripts/evaluate.py
```

Results are written to:

```text
data/evaluation_results.json
```

## Import another corpus

Accepted JSONL schema per record:

```json
{
  "id": "optional-source-id",
  "timestamp": "2026-01-02T10:15:00Z",
  "source": "slack",
  "raw_asr": "...",
  "formatted_text": "...",
  "metadata": {"channel": "#project"}
}
```

Import via API:

```bash
curl -X POST http://127.0.0.1:8000/api/import \
  -H 'Content-Type: application/json' \
  --data @data/sample_import.jsonl
```

Or use the UI import box.

## Inspect evaluation and memory state

- UI: `http://127.0.0.1:8000`
- Evaluation JSON: `data/evaluation_results.json`
- SQLite database: `data/kivi.db`
- API:
  - `GET /api/memories`
  - `GET /api/interactions`
  - `GET /api/traces`
  - `GET /api/evaluation`

## Reset

```bash
python scripts/manage.py reset
python scripts/manage.py init
python scripts/manage.py seed
```

## Review notes

The product is intentionally narrow: memory is designed around grounded recall and context-aware assistance, not autonomous life management. The evaluator can therefore inspect exactly why a memory was created, what evidence was retrieved, and why the assistant answered or abstained.
