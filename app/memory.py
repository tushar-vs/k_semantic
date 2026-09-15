from __future__ import annotations

import json
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .db import connect

STOP = {
    "the","a","an","and","or","to","of","in","on","for","with","my","our","is","are",
    "i","we","you","this","that","it","be","as","at","from","about","do","did","what",
    "how","should","can","could","would","please","hey","kivi","me","into","by","was","were",
}

@dataclass
class MemoryCandidate:
    memory_type: str
    statement: str
    key: str
    confidence: float
    decision_reason: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_key(text: str) -> str:
    s = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    s = " ".join(s.split())
    return s[:180]


def extract_candidates(text: str) -> list[MemoryCandidate]:
    """Deterministic fallback extractor. Intentionally conservative."""
    cands: list[MemoryCandidate] = []
    patterns = [
        (r"\bi prefer ([^.?!]+)", "preference", 0.96, "Explicit preference phrase"),
        (r"\bi like ([^.?!]+)", "preference", 0.92, "Explicit preference phrase"),
        (r"\bmy preferred ([a-z ]+) is ([^.?!]+)", "preference", 0.97, "Explicit preferred-value phrase"),
        (r"\bremember that ([^.?!]+)", "fact", 0.99, "Explicit remember instruction"),
        (r"\b([A-Z][A-Za-z0-9_-]{2,}) (?:launches|launch) ([^.?!]+)", "fact", 0.90, "Named project fact"),
        (r"\b([A-Z][A-Za-z0-9_-]{2,}) (?:is|was) ([^.?!]+)", "fact", 0.82, "Named entity statement"),
        (r"\b(?:yesterday|today|last week|last month) ([^.?!]+)", "episode", 0.74, "Time-anchored episode"),
        (r"\bwe (?:decided|agreed) ([^.?!]+)", "episode", 0.92, "Explicit decision episode"),
        (r"\bthe ([a-z0-9 -]+) review (?:moved|was moved) to ([^.?!]+)", "episode", 0.92, "Named review episode"),
    ]
    for pat, typ, conf, why in patterns:
        m = re.search(pat, text, flags=re.I)
        if not m:
            continue
        statement = text.strip()
        key = normalize_key(statement)
        cands.append(MemoryCandidate(typ, statement, key, conf, why))
    return cands[:3]


def insert_interaction(external_id: str | None, occurred_at: str, source: str, raw_asr: str, formatted_text: str, metadata: dict[str, Any] | None) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO interactions(external_id, occurred_at, source, raw_asr, formatted_text, metadata_json) VALUES (?,?,?,?,?,?)",
            (external_id, occurred_at, source, raw_asr, formatted_text, json.dumps(metadata or {})),
        )
        if cur.lastrowid:
            return int(cur.lastrowid)
        row = conn.execute("SELECT id FROM interactions WHERE external_id=?", (external_id,)).fetchone()
        return int(row["id"])


def add_memory(candidate: MemoryCandidate, interaction_id: int) -> tuple[int | None, str]:
    now = now_iso()
    with connect() as conn:
        existing = conn.execute("SELECT * FROM memories WHERE memory_key=?", (candidate.key,)).fetchone()
        if existing:
            conn.execute(
                "INSERT OR IGNORE INTO memory_evidence(memory_id, interaction_id) VALUES (?,?)",
                (existing["id"], interaction_id),
            )
            if candidate.confidence > existing["confidence"] and existing["status"] == "active":
                conn.execute("UPDATE memories SET confidence=?, updated_at=?, decision_reason=? WHERE id=?",
                             (candidate.confidence, now, candidate.decision_reason, existing["id"]))
            return int(existing["id"]), "reinforced"

        # Lightweight contradiction handling: same type + overlapping normalized words.
        tokens = [t for t in candidate.key.split() if t not in STOP and len(t) > 2]
        potential = []
        for row in conn.execute("SELECT * FROM memories WHERE memory_type=? AND status='active'", (candidate.memory_type,)).fetchall():
            old_tokens = set(row["memory_key"].split())
            overlap = sum(1 for t in tokens if t in old_tokens)
            if overlap >= max(2, min(4, len(tokens))):
                potential.append(row)
        supersede_id = None
        if potential and candidate.memory_type == 'fact':
            # A new explicit statement can supersede an earlier one when it shares a strong subject.
            old = max(potential, key=lambda r: r["confidence"])
            old_text = old["statement"].lower()
            new_text = candidate.statement.lower()
            if ("prefer" in old_text and "prefer" in new_text) or candidate.memory_type == "fact":
                supersede_id = int(old["id"])
                conn.execute("UPDATE memories SET status='superseded', updated_at=? WHERE id=?", (now, supersede_id))

        cur = conn.execute(
            "INSERT INTO memories(memory_key,memory_type,statement,confidence,status,created_at,updated_at,decision_reason,supersedes_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (candidate.key, candidate.memory_type, candidate.statement, candidate.confidence, "active", now, now, candidate.decision_reason, supersede_id),
        )
        mid = int(cur.lastrowid)
        conn.execute("INSERT INTO memory_evidence(memory_id, interaction_id) VALUES (?,?)", (mid, interaction_id))
        conn.execute("INSERT INTO memory_fts(memory_id,statement,memory_type) VALUES (?,?,?)", (str(mid), candidate.statement, candidate.memory_type))
        return mid, "created"


