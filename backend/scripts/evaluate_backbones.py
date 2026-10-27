"""Small, declared synthetic compatibility comparison; not clinical validation.

Reuses three previously exposed development cases and frozen evidence packets.
Records every failure and raw role response. No patient-table rows are sent.
"""
import hashlib
import json
import argparse
from pathlib import Path
import time
import threading

from config import get_settings
from rag.verification_graph import run_verification
from services.groq_client import complete_json,GenerationUnavailable
from scripts.evaluation_transport import quality_eligible,cached_role_response,provider_failure

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/research/backbones'
CASES=['deterioration-1','crp_alone-1','initial_investigation-1']
MODELS=[('groq','openai/gpt-oss-20b'),('groq','qwen/qwen3.8-27b'),
        ('ollama','qwen3:4b-q4_K_M'),('ollama','mistral:7b-instruct-q4_K_M')]

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--provider',choices=['groq','ollama'])
    parser.add_argument('--output',type=Path,default=OUT)
    parser.add_argument('--replay-from',type=Path)
    parser.add_argument('--retry-transport',action='store_true')
    parser.add_argument('--gap-seconds',type=float,default=20.)
    parser.add_argument('--repairs',type=int,choices=[0,1],default=0)
    parser.add_argument('--structured',action='store_true')
    args=parser.parse_args()
    out=args.output.resolve()
    selected=[(p,m) for p,m in MODELS if not args.provider or p==args.provider]
    available={p.stem for p in (ROOT/'output/research/rag_v2/runs').glob('*.json')}
    # Match actual prepared identifiers; do not silently substitute scenarios.
    case_ids=CASES
    if not all(c in available for c in case_ids):raise ValueError('Declared frozen case not found')
    protocol={'purpose':'synthetic backbone compatibility and release behavior only',
              'cases':case_ids,'models':selected,'case_source':'Previously exposed rag_v2 development cases',
              'clinical_validation':False,'untouched_test':False,'transport_retries':3,
              'quality_population':'Cases with completed provider transport; malformed model answers and semantic rejections remain outcomes',
              'paired_arm_population':'The same eligible cases for both release arms',
              'minimum_cloud_call_gap_seconds':args.gap_seconds,
              'maximum_resolution_passes':args.repairs,
              'provider_constrained_schema':args.structured,
              'local_timeout_seconds':60,'local_cloud_fallback':False,
              'verification_source_sha256':hashlib.sha256((ROOT/'backend/rag/verification_graph.py').read_bytes()).hexdigest()}
    save(out/'protocol.json',protocol)
    base=get_settings();summary=[]
    cloud_lock=threading.Lock();next_call=[0.]
    for provider,model in selected:
        config=base.model_copy(update={'llm_provider':provider,'groq_model':model,'verifier_model':model,
            'verifier_provider':provider,'local_llm_model':model,'ollama_verifier_model':model,
            'local_llm_timeout_seconds':60})
        config=config.model_copy(update={'verification_max_repairs':args.repairs,
                                        'llm_schema_enforcement':args.structured,
                                        'verification_budget_seconds':120.})
        label=provider+'-'+model.replace('/','_').replace(':','_')
        folder=out/label
        for case_id in case_ids:
            path=folder/(case_id+'.json')
            previous=None
            if path.exists():
                previous=json.loads(path.read_text())
                if quality_eligible(previous) or not args.retry_transport:continue
                save(ROOT/f'output/operational/backbone_attempts/{label}/{case_id}-{time.time_ns()}.json',previous)
            elif args.replay_from:
                old=args.replay_from/label/(case_id+'.json')
                if old.exists():previous=json.loads(old.read_text())
            packet=json.loads((ROOT/f'output/research/rag_v2/runs/{case_id}.json').read_text())['packet']
            calls=[]
            cached_roles=set()
            def traced(prompt,settings,**kw):
                start=time.monotonic();prompt_sha=hashlib.sha256(prompt.encode()).hexdigest()
                entry={'role':kw['role'],'model':kw.get('model',model),'prompt_sha256':prompt_sha}
                cached=cached_role_response(previous,kw['role'],prompt_sha) if previous and kw['role'] not in cached_roles else None
                if cached is not None:
                    cached_roles.add(kw['role'])
                    calls.append({**entry,'seconds':0.,'replayed':True,'response':cached})
                    return cached
                try:
                    for attempt in range(4):
                        try:
                            if provider=='groq':
                                with cloud_lock:
                                    while time.monotonic()<next_call[0]:time.sleep(min(5,next_call[0]-time.monotonic()))
                                    try:response=complete_json(prompt,settings,**kw)
                                    finally:next_call[0]=time.monotonic()+args.gap_seconds
                            else:response=complete_json(prompt,settings,**kw)
                            break
                        except GenerationUnavailable as exc:
                            if exc.code not in {'http_429','http_500','http_502','http_503','http_504'} or attempt==3:raise
                            save(ROOT/f'output/operational/provider_retries/{label}/{case_id}-{time.time_ns()}.json',
                                 {'case':case_id,'role':kw['role'],'error_code':exc.code,'attempt':attempt+1})
                            until=time.monotonic()+(exc.retry_after_seconds or 30)+2
                            while time.monotonic()<until:time.sleep(min(5,until-time.monotonic()))
                    entry['response']=response
                    return response
                except GenerationUnavailable as exc:
                    entry['error_code']=exc.code
                    raise
                finally:
                    entry['seconds']=time.monotonic()-start;calls.append(entry)
            start=time.monotonic()
            result=run_verification(packet,config,llm=traced)
            record={'synthetic':True,'case':case_id,'provider':provider,'model':model,
                       'seconds':time.monotonic()-start,'packet':packet,'calls':calls,'result':result}
            save(path,record)
            print({'provider':provider,'model':model,'case':case_id,'status':result['status'],
                   'generated':bool(result.get('draft')),'error_codes':[c['error_code'] for c in calls if 'error_code' in c]},flush=True)
        records=[json.loads((folder/(case_id+'.json')).read_text()) for case_id in case_ids]
        eligible=[r for r in records if quality_eligible(r)]
        summary.append({'provider':provider,'model':model,'planned_n':len(case_ids),'n':len(eligible),
            'generated':sum(bool(r['result'].get('draft')) for r in eligible),
            'released':sum(r['result']['status']=='supported_for_review' for r in eligible),
            'case_ids':[r['case'] for r in eligible]})
        save(out/'summary.json',{'protocol':protocol,'results':summary})

if __name__=='__main__':main()
