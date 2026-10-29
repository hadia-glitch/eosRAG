from types import SimpleNamespace
from services.clinical_pipeline import accepted_claims,format_plan,explanation_from_plan,summarize_trends,context_history
from config import Settings
from rag.production_retrieval import retrieve_plan,Retrieval,PLAN_QUERIES
from rag.verification_graph import validate_support,Draft,index_quotes

def state():
    claims=[{'id':f'C{i}','section':section,'text':'Record measured observations during review.',
             'support':[{'evidence_id':'E1','quote':'Record measured observations.'}]} for i,section in enumerate(
              ['risk_analysis','recommended_actions','investigations','antibiotic_review','monitoring_plan',
               'escalation_criteria','parent_communication_notes','follow_up'],1)]
    verdict={'supported':True,'checked_claim_ids':[c['id'] for c in claims], 'rejected_claim_ids':[], 'reasons':[]}
    return {'draft':{'claims':claims},'status':'supported_for_review','errors':[],
            'evidence_verdict':dict(verdict),'safety_verdict':dict(verdict)}

def test_complete_review_reaches_plan_and_explanation_without_dropping_sections():
    packet={'evidence':[{'id':'E1','chunk_id':'fixture','source':'Fixture','section':'observations',
                        'text':'Record measured observations.','page_number':1,'file_name':'','document_url':''}]}
    plan=format_plan({'age_hours':12,'gestational_age_weeks':36},[],Retrieval(),packet,state(),Settings(_env_file=None))
    assert sum(s.status=='evidence_supported' for s in plan.plan_sections)==8
    assert plan.plan_sections[10].items[0]=='Not supported by retrieved evidence'
    assert any('Feeding tolerance'in item for item in plan.plan_sections[10].items)
    assert plan.antibiotic_plan.regimen
    explanation=explanation_from_plan(plan)
    assert explanation.monitoring_plan==plan.monitoring_plan
    assert explanation.escalation_criteria==plan.escalation_criteria
    assert explanation.antibiotic_plan['regimen']==plan.antibiotic_plan.regimen
    assert explanation.per_driver_explanations

def test_partial_review_releases_only_claims_explicitly_accepted_by_both_auditors():
    result=state();result['status']='abstained'
    result['safety_verdict']={**result['safety_verdict'],'supported':False,'rejected_claim_ids':['C3'],'reasons':['Unsupported timing.']}
    assert {c['id'] for c in accepted_claims(result)}=={'C1','C2','C4','C5','C6','C7','C8'}
    result['evidence_verdict']['checked_claim_ids']=[]
    assert accepted_claims(result)==[]

def test_unassigned_dissent_or_structural_failure_never_enables_partial_release():
    result=state();result['safety_verdict']['supported']=False
    assert accepted_claims(result)==[]
    result=state();result['citation_errors']=['Unknown quote']
    assert accepted_claims(result)==[]

def test_current_assessment_is_included_in_measured_longitudinal_change():
    text=summarize_trends([{'measurements':{'respiratory_rate':48,'spo2':97}}],{'respiratory_rate':72,'spo2':91})
    assert '48 to 72' in text and '97 to 91' in text

def test_plan_retrieval_covers_multiple_domains_and_deduplicates_passages():
    calls=[]
    def retrieve(query,guideline,limit,settings,**kwargs):
        calls.append(query)
        return Retrieval(chunks=[SimpleNamespace(chunk_id='shared'),SimpleNamespace(chunk_id=str(len(calls)))],mode='hybrid')
    result=retrieve_plan('NICE',Settings(_env_file=None),{},retriever=retrieve)
    assert calls==list(PLAN_QUERIES) and len(result.chunks)==len(PLAN_QUERIES)+1

def test_recorded_concentration_is_not_confused_with_a_medication_dose():
    packet={'patient':{'crp_level':20},'evidence':[{'id':'E1','text':'Review measured observations during assessment.'}]}
    def draft(text):return Draft.model_validate({'claims':[{'id':'C1','section':'risk_analysis','text':text,
         'support':[{'evidence_id':'E1','quote':'Review measured observations during assessment.'}]}]})
    assert validate_support(draft('Recorded CRP is 20 mg/L at the current assessment.'),packet)==[]
    assert validate_support(draft('Give an antibiotic dose of 20 mg/kg.'),packet)
    assert validate_support(draft('Recorded CRP is 25 mg/L at the current assessment.'),packet)


def test_personal_safety_and_history_reach_retrieval_without_losing_domain_coverage():
    calls=[]
    def retriever(query,guideline,limit,settings,**kwargs):
        calls.append((query,kwargs['patient']))
        return Retrieval(mode='hybrid+graph',graph_status='available',selection_mode='maximal_marginal_relevance')
    patient={'age_hours':12,'penicillin_allergy':True,'creatinine_mg_dl':1.7}
    result=retrieve_plan('NICE',Settings(_env_file=None),patient,retriever=retriever,
        context_query='recorded respiratory distress',history=[{'measurements':{'spo2':97}}])
    queries=[q for q,_ in calls]
    assert queries[0]=='recorded respiratory distress'
    assert any('allergy' in q for q in queries)
    assert any('renal function' in q for q in queries)
    assert any('serial neonatal observations' in q for q in queries)
    assert all(q in queries for q in PLAN_QUERIES)
    assert all(p is patient for _,p in calls)
    assert result.graph_status=='available'
    assert 'maximal_marginal_relevance' in result.selection_mode


