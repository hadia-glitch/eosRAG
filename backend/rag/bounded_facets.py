"""Prevent query-facet anchors from bypassing the original-question guard."""
from rag.faceted_selection import select_facets


def select_guarded_facets(order, vectors, limit, anchors=(), *, question_order):
    allowed = set(order[:2 * limit]) & set(question_order[:2 * limit])
    supported = [anchor for anchor in anchors if anchor in allowed]
    return select_facets(order, vectors, limit, supported)
