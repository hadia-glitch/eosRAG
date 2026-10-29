"""Live audit batching around the existing source-selection workflow."""
import json,time
from rag.verification_v4 import evidence_packet,run_verification as existing
from rag.audit_contract_v20 import audit_one
from services.groq_client import complete_json,GenerationUnavailable


def run_verification(packet,settings,llm=complete_json):
    started=time.monotonic()
    def timed(prompt,settings,**kw):
        remaining=settings.verification_budget_seconds-(time.monotonic()-started)
        if remaining<=0:raise GenerationUnavailable('Application review time budget exhausted','verification_budget_exhausted')
        bounded=settings.model_copy(update={'llm_timeout_seconds':min(settings.llm_timeout_seconds,remaining),'local_llm_timeout_seconds':min(settings.local_llm_timeout_seconds,remaining)})
        return llm(prompt,bounded,**kw)
    def batched(prompt,settings,**kw):
        if 'auditor'not in kw.get('role',''):return timed(prompt,settings,**kw)
        payload=json.loads(prompt);claims=payload['claims'];verdicts=[]
        if not claims:return {'supported':False,'checked_claim_ids':[],'rejected_claim_ids':[],'reasons':['No claims to check']}
        for start in range(0,len(claims),4):
            group=claims[start:start+4];part={**payload,'claims':group}
            eids={s['evidence_id']for c in group for s in c.get('support',[])}|{c.get('text_ref',{}).get('evidence_id')for c in group}
            part['source_packet']={**payload['source_packet'],'evidence':[e for e in payload['source_packet']['evidence']if e['id']in eids]}
            part['conciseness']='At most four short rejection reasons. A conditional source reference does not assert patient eligibility.'
            options={k:v for k,v in kw.items()if k not in {'role','response_schema','completion_tokens'}}
            options['completion_tokens']=900 if 'qwen'in str(options.get('model',''))else 1600
            v=audit_one(timed,json.dumps(part,ensure_ascii=False),settings,kw['role'],options,{c['id']for c in group})
            if v.get('error_code'):raise GenerationUnavailable('Audit did not complete valid output',v['error_code'])
            verdicts.append(v)
        rejected=[i for v in verdicts for i in v['rejected_claim_ids']]
        return {'supported':not rejected,'checked_claim_ids':[c['id']for c in claims],'rejected_claim_ids':rejected,'reasons':[x for v in verdicts for x in v['reasons']]}
    result=existing(packet,settings,batched)
    result['verification_version']='application-batched-contract-v1'
    return result
