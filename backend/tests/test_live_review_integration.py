import json
import pytest
from config import Settings
from rag.application_verification import run_verification
from services.clinical_pipeline import sanitize_snapshot
from rag.offline_repairs_v23 import clean_numbering,distress_state

@pytest.mark.parametrize('provider',['groq','ollama'])
def test_live_audits_are_batched_and_preserve_conditions(provider):
    text='Review the observations and document the findings. Missing observations do not establish clinical reassurance.'
    calls=[]
    sections=['risk_analysis','recommended_actions','investigations','antibiotic_review','monitoring_plan','escalation_criteria','nutrition_fluids','parent_communication_notes','follow_up']
    def llm(prompt,settings,**kw):
        p=json.loads(prompt)
        if 'synthesis'in kw['role']:return {'claims':[{'id':f'C{i+1}','section':s,'support':[{'quote_id':'E1Q1'}]}for i,s in enumerate(sections)]}
        calls.append(p)
        assert kw.get('provider',settings.llm_provider)==provider
        ids=[c['id']for c in p['claims']]
        assert len(ids)<=4 and p['source_packet']['evidence'][0]['text']==text
        return {'supported':True,'checked_claim_ids':ids,'rejected_claim_ids':[],'reasons':[]}
    packet={'guideline':'NICE','task_mode':'care_plan','patient':{'age_hours':12},'history':[],'evidence':[{'id':'E1','text':text,'source':'Synthetic fixture'}]}
    r=run_verification(packet,Settings(_env_file=None,verification_max_repairs=0,llm_provider=provider,verifier_provider=provider),llm)
    assert len(r['evidence_verdict']['checked_claim_ids'])==9 and len(calls)==6

def test_snapshot_numeric_bounds_and_boolean_types():
    assert sanitize_snapshot({'spo2':True,'gestational_age_weeks':999,'gbs_positive':1})=={}
    assert sanitize_snapshot({'spo2':98,'gbs_positive':False})=={'spo2':98,'gbs_positive':False}

def test_app_categories_and_decimal_prefixes_preserved():
    assert distress_state({'respiratory_distress':'Severe'})=='met'
    assert distress_state({'respiratory_distress':'Mild'})=='met'
    assert distress_state({'respiratory_distress':'None'})=='not met'
    assert clean_numbering(['1.5 mg/L','1.3.4 Recommendation'])==['1. 1.5 mg/L','2. 1.3.4 Recommendation']


def test_current_observations_and_uncertainty_reach_explanation():
    from services.clinical_pipeline import format_plan,explanation_from_plan
    from rag.production_retrieval import Retrieval
    patient={'age_hours':48,'respiratory_distress':'Severe','respiratory_rate':76,'spo2':97,'crp_level':3,'culture_status':'negative','culture_incubation_hours':36}
    packet={'guideline':'NICE','patient':patient,'evidence':[]}
    state={'status':'abstained','draft':{},'errors':['No reviewed sources']}
    plan=format_plan(patient,[],Retrieval(),packet,state,Settings(_env_file=None))
    explanation=explanation_from_plan(plan)
    assert '76 breaths/min'in explanation.evidence_summary and '97 %'in explanation.evidence_summary
    assert '3 mg/L'in explanation.evidence_summary
    assert 'Clinical condition reassuring: NOT MET'in explanation.evidence_summary
    assert not plan.fact_check.verified and len(plan.plan_sections)==13


def test_audit_budget_exhaustion_cannot_release_or_start_more_calls():
    from unittest.mock import patch
    from types import SimpleNamespace
    clock=SimpleNamespace(value=0)
    calls=[]
    def llm(prompt,settings,**kw):
        calls.append(kw['role'])
        assert settings.llm_timeout_seconds<=settings.verification_budget_seconds
        clock.value=100
        return {'claims':[{'id':'C1','section':'monitoring_plan','support':[{'quote_id':'E1Q1'}]}]}
    text='Review the observations and document the findings. Missing observations do not establish clinical reassurance.'
    packet={'guideline':'NICE','task_mode':'care_plan','patient':{'age_hours':12},'history':[],'evidence':[{'id':'E1','text':text,'source':'Synthetic fixture'}]}
    with patch('rag.application_verification.time',SimpleNamespace(monotonic=lambda:clock.value)):
        result=run_verification(packet,Settings(_env_file=None,verification_max_repairs=0),llm)
    assert len(calls)==1
    assert result['evidence_verdict']['error_code']=='verification_budget_exhausted'
    assert not result['evidence_verdict']['supported']
