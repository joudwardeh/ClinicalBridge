"""
EHR document loader — turns the fictional ClinicalBridge EHR into LangChain ``Document`` objects.

This is step 1 of the genuine LangChain RAG pipeline (load -> split -> embed -> index -> retrieve).
Every EHR item in ``data/patients.json`` becomes one ``langchain_core.documents.Document`` whose
``page_content`` is the clinical text and whose ``metadata`` carries the citation handles the rest of
ClinicalBridge already relies on (``source_id``), plus ``patient_id``, ``source_type`` and
``scenario_id``.

All data is fictional. No real PHI. This module does not call any network or API.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from langchain_core.documents import Document

# langchain_pipeline/ lives one level below the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PATIENTS_PATH = PROJECT_ROOT / "data" / "patients.json"


# --------------------------------------------------------------------------- #
# Loading the raw fictional dataset
# --------------------------------------------------------------------------- #
def _load_patients_raw() -> Dict:
    return json.loads(PATIENTS_PATH.read_text(encoding="utf-8"))


def _patient_to_scenario_map(raw: Dict) -> Dict[str, Optional[int]]:
    """Map patient_id -> scenario number using the dataset's own _meta block.

    e.g. {"P001": "Scenario 1 - Missed Medication"} -> {"P001": 1}. Patients that are not tied to a
    shipped scenario (P006-P010) map to None.
    """
    mapping: Dict[str, Optional[int]] = {}
    scenario_patients = raw.get("_meta", {}).get("scenario_patients", {})
    for pid, label in scenario_patients.items():
        m = re.search(r"Scenario\s+(\d+)", str(label))
        mapping[pid] = int(m.group(1)) if m else None
    return mapping


# --------------------------------------------------------------------------- #
# Per-item clinical text builders (one faithful, citation-bearing chunk per EHR item)
# --------------------------------------------------------------------------- #
def _diagnosis_text(d: Dict) -> str:
    return (f"Diagnosis: {d.get('description', '')} ({d.get('code', '')}); "
            f"status {d.get('status', '')}; diagnosed {d.get('diagnosed_date', '')}").strip()


def _medication_text(m: Dict) -> str:
    supply = f"{m.get('days_supply', '')}-day supply" if m.get("days_supply") else ""
    return (f"Medication: {m.get('name', '')} {m.get('dose', '')} {m.get('frequency', '')} "
            f"({m.get('route', '')}) for {m.get('indication', '')}; status {m.get('status', '')}; "
            f"last refill {m.get('last_refill_date', '')}; {supply}").strip()


def _lab_text(l: Dict) -> str:
    return (f"Lab: {l.get('test', '')} {l.get('value', '')} {l.get('unit', '')} "
            f"(ref {l.get('reference_range', '')}) on {l.get('date', '')}; flag {l.get('flag', '')}").strip()


def _allergy_text(a: Dict) -> str:
    return (f"Allergy: {a.get('substance', '')}; reaction {a.get('reaction', '')}; "
            f"severity {a.get('severity', '')}").strip()


def _visit_note_text(n: Dict) -> str:
    return (f"Visit note ({n.get('date', '')}, {n.get('type', '')}, {n.get('provider', '')}): "
            f"{n.get('summary', '')}").strip()


# (source_type, ehr-section key, text builder)
_SECTIONS = [
    ("diagnosis", "diagnoses", _diagnosis_text),
    ("medication", "medications", _medication_text),
    ("lab", "labs", _lab_text),
    ("allergy", "allergies", _allergy_text),
    ("visit_note", "visit_notes", _visit_note_text),
]


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def load_ehr_documents(patient_id: Optional[str] = None) -> List[Document]:
    """Return LangChain ``Document`` objects for the fictional EHR.

    Args:
        patient_id: if given, only that patient's EHR is loaded; otherwise every patient is loaded
            (the full corpus the vector store is built from).

    Each Document:
        * ``page_content`` — the clinical text for one EHR item.
        * ``metadata`` — ``{patient_id, source_id, source_type, scenario_id}``.
    """
    raw = _load_patients_raw()
    scenario_map = _patient_to_scenario_map(raw)
    docs: List[Document] = []

    for patient in raw.get("patients", []):
        pid = patient.get("patient_id")
        if patient_id is not None and pid != patient_id:
            continue
        ehr = patient.get("ehr", {})
        scenario_id = scenario_map.get(pid)
        for source_type, key, builder in _SECTIONS:
            for item in ehr.get(key, []) or []:
                source_id = item.get("id")
                if not source_id:
                    continue
                metadata = {
                    "patient_id": pid,
                    "source_id": source_id,
                    "source_type": source_type,
                }
                # Only attach scenario_id when the patient maps to a shipped scenario.
                if scenario_id is not None:
                    metadata["scenario_id"] = scenario_id
                docs.append(Document(page_content=builder(item), metadata=metadata))
    return docs


def available_patient_ids() -> List[str]:
    """List every patient_id in the fictional dataset (for building the full corpus)."""
    return [p.get("patient_id") for p in _load_patients_raw().get("patients", [])]
