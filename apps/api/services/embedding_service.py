"""
services/embedding_service.py — Sentence-transformer embedding generation.

Uses all-MiniLM-L6-v2 (384-dim) for both job and resume embeddings.
The model is loaded once and cached in-process. CPU-only — no GPU required.
"""
from __future__ import annotations

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

_model = None


def _get_model():
    """Lazy-load the sentence-transformer model (heavy import)."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence-transformer model: %s", MODEL_NAME)
            _model = SentenceTransformer(MODEL_NAME)
            logger.info("Model loaded successfully (dim=%d)", EMBEDDING_DIM)
        except ImportError:
            logger.error(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers torch"
            )
            raise
    return _model


def embed_text(text: str) -> list[float]:
    """Generate a 384-dim embedding for a single text string."""
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts. More efficient than calling embed_text in a loop."""
    if not texts:
        return []
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return [e.tolist() for e in embeddings]


def build_job_text(title: str, company_name: str | None, skills: list[str], description: str | None) -> str:
    """Build the text string used to generate a job embedding.
    
    Combines title (most important), company, skills, and a truncated description
    into a single string. The sentence-transformer handles the semantics.
    """
    parts = [title]
    if company_name:
        parts.append(company_name)
    if skills:
        parts.append(" ".join(skills))
    if description:
        # Truncate description to ~500 chars to keep embedding focused
        parts.append(description[:500])
    return " ".join(parts)


def build_profile_text(
    current_title: str | None,
    skills: list[str] | None,
    experience: list[dict] | None,
) -> str:
    """Build text string for a user profile embedding."""
    parts = []
    if current_title:
        parts.append(current_title)
    if skills:
        parts.append(" ".join(skills))
    if experience:
        for exp in experience[:3]:  # top 3 most recent
            if exp.get("title"):
                parts.append(exp["title"])
            if exp.get("summary"):
                parts.append(exp["summary"][:200])
    return " ".join(parts) if parts else ""
