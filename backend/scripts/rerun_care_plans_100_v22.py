"""Resumable 100-case research run; model failures stay in denominator."""
import argparse,hashlib,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from config import get_settings
from rag.verification_v20 import run_verification
from rag.section_evidence_v20 import augment
from scripts.evaluate_expanded import Tracer
from scripts.evaluate_rag_improvements import save
BASE=ROOT/'output/research/rag_development';OUT=BASE/'care_plan_100_v22'
PILOT={'aap-expanded-crp_alone-01','nice-expanded-incomplete_stop-01','who-expanded-missing_results-01'}
MODEL_FAILURES={'invalid_audit_contract','model_json_contract_failure','finish_reason_length','JSONDecodeError'}

def packet_for(case,corpus):
    record=json.loads((BASE/'semantic_guidance/runs'/f'{case["id"]}.json').read_text())
    lookup={c['chunk_id']:c for c in corpus};ids=record['rankings']['ce_definition_graph']['8']
    evidence=[]
    def add(c,kind=None):
        if c['chunk_id']in {e['chunk_id']for e in evidence}:return
        evidence.append({'id':f'E{len(evidence)+1}','chunk_id':c['chunk_id'],'text':c.get('raw_text',c['text']),'source':c['source'],'version':c['version'],'page_number':c.get('pdf_page'),'kind':kind})
    for cid in ids:add(lookup[cid])
    guide=record['guideline']
    if guide=='AAP':
        for c in corpus:
            if c['guideline_id']==guide and 'unexplained critical cardiorespiratory illness'in c.get('raw_text',c['text']).lower():add(c,'exception_context')
    packet={'guideline':guide,'task_mode':'care_plan','patient':case['patient'],'history':case['history'],'evaluation_question':case['query'],'evidence':evidence}
    packet,trace=augment(packet,corpus,guide,max_additional=8);evidence=packet['evidence']
    for c in corpus:
        text=c.get('raw_text',c['text'])
        if c['guideline_id']==guide and ((guide=='NICE'and 'Other clinical indicators'in text and 'Red flag clinical indicators'in text)or(guide=='WHO'and any(x in text.lower()for x in ['clinical severe infection is defined','critical illness is defined']))):add(c,'supplemental_publisher_definition')
    return packet,trace,guide

def main():
    from concurrent.futures import ThreadPoolExecutor
    import threading
    stop=threading.Event()
    from scripts.research_key_pool_v22 import ResearchKeyPool
    import services.groq_client as transport
    pool=ResearchKeyPool(transport.complete_json,ROOT/'backend/.env');transport.complete_json=pool
    arg=argparse.ArgumentParser();arg.add_argument('--pilot',action='store_true');args=arg.parse_args()
    casefile=ROOT/'output/research/expanded100/cases.json';corpusfile=BASE/'recommendation_units/corpus.json'
    cases=json.loads(casefile.read_text(encoding='utf8'));corpus=json.loads(corpusfile.read_text(encoding='utf8'))['chunks'];lookup={c['chunk_id']for c in corpus}
    assert len(cases)==100 and len({c['id']for c in cases})==100
    for c in cases:
        for g in c['gold_chunk_ids']:
            if g not in lookup:raise ValueError('Missing gold passage: '+g)
    files=['backend/rag/verification_v20.py','backend/rag/verification_core_v20.py','backend/rag/audit_contract_v20.py','backend/rag/section_evidence_v20.py','backend/rag/patient_application_v13.py','backend/scripts/rerun_care_plans_100_v22.py','backend/scripts/research_key_pool_v22.py']
    protocol={'stage':'exposed_synthetic_research_rerun_not_clinical_validation','planned_cases':100,'seed':31,'generation_model':'openai/gpt-oss-120b','safety_model':'qwen/qwen3.8-27b','audit_batch_size':4,'audit_attempts':2,'source_supplement_budget':8,'gold_used_for_retrieval_or_generation':False,'case_sha256':hashlib.sha256(casefile.read_bytes()).hexdigest(),'corpus_sha256':hashlib.sha256(corpusfile.read_bytes()).hexdigest(),'code_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in files},'clinical_review_status':'pending','output_kind':'13-section patient-specific evidence review; unsupported sections explicit; not autonomous treatment orders','sampling_seed_support':'fixed local seed; no provider seed assumed','temperature':0,'transport':'user-authorized key pool; same models/prompts; no secret values logged','workers':3,'cache_provenance':'v20/v21 identical-pipeline completed calls reused; all other calls fresh'}
    path=OUT/'protocol.json'
    if path.exists()and json.loads(path.read_text())!=protocol:raise ValueError('Protocol drift: use new version')
    save(path,protocol)
    selected=[c for c in cases if not args.pilot or c['id']in PILOT]
    def process(case):
        if stop.is_set():return
        target=OUT/'runs'/f'{case["id"]}.json'
        if target.exists():return
        packet,coverage,guide=packet_for(case,corpus)
        for execution in range(6):
            settings=get_settings().model_copy(update={'llm_provider':'groq','verifier_provider':'groq','groq_model':protocol['generation_model'],'verifier_model':protocol['generation_model'],'llm_schema_enforcement':True,'llm_timeout_seconds':60.,'verification_budget_seconds':360.})
            tracer=Tracer(OUT/'role_cache'/case['id'],protocol['generation_model'],gap=0)
            started=time.monotonic();result=run_verification(packet,settings,tracer)
            codes=[result.get('generation_error_code')]+[result.get(k,{}).get('error_code')for k in ['evidence_verdict','safety_verdict']]
            operational=[c for c in codes if c and c not in MODEL_FAILURES]
            record={'id':case['id'],'guideline':guide,'family':case['family'],'packet':packet,'result':result,'coverage_trace':coverage,'elapsed_seconds':time.monotonic()-started,'execution_classification':'completed_model_failure'if any(codes)and not operational else 'completed','calls':tracer.calls,'clinical_validation':False}
            if not operational:
                save(target,record);print(case['id'],result['plan_release_status'],len(result['source_reference_claims']),flush=True);break
            save(OUT/'operational'/f'{case["id"]}-{execution}.json',record)
            if 'authorized_quota_exhausted'in operational:
                stop.set();print('All user-authorized daily quotas exhausted; checkpoints saved',flush=True);return
            if 'http_429'in operational:
                print('Minute cooldown: checkpoints retained',flush=True);time.sleep(45)
            else:
                stop.set();print('Execution pending',case['id'],operational,flush=True);return
        else:stop.set();return
    with ThreadPoolExecutor(max_workers=3)as executor:
        list(executor.map(process,selected))
    print('Saved completed cases',len(list((OUT/'runs').glob('*.json'))),'/100',flush=True)
if __name__=='__main__':main()
