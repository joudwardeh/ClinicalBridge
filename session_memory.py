"""
Session-level audit memory (Module 7 'memory' concept) - NOT long-term clinical memory.

Records a short audit trail per pipeline run to memory/session_memory.json:
scenario_id, patient_id, triage urgency, retrieved EHR source IDs, and the final brief ID.

This is deliberately minimal: it stores only IDs and the triage label (no clinical narrative, no
real patient data). It demonstrates how an orchestrator could keep an auditable session log. Records
are de-duplicated by scenario_id so re-running keeps the file clean.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MEM_PATH = ROOT / "memory" / "session_memory.json"


def _load():
    if MEM_PATH.exists():
        try:
            return json.loads(MEM_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"_meta": {"description": "Session-level audit memory for ClinicalBridge (IDs only; "
                                     "fictional data; not long-term clinical memory)."},
            "sessions": []}


def record_session(scenario_id, patient_id, triage_urgency, retrieved_source_ids, brief_id):
    MEM_PATH.parent.mkdir(exist_ok=True)
    mem = _load()
    mem["sessions"] = [s for s in mem.get("sessions", []) if s.get("scenario_id") != scenario_id]
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scenario_id": scenario_id,
        "patient_id": patient_id,
        "triage_urgency": triage_urgency,
        "retrieved_source_ids": list(retrieved_source_ids),
        "brief_id": brief_id,
    }
    mem["sessions"].append(entry)
    mem["sessions"].sort(key=lambda s: s.get("scenario_id", 0))
    MEM_PATH.write_text(json.dumps(mem, indent=2), encoding="utf-8")
    return entry


def load_sessions():
    return _load().get("sessions", [])
