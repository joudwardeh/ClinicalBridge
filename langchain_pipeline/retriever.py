"""
Retriever construction for the ClinicalBridge LangChain RAG pipeline.

Wraps a LangChain vector store as a configurable top-k retriever and provides a small helper that
also surfaces similarity scores (useful for the ``--langchain-rag-demo`` and for Precision@k /
Recall@k evaluation). Top-k is configurable; the project default is ``k = 5``.
"""

from typing import Dict, List, Optional

from langchain_core.documents import Document

DEFAULT_K = 5


def make_retriever(vector_store, k: int = DEFAULT_K, patient_id: Optional[str] = None):
    """Return a LangChain retriever over ``vector_store``.

    Args:
        vector_store: a LangChain ``VectorStore`` (FAISS or in-memory).
        k: number of chunks to retrieve (configurable; default 5).
        patient_id: when given, restrict retrieval to that patient's EHR via metadata filtering,
            so one patient's alert never retrieves another patient's chart.
    """
    search_kwargs: Dict = {"k": k}
    if patient_id is not None:
        search_kwargs["filter"] = {"patient_id": patient_id}
    return vector_store.as_retriever(search_kwargs=search_kwargs)


def _matches_patient(doc: Document, patient_id: Optional[str]) -> bool:
    return patient_id is None or doc.metadata.get("patient_id") == patient_id


def retrieve_with_scores(vector_store, query: str, k: int = DEFAULT_K,
                         patient_id: Optional[str] = None) -> List[Dict]:
    """Retrieve top-k chunks for ``query`` and include similarity scores when available.

    Returns a list of dicts: ``{document, source_id, source_type, patient_id, score}`` ordered by
    relevance. ``score`` is the vector store's distance/similarity score (``None`` if the backend
    does not expose one). Patient filtering is applied so a query only sees that patient's EHR.
    """
    results: List[Dict] = []
    flt = {"patient_id": patient_id} if patient_id is not None else None
    # The EHR corpus is tiny, so fetch a generous candidate pool BEFORE patient-filtering. FAISS
    # post-filters its `fetch_k` candidates, so a small fetch_k would silently drop a patient's
    # relevant chunks that don't fall in the global top-fetch_k. 256 comfortably covers the corpus.
    fetch_k = 256
    scored = None

    # Attempt 1: native FAISS filter + fetch_k.
    try:
        scored = vector_store.similarity_search_with_score(
            query, k=max(k, fetch_k if flt else k), filter=flt, fetch_k=fetch_k)
        scored = [(d, s) for (d, s) in scored if _matches_patient(d, patient_id)]
    except Exception:
        scored = None

    # Attempt 2: backend without dict-filter/fetch_k (e.g. in-memory): fetch broad, filter here.
    if not scored:
        try:
            raw = vector_store.similarity_search_with_score(query, k=fetch_k)
            scored = [(d, s) for (d, s) in raw if _matches_patient(d, patient_id)]
        except Exception:
            scored = None

    if scored is not None:
        for doc, score in scored[:k]:
            results.append(_pack(doc, float(score)))
        if results:
            return results

    # Attempt 3 (last resort): plain retrieval without scores.
    retriever = make_retriever(vector_store, k=k, patient_id=patient_id)
    for doc in retriever.invoke(query):
        results.append(_pack(doc, None))
    return results


def _pack(doc: Document, score) -> Dict:
    return {
        "document": doc,
        "source_id": doc.metadata.get("source_id"),
        "source_type": doc.metadata.get("source_type"),
        "patient_id": doc.metadata.get("patient_id"),
        "scenario_id": doc.metadata.get("scenario_id"),
        "score": score,
        "text": doc.page_content,
    }
