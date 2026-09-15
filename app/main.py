from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .db import init_db
from .llm import answer as llm_answer
from .memory import ingest_record, retrieve, forget_memory, list_memories, list_interactions, traces

app = FastAPI(title="Kivi — Grounded Semantic Memory", version="1.0.0")
BASE_DIR = Path(__file__).resolve().parents[1]

class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)

class ImportRecord(BaseModel):
    id: str | None = None
    timestamp: str | None = None
    source: str = "unknown"
    raw_asr: str
    formatted_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def home():
    return (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/api/memories")
def api_memories():
    return list_memories()

@app.get("/api/interactions")
def api_interactions():
    return list_interactions()

@app.get("/api/traces")
def api_traces():
    return traces()

@app.post("/api/ask")
def api_ask(body: AskRequest):
    started = time.perf_counter()
    hits = retrieve(body.query, limit=8)
    answer, meta = llm_answer(body.query, hits)
    latency = (time.perf_counter() - started) * 1000
    from .db import connect
    # Keep logging local and simple.
    with connect() as conn:
        conn.execute(
            "INSERT INTO traces(trace_type,request_text,decision,reason,latency_ms,model_name,prompt_tokens,completion_tokens,payload_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("hey_kivi", body.query, "answer" if meta.get("used_memory") else "abstain", "Grounded retrieval + evidence gate", latency, meta.get("model"), meta.get("prompt_tokens"), meta.get("completion_tokens"), json.dumps({"hits": [{"memory_id": h['memory']['id'], "score": h['score'], "sources": [e['id'] for e in h['evidence']]} for h in hits]}), datetime.now(timezone.utc).isoformat()),
        )
    return {"answer": answer, "hits": hits, "latency_ms": latency, "model": meta.get("model")}

@app.post("/api/ingest")
def api_ingest(body: ImportRecord):
    rec = body.model_dump()
    if not rec.get("timestamp"):
        rec["timestamp"] = datetime.now(timezone.utc).isoformat()
    return ingest_record(rec)

@app.post("/api/import")
def api_import(file: UploadFile | None = File(default=None)):
    if file is None:
        raise HTTPException(400, "Upload a JSONL file")
    content = file.file.read().decode("utf-8")
    results = []
    for line in content.splitlines():
        if not line.strip():
            continue
        results.append(ingest_record(json.loads(line)))
    return {"count": len(results), "results": results[-20:]}

@app.post("/api/forget/{memory_id}")
def api_forget(memory_id: int):
    return {"forgotten": forget_memory(memory_id)}

@app.get("/api/evaluation")
def api_evaluation():
    p = BASE_DIR / "data" / "evaluation_results.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
