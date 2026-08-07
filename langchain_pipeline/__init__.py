"""
langchain_pipeline — the genuine LangChain RAG backend for ClinicalBridge EHR retrieval.

Public surface:
    load_ehr_documents          -> EHR records as LangChain Document objects
    EHRRagPipeline / get_pipeline -> the end-to-end load->split->embed->FAISS->retrieve pipeline
    clinical_question_for_scenario -> build the retrieval query from a scenario (+ triage)
    LANGCHAIN_AVAILABLE         -> True when the LangChain stack imported successfully

The whole package is import-guarded so the rest of ClinicalBridge can fall back to the local
TF-IDF retriever (rag_retrieval.py) if LangChain is not installed, without ever crashing.
Local embeddings only — no API keys. All data is fictional.
"""

try:
    from .ehr_loader import load_ehr_documents, available_patient_ids
    from .rag_pipeline import (
        EHRRagPipeline,
        get_pipeline,
        clinical_question_for_scenario,
    )
    from . import vector_store, retriever, ehr_loader, rag_pipeline

    LANGCHAIN_AVAILABLE = True
    IMPORT_ERROR = None
except Exception as _exc:  # pragma: no cover - exercised only when LangChain is absent
    LANGCHAIN_AVAILABLE = False
    IMPORT_ERROR = _exc

    def get_pipeline(*_args, **_kwargs):  # type: ignore
        raise ImportError(
            "langchain_pipeline is unavailable. Install the LangChain stack "
            "(see requirements.txt: langchain, langchain-community, langchain-text-splitters, "
            f"faiss-cpu, sentence-transformers). Original import error: {IMPORT_ERROR}"
        )

__all__ = [
    "load_ehr_documents",
    "available_patient_ids",
    "EHRRagPipeline",
    "get_pipeline",
    "clinical_question_for_scenario",
    "LANGCHAIN_AVAILABLE",
    "IMPORT_ERROR",
]
