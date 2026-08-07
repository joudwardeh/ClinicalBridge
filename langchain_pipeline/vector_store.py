"""
Embeddings + vector store for the ClinicalBridge LangChain RAG pipeline.

Design goals (per the project's hard constraints):
  * LOCAL ONLY — no OpenAI, no Anthropic, no API keys, no paid service.
  * Genuine LangChain components — real ``Embeddings`` and a real ``VectorStore``.
  * Never break the rest of the project — every layer degrades gracefully and reports which
    backend it actually used, so the project can honestly describe its configuration.

Embeddings preference order:
  1. ``sentence-transformers/all-MiniLM-L6-v2`` via ``langchain_huggingface.HuggingFaceEmbeddings``
     (local model; weights are cached on first use — no API key).
  2. The same model via the older ``langchain_community.embeddings.HuggingFaceEmbeddings``.
  3. ``FakeEmbeddings`` (deterministic, dependency-free) as a DOCUMENTED last-resort fallback so the
     pipeline still runs fully offline on a machine without ``sentence-transformers`` installed.

Vector store preference order:
  1. ``FAISS`` (``langchain_community.vectorstores.FAISS``) — the preferred real vector store.
  2. ``InMemoryVectorStore`` (``langchain_core.vectorstores``) — still a genuine LangChain vector
     store, used only if ``faiss-cpu`` is unavailable.
"""

import os
import warnings
from pathlib import Path
from typing import List, Optional, Tuple

# Keep the local embedding model quiet and offline-friendly (no progress bars, no symlink warnings,
# no tokenizer fork spam). These only affect logging, never behaviour.
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from langchain_core.documents import Document

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Preferred local embedding model (small, fast, CPU-friendly, no API key).
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# Dimension used by FakeEmbeddings so the fallback matches MiniLM's 384-d space conceptually.
_FAKE_EMBEDDING_DIM = 384

# Where a persisted FAISS index is written (tagged by backend so a Fake index is never confused
# with a real MiniLM index of a different dimension).
INDEX_DIR = PROJECT_ROOT / "langchain_pipeline" / "faiss_index"


# --------------------------------------------------------------------------- #
# Embeddings
# --------------------------------------------------------------------------- #
def get_embeddings(model_name: str = DEFAULT_EMBEDDING_MODEL,
                   prefer: str = "auto") -> Tuple[object, str]:
    """Return ``(embeddings, backend_name)`` using local embeddings only.

    Args:
        model_name: HuggingFace model id to load when a real embedding backend is available.
        prefer: ``"auto"`` (try HuggingFace, fall back to Fake), ``"huggingface"`` (require HF, raise
            on failure), or ``"fake"`` (force the deterministic offline fallback).

    backend_name is one of ``"huggingface"`` or ``"fake"`` so callers/reports can state the truth.
    """
    if prefer == "fake":
        return _fake_embeddings(), "fake"

    # 1) Preferred: langchain-huggingface (the maintained integration package).
    try:
        from langchain_huggingface import HuggingFaceEmbeddings  # type: ignore
        _quiet_transformers()
        return HuggingFaceEmbeddings(model_name=model_name), "huggingface"
    except Exception:
        pass

    # 2) Fallback: the older community embedding wrapper (same underlying model).
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from langchain_community.embeddings import HuggingFaceEmbeddings  # type: ignore
        _quiet_transformers()
        return HuggingFaceEmbeddings(model_name=model_name), "huggingface"
    except Exception as exc:
        if prefer == "huggingface":
            raise RuntimeError(
                f"HuggingFace embeddings unavailable ({exc}). Install 'sentence-transformers' and "
                f"'langchain-huggingface', or call get_embeddings(prefer='fake')."
            ) from exc

    # 3) Documented last resort: deterministic fake embeddings (fully offline, no model download).
    return _fake_embeddings(), "fake"


def _quiet_transformers():
    """Silence transformers/HF progress bars + advisory logs (cosmetic only, never behaviour)."""
    try:
        from transformers.utils import logging as _hf_logging
        _hf_logging.set_verbosity_error()
        _hf_logging.disable_progress_bar()
    except Exception:
        pass
    try:
        from huggingface_hub.utils import logging as _hub_logging
        _hub_logging.set_verbosity_error()
    except Exception:
        pass


def _fake_embeddings():
    """Deterministic, dependency-free embeddings (documented offline fallback)."""
    try:
        from langchain_core.embeddings import FakeEmbeddings
    except Exception:  # very old layouts
        from langchain_community.embeddings import FakeEmbeddings  # type: ignore
    return FakeEmbeddings(size=_FAKE_EMBEDDING_DIM)


# --------------------------------------------------------------------------- #
# Vector store
# --------------------------------------------------------------------------- #
def build_vector_store(documents: List[Document], embeddings) -> Tuple[object, str]:
    """Build a real LangChain vector store from EHR documents.

    Returns ``(vector_store, backend_name)`` where backend_name is ``"faiss"`` or ``"in_memory"``.
    FAISS is preferred; the in-memory store is a genuine LangChain fallback if faiss-cpu is absent.
    """
    # 1) Preferred: FAISS.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from langchain_community.vectorstores import FAISS
        return FAISS.from_documents(documents, embeddings), "faiss"
    except Exception:
        pass

    # 2) Fallback: in-memory vector store (still a real LangChain VectorStore).
    from langchain_core.vectorstores import InMemoryVectorStore
    store = InMemoryVectorStore(embeddings)
    store.add_documents(documents)
    return store, "in_memory"


# --------------------------------------------------------------------------- #
# Optional persistence (FAISS). The high-level pipeline rebuilds in-memory on startup by default
# because the fictional corpus is tiny; these helpers exist for completeness and are tagged by
# backend so a persisted index is only ever loaded back with a matching embedding backend.
# --------------------------------------------------------------------------- #
def _index_path(embedding_backend: str) -> Path:
    return INDEX_DIR / embedding_backend


def save_faiss(vector_store, embedding_backend: str) -> Optional[Path]:
    """Persist a FAISS store locally (no-op for non-FAISS stores). Returns the path or None."""
    if vector_store.__class__.__name__ != "FAISS":
        return None
    path = _index_path(embedding_backend)
    path.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(path))
    return path


def load_faiss(embeddings, embedding_backend: str):
    """Load a persisted FAISS store for this embedding backend, or None if not present/unavailable."""
    path = _index_path(embedding_backend)
    if not path.exists():
        return None
    try:
        from langchain_community.vectorstores import FAISS
        return FAISS.load_local(str(path), embeddings, allow_dangerous_deserialization=True)
    except Exception:
        return None
