from rag.topic_scope import current_case_topic


def test_future_maternal_counselling_is_separate_from_current_infant_guidance():
    c={'raw_text':'If they become pregnant again, inform the maternity team.'}
    assert current_case_topic(c,'Review the current infant risk factor.',{})[0] is False
    assert current_case_topic(c,'Discuss future pregnancies.',{})[0] is True


def test_unknown_maternal_history_does_not_request_labour_management():
    c={'raw_text':'For women in labour, identify and assess risk factors.'}
    assert current_case_topic(c,'Explain unknown maternal history.',{})[0] is False
    assert current_case_topic(c,'Describe maternal assessment before birth.',{})[0] is True
    risk={'raw_text':'Maternal GBS colonisation is a neonatal risk factor.'}
    assert current_case_topic(risk,'Review neonatal risks.',{})[0] is True


def test_csf_interpretation_requires_topic_or_recorded_results_not_assumed_results():
    c={'raw_text':'Interpret the CSF results alongside clinical presentation.'}
    assert current_case_topic(c,'Explain unavailable culture results.',{})[0] is False
    assert current_case_topic(c,'Explain why missing CSF results limit interpretation.',{})[0] is True
    assert current_case_topic(c,'Discuss available investigations.',{'csf_wbc':20})[0] is True
