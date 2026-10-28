"""Three difficult exposed cases, capped primary-model development check."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from config import get_settings
from rag.patient_passage_ranker import select_patient_passages
from rag.rank_fusion import fuse_rankings
from rag.relevance import focus_query
from rag.topic_scope import current_case_topic
from scripts.evaluate_expanded import Tracer
from scripts.evaluate_rag_improvements import save
from scripts.evaluation_transport import provider_failure
from services.groq_client import GenerationUnavailable

OUT=ROOT/'output/research/rag_development/recommendation_units/scoped_primary_smoke'
IDS=['single_risk-1','aap-expanded-missing_results-01','who-expanded-incomplete_stop-01']


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    base=ROOT/'output/research/rag_development/recommendation_units'
    source=base/'corpus.json'
    corpus={c['chunk_id']:c for c in json.loads(source.read_text())['chunks']}
    cases={c['id']:{k:c[k] for k in ['id','family','query','patient','history']}
        for c in json.loads((ROOT/'output/research/expanded100/cases.json').read_text())}
    protocol={'stage':'development_only','final_evaluation':False,'case_ids':IDS,'maximum_unique_model_requests':3,
              'case_selection':'Previously observed difficult risk-factor, missing-result and source-limitation cases; one per guideline, not an unbiased performance population.',
              'model':'openai/gpt-oss-120b','temperature':0,'sampling_seed':None,'rrf_k':60,
              'completion_tokens':2000,'candidate_budget':24,'selected_budget':8,
              'corpus_sha256':sha(source),'code_sha256':{p:sha(ROOT/p) for p in ['backend/scripts/develop_scoped_primary_smoke.py','backend/rag/topic_scope.py','backend/rag/patient_passage_ranker.py','backend/rag/listwise_rerank.py']},
              'policy':'No generation/evidence-auditor/safety-auditor/judge calls. Preserve all completed responses, including model errors. No clinical readiness claim from three cases.'}
    target=OUT/'development_protocol.json'
    if target.exists() and json.loads(target.read_text())!=protocol:raise ValueError('Capped primary smoke protocol drift')
    save(target,protocol)
    settings=get_settings().model_copy(update={'llm_provider':'groq','groq_model':protocol['model']})
    for case_id in IDS:
        target=OUT/'runs'/f'{case_id}.json'
        if target.exists():continue
        c=cases[case_id]
        upstream=json.loads((base/'guarded_facets/runs'/f'{case_id}.json').read_text())
        order=fuse_rankings([upstream['rankings'][m]['12'] for m in ['generic_single','medical_single','generic_faceted','medical_faceted']],60)
        decisions={i:current_case_topic(corpus[i],c['query'],c['patient']) for i in order}
        candidates=[i for i in order if decisions[i][0]][:24]
        trace=Tracer(OUT/'role_cache'/case_id,protocol['model'],gap=3)
        record={'id':case_id,'guideline':upstream['guideline'],'family':c['family'],
                'candidate_ids':candidates,'topic_exclusions':{i:reason for i,(allowed,reason) in decisions.items() if not allowed},'stage':'development_only'}
        try:
            selected=select_patient_passages(focus_query(c['query']),[corpus[i] for i in candidates],c['patient'],c['history'],settings,llm=trace)
            record.update(available=True,selected_ids=selected,consensus_ids=fuse_rankings([candidates,selected],60)[:8])
        except GenerationUnavailable as exc:
            if provider_failure(exc.code):
                save(OUT/'pending_transport.json',{'id':case_id,'code':exc.code,
                    'completed':len(list((OUT/'runs').glob('*.json'))),'planned':3,
                    'messages':[x.get('provider_message') for x in trace.calls if x.get('provider_message')],
                    'policy':'Provider failures remain pending, not model-quality failures'})
                raise SystemExit(75)
            record.update(available=False,selected_ids=[],consensus_ids=candidates[:8],completed_model_error=exc.code)
        except (ValueError,TypeError) as exc:
            record.update(available=False,selected_ids=[],consensus_ids=candidates[:8],completed_contract_error=type(exc).__name__)
        record['calls']=trace.calls;save(target,record)
        print('Capped primary development',case_id,'valid',record['available'],flush=True)


if __name__=='__main__':main()
