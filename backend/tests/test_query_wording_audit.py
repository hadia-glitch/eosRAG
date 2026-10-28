import re
import pytest
from scripts.rag_audit_design import variants
from rag.canonical_clinical_query import canonical_query
from rag.workflow_context_graph import query_functions


def test_query_normalization_preserves_unknowns_negation_numbers_and_units():
    q='No BCx result at 36 h; do not stop ABx from C reactive protein 3 mg/L alone. Maternal background is unknown.'
    text=canonical_query(q)
    assert 'No blood culture result' in text and 'do not stop antibiotics' in text
    assert '3 mg/L' in text and '36 h' in text and 'unknown' in text
    assert 'maternal history' in text
    assert canonical_query('RR and BP are not documented.')=='RR and BP are not documented.'


def test_laboratory_and_assessment_intents_accept_medical_synonyms():
    assert 'diagnostics' in query_functions(canonical_query('Can C reactive protein exclude infection?'))
    assert 'assessment' in query_functions(canonical_query('Discuss a predisposing feature in a currently well baby.'))
    assert 'diagnostics' in query_functions(canonical_query('What does a PCT result mean?'))


def test_paraphrase_generation_preserves_numeric_and_explicit_unknown_tokens():
    q='No blood culture result at 36 hours; oxygen saturation fell. Do not assume the missing examination is normal.'
    for text in variants(q).values():
        assert re.findall(r'(?<!\w)\d+(?!\w)',text)==['36']
        assert 'missing' in text and 'Do not' in text and text.startswith('No')


def test_empty_or_nontext_queries_fail_instead_of_manufacturing_a_topic():
    for q in ['',None,31]:
        with pytest.raises(ValueError):canonical_query(q)
