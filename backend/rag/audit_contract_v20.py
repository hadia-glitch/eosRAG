"""Bounded, schema-checked claim audits. Never retry quota/auth failures."""
import json
from rag.verification_graph import Verdict
from rag.output_contracts import constrained_schema
from services.groq_client import GenerationUnavailable


def audit_one(llm, prompt, settings, role, options, expected, attempts=2):
    failures=[]
    for attempt in range(attempts):
        try:
            payload=json.loads(prompt)
            payload['output_schema']=Verdict.model_json_schema()
            payload['required_checked_claim_ids']=sorted(expected)
            payload['response_contract']='Check every claim exactly once. Reject unknown IDs, duplicate IDs and contradictory verdicts. reasons explain rejected claims only. supported=false requires at least one rejected claim. Never assume missing patient information is normal.'
            if failures:payload['previous_contract_error']=failures[-1]
            response=llm(json.dumps(payload,ensure_ascii=False,separators=(',',':')),settings,role=role,
                **{**options,'response_schema':constrained_schema(Verdict,claim_ids=expected)})
            v=Verdict.model_validate(response)
            checked=v.checked_claim_ids;bad=v.rejected_claim_ids
            if (set(checked)!=expected or len(checked)!=len(expected) or len(bad)!=len(set(bad))
                or not set(bad)<=expected or (v.supported and (bad or v.reasons))
                or (not v.supported and (not bad or not v.reasons))):
                raise ValueError('Incomplete, duplicate or contradictory audit')
            return {**v.model_dump(),'attempts':attempt+1,'contract_failures':failures}
        except GenerationUnavailable as exc:
            failures.append(exc.code)
            if exc.code not in {'http_500','http_502','http_503','http_504','ReadTimeout','ConnectTimeout','JSONDecodeError','finish_reason_length'} or attempt+1==attempts:
                return {'supported':False,'checked_claim_ids':[],'rejected_claim_ids':[],
                    'reasons':['Audit transport did not complete; no claim is approved'],'error_code':exc.code,'attempts':attempt+1,'contract_failures':failures}
        except (ValueError,TypeError,KeyError):
            failures.append('invalid_audit_contract')
    return {'supported':False,'checked_claim_ids':[],'rejected_claim_ids':[],
        'reasons':['Audit contract remained invalid after bounded retry'],'error_code':'invalid_audit_contract',
        'attempts':attempts,'contract_failures':failures}


def approved_claims(state):
    """Partial approval requires both auditors to have checked the entire draft."""
    claims=state.get('draft',{}).get('claims',[]);ids={c['id'] for c in claims}
    if not ids or len(ids)!=len(claims) or state.get('citation_errors'):return []
    rejected=set()
    for key in ['evidence_verdict','safety_verdict']:
        v=state.get(key,{})
        if v.get('error_code') or set(v.get('checked_claim_ids',[]))!=ids or len(v.get('checked_claim_ids',[]))!=len(ids):return []
        bad=v.get('rejected_claim_ids',[])
        if len(bad)!=len(set(bad)) or not set(bad)<=ids:return []
        if (v.get('supported') and (bad or v.get('reasons'))) or (not v.get('supported') and (not bad or not v.get('reasons'))):return []
        rejected.update(bad)
    return [c for c in claims if c['id'] not in rejected]


def audit_with_retry(llm,prompt,settings,role,options,expected,attempts=2):
    """At most four claims per audit; every batch must validate before release."""
    payload=json.loads(prompt);ids=sorted(expected);results=[]
    for start in range(0,len(ids),4):
        group=set(ids[start:start+4]);part=dict(payload)
        part['claims']=[c for c in payload['claims'] if c['id']in group]
        evidence_ids={eid for c in part['claims'] for eid in c.get('evidence_ids',[])}
        part['evidence']=[e for e in payload.get('evidence',[]) if e['id']in evidence_ids]
        part['conciseness']='Return at most four brief rejection reasons, one per rejected claim; do not repeat source text. Evaluate only the supplied narrow source-reference purpose. Patient criterion states are supplied separately.'
        v=audit_one(llm,json.dumps(part,ensure_ascii=False),settings,role,options,group,attempts)
        results.append(v)
        if v.get('error_code'):
            return {**v,'batches':results,'batch_size':4}
    rejected=[i for v in results for i in v['rejected_claim_ids']]
    return {'supported':not rejected,'checked_claim_ids':ids,'rejected_claim_ids':rejected,
            'reasons':[s for v in results for s in v['reasons']], 'batches':results,'batch_size':4}
