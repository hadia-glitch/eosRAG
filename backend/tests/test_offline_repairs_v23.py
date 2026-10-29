import copy,json
from config import Settings
from rag.offline_repairs_v23 import missing_observations,distress_state,clean_numbering,repair_rendering
from rag.section_proposals_v23 import eligible_topic,propose
from rag.verification_v23 import run_verification

def test_temperature_alias_and_unknowns():
    assert 'temperature'not in missing_observations({'temperature_c':36.8})
    assert 'temperature'in missing_observations({'temperature_c':float('nan')})
    assert 'feeding'in missing_observations({'feeding':' UNKNOWN '})

def test_explicit_negation_is_not_positive_distress():
    for value in ['no respiratory distress','without respiratory distress','no signs of respiratory distress','absent']:
        assert distress_state({'respiratory_distress':value})=='not met'
    assert distress_state({'clinical_condition':'persistent respiratory distress'})=='met'
    assert distress_state({'respiratory_distress':'not documented'})=='unknown'

def test_duplicate_numbering_removed():
    assert clean_numbering(['1. 1. do now','2. 3. monitor'])==['1. do now','2. monitor']

def test_model_development_and_marker_only_sources_not_action_proposals():
    assert not eligible_topic('A cohort was used to develop predictive models of neonatal sepsis risk based on birth data and postnatal observations.','monitoring_plan')
    assert not eligible_topic('C-reactive protein and procalcitonin concentrations increase in response to multiple inflammatory stimuli in newborn infants.','antibiotic_review')
    assert not eligible_topic('Categorical Risk Factor Assessment','escalation_criteria')
    assert eligible_topic('Regularly reassess the clinical condition and results of investigations in babies receiving antibiotic treatment.','monitoring_plan')

def test_proposals_require_new_audits_and_preserve_original_selection():
    raw={'claims':[{'id':'C1','section':'risk_analysis','support':[{'quote_id':'E1Q1'}]}]}
    packet={'evidence':[{'id':'E1','text':'A cohort was used to develop predictive models based on neonatal birth data.'},{'id':'E2','text':'Regularly reassess the clinical condition and results of investigations in babies receiving antibiotic treatment.'}]}
    r,t=propose(raw,packet)
    assert r['claims'][0]==raw['claims'][0]
    assert all(x['evidence_id']=='E2'and x['requires_fresh_dual_audit']for x in t)
    assert raw['claims']==[r['claims'][0]]

def test_offline_render_replay_never_promotes_decisions():
    packet={'patient':{'temperature_c':37,'respiratory_distress':'no respiratory distress'},'evidence':[]}
    saved={'uncertainty':{'missing_bedside_observations':['temperature']},'patient_application':{'NICE_indicator_review':{'respiratory_distress':{'status':'met'}}},'plan_sections':[{'id':'S06','items':['1. 1. Clinical judgement â€” do now: obtain missing bedside observations: temperature.']}], 'source_reference_claims':[], 'completeness':{'passed':False},'plan_release_status':'incomplete_for_research_review'}
    before=copy.deepcopy(saved);r=repair_rendering(saved,packet)
    assert saved==before and not r['completeness']['passed']
    assert r['source_reference_claims']==[]and r['plan_release_status']==before['plan_release_status']
    assert 'temperature'not in r['uncertainty']['missing_bedside_observations']
    assert r['patient_application']['NICE_indicator_review']['respiratory_distress']['status']=='not met'
    json.dumps(r)

def test_new_candidate_cannot_approve_sources_when_auditors_reject():
    def llm(prompt,settings,**kw):
        if 'synthesis'in kw['role']:return {'claims':[]}
        ids=[c['id']for c in json.loads(prompt)['claims']]
        return {'supported':False,'checked_claim_ids':ids,'rejected_claim_ids':ids,'reasons':['Fixture rejection']}
    packet={'guideline':'NICE','patient':{'temperature_c':37,'respiratory_distress':'no respiratory distress'},'history':[],'evidence':[{'id':'E1','text':'Regularly reassess the clinical condition and results of investigations in babies receiving antibiotic treatment.','source':'Synthetic regression fixture'}]}
    r=run_verification(packet,Settings(_env_file=None),llm)
    assert not r['source_reference_claims']and not r['completeness']['passed']
    assert r['patient_application']['NICE_indicator_review']['respiratory_distress']['status']=='not met'


def test_unicode_microgram_drug_dose_stays_blocked():
    for unit in ['µg','μg','ug']:
        def llm(prompt,settings,**kw):
            if 'synthesis'in kw['role']:return {'claims':[{'id':'C1','section':'antibiotic_review','support':[{'quote_id':'E1Q1'}]}]}
            ids=[c['id']for c in json.loads(prompt)['claims']]
            return {'supported':True,'checked_claim_ids':ids,'rejected_claim_ids':[],'reasons':[]}
        packet={'guideline':'WHO','patient':{'referral_possible':True},'history':[],'evidence':[{'id':'E1','text':'If referral is not possible administer gentamicin 5 '+unit+'/kg.','source':'Synthetic safety fixture'}]}
        result=run_verification(packet,Settings(_env_file=None),llm)
        assert not result['source_reference_claims']
        assert any('dose'in r['reason'].lower()for r in result['selection_rejections'])


def test_who_thresholds_do_not_come_from_unrelated_numbers():
    from rag.patient_application_v23 import states
    r=states({'guideline':'WHO','patient':{'temperature_c':39,'respiratory_rate':70,'age_hours':12},'evidence':[{'id':'E1','text':'A study of infants born at 38 weeks recorded 60 observations over 0-6 days.'}]})
    v=r['WHO_category_review']
    assert v['clinical_severe_infection_signs']['high_temperature']['status']=='unknown'
    assert v['clinical_severe_infection_signs']['fast_breathing_age_0_to_6_days']['status']=='unknown'
    assert v['clinical_severe_infection_definition_matches']=='unknown'


def test_who_thresholds_are_tied_to_definition_passage():
    from rag.patient_application_v23 import states
    text='Clinical severe infection is defined by high body temperature (>= 38 C), low body temperature (< 35.5 C). In infants aged 0-6 days an additional sign is fast breathing (>= 60 breaths per minute).'
    r=states({'guideline':'WHO','patient':{'temperature_c':39,'respiratory_rate':70,'age_hours':12},'evidence':[{'id':'E1','text':text}]})['WHO_category_review']
    assert r['clinical_severe_infection_signs']['high_temperature']['status']=='met'
    assert r['clinical_severe_infection_signs']['high_temperature']['evidence_ids']==['E1']
    assert r['clinical_severe_infection_definition_matches']=='met'


def test_display_prefix_repair_does_not_rewrite_source_text():
    bad='\u00e2\u20ac\u201d'
    result={'uncertainty':{},'plan_sections':[{'id':'S08','items':['Clinical judgement '+bad+' patient application.','Guideline-derived reference: literal '+bad+' source text']}],'source_reference_claims':[]}
    repaired=repair_rendering(result,{'patient':{}})
    assert 'Clinical judgement \u2014'in repaired['plan_sections'][0]['items'][0]
    assert bad in repaired['plan_sections'][0]['items'][1]
