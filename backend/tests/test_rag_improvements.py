"""Safety regressions for the improved retrieval and verification contracts."""
import json
from types import SimpleNamespace

import numpy as np
import pytest

from config import Settings
from rag.relevance import focus_query, passage_windows, rerank_scores
from rag.verification_v2 import run_verification
from scripts.evaluate_rag_improvements import metrics


def test_metric_ceiling_does_not_normalize_away_false_positives():
    r = metrics(['a', 'b', 'x', 'y'], {'a', 'b'})
    assert r['recall_at_4'] == r['mrr_at_4'] == r['ndcg_at_4'] == 1
    assert r['precision_at_4'] == r['precision_at_4_ceiling'] == .5
    assert metrics(['a','b','c','d'], set('abcde'))['recall_at_4_ceiling'] == .8


def test_reranker_sees_late_qualifier_without_editing_source():
    text = ' '.join(['background'] * 400 + ['essential_condition'])
    class CE:
        def predict(self, pairs, **kwargs):
            return [3 if 'essential_condition' in span else -2 for _, span in pairs]
    assert rerank_scores('question', [text], CE()) == [3]
    assert all(len(w.split()) <= 180 for w in passage_windows(text))
    assert text.endswith('essential_condition')


def test_invalid_reranker_scores_are_not_accepted():
    with pytest.raises(ValueError):
        rerank_scores('question', ['source'], SimpleNamespace(predict=lambda *a, **k: [np.nan]))


def test_query_focus_preserves_clinical_negation_and_question():
    q = 'Can antibiotics stop when symptoms persist? Gestation 38 weeks; age 36 hours; setting postnatal_ward.'
    assert focus_query(q) == 'Can antibiotics stop when symptoms persist?'


@pytest.mark.parametrize('invalid', [False, True])
def test_explicit_auditor_schema_and_missing_ids_still_fail_closed(invalid):
    seen = []
    packet = {'guideline':'NICE', 'patient':{'age_hours':6}, 'history':[],
              'evidence':[{'id':'E1','text':'Measure and record clinical observations during assessment.'}]}
    def llm(prompt, settings, **kwargs):
        p = json.loads(prompt)
        if 'synthesis' in kwargs['role']:
            return {'claims':[{'id':'C1','section':'monitoring_plan','text':'Record clinical observations during assessment.',
                              'support':[{'evidence_id':'E1','quote':packet['evidence'][0]['text']}]}]}
        seen.append((p, kwargs))
        assert p['required_checked_claim_ids'] == ['C1']
        assert 'output_schema' in p and kwargs['completion_tokens'] == 2400
        assert kwargs['response_schema']['required']
        verdict = {'supported':True,'checked_claim_ids':['C1'],'rejected_claim_ids':[],'reasons':[]}
        if invalid:
            verdict.pop('checked_claim_ids')
        return verdict
    r = run_verification(packet, Settings(_env_file=None, verification_max_repairs=0), llm)
    assert len(seen) == 2
    assert r['status'] == ('abstained' if invalid else 'supported_for_review')


def test_graph_outage_does_not_break_reviewed_lexical_fallback(monkeypatch, tmp_path):
    from rag import production_retrieval as pr
    row = {'id':'x','chunk_text':'Measure and record clinical observations during assessment.', 'metadata':{}}
    doc = {'title':'NICE','url':'https://www.nice.org.uk','source':'NICE'}
    monkeypatch.setattr(pr, 'load_manifest', lambda _: ([{'approved_for_generation':True,'source':'NICE','status':'current'}], 'test'))
    monkeypatch.setattr(pr, 'admit_chunk', lambda *a: True)
    monkeypatch.setattr(pr, 'approved_document', lambda *a: doc)
    monkeypatch.setattr(pr, 'graph_candidate_ids', lambda *a: (_ for _ in ()).throw(RuntimeError('offline')))
    class DB:
        def rpc(self, *a):
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=[row]))
    encoder = SimpleNamespace(encode=lambda *a, **k: (_ for _ in ()).throw(RuntimeError('offline')))
    ce = SimpleNamespace(predict=lambda *a, **k: (_ for _ in ()).throw(RuntimeError('offline')))
    result = pr.retrieve('assessment', 'NICE', 4, Settings(_env_file=None), db=DB(), encoder=encoder, reranker=ce)
    assert [r.chunk_id for r in result.chunks] == ['x']
    assert 'Graph retrieval unavailable' in result.warnings


