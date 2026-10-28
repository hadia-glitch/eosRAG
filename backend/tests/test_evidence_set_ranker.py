import json
import pytest
from rag.evidence_set_ranker import select_evidence_set


def test_quotes_are_exact_and_essential_evidence_precedes_context():
    chunks = [{'chunk_id': 'a', 'raw_text': 'Review the clinical condition.'},
              {'chunk_id': 'b', 'raw_text': 'Perform an immediate assessment.'}]
    patient = {'culture_status': 'unknown'}
    history = [{'age_hours': 2}]
    def model(prompt, settings, **kwargs):
        p = json.loads(prompt)
        assert p['clinical_case_context'] == {'patient': patient, 'history': history}
        assert 'gold_chunk_ids' not in p
        assert kwargs['response_schema']['$defs']['EvidenceChoice']['properties']['id']['enum'] == ['a', 'b']
        return {'choices': [
            {'id': 'a', 'importance': 'supporting', 'purpose': 'Context', 'population': 'conditional_pathway', 'quote': 'Review the clinical condition.'},
            {'id': 'b', 'importance': 'essential', 'purpose': 'Assessment', 'population': 'current_infant', 'quote': 'Perform an immediate assessment.'}]}
    ids, rationale = select_evidence_set('Assess', chunks, patient, history, None, llm=model)
    assert ids == ['b', 'a'] and rationale[0]['importance'] == 'essential'


@pytest.mark.parametrize('bad_id,bad_quote', [('unknown', 'Review the clinical condition.'), ('a', 'Invented clinical guidance.')])
def test_invented_identity_or_quote_rejected(bad_id, bad_quote):
    def model(*args, **kwargs):
        return {'choices': [{'id': bad_id, 'importance': 'essential', 'purpose': 'Reason',
                             'population': 'current_infant', 'quote': bad_quote}]}
    with pytest.raises(ValueError):
        select_evidence_set('Assess', [{'chunk_id': 'a', 'raw_text': 'Review the clinical condition.'}], {}, [], None, llm=model)
