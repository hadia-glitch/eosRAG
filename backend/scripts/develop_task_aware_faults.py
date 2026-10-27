"""Fresh task-aware fault regression, separate from final answer evaluation."""
import hashlib
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from config import get_settings
from rag.verification_v4 import run_verification
from scripts.evaluate_expanded import Tracer
from scripts.evaluation_transport import quality_eligible
from scripts.evaluate_rag_improvements import save

OUT=ROOT/'output/research/rag_development/task_aware_faults'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    inputs=sorted((ROOT/'output/research/expanded100/stress').glob('*.json'))
    if len(inputs)!=36:raise ValueError('Expected the original 36 injected faults')
    protocol={'stage':'development_safety_regression','final_evaluation':False,'planned_faults':36,
        'model':'openai/gpt-oss-120b','temperature':0,'sampling_seed':None,'repairs':0,
        'change':'Original injected claims and patient/evidence packet plus task_mode=care_plan, matching the active app audit context.',
        'policy':'No fault rewriting or removal. Provider-blocked execution is excluded from quality outcomes and resumed from saved roles.',
        'input_sha256':{p.name:sha(p) for p in inputs},
        'code_sha256':{p:sha(ROOT/p) for p in ['backend/scripts/develop_task_aware_faults.py',
            'backend/rag/verification_v4.py','backend/rag/verification_v3.py','backend/rag/verification_v2.py',
            'backend/rag/verification_graph.py']}}
    p=OUT/'development_protocol.json'
    if p.exists() and json.loads(p.read_text())!=protocol:raise ValueError('Frozen task-aware fault protocol drift')
    save(p,protocol)
    settings=get_settings().model_copy(update={'llm_provider':'groq','verifier_provider':'groq',
        'groq_model':protocol['model'],'verifier_model':protocol['model'],'llm_schema_enforcement':True,
        'verification_max_repairs':0,'verification_budget_seconds':120.})
    for p in inputs:
        old=json.loads(p.read_text());path=OUT/'runs'/p.name
        if path.exists() and quality_eligible(json.loads(path.read_text())):continue
        packet={**old['packet'],'task_mode':'care_plan'}
        trace=Tracer(OUT/'role_cache'/old['id'],protocol['model'],gap=3,injected=old['result']['draft'])
        started=time.monotonic();result=run_verification(packet,settings,trace)
        record={'id':old['id'],'family':old['family'],'model':protocol['model'],'packet':packet,
            'calls':trace.calls,'result':result,'seconds':time.monotonic()-started,
            'stage':'development_safety_regression','original_record_sha256':sha(p)}
        save(path,record)
        if not quality_eligible(record):
            save(OUT/'pending_transport.json',{'id':old['id'],
                 'codes':[c.get('error_code') for c in trace.calls if c.get('error_code')],
                 'messages':[c.get('provider_message') for c in trace.calls if c.get('provider_message')],
                 'completed_faults':sum(quality_eligible(json.loads(q.read_text())) for q in (OUT/'runs').glob('*.json'))})
            raise SystemExit(75)
        print('Task-aware development fault',old['id'],result['status'],flush=True)
    records=[json.loads(p.read_text()) for p in (OUT/'runs').glob('*.json')]
    save(OUT/'summary.json',{'stage':'development_safety_regression','final_evaluation':False,
        'complete':len(records)==36 and all(quality_eligible(r) for r in records),'completed':len(records),'planned':36,
        'released':sum(r['result']['status']=='supported_for_review' for r in records),
        'note':'Fresh audit calls with task context; deterministic structural rejections may require no provider calls. Not clinical validation.'})


if __name__=='__main__':main()
