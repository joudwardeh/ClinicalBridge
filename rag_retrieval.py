"""
Lightweight, local, no-API RAG-style EHR retrieval (educational approximation).

WHAT THIS IS: a dependency-free demonstration of the chunk -> index -> retrieve -> cite pattern
(Module 6 / RAG concept). It loads EHR items from data/patients.json, turns each item into a small
text chunk that carries its source id, and ranks chunks against a clinical question using a
pure-Python TF-IDF cosine score (with simple clinical query expansion).

WHAT THIS IS NOT: production RAG. There is NO embedding model, NO vector database (ChromaDB/FAISS),
and NO network or paid API. It is intentionally simple and honest. The main ClinicalBridge pipeline
still runs in no-API stored-output mode; this module is a separate, optional demonstration.

All data is fictional.
"""

import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Small clinical query-expansion map: alert metric -> related concept terms (no specific drug names,
# to keep retrieval honest rather than answer-leaking).
_METRIC_TERMS = {
    "blood_pressure": "hypertension blood pressure antihypertensive renal kidney creatinine potassium egfr",
    "glucose_fasting": "glucose diabetes hyperglycemia insulin hba1c thirst",
    "glucose": "glucose diabetes hyperglycemia insulin hba1c thirst",
    "heart_rate": "heart rate cardiac arrhythmia ecg palpitations",
    "spo2": "oxygen saturation respiratory pulmonary copd breathing",
    "weight": "weight heart failure fluid retention diuretic edema bnp swelling",
    "weight_trend": "weight heart failure fluid retention diuretic edema bnp swelling spo2",
}


def _load_patients():
    data = json.loads((ROOT / "data" / "patients.json").read_text(encoding="utf-8"))
    return {p["patient_id"]: p for p in data["patients"]}


def _tokenize(text):
    return re.findall(r"[a-z0-9]+", str(text).lower())


def load_ehr_chunks(patient_id):
    """Chunk a patient's EHR into [{'source_id','text'}] - one chunk per EHR item, each cited."""
    ehr = _load_patients()[patient_id]["ehr"]
    chunks = []
    for d in ehr.get("diagnoses", []):
        chunks.append({"source_id": d["id"],
                       "text": f"Diagnosis: {d.get('description','')} ({d.get('code','')}); status {d.get('status','')}"})
    for m in ehr.get("medications", []):
        chunks.append({"source_id": m["id"],
                       "text": f"Medication: {m.get('name','')} {m.get('dose','')} {m.get('frequency','')} "
                               f"for {m.get('indication','')}; status {m.get('status','')}; last refill {m.get('last_refill_date','')}"})
    for l in ehr.get("labs", []):
        chunks.append({"source_id": l["id"],
                       "text": f"Lab: {l.get('test','')} {l.get('value','')} {l.get('unit','')} "
                               f"(ref {l.get('reference_range','')}) on {l.get('date','')}; flag {l.get('flag','')}"})
    for a in ehr.get("allergies", []):
        chunks.append({"source_id": a["id"],
                       "text": f"Allergy: {a.get('substance','')}; reaction {a.get('reaction','')}"})
    for n in ehr.get("visit_notes", []):
        chunks.append({"source_id": n["id"],
                       "text": f"Visit note ({n.get('date','')}): {n.get('summary','')}"})
    return chunks


def _build_idf(chunks):
    n = len(chunks)
    df = Counter()
    for c in chunks:
        for t in set(_tokenize(c["text"])):
            df[t] += 1
    return {t: math.log((n + 1) / (dft + 1)) + 1 for t, dft in df.items()}


def _vec(tokens, idf):
    tf = Counter(tokens)
    return {t: tf[t] * idf.get(t, 1.0) for t in tf}


def _cosine(a, b):
    common = set(a) & set(b)
    num = sum(a[t] * b[t] for t in common)
    da = math.sqrt(sum(v * v for v in a.values()))
    db = math.sqrt(sum(v * v for v in b.values()))
    return num / (da * db) if da and db else 0.0


def retrieve(question, patient_id, k=5):
    """Return the top-k EHR chunks for a clinical question: [{'source_id','score','text'}]."""
    chunks = load_ehr_chunks(patient_id)
    if not chunks:
        return []
    idf = _build_idf(chunks)
    qv = _vec(_tokenize(question), idf)
    scored = [{"source_id": c["source_id"], "score": round(_cosine(qv, _vec(_tokenize(c["text"]), idf)), 4),
               "text": c["text"]} for c in chunks]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]


def clinical_question_for_scenario(scenario):
    """Build a clinical question from the scenario's RPM alert (with light query expansion)."""
    alert = scenario["rpm_alert"]
    metric = alert.get("metric", "")
    expansion = _METRIC_TERMS.get(metric, "")
    return (f"{metric.replace('_', ' ')} alert, value {alert.get('value','')} {alert.get('unit','')}. "
            f"Related concepts: {expansion}. "
            f"Retrieve the relevant diagnosis, medication, lab, and visit note for this patient.")
