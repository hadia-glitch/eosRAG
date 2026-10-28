import hashlib
import json
import pytest
from rag.evidence_set_ids import select_evidence_ids


def test_full_source_materialized_without_model_reconstruction():
    text = 'A complete source rule: first condition; second condition. Unknown stays unknown.'
    patient = {'culture_status': 'unknown'}
    history = [{'age_hours': 2}]
    def model(prompt, settings, **kwargs):
        p = json.loads(prompt)
        assert p['clinical_case_context'] == {'patient': patient, 'history': history}
        assert 'quote' not in kwargs['response_schema']['$defs']['RankedEvidenceID']['properties']
        return {'choices': [{'id': 'a', 'importance': 'essential', 'purpose': 'Complete conditional framework',
                             'population': 'conditional_pathway'}]}
    ids, materialized = select_evidence_ids('Assess', [{'chunk_id': 'a', 'raw_text': text}], patient, history, None, llm=model)
    assert ids == ['a'] and materialized[0]['source_text'] == text
    assert materialized[0]['source_text_sha256'] == hashlib.sha256(text.encode()).hexdigest()
    assert materialized[0]['clinical_review_status'] == 'pending'


@pytest.mark.parametrize('ids', [['unknown'], ['a', 'a']])
def test_unknown_or_duplicate_evidence_rejected(ids):
    def model(*args, **kwargs):
        return {'choices': [{'id': i, 'importance': 'essential', 'purpose': 'Relevance', 'population': 'current_infant'} for i in ids]}
    with pytest.raises(ValueError):
        select_evidence_ids('Assess', [{'chunk_id': 'a', 'raw_text': 'Source'}], {}, [], None, llm=model)
