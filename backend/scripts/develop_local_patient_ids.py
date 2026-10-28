"""Progressive local-only evidence ranking on the corrected development corpus."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from rag.patient_passage_ranker import select_patient_passages
from rag.local_development_transport import LocalDevelopmentClient
from rag.rank_fusion import fuse_rankings
from rag.relevance import focus_query
from scripts.evaluate_rag_improvements import save
from scripts.evaluation_transport import provider_failure
from services.groq_client import GenerationUnavailable


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main(limit):
    base=ROOT/'output/research/rag_development';source=base/'recommendation_units/corpus.json'
    corpus={c['chunk_id']:c for c in json.loads(source.read_text())['chunks']}
    ids=json.loads((base/'patient_conditioned/development_protocol.json').read_text())['pilot_case_ids']
    smoke=[ids[0],ids[6],ids[12]]
    order=smoke+[i for i in ids if i not in smoke]
    cases={c['id']:{k:c[k] for k in ['id','family','query','patient','history']}
           for c in json.loads((ROOT/'output/research/expanded100/cases.json').read_text())}
    model='qwen3:4b-q4_K_M';out=base/'recommendation_units/local_patient_ids'
    metadata=httpx.post('http://127.0.0.1:11434/api/show',json={'model':model},timeout=10,trust_env=False).json()
    tags=httpx.get('http://127.0.0.1:11434/api/tags',timeout=10,trust_env=False).json()['models']
    digest=next(m['digest'] for m in tags if m['name']==model)
    protocol={'stage':'development_only','final_evaluation':False,'model':model,'model_digest':digest,
              'pilot_case_ids':ids,'first_three_case_ids':smoke,'candidate_budget':24,'selected_budget':8,
              'seed':31,'temperature':0,'think':False,'context':32768,'completion_tokens':2000,
              'rrf_k':60,'provider':'local_Ollama_native_schema','groq_calls':0,
              'corpus_sha256':sha(source),'upstream_protocol_sha256':sha(base/'recommendation_units/guarded_facets/development_protocol.json'),
              'code_sha256':{p:sha(ROOT/p) for p in ['backend/rag/local_development_transport.py','backend/rag/patient_passage_ranker.py','backend/rag/listwise_rerank.py','backend/scripts/develop_local_patient_ids.py']},
              'scope':'Progressive local-only identifier-only development smoke, not clinical validation. No generated relevance rationale. Review first three sources before expansion.'}
    p=out/'development_protocol.json'
    if p.exists() and json.loads(p.read_text())!=protocol:raise ValueError('Local development protocol drift')
    save(p,protocol)
    client=LocalDevelopmentClient(model,metadata)
    for case_id in order[:limit]:
        target=out/'runs'/f'{case_id}.json'
        if target.exists():continue
        c=cases[case_id]
        upstream=json.loads((base/'recommendation_units/guarded_facets/runs'/f'{case_id}.json').read_text())
        candidates=fuse_rankings([upstream['rankings'][m]['12'] for m in ['generic_single','medical_single','generic_faceted','medical_faceted']],60)[:24]
        record={'id':case_id,'family':c['family'],'guideline':upstream['guideline'],'candidate_ids':candidates,'stage':'development_only','groq_calls':0}
        calls=[]
        def traced(prompt,settings,**kwargs):
            key=hashlib.sha256(json.dumps([prompt,kwargs,digest],sort_keys=True).encode()).hexdigest()
            cache=out/'role_cache'/f'{key}.json'
            if cache.exists():
                old=json.loads(cache.read_text());calls.append({**old,'replayed':True})
                if 'response' in old:return old['response']
                raise GenerationUnavailable('Cached completed local failure',old['error_code'])
            entry={'prompt':prompt,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'model_digest':digest}
            try:
                response=client(prompt,settings,**kwargs);entry['response']=response
                return response
            except GenerationUnavailable as exc:
                entry['error_code']=exc.code
                if provider_failure(exc.code):raise
                raise
            finally:
                entry['usage']=client.calls[-1] if client.calls else {}
                calls.append(entry)
                if 'response' in entry or not provider_failure(entry.get('error_code')):save(cache,entry)
        try:
            selected=select_patient_passages(focus_query(c['query']),[corpus[i] for i in candidates],c['patient'],c['history'],None,llm=traced)
            materialized=[{'id':i,'source_text':corpus[i]['raw_text'],'source_text_sha256':hashlib.sha256(corpus[i]['raw_text'].encode()).hexdigest()} for i in selected]
            record.update(available=True,selected_ids=selected,selection_rationale=materialized,consensus_ids=fuse_rankings([candidates,selected],60)[:8])
        except GenerationUnavailable as exc:
            if provider_failure(exc.code):
                save(out/'pending_transport.json',{'id':case_id,'error_code':exc.code,'completed':len(list((out/'runs').glob('*.json'))),'policy':'Local provider/configuration failure remains pending, not a quality zero','groq_calls':0})
                raise SystemExit(75)
            record.update(available=False,selected_ids=[],consensus_ids=candidates[:8],completed_model_error=exc.code)
        except (TypeError,ValueError) as exc:
            record.update(available=False,selected_ids=[],consensus_ids=candidates[:8],completed_contract_error=type(exc).__name__)
        record['calls']=calls;save(target,record)
        print('Local evidence development',case_id,'valid',record['available'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int,choices=[3,18],default=3)
    main(parser.parse_args().limit)
