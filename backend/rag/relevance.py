"""Shared, label-blind second-stage ranking for clinical evidence.

Passages remain immutable. Long passages are scored in overlapping windows so
recommendation qualifiers near the end are not silently truncated by a model.
Graph candidates compete on relevance; graph degree is not a relevance score.
"""
from __future__ import annotations

import re
import numpy as np


def focus_query(query: str) -> str:
    # The patient still reaches applicability checks and both auditors. Removing
    # boilerplate demographics here avoids matching irrelevant numeric tables.
    text = re.sub(r"\s*Gestation\s+\d+(?:\.\d+)?\s+weeks;\s*age\s+\d+(?:\.\d+)?\s+hours;\s*setting\s+[^.]+\.?", "", query, flags=re.I)
    return " ".join(text.split())[:2500]


def passage_windows(text: str, words: int = 180, overlap: int = 40) -> list[str]:
    tokens = text.split()
    if not tokens:
        return []
    if words <= overlap or overlap < 0:
        raise ValueError("Window length must exceed nonnegative overlap")
    windows = []
    for start in range(0, len(tokens), words - overlap):
        windows.append(" ".join(tokens[start:start + words]))
        if start + words >= len(tokens):
            break
    return windows


def rerank_scores(query: str, texts: list[str], model) -> list[float]:
    pairs, owners = [], []
    for i, text in enumerate(texts):
        for span in passage_windows(text):
            pairs.append((focus_query(query), span))
            owners.append(i)
    if not pairs:
        return [-1e9] * len(texts)
    values = np.asarray(model.predict(pairs, batch_size=32, show_progress_bar=False), dtype=float).reshape(-1)
    if len(values) != len(pairs) or not np.isfinite(values).all():
        raise ValueError("Reranker returned invalid scores")
    scores = np.full(len(texts), -1e9)
    for owner, value in zip(owners, values):
        scores[owner] = max(scores[owner], value)
    return scores.tolist()


def exact_deduplicate(ranked):
    seen, out = set(), []
    for row, score in ranked:
        key = " ".join(row["chunk_text"].split())
        if key and key not in seen:
            seen.add(key)
            out.append((row, score))
    return out
