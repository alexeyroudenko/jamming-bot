"""
Mood + palette from page text and semantic-service shaped JSON.
Ported from jamming-analyze.py with analyze_mood_extended implemented.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import pandas as pd
import torch
from rapidfuzz import fuzz, process
from transformers import pipeline

logger = logging.getLogger(__name__)

_df_colors: Optional[pd.DataFrame] = None
_emotion_pipeline = None


def analyze_mood_extended(data_json: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Rule-based scores from semantic payload (noun_phrases, keywords, dependency, etc.)."""
    scores: Dict[str, float] = {"melancholy": 0.0, "curiosity": 0.0, "tension": 0.0}
    if not isinstance(data_json, dict):
        return {"scores": scores, "full_description": "neutral"}

    fragments: List[str] = []

    for key in ("noun_phrases", "keywords", "verbs", "subjects", "objects", "entities"):
        v = data_json.get(key)
        if isinstance(v, list):
            fragments.extend(str(x) for x in v[:60])
        elif isinstance(v, str) and v.strip():
            fragments.append(v)

    for item in data_json.get("dependency") or []:
        if isinstance(item, str):
            fragments.append(item.replace(">", " "))
        elif isinstance(item, dict):
            fragments.append(f"{item.get('token', '')} {item.get('head', '')}")

    blob = " ".join(fragments).lower()
    if not blob.strip():
        blob = (data_json.get("snippet") or data_json.get("text") or "").lower()

    mel_words = (
        "melancholy", "lonely", "ruin", "forgot", "loss", "path", "empty", "silence",
        "абандон", "пуст", "руин", "одиноч", "тлен", "забыт", "меланхол",
    )
    cur_words = (
        "curious", "explore", "discover", "trace", "digital", "future", "neon",
        "исслед", "поиск", "цифр", "сеть", "путь", "бот",
    )
    ten_words = ("tension", "conflict", "urgent", "fear", "stress", "конфликт", "угроз")

    for w in mel_words:
        if w in blob:
            scores["melancholy"] += 2.0
    for w in cur_words:
        if w in blob:
            scores["curiosity"] += 2.0
    for w in ten_words:
        if w in blob:
            scores["tension"] += 1.5

    scores["melancholy"] += min(6.0, len(re.findall(r"\b(no|never|without|void|loss)\b", blob)) * 1.5)
    scores["curiosity"] += min(6.0, len(re.findall(r"\b(how|what|why|discover|explore)\b", blob)) * 1.2)

    top = max(scores, key=lambda k: scores[k])
    if scores[top] < 1.0:
        full_description = "neutral"
    else:
        full_description = f"{top} bias ({scores[top]:.1f})"
    return {"scores": scores, "full_description": full_description}


def load_models() -> None:
    global _df_colors, _emotion_pipeline
    if _emotion_pipeline is not None and _df_colors is not None:
        return

    from datasets import load_dataset

    logger.info("Loading Color-Pedia dataset (first run may download ~100MB+)...")
    color_pedia = load_dataset("boltuix/color-pedia", split="train")
    df = pd.DataFrame(color_pedia)
    df["search_text"] = (
        df["Mood"].fillna("").astype(str)
        + " "
        + df["Emotion"].fillna("").astype(str)
        + " "
        + df["Keywords"].fillna("").astype(str)
    ).str.lower()
    _df_colors = df

    logger.info("Loading rubert-tiny2 emotion model...")
    _emotion_pipeline = pipeline(
        "text-classification",
        model="seara/rubert-tiny2-russian-emotion-detection-cedr",
        return_all_scores=True,
        device=0 if torch.cuda.is_available() else -1,
    )
    logger.info("Mood models ready.")


def get_mood_and_palette(raw_text: str, data_json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    load_models()
    assert _df_colors is not None and _emotion_pipeline is not None

    text_in = (raw_text or "").strip() or " "
    text_in = text_in[:4096]

    raw_nn = _emotion_pipeline(text_in)
    if isinstance(raw_nn, list) and raw_nn and isinstance(raw_nn[0], dict):
        nn_result = raw_nn
    elif isinstance(raw_nn, list) and raw_nn and isinstance(raw_nn[0], list):
        nn_result = raw_nn[0]
    else:
        nn_result = raw_nn[0] if isinstance(raw_nn, list) else raw_nn
    nn_emotions = {item["label"]: round(float(item["score"]) * 100, 1) for item in nn_result}
    dominant_emo = max(nn_emotions, key=nn_emotions.get)

    rule_mood = analyze_mood_extended(data_json) if data_json else {"scores": {}, "full_description": "neutral"}
    rule_scores = rule_mood.get("scores") or {}

    query = str(dominant_emo).lower()
    if rule_scores.get("melancholy", 0) > 7:
        query += " calm serene dark melancholic path ruins"
    elif rule_scores.get("curiosity", 0) > 6:
        query += " explore digital neon trace"

    choices = _df_colors["search_text"].tolist()
    extracted = process.extract(
        query,
        choices,
        scorer=fuzz.WRatio,
        limit=40,
        score_cutoff=65,
    )
    matched_indices: List[int] = []
    for row in extracted:
        if len(row) >= 3:
            matched_indices.append(int(row[2]))
        elif len(row) >= 1:
            try:
                matched_indices.append(choices.index(row[0]))
            except ValueError:
                continue

    if not matched_indices:
        neutral_mask = _df_colors["Mood"].astype(str).str.contains(
            "calm|neutral", case=False, na=False,
        )
        matched_indices = _df_colors[neutral_mask].head(10).index.tolist()

    palette_df = _df_colors.iloc[matched_indices].copy()

    if rule_scores.get("melancholy", 0) > 8 and "Lightness" in palette_df.columns:
        try:
            palette_df = palette_df[palette_df["Lightness"].astype(float) < 60]
        except (TypeError, ValueError, KeyError):
            pass

    if "Hue" in palette_df.columns:
        try:
            palette_df = palette_df.sort_values("Hue").head(5)
        except (TypeError, ValueError):
            palette_df = palette_df.head(5)
    else:
        palette_df = palette_df.head(5)

    palette = []
    for _, row in palette_df.iterrows():
        hex_code = row.get("HEX Code", row.get("HEX", "#444444"))
        palette.append(
            {
                "hex": str(hex_code),
                "name": str(row.get("Color Name", "")),
                "mood": str(row.get("Mood", "")),
                "emotion": str(row.get("Emotion", "")),
            }
        )

    return {
        "timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
        "dominant_mood": dominant_emo,
        "mood_scores_nn": nn_emotions,
        "rule_scores": rule_scores,
        "full_description": f"{dominant_emo} ({rule_mood.get('full_description', 'neutral')})",
        "palette": palette,
        "palette_description": f"Jamming mood snapshot • {len(palette)} colors",
        "update_interval_ok": True,
    }