def test_same_dimension_other_encoder_cannot_enter_vector_results(monkeypatch):
    from rag import production_retrieval as pr
    good = {'id':'lexical','chunk_text':'Review the clinical observations.', 'metadata':{}}
    wrong = {'id':'wrong-space','chunk_text':'Unrelated vector result.', 'metadata':{'embedding_model':'other-model'}}
    doc = {'title':'NICE','url':'https://www.nice.org.uk','source':'NICE'}
    monkeypatch.setattr(pr,'load_manifest',lambda _: ([{'approved_for_generation':True,'source':'NICE','status':'current'}],'test'))
    monkeypatch.setattr(pr,'admit_chunk',lambda *a: True)
    monkeypatch.setattr(pr,'approved_document',lambda *a: doc)
    monkeypatch.setattr(pr,'graph_candidate_ids',lambda *a: ([], 'disabled'))
    calls=[]
    class DB:
        def rpc(self,name,params):
            calls.append((name,params))
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=[wrong] if 'vector' in name else [good]))
    enc=SimpleNamespace(encode=lambda *a,**k: np.ones(384))
    ce=SimpleNamespace(predict=lambda pairs,**k: np.ones(len(pairs)))
    r=pr.retrieve('assessment','NICE',4,Settings(_env_file=None),db=DB(),encoder=enc,reranker=ce)
    assert [c.chunk_id for c in r.chunks]==['lexical']
    assert any('incompatible embedding' in warning for warning in r.warnings)
    assert next(p for n,p in calls if n=='eos_vector_search_v2')['encoder_name']=='sentence-transformers/all-MiniLM-L6-v2'


@pytest.mark.parametrize('invented_text', [False, True])
def test_source_answer_materializes_only_original_words(invented_text):
    from rag.source_answer import run_source_answer
    text='Do not use C-reactive protein results alone to make antibiotic decisions.'
    packet={'guideline':'NICE','patient':{'age_hours':12},'history':[],
            'evaluation_question':'Can CRP alone exclude infection?',
            'evidence':[{'id':'E1','text':text}]}
    def llm(prompt, settings, **kwargs):
        data=json.loads(prompt)
        if 'synthesis' in kwargs['role']:
            assert data['data']['evaluation_question']==packet['evaluation_question']
            claim={'id':'C1','section':'antibiotic_review','support':[{'quote_id':'E1Q1'}]}
            if invented_text:claim['text']='Stop antibiotics now.'
            return {'claims':[claim]}
        return {'supported':True,'checked_claim_ids':['C1'],'rejected_claim_ids':[],'reasons':[]}
    result=run_source_answer(packet,Settings(_env_file=None,verification_max_repairs=0),llm)
    if invented_text:assert result['status']=='abstained'
    else:
        assert result['status']=='supported_for_review'
        assert result['draft']['claims'][0]['text']==text


def test_lossless_audit_reference_retains_full_patient_and_evidence_packet():
    from rag.verification_v3 import compact_auditor
    text='Stop treatment only if culture and clinical criteria are all satisfied.'
    packet={'patient':{'culture_status':'unknown'},'history':[{'crp':4}],
            'evidence':[{'id':'E1','text':text},{'id':'E2','text':'Do not treat missing results as normal.'}]}
    payload={'source_packet':packet,'claims':[{'id':'C1','section':'antibiotic_review','text':text,
             'support':[{'evidence_id':'E1'}]}]}
    def llm(prompt,settings,**kw):
        p=json.loads(prompt)
        assert p['source_packet']==packet
        claim=p['claims'][0]
        assert 'text' not in claim
        assert next(e['text'] for e in p['source_packet']['evidence'] if e['id']==claim['text_ref']['evidence_id'])==text
        assert kw['completion_tokens']==1600
        return {}
    compact_auditor(llm)(json.dumps(payload),None,role='source-entailment auditor',completion_tokens=2400)


def test_injected_false_claim_is_never_compacted_or_changed():
    from rag.verification_v3 import compact_auditor
    payload={'source_packet':{'evidence':[{'id':'E1','text':'Do not use CRP alone to stop antibiotics.'}]},
             'claims':[{'id':'C1','text':'CRP alone rules out infection.','support':[{'evidence_id':'E1'}]}]}
    prompt=json.dumps(payload)
    def llm(actual,settings,**kw):
        assert actual==prompt and kw['completion_tokens']==2400
        return {}
    compact_auditor(llm)(prompt,None,role='neonatal safety auditor',completion_tokens=2400)


def test_guarded_mmr_cannot_promote_an_unrelated_tail_over_relevance_head():
    from rag.rank_fusion import guarded_mmr
    vectors=np.eye(20)
    chosen=guarded_mmr(list(range(20)),vectors,4)
    assert chosen[0]==0
    assert set(chosen)<=set(range(8))
    assert len(chosen)==len(set(chosen))==4
