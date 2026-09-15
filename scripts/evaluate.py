from __future__ import annotations
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import init_db, connect
from app.memory import retrieve
from app.llm import answer

EVAL = [
    ("What format do I prefer for meeting notes?", True, ["meeting notes"]),
    ("When does Atlas launch?", True, ["Atlas launches"]),
    ("What happened with the Atlas review?", True, ["Atlas review"]),
    ("What is my preferred status update format?", True, ["next steps"]),
    ("What is my mother's birthday?", False, []),
    ("Which city did I live in as a child?", False, []),
    ("What is the exact revenue target for next quarter?", False, []),
    ("What did we decide about Atlas pricing?", True, ["Atlas pricing"]),
]

def main():
    init_db()
    results=[]; total_latency=0
    for q, should_answer, needles in EVAL:
        t=time.perf_counter(); hits=retrieve(q); ans,meta=answer(q,hits); latency=(time.perf_counter()-t)*1000; total_latency+=latency
        text=ans.lower()
        if should_answer:
            evidence_ok=bool(hits and hits[0]['score']>=0.20)
            content_ok=any(n.lower() in text for n in needles)
            passed=evidence_ok and content_ok
        else:
            passed=not meta.get('used_memory',False) or 'not enough evidence' in text or "don't have enough evidence" in text
        results.append({"query":q,"expected_answerable":should_answer,"passed":passed,"top_score":hits[0]['score'] if hits else 0,"answer":ans,"latency_ms":latency})
    score=sum(r['passed'] for r in results)/len(results)
    with connect() as conn:
        interaction_count=conn.execute('SELECT count(*) c FROM interactions').fetchone()['c']
        memory_count=conn.execute("SELECT count(*) c FROM memories WHERE status='active'").fetchone()['c']
        db_bytes=Path(__file__).resolve().parents[1]/'data'/'kivi.db'
    out={"overall_score":score,"summary":f"{sum(r['passed'] for r in results)}/{len(results)} evaluation cases passed; average query latency {total_latency/len(results):.1f} ms.","cases":results,"metrics":{"interactions":interaction_count,"active_memories":memory_count,"database_bytes":db_bytes.stat().st_size if db_bytes.exists() else 0,"average_latency_ms":total_latency/len(results)}}
    p=Path(__file__).resolve().parents[1]/'data'/'evaluation_results.json'; p.write_text(json.dumps(out,indent=2),encoding='utf-8'); print(json.dumps(out,indent=2))

if __name__=='__main__': main()
