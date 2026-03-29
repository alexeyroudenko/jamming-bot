"""
spaCy vectors (en_core_web_md) for tag visualizations: 2D projection + similarity links.
"""
from __future__ import annotations

import logging
import math
import threading
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

_nlp = None
_nlp_lock = threading.Lock()


def _get_nlp():
    global _nlp
    with _nlp_lock:
        if _nlp is None:
            import spacy

            try:
                _nlp = spacy.load("en_core_web_md")
            except OSError as e:
                logger.warning("tag_embeddings: en_core_web_md not available: %s", e)
                _nlp = False
        return _nlp if _nlp else None


def build_embeddings_response(
    words: List[str],
    *,
    max_words: int = 48,
    min_sim: float = 0.38,
    max_links: int = 160,
) -> Dict[str, Any]:
    """
    Returns { ok, mode, words, vectors2d, vectors3d?, links, error? }
    vectors2d: first two components of each doc vector divided by vector_norm (unit-norm slice).
    vectors3d: first three components / vector_norm — same convention, for 3D tag visualizations.
    links: [{ "i", "j", "sim" }] indices into words
    """
    if not isinstance(words, list):
        return {
            "ok": False,
            "error": "words must be a list",
            "words": [],
            "vectors2d": [],
            "vectors3d": [],
            "links": [],
        }

    clean: List[str] = []
    seen = set()
    for w in words:
        if not isinstance(w, str):
            continue
        s = w.strip()[:80]
        if len(s) < 1 or s.lower() in seen:
            continue
        seen.add(s.lower())
        clean.append(s)
        if len(clean) >= max_words:
            break

    nlp = _get_nlp()
    if not nlp:
        return {
            "ok": False,
            "mode": "unavailable",
            "error": "spaCy en_core_web_md not loaded",
            "words": clean,
            "vectors2d": [],
            "vectors3d": [],
            "links": [],
        }

    docs = []
    valid_words: List[str] = []
    for w in clean:
        d = nlp(w)
        if d.has_vector and d.vector_norm > 1e-9:
            docs.append(d)
            valid_words.append(w)

    if len(docs) < 2:
        v2 = _fallback_2d(valid_words)
        v3 = _fallback_3d_from_2d(v2)
        return {
            "ok": True,
            "mode": "sparse",
            "words": valid_words,
            "vectors2d": v2,
            "vectors3d": v3,
            "links": [],
        }

    vectors2d: List[List[float]] = []
    vectors3d: List[List[float]] = []
    for d in docs:
        v = d.vector
        norm = float(d.vector_norm)
        x = float(v[0]) / norm if norm else 0.0
        y = float(v[1]) / norm if norm else 0.0
        z = float(v[2]) / norm if norm else 0.0
        vectors2d.append([x, y])
        vectors3d.append([x, y, z])

    pairs: List[Tuple[int, int, float]] = []
    n = len(docs)
    for i in range(n):
        for j in range(i + 1, n):
            sim = float(docs[i].similarity(docs[j]))
            if sim >= min_sim:
                pairs.append((i, j, sim))

    pairs.sort(key=lambda t: -t[2])
    pairs = pairs[:max_links]
    links = [{"i": a, "j": b, "sim": round(s, 4)} for a, b, s in pairs]

    return {
        "ok": True,
        "mode": "vectors",
        "words": valid_words,
        "vectors2d": vectors2d,
        "vectors3d": vectors3d,
        "links": links,
    }


def _fallback_3d_from_2d(vectors2d: List[List[float]]) -> List[List[float]]:
    """Synthetic z from 2D fallback coords for sparse mode (deterministic, bounded)."""
    out: List[List[float]] = []
    for i, row in enumerate(vectors2d):
        if len(row) < 2:
            out.append([0.0, 0.0, 0.0])
            continue
        ex, ey = float(row[0]), float(row[1])
        ez = 0.55 * math.sin(ex * 4.2 + ey * 2.7) * math.cos(ex * 1.9 - ey * 3.1)
        out.append([ex, ey, ez])
    return out


def _fallback_2d(words: List[str]) -> List[List[float]]:
    out: List[List[float]] = []
    for i, w in enumerate(words):
        h = hash(w + str(i)) % 100000 / 100000.0
        out.append([0.6 * (h - 0.5), 0.6 * (((h * 17) % 1) - 0.5)])
    return out
