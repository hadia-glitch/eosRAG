"""Fresh three-case check of the offline candidate; no automatic app promotion."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from scripts.evaluate_expanded import Tracer
from scripts.evaluate_rag_improvements import save
from scripts.research_key_pool_v22 import ResearchKeyPool
from config import get_settings
from rag.verification_v23 import run_verification
import services.groq_client as transport
BASE=ROOT/'output/research/rag_development';OUT=BASE/'patient_care_plan_v23_fresh'
def main():
    pool=ResearchKeyPool(transport.complete_json,ROOT/'backend/.env');transport.complete_json=pool
    ids=['aap-expanded-crp_alone-01','nice-expanded-incomplete_stop-01','who-expanded-missing_results-01']
    files=list((ROOT/'backend/rag').glob('*v23.py'))
    protocol={'cases':ids,'generator':'openai/gpt-oss-120b','safety':'qwen/qwen3.8-27b','stage':'exposed_three_case_development','fresh_calls':True,'clinical_validation':False,'code_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in files}}
    path=OUT/'protocol.json'
    if path.exists()and json.loads(path.read_text())!=protocol:raise ValueError('Candidate code changed; use new output version')
    save(path,protocol)
    settings=get_settings().model_copy(update={'llm_provider':'groq','verifier_provider':'groq','groq_model':protocol['generator'],'verifier_model':protocol['generator'],'llm_schema_enforcement':True,'llm_timeout_seconds':60.})
    for cid in ids:
        target=OUT/'runs'/f'{cid}.json'
        if target.exists():continue
        old=json.loads((BASE/'care_plan_100_v22/runs'/f'{cid}.json').read_text(encoding='utf8'))
        tracer=Tracer(OUT/'role_cache'/cid,protocol['generator'],gap=0)
        result=run_verification(old['packet'],settings,tracer)
        record={'id':cid,'guideline':old['guideline'],'family':old['family'],'packet':old['packet'],'result':result,'calls':tracer.calls,'clinical_validation':False}
        codes=[result.get('generation_error_code')]+[result.get(k,{}).get('error_code')for k in ['evidence_verdict','safety_verdict']]
        if any(c and c not in {'invalid_audit_contract','model_json_contract_failure','finish_reason_length','JSONDecodeError'}for c in codes):
            save(OUT/'pending_execution.json',record);print('Execution pending; checkpoint retained',cid,flush=True);return
        save(target,record);print(cid,result['plan_release_status'],len(result['source_reference_claims']),flush=True)
if __name__=='__main__':main()
