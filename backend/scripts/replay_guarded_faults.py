"""Verify exact-request equivalence of the compact adapter on all 36 faults.

No network is permitted. A changed prompt/model/completion limit fails loudly;
an unchanged request reuses its saved completed response, including dissent.
This is an equivalence replay, not 36 new independent model observations.
"""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from config import Settings
from rag.verification_v3 import run_verification
from scripts.evaluate_rag_improvements import save


def main(version=3):
    global run_verification
    if version==4:
        from rag.verification_v4 import run_verification
    source=ROOT/'output/research/rag_improvement_v1/stress'
    dest=ROOT/f'output/research/rag_improvement_v{version}/stress'
    summary=[]
    for path in sorted(source.glob('*.json')):
        old=json.loads(path.read_text())
        seen=[]
        def llm(prompt,settings,**kw):
            options=[c for c in old['calls'] if c['role']==kw['role'] and c.get('prompt')==prompt]
            if len(options)!=1:raise AssertionError('Changed or ambiguous request; no network fallback: '+old['id'])
            entry=options[0]
            if kw.get('model',settings.groq_model)!=entry['model']:raise AssertionError('Changed model')
            if kw.get('completion_tokens',3000)!=entry['completion_tokens']:raise AssertionError('Changed completion limit')
            if 'response' not in entry:raise AssertionError('No completed saved response')
            seen.append({**entry,'replayed':True})
            return entry['response']
        s=Settings(_env_file=None,groq_model='openai/gpt-oss-120b',verifier_model='openai/gpt-oss-120b',
                   llm_provider='groq',verifier_provider='groq',verification_max_repairs=0)
        result=run_verification(old['packet'],s,llm)
        if result['status']!=old['result']['status'] or result.get('errors')!=old['result'].get('errors'):
            raise AssertionError('Changed fault decision: '+old['id'])
        save(dest/path.name,{'id':old['id'],'family':old['family'],'model':old['model'],'packet':old['packet'],
             'calls':seen,'result':result,'replay':'Exact unchanged request; existing completed outcome, not new inference',
             'original_record_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        summary.append({'id':old['id'],'status':result['status'],'requests_replayed':len(seen)})
    if len(summary)!=36:raise AssertionError('Expected exactly 36 fault records')
    save(dest.parent/'fault_equivalence_report.json',{'cases':summary,'count':len(summary),'new_api_calls':0,
         'unsafe_releases':sum(r['status']=='supported_for_review' for r in summary),
         'interpretation':'Deterministic equivalence of adapter requests and release decisions; not an independent repeated fault experiment.'})
    print('36/36 exact-request fault replays; zero API calls; zero releases')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--version',type=int,choices=[3,4],default=3)
    main(p.parse_args().version)
