# Kivi — Grounded Semantic Memory

Kivi is a voice-first assistant where semantic memory is a **decision-support layer**, not a personality profile. It remembers durable, useful context only when the evidence is strong enough, keeps provenance for every memory, and refuses to manufacture answers when the user's history does not support them.

## What this submission demonstrates

- Regular dictation stays mostly memory-neutral.
- Hey Kivi can use facts, preferences, and episodes learned from prior dictations.
- Memories have explicit provenance, confidence, status, and decision rationale.
- Conflicts create superseding memories rather than silently rewriting history.
- Users can inspect, edit, forget, and disable memory.
- Hey Kivi answers with source interactions and abstains when evidence is missing.
- An evaluation pipeline runs over 500 synthetic transcript-like records and reports retrieval quality, abstention behavior, latency, database growth, and model usage.

## Primary review method

Local FastAPI application + SQLite. See `RUN.md`.

## Architecture

```text
Transcript import / Dictation
        |
        v
  normalization + memory decision
        |
        +--> interactions table
        |
        +--> memory candidates --> active memories + evidence links
        |
        v
     SQLite + FTS5
        |
   Hey Kivi query
        |
        v
 retrieval -> evidence gate -> response generator -> citations
        |
        v
   normal user UI + inspectable trace
```

The LLM layer is provider-agnostic. When `OPENAI_API_KEY` is configured, it can use an OpenAI-compatible model for extraction and grounded answering. Without a key, a deterministic fallback is used so the app remains fully runnable offline.

## Key design principle

**Memory is allowed to change behavior only when the system can point back to evidence.** A useful memory therefore consists of a claim, type, provenance, confidence, status, and a set of source interaction IDs. A low-confidence or conflicting candidate can be retained as rejected evidence without becoming active memory.


