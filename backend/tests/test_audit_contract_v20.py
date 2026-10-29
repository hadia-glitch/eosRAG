import json
from config import Settings
from rag.audit_contract_v20 import audit_with_retry

def test_batches_are_bounded_and_every_claim_checked():
    observed=[]
    def llm(prompt,settings,**kw):
        p=json.loads(prompt);ids=[c['id']for c in p['claims']];observed.append(ids)
        return {'supported':True,'checked_claim_ids':ids,'rejected_claim_ids':[],'reasons':[]}
    ids={f'C{i}'for i in range(1,10)}
    prompt=json.dumps({'claims':[{'id':i,'evidence_ids':['E1']}for i in sorted(ids)],'evidence':[{'id':'E1','text':'fixture'}]})
    r=audit_with_retry(llm,prompt,Settings(_env_file=None),'audit',{},ids)
    assert r['supported']and set(r['checked_claim_ids'])==ids
    assert max(map(len,observed))<=4 and len(observed)==3

def test_failed_batch_cannot_approve_earlier_batches():
    def llm(prompt,settings,**kw):
        p=json.loads(prompt);ids=[c['id']for c in p['claims']]
        return {'supported':True,'checked_claim_ids':ids if 'C5'not in ids else [],'rejected_claim_ids':[],'reasons':[]}
    ids={f'C{i}'for i in range(1,6)}
    r=audit_with_retry(llm,json.dumps({'claims':[{'id':i}for i in sorted(ids)],'evidence':[]}),Settings(_env_file=None),'audit',{},ids)
    assert r['error_code']=='invalid_audit_contract'and not r['supported']
