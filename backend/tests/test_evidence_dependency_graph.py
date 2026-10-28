import pytest
from rag.evidence_dependency_graph import build_graph, expand_candidates


def chunk(cid, text, source='NICE'):
    return {'chunk_id': cid, 'raw_text': text, 'guideline_id': source,
            'scope': {'postnatal_age_hours': [0, 72], 'care_setting': ['hospital']}}


def test_exact_source_dependencies_expand_without_promoting_or_crossing_scope():
    chunks = [chunk('base', 'Use CRP readings.'),
              chunk('limit', 'Do not use CRP alone.'),
              chunk('other', 'Do not use CRP alone.', 'AAP')]
    graph = build_graph(chunks)
    corpus = {c['chunk_id']: c for c in chunks}
    order, added = expand_candidates('Interpret CRP', ['base'], corpus, graph,
                                    {'age_hours': 12, 'care_setting': 'hospital'}, 'NICE')
    assert order == ['base', 'limit'] and added == ['limit']
    assert graph['clinical_review_status'] == 'pending'
    assert expand_candidates('Interpret CRP', ['base'], corpus, graph,
                             {'age_hours': 100, 'care_setting': 'hospital'}, 'NICE')[1] == []
    assert expand_candidates('Assess respiration', ['base'], corpus, graph,
                             {'age_hours': 12, 'care_setting': 'hospital'}, 'NICE')[1] == []


def test_hash_failure_and_zero_budget():
    chunks = [chunk('base', 'Use CRP readings.'), chunk('limit', 'Do not use CRP alone.')]
    graph = build_graph(chunks)
    corpus = {c['chunk_id']: c for c in chunks}
    p = {'age_hours': 12, 'care_setting': 'hospital'}
    assert expand_candidates('CRP', ['base'], corpus, graph, p, 'NICE', dependency_budget=0) == (['base'], [])
    corpus['limit']['raw_text'] = 'Changed source'
    with pytest.raises(ValueError, match='hash mismatch'):
        expand_candidates('CRP', ['base'], corpus, graph, p, 'NICE')
