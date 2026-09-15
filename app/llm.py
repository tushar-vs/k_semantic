from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
API_KEY = os.getenv("OPENAI_API_KEY", "")


def enabled() -> bool:
    return bool(API_KEY)


def _responses_api(prompt: str) -> tuple[str, dict[str, Any]]:
    payload = {"model": MODEL, "input": prompt}
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    started = time.perf_counter()
    with httpx.Client(timeout=45) as client:
        r = client.post("https://api.openai.com/v1/responses", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    latency_ms = (time.perf_counter() - started) * 1000
    text = data.get("output_text") or ""
    usage = data.get("usage") or {}
    meta = {"latency_ms": latency_ms, "model": MODEL, "prompt_tokens": usage.get("input_tokens"), "completion_tokens": usage.get("output_tokens")}
    return text, meta


def answer(query: str, retrieved: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    if not retrieved or retrieved[0]["score"] < 0.30:
        return (
            "I don't have enough evidence in your Kivi history to answer that confidently. I’d rather not guess."
            " You can add or say the missing context and I can use it later.",
            {"model": "grounded-abstention", "latency_ms": 0, "used_memory": False},
        )
    evidence_text = []
    for idx, item in enumerate(retrieved[:6], 1):
        m = item["memory"]
        evidence_text.append(f"MEMORY {idx}: [{m['memory_type']}] {m['statement']} | confidence={m['confidence']:.2f} | sources={[e['id'] for e in item['evidence']]}")
        for ev in item["evidence"][:3]:
            evidence_text.append(f"SOURCE {ev['id']}: {ev['formatted_text']}")
    context = "\n".join(evidence_text)
    if not enabled():
        best = retrieved[0]["memory"]
        answer_text = f"Based on your history: {best['statement']}\n\nSources: {', '.join(str(e['id']) for e in retrieved[0]['evidence']) or 'none'}."
        return answer_text, {"model": "deterministic-grounded", "latency_ms": 0, "used_memory": True}
    prompt = f"""You are Hey Kivi. Answer the user's request using ONLY the evidence below.\n\nUSER REQUEST: {query}\n\nEVIDENCE:\n{context}\n\nRules:\n1. Never invent facts not in evidence.\n2. If the evidence is insufficient or conflicting, say so clearly.\n3. Keep the answer concise and useful.\n4. End with a line `Sources: ...` listing the source interaction IDs you actually relied on.\n"""
    text, meta = _responses_api(prompt)
    meta["used_memory"] = True
    return text.strip(), meta
