"""
Lightweight agent tools (Module 7 'tools' concept).

Each function is a small, named, documented tool that wraps existing project logic so an agent or
the orchestrator could call it as a discrete capability. These add no new behavior - they expose
schema validation, EHR retrieval, patient-consistency, and traceability checking as callable tools.

All data is fictional. No network or paid API is used.
"""

import sys

import pipeline as cb
import rag_retrieval

sys.path.insert(0, str(cb.ROOT / "evaluation"))
import metrics  # noqa: E402

TOOLS = {
    "schema_validation": "Validate an object against a named JSON schema.",
    "ehr_retrieval": "Retrieve top-k relevant EHR chunks for a clinical question (genuine LangChain "
                     "RAG backend; local TF-IDF fallback).",
    "patient_consistency": "Verify all agent outputs belong to the same (expected) patient.",
    "traceability_check": "Verify every brief claim cites a valid, resolvable source id.",
}


def schema_validation_tool(obj, schema_name):
    """Tool: validate `obj` against `schema_name`. Returns {'valid': bool, 'error': str|None}."""
    try:
        cb.validate(obj, schema_name)
        return {"valid": True, "error": None}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def ehr_retrieval_tool(question, patient_id, k=5):
    """Tool: return top-k relevant EHR chunks (each with source_id + score) for a clinical question.

    Uses the genuine LangChain RAG backend by default (langchain_pipeline: Documents + FAISS + local
    embeddings); transparently falls back to the local TF-IDF retriever if LangChain is unavailable.
    """
    try:
        return cb.get_retrieval_backend().retrieve(question, patient_id, k=k)
    except Exception:
        return rag_retrieval.retrieve(question, patient_id, k)


def patient_consistency_tool(expected_pid, *agent_outputs):
    """Tool: check patient-ID consistency. Returns {'consistent': bool, 'error': str|None}."""
    try:
        cb.assert_consistent_patient(expected_pid, *agent_outputs)
        return {"consistent": True, "error": None}
    except ValueError as e:
        return {"consistent": False, "error": str(e)}


def traceability_tool(brief, valid_source_ids):
    """Tool: check brief claim traceability against a set of valid source ids."""
    res = metrics.score_hallucination_and_traceability(brief, set(valid_source_ids))
    return {"traceability": res["traceability"],
            "hallucination_rate": res["hallucination_rate"],
            "unsupported_claims": res["unsupported_claims"]}
