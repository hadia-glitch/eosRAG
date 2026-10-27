"""Backend tests for RAG pipeline."""

import pytest

from rag.rrf import reciprocal_rank_fusion
from rag.query_builder import build_clinical_query
from rag.production_retrieval import retrieve
from config import Settings


def test_rrf_merges_lists():
    list_a = ["a", "b", "c"]
    list_b = ["b", "d", "a"]
    merged = reciprocal_rank_fusion([list_a, list_b], k=60)
    ids = [str(x) for x, _ in merged]
    assert "b" in ids
    assert "a" in ids
    assert len(merged) <= 4


def test_unreviewed_corpus_never_returns_seed_evidence(tmp_path):
    settings = Settings(_env_file=None, evidence_manifest_path=str(tmp_path / 'missing.json'))
    result = retrieve("EOS management", "NICE", 5, settings)
    assert result.chunks == []
    assert result.mode == "unavailable"