def ingest_record(rec: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    interaction_id = insert_interaction(
        rec.get("id"), rec.get("timestamp") or now_iso(), rec.get("source", "unknown"),
        rec.get("raw_asr", ""), rec.get("formatted_text") or rec.get("raw_asr", ""), rec.get("metadata") or {},
    )
    text = rec.get("formatted_text") or rec.get("raw_asr") or ""
    candidates = extract_candidates(text)
    created = []
    rejected = []
    for c in candidates:
        if c.confidence < 0.78:
            rejected.append({"candidate": c.statement, "reason": "Below conservative confidence threshold"})
            continue
        mid, action = add_memory(c, interaction_id)
        created.append({"memory_id": mid, "action": action, "type": c.memory_type, "statement": c.statement})
    latency = (time.perf_counter() - started) * 1000
    with connect() as conn:
        conn.execute(
            "INSERT INTO traces(trace_type,interaction_id,decision,reason,latency_ms,model_name,payload_json,created_at) VALUES (?,?,?,?,?,?,?,?)",
            ("ingest", interaction_id, "memory-update", "Conservative candidate extraction with provenance", latency, "deterministic-fallback", json.dumps({"created": created, "rejected": rejected}), now_iso()),
        )
    return {"interaction_id": interaction_id, "created": created, "rejected": rejected, "latency_ms": latency}


def _stem(token: str) -> str:
    for suffix in ("ingly", "edly", "ing", "ers", "ies", "es", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            return token[:-len(suffix)]
    return token

def token_score(query: str, text: str, memory_type: str = "") -> float:
    qraw = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if t not in STOP and len(t) > 2]
    xraw = [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP and len(t) > 2]
    q = {_stem(t) for t in qraw}; x = {_stem(t) for t in xraw}
    if not q or not x:
        return 0.0
    score = len(q & x) / len(q)
    qtext = query.lower()
    if any(w in qtext for w in ("prefer", "preferred", "format")) and memory_type == "preference":
        score += 0.22
    if any(w in qtext for w in ("happened", "moved", "decided")) and memory_type == "episode":
        score += 0.12
    return min(score, 1.0)


def retrieve(query: str, limit: int = 8) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM memories WHERE status='active'").fetchall()
        scored = [(token_score(query, r["statement"], r["memory_type"]), r) for r in rows]
        scored.sort(key=lambda x: (x[0], x[1]["confidence"]), reverse=True)
        results = []
        for score, row in scored[:limit]:
            evidence = conn.execute(
                "SELECT i.id,i.occurred_at,i.source,i.raw_asr,i.formatted_text FROM interactions i JOIN memory_evidence me ON me.interaction_id=i.id WHERE me.memory_id=? ORDER BY i.occurred_at DESC",
                (row["id"],),
            ).fetchall()
            results.append({
                "memory": dict(row),
                "score": round(score, 4),
                "evidence": [dict(e) for e in evidence],
            })
        return results


def forget_memory(memory_id: int) -> bool:
    with connect() as conn:
        cur = conn.execute("UPDATE memories SET status='forgotten', updated_at=? WHERE id=? AND status IN ('active','superseded')", (now_iso(), memory_id))
        return cur.rowcount > 0


def list_memories() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM memories ORDER BY updated_at DESC").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            ev = conn.execute("SELECT interaction_id FROM memory_evidence WHERE memory_id=?", (r["id"],)).fetchall()
            d["evidence"] = [x["interaction_id"] for x in ev]
            out.append(d)
        return out


def list_interactions(limit=100):
    with connect() as conn:
        rows = conn.execute("SELECT * FROM interactions ORDER BY occurred_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def traces(limit=100):
    with connect() as conn:
        rows = conn.execute("SELECT * FROM traces ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
