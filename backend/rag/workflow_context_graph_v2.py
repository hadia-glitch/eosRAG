"""Versioned terminology-aware context routing; no clinical decision rules."""
from rag.canonical_clinical_query import canonical_query
from rag.workflow_context_graph import select_context as original_select_context


def select_context(order,corpus,graph,query,patient,history,**kwargs):
    # Only retrieval-intent routing sees normalized terms. Original wording,
    # patient facts, source quotations and audit packets remain unchanged.
    return original_select_context(order,corpus,graph,canonical_query(query),patient,history,**kwargs)
