import json
from config import Settings
from rag.verification_core_v16 import run_verification


def test_conditional_context_cannot_clear_drug_dose_rejection():
    def llm(prompt,settings,**kw):
        if 'synthesis' in kw['role']:
            return {'claims':[{'id':'C1','section':'recommended_actions','support':[{'quote_id':'E1Q1'}]}]}
        return {'supported':True,'rejected_claim_ids':[],'checked_claim_ids':['C1'],'reasons':[]}
    p={'guideline':'WHO','patient':{'referral_possible':True},'history':[],
       'evidence':[{'id':'E1','source':'Synthetic safety fixture','text':'If referral is not possible, administer gentamicin 5 mg/kg.'}]}
    r=run_verification(p,Settings(_env_file=None),llm)
    assert not r['source_reference_claims']
    assert any('dose' in x['reason'].lower() for x in r['selection_rejections'])


def test_historical_context_cannot_clear_drug_dose_rejection():
    def llm(prompt,settings,**kw):
        if 'synthesis' in kw['role']:
            return {'claims':[{'id':'C1','section':'investigations','support':[{'quote_id':'E1Q1'}]}]}
        return {'supported':True,'rejected_claim_ids':[],'checked_claim_ids':['C1'],'reasons':[]}
    p={'guideline':'NICE','patient':{'antibiotic_duration_hours':36},'history':[],
       'evidence':[{'id':'E1','source':'Synthetic safety fixture','text':'Take culture before first dose and administer gentamicin 5 mg/kg.'}]}
    r=run_verification(p,Settings(_env_file=None),llm)
    assert not r['source_reference_claims']
