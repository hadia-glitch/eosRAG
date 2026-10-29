from rag.patient_application_v13 import states


def test_nice_other_indicators_are_not_red_flags_and_unknown_saturation_is_not_normal():
    p={'guideline':'NICE','patient':{'respiratory_rate':76,'spo2':97,'clinical_condition':'persistent respiratory distress'},'evidence':[]}
    s=states(p)['NICE_indicator_review']
    assert s['respiratory_distress']['guideline_category']=='other clinical indicator'
    assert s['respiratory_distress']['status']=='met'
    assert s['hypoxia']['status']=='unknown' and s['tachypnoea']['status']=='unknown'
    assert s['apnoea']['status']=='unknown'


def test_who_fast_breathing_is_age_specific_and_does_not_establish_critical_illness():
    definition='Clinical severe infection: temperature ≥38 or <35.5. Additional sign in 0–6 days is fast breathing ≥60.'
    p={'guideline':'WHO','patient':{'age_hours':12,'respiratory_rate':76,'referral_possible':True},'evidence':[{'id':'E1','text':definition}]}
    s=states(p)
    assert s['WHO_category_review']['clinical_severe_infection_signs']['fast_breathing_age_0_to_6_days']['status']=='met'
    assert s['WHO_category_review']['critical_illness_definition_matches']=='unknown'
    assert s['treatment_pathway_review']['referral_unavailable']['status']=='not met'
    p['patient']['age_hours']=200
    assert states(p)['WHO_category_review']['clinical_severe_infection_signs']['fast_breathing_age_0_to_6_days']['status']=='not met'


def test_missing_signs_remain_unknown():
    p={'guideline':'WHO','patient':{'age_hours':6,'feeding':'unknown','movement':'unknown'},'evidence':[]}
    s=states(p)['WHO_category_review']
    assert s['clinical_severe_infection_definition_matches']=='unknown'
    assert s['critical_illness_definition_matches']=='unknown'
    assert s['diagnosis_or_treatment_authorized'] is False
