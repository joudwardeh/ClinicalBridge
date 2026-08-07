"""
ClinicalBridge EHR RAG pipeline — the genuine LangChain backend for EHR retrieval.

Wires the standard LangChain RAG chain end to end:

    load EHR -> Document objects        (ehr_loader.load_ehr_documents)
        -> RecursiveCharacterTextSplitter   (chunk larger notes, preserve metadata)
        -> local embeddings                 (sentence-transformers/all-MiniLM-L6-v2, or fallback)
        -> FAISS vector store               (or in-memory fallback)
        -> retriever (top-k, k=5 default)   (filtered to the alert's patient)

The rest of ClinicalBridge talks to this module through :class:`EHRRagPipeline` (or the cached
:func:`get_pipeline` singleton), so the retrieval backend is genuinely LangChain while the
orchestrator, prompts, schemas, evaluation, and the 8-section brief are all unchanged.

No API keys. No network beyond the one-time, cached download of the local embedding model.
All data is fictional.
"""

import os
from typing import Dict, List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from . import ehr_loader, retriever, vector_store

# Chunking: most EHR items are short one-liners; this only splits longer visit notes, and
# RecursiveCharacterTextSplitter copies each parent's metadata (incl. source_id) onto every chunk.
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 64

# Small clinical query-expansion map: alert metric -> related concepts. Mirrors the local TF-IDF
# fallback so the two backends ask the same clinical question (no specific drug names, to keep
# retrieval honest rather than answer-leaking).
_METRIC_TERMS = {
    "blood_pressure": "hypertension blood pressure antihypertensive renal kidney creatinine potassium egfr",
    "glucose_fasting": "glucose diabetes hyperglycemia insulin hba1c thirst",
    "glucose": "glucose diabetes hyperglycemia insulin hba1c thirst",
    "heart_rate": "heart rate cardiac arrhythmia ecg palpitations",
    "spo2": "oxygen saturation respiratory pulmonary copd breathing",
    "weight": "weight heart failure fluid retention diuretic edema bnp swelling",
    "weight_trend": "weight heart failure fluid retention diuretic edema bnp swelling spo2",
}


# --------------------------------------------------------------------------- #
# Clinical question (the query the Alert Triage Agent hands to retrieval)
# --------------------------------------------------------------------------- #
def clinical_question_for_scenario(scenario: Dict, triage: Optional[Dict] = None) -> str:
    """Build the clinical retrieval question for a scenario.

    When the Alert Triage Agent's output is available, its ``retrieval_plan.ehr_focus`` is folded in
    so the query genuinely reflects what triage asked retrieval to look for (architecture:
    Triage -> question -> EHR Retrieval). Falls back to alert + metric expansion otherwise.
    """
    alert = scenario["rpm_alert"]
    metric = alert.get("metric", "")
    expansion = _METRIC_TERMS.get(metric, "")
    focus = ""
    if triage:
        ehr_focus = triage.get("retrieval_plan", {}).get("ehr_focus", []) or []
        if ehr_focus:
            focus = " Triage retrieval focus: " + "; ".join(ehr_focus) + "."
    return (f"{metric.replace('_', ' ')} alert, value {alert.get('value', '')} "
            f"{alert.get('unit', '')}. Related concepts: {expansion}.{focus} "
            f"Retrieve the relevant diagnosis, medication, lab, and visit note for this patient.")


# --------------------------------------------------------------------------- #
# The pipeline
# --------------------------------------------------------------------------- #
class EHRRagPipeline:
    """End-to-end LangChain RAG pipeline over the fictional EHR corpus.

    Builds one vector store across all patients' EHR documents and retrieves with a per-patient
    metadata filter. The store is rebuilt in memory on construction (the corpus is tiny);
    persistence helpers live in :mod:`vector_store` for completeness.
    """

    def __init__(self, embeddings_pref: Optional[str] = None,
                 chunk_size: int = DEFAULT_CHUNK_SIZE,
                 chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
        # Embedding backend can be forced via the CLINICALBRIDGE_EMBEDDINGS env var
        # (auto|huggingface|fake); defaults to "auto" (real MiniLM if installed, else fake).
        self.embeddings_pref = embeddings_pref or os.environ.get(
            "CLINICALBRIDGE_EMBEDDINGS", "auto")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # 1) Load EHR -> Document objects (all patients form the corpus).
        self.documents: List = ehr_loader.load_ehr_documents()

        # 2) Split larger notes while preserving metadata (incl. source_id).
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        self.chunks: List = self.splitter.split_documents(self.documents)

        # 3) Embeddings (local only) and 4) vector store (FAISS preferred).
        self.embeddings, self.embedding_backend = vector_store.get_embeddings(
            prefer=self.embeddings_pref)
        self.store, self.store_backend = vector_store.build_vector_store(
            self.chunks, self.embeddings)

    # ---- configuration summary (for the demo + reports) ---------------------------------- #
    def config(self) -> Dict:
        return {
            "embedding_model": vector_store.DEFAULT_EMBEDDING_MODEL
            if self.embedding_backend == "huggingface" else "FakeEmbeddings (offline fallback)",
            "embedding_backend": self.embedding_backend,
            "vector_store": self.store_backend,
            "num_documents": len(self.documents),
            "num_chunks": len(self.chunks),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
        }

    # ---- retrieval ----------------------------------------------------------------------- #
    def get_retriever(self, patient_id: str, k: int = retriever.DEFAULT_K):
        """Return a configurable LangChain retriever scoped to one patient (default k=5)."""
        return retriever.make_retriever(self.store, k=k, patient_id=patient_id)

    def retrieve(self, question: str, patient_id: str,
                 k: int = retriever.DEFAULT_K) -> List[Dict]:
        """Retrieve the top-k EHR chunks for a clinical question (with similarity scores)."""
        return retriever.retrieve_with_scores(self.store, question, k=k, patient_id=patient_id)

    def retrieve_documents(self, question: str, patient_id: str,
                           k: int = retriever.DEFAULT_K) -> List:
        """Retrieve the top-k results as raw LangChain ``Document`` objects (deduped by source_id).

        These Documents are what the EHR Retrieval Agent receives as its grounding context.
        """
        seen = set()
        docs = []
        for r in self.retrieve(question, patient_id, k=k):
            sid = r["source_id"]
            if sid in seen:
                continue
            seen.add(sid)
            docs.append(r["document"])
        return docs


# --------------------------------------------------------------------------- #
# Cached singleton (built once per process; the corpus and model don't change at runtime).
# --------------------------------------------------------------------------- #
_PIPELINE: Optional[EHRRagPipeline] = None


def get_pipeline(embeddings_pref: Optional[str] = None) -> EHRRagPipeline:
    """Return a process-wide cached :class:`EHRRagPipeline` (build it on first use)."""
    global _PIPELINE
    if _PIPELINE is None or (embeddings_pref and embeddings_pref != _PIPELINE.embeddings_pref):
        _PIPELINE = EHRRagPipeline(embeddings_pref=embeddings_pref)
    return _PIPELINE
