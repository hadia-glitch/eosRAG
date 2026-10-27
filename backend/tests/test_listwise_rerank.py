import json
import pytest
from rag.listwise_rerank import select_passages


def chunks():
    return [{'chunk_id': i, 'raw_text': text} for i, text in [
        ('culture', 'Perform a culture before the first antibiotic dose.'),
        ('schedule', 'A subsequent dose may be scheduled after an interval.')]]


def test_model_cannot_invent_ids_or_repeat_an_id():
    for output in [{'ordered_ids': ['invented']}, {'ordered_ids': ['culture', 'culture']}]:
        with pytest.raises(ValueError):
            select_passages('Explain investigations.', chunks(), None, llm=lambda *a, **k: output)


def test_valid_empty_selection_is_not_filled_with_irrelevant_context():
    assert select_passages('Unrelated topic.', chunks(), None,
                           llm=lambda *a, **k: {'ordered_ids': []}) == []


def test_full_passages_and_question_are_retained_without_reference_answers():
    def llm(prompt, settings, **kw):
        data = json.loads(prompt)
        assert data['original_information_need'] == 'What is missing?'
        assert data['candidates'][0]['text'] == chunks()[0]['raw_text']
        assert kw['response_schema']['properties']['ordered_ids']['items']['enum'] == ['culture', 'schedule']
        assert not {'gold_chunk_ids', 'reference_answer', 'Sepsis_Label'} & set(data)
        return {'ordered_ids': ['culture']}
    assert select_passages('What is missing?', chunks(), None, llm=llm) == ['culture']


def test_candidate_budget_and_response_types_fail_closed():
    with pytest.raises(ValueError):
        select_passages('Question', chunks() * 13, None)
    with pytest.raises(ValueError):
        select_passages('Question', chunks(), None, llm=lambda *a, **k: {'ordered_ids': 'culture'})
