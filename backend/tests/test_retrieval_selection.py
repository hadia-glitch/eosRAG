import numpy as np
from rag.selection import expand_query,mmr_indices
from rag.knowledge_graph import concepts,query_concepts


def test_synonyms_expand_terms_without_diagnostic_thresholds():
    q='EOS with apnea and a CRP trend'
    expanded=expand_query(q)
    assert expanded.startswith(q)
    assert 'apnoea' in expanded and 'C-reactive protein' in expanded
    assert len(expanded)<=2500
    assert expand_query('Unrelated phrase')=='Unrelated phrase'


def test_mmr_keeps_relevance_and_avoids_duplicate_context():
    selected=mmr_indices([10,9.9,9.8],np.array([[1,0],[1,0],[0,1]]),2)
    assert selected==[0,2]


def test_specific_graph_links_do_not_reduce_to_generic_antibiotics():
    q='Can CRP alone justify stopping antibiotics?'
    assert 'single_marker_decision' in concepts(q)
    assert 'antibiotic_stopping_conditions' in query_concepts(q)
    assert 'antibiotics' not in query_concepts(q)
