"""Check corruption, source scope and replay behavior of the frozen study."""
import hashlib
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'output/research/expanded100'

def load(name):
    return json.loads((DATA/name).read_text(encoding='utf8'))

def test_exact_100_retains_original_18_and_source_scope():
    cases=load('cases.json')
    original=json.loads((ROOT/'output/research/rag_v2/cases.json').read_text())
    assert len(cases)==100 and cases[:18]==original
    meta={r['id']:r for r in load('manifest.json')['cases']}
    assert {g:sum(r['guideline']==g for r in meta.values()) for g in ['NICE','AAP','WHO']}=={'NICE':40,'AAP':30,'WHO':30}
    corpus={r['chunk_id']:r for r in load('corpus.json')['chunks']}
    for case in cases:
        assert set(case)==set(original[0])
        assert case['synthetic'] is True
        assert 0<=case['patient']['age_hours']<72
        assert all(h['age_hours']<case['patient']['age_hours'] for h in case['history'])
        assert all(corpus[g]['guideline_id']==meta[case['id']]['guideline'] for g in case['gold_chunk_ids'])
        if meta[case['id']]['guideline']=='AAP':
            assert case['patient']['gestational_age_weeks']>=35
        for gold in meta[case['id']]['gold']:
            assert hashlib.sha256(corpus[gold['id']]['text'].encode()).hexdigest()==gold['text_sha256']

def test_no_who_exact_text_duplicate_can_hide_gold_retrieval():
    chunks=[r for r in load('corpus.json')['chunks'] if r['guideline_id']=='WHO']
    assert len({r['text_sha256'] for r in chunks})==len(chunks)
    assert load('corpus.json')['sources']['WHO']['exact_text_duplicate_aliases']

def test_original_rankings_replay_without_tuning():
    replay=load('retrieval_replay_check.json')
    assert replay['original_cases']==18 and replay['changed_rankings']==[]

def test_role_replay_preserves_responses_and_audit_occurrences(tmp_path,monkeypatch):
    from scripts.evaluate_expanded import Tracer
    import services.groq_client as client
    calls=[]
    def fake(prompt,settings,**kwargs):
        calls.append(prompt)
        return {'supported':False,'sequence':len(calls)}
    monkeypatch.setattr(client,'complete_json',fake)
    tracer=Tracer(tmp_path,'frozen-model')
    # An identical prompt in the second audit round still needs a fresh response.
    a=tracer('same prompt',object(),role='auditor')
    b=tracer('same prompt',object(),role='auditor')
    assert a!=b and len(calls)==2
    resumed=Tracer(tmp_path,'frozen-model')
    assert resumed('same prompt',object(),role='auditor')==a
    assert resumed('same prompt',object(),role='auditor')==b
    assert len(calls)==2

def test_model_truncation_is_not_retried_into_success(tmp_path,monkeypatch):
    from scripts.evaluate_expanded import Tracer
    import services.groq_client as client
    calls=[]
    def fake(*args,**kwargs):
        calls.append(1)
        raise client.GenerationUnavailable('truncated','finish_reason_length')
    monkeypatch.setattr(client,'complete_json',fake)
    for _ in range(2):
        with pytest.raises(client.GenerationUnavailable,match='truncated|Cached'):
            Tracer(tmp_path,'frozen-model')('same',object(),role='generator')
    assert len(calls)==1

def test_legacy_nonobject_reply_is_recovered_without_resampling(tmp_path,monkeypatch):
    from scripts.evaluate_expanded import Tracer,hydrate_completed_calls
    import services.groq_client as client
    def forbidden(*args,**kwargs):
        pytest.fail('A completed malformed reply must not be regenerated')
    monkeypatch.setattr(client,'complete_json',forbidden)
    record={'id':'synthetic-case','calls':[{'prompt':'fixed','role':'auditor','model':'frozen',
            'occurrence':0,'error_code':'ValueError','seconds':1.}]}
    hydrate_completed_calls(record,tmp_path)
    with pytest.raises(client.GenerationUnavailable) as exc:
        Tracer(tmp_path/'role_cache'/'synthetic-case','frozen')('fixed',object(),role='auditor')
    assert exc.value.code=='ValueError'

def test_provider_decoder_rejection_is_completed_model_failure(tmp_path,monkeypatch):
    import httpx
    import services.groq_client as client
    from scripts.evaluate_expanded import Tracer
    from scripts.evaluation_transport import provider_failure
    calls=[]
    def fake(*args,**kwargs):
        calls.append(1)
        req=httpx.Request('POST','https://example.invalid')
        response=httpx.Response(400,request=req,json={'error':{'code':'json_validate_failed',
            'message':'Failed to generate JSON.','failed_generation':'{invalid'}})
        cause=httpx.HTTPStatusError('decoder rejected',request=req,response=response)
        raise client.GenerationUnavailable('decoder rejected','http_400') from cause
    monkeypatch.setattr(client,'complete_json',fake)
    for _ in range(2):
        with pytest.raises(client.GenerationUnavailable) as exc:
            Tracer(tmp_path,'frozen')('fixed',object(),role='auditor')
        assert exc.value.code=='model_json_contract_failure'
        assert not provider_failure(exc.value.code)
    assert calls==[1]
    saved=json.loads(next(tmp_path.glob('*.json')).read_text())
    assert saved['raw_failed_generation']=='{invalid'

def test_paired_family_bootstrap_preserves_signed_effect_and_whole_clusters():
    from scripts.summarize_expanded import ci
    zero=ci([0.,0.,0.],['a','a','b'])
    assert [zero[k] for k in ['mean','case_low','case_high','family_low','family_high']]==[0.]*5
    negative=ci([-1.,-1.,-.5,-.5],['a','a','b','b'])
    assert negative['mean']==-.75
    assert negative['family_low']==-1. and negative['family_high']==-.5
    assert negative['resamples']==2000 and negative['seed']==31
