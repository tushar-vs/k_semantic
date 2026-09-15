import json
import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "kivi.db"

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT UNIQUE,
    occurred_at TEXT NOT NULL,
    source TEXT NOT NULL,
    raw_asr TEXT NOT NULL,
    formatted_text TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_interactions_occurred_at ON interactions(occurred_at);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_key TEXT NOT NULL UNIQUE,
    memory_type TEXT NOT NULL CHECK(memory_type IN ('fact','preference','episode')),
    statement TEXT NOT NULL,
    confidence REAL NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active','rejected','superseded','forgotten')) DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    decision_reason TEXT NOT NULL,
    supersedes_id INTEGER,
    FOREIGN KEY(supersedes_id) REFERENCES memories(id)
);
CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);

CREATE TABLE IF NOT EXISTS memory_evidence (
    memory_id INTEGER NOT NULL,
    interaction_id INTEGER NOT NULL,
    evidence_role TEXT NOT NULL DEFAULT 'supporting',
    PRIMARY KEY(memory_id, interaction_id),
    FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE,
    FOREIGN KEY(interaction_id) REFERENCES interactions(id) ON DELETE CASCADE
);

CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    memory_id UNINDEXED,
    statement,
    memory_type,
    content=''
);

CREATE TABLE IF NOT EXISTS traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_type TEXT NOT NULL,
    request_text TEXT,
    interaction_id INTEGER,
    memory_id INTEGER,
    decision TEXT,
    reason TEXT,
    latency_ms REAL,
    model_name TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    estimated_cost_usd REAL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_traces_created_at ON traces(created_at);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def json_loads(value: str, default=None):
    try:
        return json.loads(value)
    except Exception:
        return default if default is not None else {}
