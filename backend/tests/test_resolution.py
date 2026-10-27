import json
from config import Settings
from rag.verification_graph import run_verification
from services.groq_client import GenerationUnavailable

PACKET={'guideline':'Synthetic documentation fixture','patient':{'age_hours':6},'history':[],
        'evidence':[{'id':'E1','text':'Measure and record clinical observations during assessment.','chunk_id':'synthetic'}]}

def exercise(*,repair_passes=True,outage=False,resolver_outage=False):
    calls=[]
    def llm(prompt,settings,*,role,**kw):
        calls.append(role)
        if role=='You are the evidence synthesis agent.':
            return {'claims':[{'id':'C1','section':'monitoring_plan','text':'Record observations twice daily.',
                     'support':[{'quote_id':'E1Q1'}]}]}
        if role=='You are the source-grounded resolution agent.':
            if resolver_outage:raise GenerationUnavailable('Synthetic outage','http_429')
            return {'claims':[{'id':'C1','section':'monitoring_plan',
                     'text':'Record clinical observations during assessment.' if repair_passes else 'Record observations twice daily.',
                     'support':[{'quote_id':'E1Q1'}]}]}
        if outage:raise GenerationUnavailable('Synthetic outage','http_429')
        claims=json.loads(prompt)['claims']
        good='twice daily' not in claims[0]['text']
        return {'supported':good,'checked_claim_ids':['C1'],'rejected_claim_ids':[] if good else ['C1'],
                'reasons':[] if good else ['The source provides no twice-daily interval.']}
    result=run_verification(PACKET,Settings(_env_file=None,verification_max_repairs=1),llm)
    return result,calls

def test_resolution_requires_fresh_unanimous_audits():
    result,calls=exercise()
    assert result['status']=='supported_for_review'
    assert result['resolution_trace'][0]['status']=='abstained'
    assert calls.count('You are the source-grounded resolution agent.')==1
    assert sum('auditor.' in r for r in calls)==4

def test_resolution_cannot_loop_until_a_favorable_verdict():
    result,calls=exercise(repair_passes=False)
    assert result['status']=='abstained'
    assert calls.count('You are the source-grounded resolution agent.')==1
    assert len(result['resolution_trace'])==1

def test_auditor_outage_is_never_repaired_into_release():
    result,calls=exercise(outage=True)
    assert result['status']=='abstained'
    assert not any('resolution agent' in role for role in calls)

def test_resolution_outage_keeps_original_abstention():
    result,calls=exercise(resolver_outage=True)
    assert result['status']=='abstained'
    assert result['resolution_error_code']=='http_429'


def test_reviews_cannot_reject_nonexistent_claim_ids():
    def llm(prompt,settings,*,role,**kw):
        if role=='You are the evidence synthesis agent.':
            return {'claims':[{'id':'C1','section':'monitoring_plan','text':'Record clinical observations during assessment.',
                              'support':[{'quote_id':'E1Q1'}]}]}
        assert 'resolution agent' not in role
        return {'supported':False,'checked_claim_ids':['C1'],'rejected_claim_ids':['C99'],
                'reasons':['A review of a different claim is invalid.']}
    result=run_verification(PACKET,Settings(_env_file=None),llm)
    assert result['status']=='abstained'
    assert result['evidence_verdict']['checked_claim_ids']==[]


def test_care_plan_resolution_selects_sources_then_gets_two_fresh_audits():
    first='Review only after every eligibility condition has been confirmed.'
    replacement='Record the observed clinical findings during assessment.'
    url='https://example.invalid/'+('metadata/'*1000)
    packet={**PACKET,'task_mode':'care_plan','evidence':[
        {'id':eid,'text':text,'source':'Fixture','version':'v1','section':'Review',
         'document_url':url} for eid,text in [('E1',first),('E2',replacement)]]}
    calls=[]
    def llm(prompt,settings,*,role,**kwargs):
        data=json.loads(prompt);calls.append((role,data))
        if role=='You are the evidence synthesis agent.':
            return {'claims':[{'id':'C1','section':'monitoring_plan','support':[{'quote_id':'E1Q1'}]}]}
        if role=='You are the source-grounded resolution agent.':
            assert kwargs['completion_tokens']==1200
            assert data['previous_claims']==[{'id':'C1','section':'monitoring_plan','support_quote_ids':['E1Q1']}]
            assert url not in prompt
            assert data['data']['evidence'][0]['available_quotes'][0]['text']==first
            return {'claims':[{'id':'C2','section':'monitoring_plan','support':[{'quote_id':'E2Q1'}]}]}
        claim=data['claims'][0];good=claim['id']=='C2'
        assert claim['text']==(replacement if good else first)
        return {'supported':good,'checked_claim_ids':[claim['id']],
            'rejected_claim_ids':[] if good else [claim['id']],
            'reasons':[] if good else ['Eligibility is unknown.']}
    result=run_verification(packet,Settings(_env_file=None,verification_max_repairs=1),llm)
    assert result['status']=='supported_for_review'
    assert result['draft']['claims'][0]['text']==replacement
    assert packet['evidence'][0]['document_url']==url
    assert sum('resolution agent' in r for r,_ in calls)==1
    assert sum('auditor.' in r for r,_ in calls)==4
    assert result['evidence_verdict']['checked_claim_ids']==['C2']
    assert result['safety_verdict']['checked_claim_ids']==['C2']
