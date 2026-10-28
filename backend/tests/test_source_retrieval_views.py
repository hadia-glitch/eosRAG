import hashlib
import pytest
from rag.source_retrieval_views import genre,retrieval_view,topic_admission


def test_definition_enriches_search_only_and_checks_scope_and_integrity():
    raw='Critical illness means unable to feed.'
    c={'chunk_id':'rec','text':'Refer a critically ill infant.','raw_text':'Refer a critically ill infant.',
       'guideline_id':'WHO','pdf_sha256':'source'}
    n={'chunk_id':'def','raw_text':raw,'text_sha256':hashlib.sha256(raw.encode()).hexdigest(),
       'guideline_id':'WHO','pdf_sha256':'source','scope':{'care_setting':['non_hospital']}}
    g={'nodes':[n],'edges':[{'from':'rec','to':'def'}]}
    assert raw in retrieval_view(c,g,{'care_setting':'community_clinic'})[0]
    assert retrieval_view(c,g,{'care_setting':'hospital'})==(c['text'],[])
    assert c['raw_text']=='Refer a critically ill infant.'
    n['raw_text']='Tampered definition'
    with pytest.raises(ValueError,match='hash mismatch'):retrieval_view(c,g,{'care_setting':'community_clinic'})


def test_csf_result_context_does_not_displace_initial_investigations():
    c={'raw_text':'When interpreting the results of cerebrospinal fluid investigations, consider prior antibiotics.'}
    assert topic_admission(c,'Explain initial diagnostic investigations.',{})[0] is False
    assert topic_admission(c,'Interpret missing cerebrospinal fluid results.',{})[0] is True


def test_empirical_cohort_report_is_not_standalone_clinical_guidance():
    c={'guideline_id':'AAP','chunk_type':'article_paragraph','raw_text':'Researchers reported a cohort with serial examinations. Two infants developed EOS.'}
    assert genre(c)=='study_background'
    c['raw_text']='Under this approach ill infants are either treated or evaluated. Researchers described the outcomes.'
    assert genre(c)=='core_guidance'


def test_unmentioned_pathogen_not_promoted_to_general_regimen():
    c={'raw_text':'In young infants who are hospitalized with suspected staphylococcal sepsis, a specific regimen is recommended.'}
    assert topic_admission(c,'Review suspected sepsis.',{})[0] is False
    assert topic_admission(c,'Compare pathogen-specific alternatives.',{})[0] is True


def test_explicit_gestational_limit_cannot_become_a_generic_option_for_preterm_case():
    c={'raw_text':'The neonatal calculator can be used for babies born after 34+0 weeks of pregnancy.'}
    assert topic_admission(c,'Initial neonatal investigations.',{'gestational_age_weeks':28})[0] is False
    assert topic_admission(c,'Explain calculator eligibility.',{'gestational_age_weeks':28})[0] is True
    assert topic_admission(c,'Initial neonatal investigations.',{'gestational_age_weeks':37})[0] is True
