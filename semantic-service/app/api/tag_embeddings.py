"""
Tag list → 2D/3D projections and similarity links (spaCy word vectors).
Uses en_core_web_lg from semantic-service (same as app.api.semantic.nlp_lg).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.semantic import nlp_lg

tag_embeddings_router = APIRouter()


class TagEmbeddingsIn(BaseModel):
    words: List[str] = Field(default_factory=list)
    max_words: int = 48
    min_sim: float = 0.38
    max_links: int = 160


def build_embeddings_response(
    words: List[str],
    *,
    max_words: int = 48,
    min_sim: float = 0.38,
    max_links: int = 160,
) -> Dict[str, Any]:
    if not isinstance(words, list):
        return {
            "ok": False,
            "error": "words must be a list",
            "words": [],
            "vectors2d": [],
            "vectors3d": [],
            "vectors2d_current": [],
            "vectors3d_current": [],
            "vectors2d_alt": [],
            "vectors3d_alt": [],
            "directions2d": [],
            "directions3d": [],
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

    if nlp_lg is None:
        return {
            "ok": False,
            "mode": "unavailable",
            "error": "spaCy model not loaded",
            "words": clean,
            "vectors2d": [],
            "vectors3d": [],
            "vectors2d_current": [],
            "vectors3d_current": [],
            "vectors2d_alt": [],
            "vectors3d_alt": [],
            "directions2d": [],
            "directions3d": [],
            "links": [],
        }

    docs = []
    valid_words: List[str] = []
    for w in clean:
        d = nlp_lg(w)
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
            "vectors2d_current": v2,
            "vectors3d_current": v3,
            "vectors2d_alt": v2,
            "vectors3d_alt": v3,
            "directions2d": v2,
            "directions3d": v3,
            "links": [],
        }

    vectors2d_current: List[List[float]] = []
    vectors3d_current: List[List[float]] = []
    vectors2d_alt: List[List[float]] = []
    vectors3d_alt: List[List[float]] = []
    directions2d: List[List[float]] = []
    directions3d: List[List[float]] = []
    for d in docs:
        v = d.vector
        norm = float(d.vector_norm)
        c0 = float(v[0]) / norm if norm and len(v) > 0 else 0.0
        c1 = float(v[1]) / norm if norm and len(v) > 1 else 0.0
        c2 = float(v[2]) / norm if norm and len(v) > 2 else 0.0
        c3 = float(v[3]) / norm if norm and len(v) > 3 else c0
        c4 = float(v[4]) / norm if norm and len(v) > 4 else c1
        c5 = float(v[5]) / norm if norm and len(v) > 5 else c2
        vectors2d_current.append([c0, c1])
        vectors3d_current.append([c0, c1, c2])
        vectors2d_alt.append([c3, c4])
        vectors3d_alt.append([c3, c4, c5])
        directions2d.append([c0, c1])
        directions3d.append([c0, c1, c2])

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
        "vectors2d": vectors2d_current,
        "vectors3d": vectors3d_current,
        "vectors2d_current": vectors2d_current,
        "vectors3d_current": vectors3d_current,
        "vectors2d_alt": vectors2d_alt,
        "vectors3d_alt": vectors3d_alt,
        "directions2d": directions2d,
        "directions3d": directions3d,
        "links": links,
    }


def _fallback_3d_from_2d(vectors2d: List[List[float]]) -> List[List[float]]:
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


@tag_embeddings_router.post("/tag-embeddings/")
async def tag_embeddings_endpoint(data: TagEmbeddingsIn):
    max_words = max(4, min(data.max_words, 80))
    min_sim = max(0.15, min(data.min_sim, 0.99))
    max_links = max(8, min(data.max_links, 400))
    return build_embeddings_response(
        data.words,
        max_words=max_words,
        min_sim=min_sim,
        max_links=max_links,
    )