def test_future_or_untimed_history_cannot_be_presented_as_a_prior_trend():
    from datetime import datetime,timezone
    for stamp in ['2026-01-02T00:00:00Z',None,'2026-01-01T00:00:00']:
        context=SimpleNamespace(history=[{'created_at':stamp,'snapshot':{'spo2':90}}],load_error='')
        assert context_history(context,now=datetime(2026,1,1,tzinfo=timezone.utc))==[]
        assert 'timestamps' in context.load_error
    context=SimpleNamespace(history=[{'created_at':'2026-01-01T05:00:00Z','snapshot':{'spo2':94}},
        {'created_at':'2026-01-01T01:00:00Z','snapshot':{'spo2':98}}],load_error='')
    rows=context_history(context,now=datetime(2026,1,1,6,tzinfo=timezone.utc))
    assert [r['measurements']['spo2'] for r in rows]==[98,94]
    assert [r['hours_ago'] for r in rows]==[5.,1.]

def test_full_plan_quote_can_preserve_a_complete_conditional_recommendation():
    text='Review the observations. Retain every relevant condition. Do not infer a missing result.'
    _,quotes=index_quotes({'evidence':[{'id':'E1','text':text}]},whole_recommendations=True)
    assert quotes['E1Q1']['quote']==text
    _,legacy=index_quotes({'evidence':[{'id':'E1','text':text}]})
    assert len(legacy)==3

def test_selection_omits_repeated_metadata_without_changing_sources_or_conditions():
    import json
    from rag.verification_graph import run_verification
    text='Review the recorded observations. Stop only if every documented condition is satisfied.'
    url='https://example.invalid/'+('metadata/'*1000)
    packet={'task_mode':'care_plan','patient':{'age_hours':10,'respiratory_distress':'None','spo2':98},'history':[],
        'evidence':[{'id':'E1','source':'Fixture','version':'v1','section':'review',
            'chunk_id':'source-row','file_name':'source.pdf','page_number':3,
            'document_url':url,'text':text}]}
    captured=[]
    def llm(prompt,settings,*,role,**kwargs):
        captured.append(json.loads(prompt))
        if role=='You are the evidence synthesis agent.':
            return {'claims':[{'id':'C1','section':'monitoring_plan','support':[{'quote_id':'E1Q1'}]}]}
        return {'supported':True,'checked_claim_ids':['C1'],'rejected_claim_ids':[],'reasons':[]}
    result=run_verification(packet,Settings(_env_file=None),llm=llm)
    assert result['status']=='supported_for_review'
    assert result['draft']['claims'][0]['text']==text
    assert packet['evidence'][0]['document_url']==url
    source=captured[0]['data']['evidence'][0]
    assert source['available_quotes']==[{'quote_id':'E1Q1','text':text}]
    assert source['source']=='Fixture' and source['section']=='review'
    assert url not in json.dumps(captured[0])
    assert captured[0]['data']['patient']['respiratory_distress']=='None'
    assert 'The patient has respiratory distress and hypoxia' not in captured[0]['task']
    assert 'do not invent illness in a well infant' in captured[0]['task']

def test_escalation_retains_the_already_accepted_complete_framework_not_a_fragment():
    reviewed=state()
    full='Use the following framework for assessment. Preserve every condition before making an individual decision.'
    reviewed['draft']['claims'][4].update(text=full,support=[{'evidence_id':'E2','quote':full}])
    reviewed['draft']['claims'][5]['text']='need for mechanical ventilation'
    packet={'task_mode':'care_plan','evidence':[
        {'id':eid,'chunk_id':chunk,'source':'Test source','section':'Test section','text':text,
         'page_number':1,'file_name':'','document_url':''} for eid,chunk,text in
        [('E1','fixture','Record measured observations.'),('E2','NICE-1.3.5',full)]]}
    plan=format_plan({'age_hours':10},[],Retrieval(),packet,reviewed,Settings(_env_file=None))
    assert plan.escalation_criteria==full+' [E2]'
    assert plan.plan_sections[9].items==['1. '+full+' [E2]']
    assert reviewed['draft']['claims'][5]['text']=='need for mechanical ventilation'
    assert explanation_from_plan(plan).escalation_criteria==plan.escalation_criteria

def test_isolated_red_flag_is_not_a_standalone_escalation_pathway():
    reviewed=state();reviewed['draft']['claims'][5]['text']='need for mechanical ventilation'
    packet={'task_mode':'care_plan','evidence':[{'id':'E1','chunk_id':'NICE-box2','source':'Test source',
        'section':'Test section','text':'Red flag indicators include need for mechanical ventilation.',
        'page_number':1,'file_name':'','document_url':''}]}
    plan=format_plan({'age_hours':10},[],Retrieval(),packet,reviewed,Settings(_env_file=None))
    assert plan.plan_sections[9].status=='not_determined'
    assert 'need for mechanical ventilation' not in plan.escalation_criteria
