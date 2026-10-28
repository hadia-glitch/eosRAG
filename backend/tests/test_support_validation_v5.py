import pytest
from rag.verification_graph import Draft, validate_support as historical
from rag.support_validation_v5 import validate_support

TEXT = ('These systems detect bacteremia if a minimum blood volume of 1 mL is inoculated. '
        'This is a source description, not a patient-specific instruction.')


def case(text=TEXT, section='investigations', quote=None, evidence_id='E1'):
    draft = Draft.model_validate({'claims': [{'id': 'C1', 'section': section, 'text': text,
                    'support': [{'evidence_id': evidence_id, 'quote': quote or text}]}]})
    return draft, {'evidence': [{'id': 'E1', 'text': quote or text}], 'patient': {}}


def test_verbatim_specimen_text_is_not_mislabeled_as_medication_dosing():
    draft, packet = case()
    assert historical(draft, packet) == ['C1: numerical medication/fluid dosing is not supported']
    assert validate_support(draft, packet) == []


@pytest.mark.parametrize('text,section', [
    ('Administer a blood volume of 1 mL and inoculate the culture.', 'investigations'),
    ('Infuse 1 mL of fluid now and collect a blood culture.', 'investigations'),
    (TEXT + ' Give 5 mg of medication.', 'investigations'),
    (TEXT, 'recommended_actions'),
])
def test_therapeutic_quantities_and_wrong_sections_remain_rejected(text, section):
    draft, packet = case(text, section)
    assert any('dosing is not supported' in e for e in validate_support(draft, packet))


def test_paraphrasing_does_not_get_the_verbatim_exception():
    draft, packet = case(TEXT.replace('1 mL', '2 mL'), quote=TEXT)
    assert any('dosing is not supported' in e for e in validate_support(draft, packet))


def test_citation_identity_failure_is_retained():
    draft, packet = case(evidence_id='E2')
    assert validate_support(draft, packet) == ['C1: unknown evidence label']
