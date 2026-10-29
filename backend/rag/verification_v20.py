"""Bounded section-coverage proposals; all proposals require both source audits."""
import json,re
import numpy as np
from rank_bm25 import BM25Plus
from rag.section_evidence_v20 import TOPICS
from rag.verification_core_v20 import run_verification as run_core
from services.groq_client import complete_json

REQUIRED={'recommended_actions','investigations','antibiotic_review','monitoring_plan','escalation_criteria'}

def propose(raw,packet):
    if not isinstance(raw,dict) or set(raw)!={'claims'} or not isinstance(raw['claims'],list):return raw,[]
    # Existing malformed/non-empty claims are left for strict per-claim validation.
    present=set()  # Propose one independent source per core topic; audits decide relevance.
    eligible=[e for e in packet['evidence'] if e.get('kind')!='supplemental_publisher_definition']
    if not eligible:return raw,[]
    tokenize=lambda s:re.findall(r'\w+',s.lower())
    bm=BM25Plus([tokenize(e['text']) for e in eligible])
    claims=list(raw['claims']);trace=[]
    used={c.get('id') for c in claims if isinstance(c,dict)}
    for section in sorted(REQUIRED-present):
        scores=bm.get_scores(tokenize(TOPICS[section]));i=int(np.argmax(scores))
        if scores[i]<=0:continue
        # Replace only an explicit empty row for this topic; never replace approved content.
        claims=[c for c in claims if not(isinstance(c,dict) and c.get('section')==section and c.get('support')==[])]
        free=next((f'C{k}' for k in range(1,17)if f'C{k}'not in used),None)
        if free is None or len(claims)>=16:continue
        e=eligible[i]
        if any(isinstance(c,dict) and c.get('section')==section and c.get('support')==[{'quote_id':e['id']+'Q1'}] for c in claims):continue
        claims.append({'id':free,'section':section,'support':[{'quote_id':e['id']+'Q1'}]});used.add(free)
        trace.append({'section':section,'evidence_id':e['id'],'selection':'fixed-query BM25 proposal; requires both audits','score':float(scores[i])})
    return {'claims':claims},trace

def run_verification(packet,settings,llm=complete_json):
    trace=[]
    def proposing(prompt,settings,**kw):
        raw=llm(prompt,settings,**kw)
        if 'synthesis' in kw.get('role',''):
            raw,added=propose(raw,packet);trace.extend(added)
        return raw
    result=run_core(packet,settings,proposing)
    result['section_coverage_proposals']=trace
    result['verification_version']='audited-section-coverage-proposals-v20-research'
    return result
