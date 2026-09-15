from __future__ import annotations
import sys
from pathlib import Path
import random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import init_db, DB_PATH, connect
from app.memory import ingest_record

DEMO = [
    ("d001", "slack", "I prefer meeting notes with a short summary followed by action items."),
    ("d002", "slack", "Remember that Atlas launches in October."),
    ("d003", "slack", "We decided Atlas pricing will stay monthly for the first release."),
    ("d004", "slack", "Yesterday the Atlas review moved to Thursday after the client requested more pricing detail."),
    ("d005", "notion", "I like design documents that start with the decision, not the background."),
    ("d006", "slack", "I prefer concise status updates with blockers called out explicitly."),
    ("d007", "slack", "Today the design review ended with a decision to test the onboarding copy again."),
    ("d008", "slack", "I prefer status updates with blockers first, then next steps."),
]

names = ["Atlas","Northstar","Beacon","Orchid","Kepler","Harbor","Juniper","Lumen","Pioneer","Quartz"]
subjects = ["pricing","onboarding copy","meeting format","launch timing","design review","status update","customer interviews","roadmap","QA plan","analytics"]

def seed():
    init_db()
    base = datetime(2026,1,1,tzinfo=timezone.utc)
    for idx,(eid,source,text) in enumerate(DEMO):
        ingest_record({"id":eid,"timestamp":(base+timedelta(hours=idx)).isoformat(),"source":source,"raw_asr":text,"formatted_text":text,"metadata":{"seed":True}})
    rng=random.Random(42)
    for i in range(500):
        product=rng.choice(names); subject=rng.choice(subjects)
        preferred_subject = subject if subject.endswith("updates") else (subject if subject == "status update" else f"{subject} updates")
        variants=[
            f"I prefer {preferred_subject} to be brief and end with next steps.",
            f"Remember that {product} is a project we discuss with the client.",
            f"We decided the {subject} for {product} will be reviewed next week.",
            f"Yesterday we moved the {product} {subject} discussion after a new customer question.",
            f"For {subject}, I like examples before implementation detail.",
            f"Today the {product} review focused on {subject} and ended without a final decision.",
        ]
        text=rng.choice(variants)
        ingest_record({"id":f"corpus-{i:04d}","timestamp":(base+timedelta(hours=i+20)).isoformat(),"source":rng.choice(["slack","notion","dictation"]),"raw_asr":text.lower(),"formatted_text":text,"metadata":{"corpus":"synthetic-v1","index":i}})
    print(f"seeded database at {DB_PATH}")

def reset():
    if DB_PATH.exists(): DB_PATH.unlink()
    print("database reset")

if __name__=='__main__':
    cmd=sys.argv[1] if len(sys.argv)>1 else 'init'
    if cmd=='init': init_db(); print('initialized')
    elif cmd=='seed': seed()
    elif cmd=='reset': reset()
    else: raise SystemExit('usage: manage.py [init|seed|reset]')
