import json
from config import Settings
from rag.verification_v5 import run_verification


def fixture(llm):
    text='A minimum blood volume of 1 mL is inoculated into the blood culture system.'
    packet={'guideline':'Synthetic source fixture','task_mode':'clinical_explanation',
        'evaluation_question':'What does the diagnostic source describe?',
        'patient':{'age_hours':6,'gestational_age_weeks':40},'history':[],
        'evidence':[{'id':'E1','text':text,'source':'Fixture','version':'test','section':'Investigations'}]}
    return run_verification(packet,Settings(_env_file=None,verification_max_repairs=0),llm)


def test_specimen_false_positive_fix_still_requires_two_complete_audits():
    called=[]
    def llm(prompt,settings,*,role,**kw):
        p=json.loads(prompt);called.append(role)
        if 'synthesis agent' in role:
            return {'claims':[{'id':'C1','section':'investigations','text':
                'A minimum blood volume of 1 mL is inoculated into the blood culture system.',
                'support':[{'quote_id':'E1Q1'}]}]}
        assert p['required_checked_claim_ids']==['C1']
        assert p['source_packet']['evaluation_question']=='What does the diagnostic source describe?'
        return {'supported':True,'checked_claim_ids':['C1'],'rejected_claim_ids':[],'reasons':[]}
    result=fixture(llm)
    assert result['status']=='supported_for_review'
    assert sum('auditor' in r for r in called)==2


def test_semantic_dissent_is_not_overridden_by_specimen_or_source_identity():
    def llm(prompt,settings,*,role,**kw):
        if 'synthesis agent' in role:
            return {'claims':[{'id':'C1','section':'risk_analysis','text':'Missing culture results establish that infection is excluded.',
                'support':[{'quote_id':'E1Q1'}]}]}
        return {'supported':False,'checked_claim_ids':['C1'],'rejected_claim_ids':['C1'],'reasons':['The source does not establish this inference.']}
    result=fixture(llm)
    assert result['status']=='abstained' and result['evidence_verdict']['checked_claim_ids']==['C1']
    assert result['safety_verdict']['checked_claim_ids']==['C1']
