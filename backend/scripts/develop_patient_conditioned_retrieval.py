"""Balanced development pilot, then optional completion of the same 100 cases."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from config import get_settings
from rag.relevance import focus_query
from rag.rank_fusion import fuse_rankings
from rag.patient_passage_ranker import select_patient_passages
from scripts.evaluate_expanded import Tracer
from scripts.evaluation_transport import provider_failure
from scripts.evaluate_rag_improvements import save
from services.groq_client import GenerationUnavailable

OUT=ROOT/'output/research/rag_development/patient_conditioned'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main(limit):
    data=ROOT/'output/research';corpusfile=data/'rag_development/medcpt/corpus.json'
    corpus={c['chunk_id']:c for c in json.loads(corpusfile.read_text())['chunks']}
    cases=[{k:c[k] for k in ['id','family','query','patient','history']}
           for c in json.loads((data/'expanded100/cases.json').read_text())]
    upstream={p.stem:json.loads(p.read_text()) for p in (data/'rag_development/listwise/runs').glob('*.json')}
    seen=set();first=[];rest=[]
    for c in cases:
        key=(upstream[c['id']]['guideline'],c['family'])
        if key not in seen:first.append(c);seen.add(key)
        else:rest.append(c)
    if len(first)!=18:raise ValueError('Balanced six-family, three-source pilot unavailable')
    protocol={'stage':'development_only','final_evaluation':False,'total_existing_cases':100,'balanced_pilot':18,
        'pilot_case_ids':[c['id'] for c in first],'model':'openai/gpt-oss-120b','temperature':0,'sampling_seed':None,
        'candidate_budget':24,'selected_budget':8,'rrf_k':60,
        'change':'Original question plus unchanged recorded current/history facts; no labels or engineering answers in model inputs.',
        'expansion':'Continue remaining existing cases only after reviewing the balanced development pilot; no untouched-test claim.',
        'code_sha256':{p:sha(ROOT/p) for p in ['backend/rag/patient_passage_ranker.py',
            'backend/rag/listwise_rerank.py','backend/scripts/develop_patient_conditioned_retrieval.py']},
        'corpus_sha256':sha(corpusfile)}
    p=OUT/'development_protocol.json'
    if p.exists() and json.loads(p.read_text())!=protocol:raise ValueError('Patient-conditioned protocol drift')
    save(p,protocol)
    settings=get_settings().model_copy(update={'llm_provider':'groq','groq_model':protocol['model']})
    for c in (first+rest)[:limit]:
        target=OUT/'runs'/f'{c["id"]}.json'
        if target.exists():continue
        r=upstream[c['id']];ids=r['candidate_ids'];question=focus_query(c['query'])
        key=hashlib.sha256(json.dumps([question,c['patient'],c['history'],ids]).encode()).hexdigest()
        trace=Tracer(OUT/'role_cache'/key,protocol['model'],gap=3)
        record={'id':c['id'],'guideline':r['guideline'],'family':c['family'],'stage':'development_only',
                'candidate_ids':ids,'request_key':key,'pilot':c in first}
        try:
            selected=select_patient_passages(question,[corpus[i] for i in ids],c['patient'],c['history'],settings,llm=trace)
            record.update(available=True,selected_ids=selected,
                consensus_ids=fuse_rankings([ids,selected],60)[:8])
        except GenerationUnavailable as exc:
            if provider_failure(exc.code):
                save(OUT/'pending_transport.json',{'id':c['id'],'code':exc.code,
                    'messages':[x.get('provider_message') for x in trace.calls if x.get('provider_message')],
                    'completed':len(list((OUT/'runs').glob('*.json'))),'planned_pilot':18,
                    'policy':'Completed role responses preserved. Provider blocks are not clinical-quality failures.'})
                raise SystemExit(75)
            record.update(available=False,selected_ids=[],consensus_ids=ids[:8],completed_model_error=exc.code)
        except (TypeError,ValueError) as exc:
            record.update(available=False,selected_ids=[],consensus_ids=ids[:8],completed_contract_error=type(exc).__name__)
        record['calls']=trace.calls;save(target,record)
        print('Patient-conditioned development',c['id'],'valid',record['available'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,choices=[18,100],default=18)
    main(p.parse_args().limit)
