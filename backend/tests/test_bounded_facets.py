import numpy as np
from rag.bounded_facets import select_guarded_facets


def test_low_rank_facet_anchor_cannot_bypass_both_relevance_heads():
    vectors=np.eye(6)
    selected=select_guarded_facets(list(range(6)),vectors,2,[5],question_order=list(range(6)))
    assert selected==[0,1]


def test_facet_anchor_needs_original_question_support_not_just_fused_rank():
    selected=select_guarded_facets(list(range(6)),np.eye(6),2,[3],question_order=[0,1,4,5,2,3])
    assert selected==[0,1]


def test_supported_complementary_anchor_remains_available():
    selected=select_guarded_facets(list(range(6)),np.eye(6),2,[3],question_order=list(range(6)))
    assert selected==[3,0]
