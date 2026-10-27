"""Checkpoint new-contract outputs separately; preserve all old results."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
from scripts.evaluate_expanded import Tracer
from scripts.evaluate_rag_improvements import OUT, OLD, save
from scripts.evaluation_transport import quality_eligible
from rag.verification_v2 import run_verification
from config import get_settings


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def execute(case, packet, folder, *, injected=None):
    path = folder/f'{case["id"]}.json'
    if path.exists() and quality_eligible(read(path)):
        return
    settings = get_settings().model_copy(update={'llm_provider':'groq','verifier_provider':'groq',
        'groq_model':'openai/gpt-oss-120b','verifier_model':'openai/gpt-oss-120b',
        'llm_schema_enforcement':True,'verification_max_repairs':0 if injected else 1,
        'verification_budget_seconds':120.})
    trace = Tracer(folder/'role_cache'/case['id'], settings.groq_model, gap=0, injected=injected)
    started = time.monotonic()
    result = run_verification(packet, settings, trace)
    record = {'id':case['id'],'family':case.get('family'), 'model':settings.groq_model,
              'packet':packet,'calls':trace.calls,'result':result,'seconds':time.monotonic()-started,
              'settings':{'strict_schema':True,'repairs':settings.verification_max_repairs,'budget':120,
                          'auditor_tokens':2400,'temperature':0},
              'code_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
                  'backend/rag/verification_v2.py','backend/rag/verification_graph.py']}}
    save(path, record)
    print(case['id'], result['status'], flush=True)
    if not quality_eligible(record):
        save(OUT/'pending_transport.json', {'id':case['id'],'stage':folder.name,
             'messages':[c.get('provider_message') for c in trace.calls if c.get('provider_message')],
             'codes':[c.get('error_code') for c in trace.calls if c.get('error_code')]})
        raise SystemExit(75)


def runs(limit):
    cases = read(OLD/'cases.json'); corpus = {c['chunk_id']:c for c in read(OLD/'corpus.json')['chunks']}
    # One per source/family first; remaining cases retain deterministic order.
    seen = set(); first = []; rest = []
    for c in cases:
        key = (c['gold_chunk_ids'][0].split('-')[0], c['family'])
        if key not in seen:
            first.append(c); seen.add(key)
        else:
            rest.append(c)
    for case in (first+rest)[:limit]:
        rank_path = OUT/'retrieval/sentence-transformers__all-MiniLM-L6-v2'/f'{case["id"]}.json'
        if not rank_path.exists():
            print('Retrieval not ready:',case['id'], flush=True)
            continue
        ranks = read(rank_path)
        selected = [corpus[i] for i in ranks['rankings']['expanded_rrf_ce_mmr']]
        packet = {'guideline':selected[0]['source']+'; EVALUATION ONLY', 'patient':case['patient'],
                  'history':case['history'],'evaluation_question':case['query'],
                  'evidence':[{'id':f'E{i+1}','text':c['text'],'chunk_id':c['chunk_id'],'source':c['source'],
                               'version':c['version'],'page_number':c['pdf_page']} for i,c in enumerate(selected)]}
        execute(case, packet, OUT/'runs')


def faults():
    for path in sorted((OLD/'stress').glob('*.json')):
        old = read(path)
        # Replay exactly the original injected fault and packet. Resolution is
        # disabled: silently rewriting a challenge would not demonstrate safety.
        execute(old, old['packet'], OUT/'stress', injected=old['result']['draft'])


def summarize():
    from collections import Counter
    report = {}
    for stage, planned in [('runs',100),('stress',36)]:
        records = [read(p) for p in (OUT/stage).glob('*.json')]
        eligible = [r for r in records if quality_eligible(r)]
        counts = Counter(r['result']['status'] for r in eligible)
        invalid = sum(any('invalid' in str(r['result'].get(v,{}).get('reasons',[])) or not r['result'].get(v,{}).get('checked_claim_ids')
                          for v in ['evidence_verdict','safety_verdict']) for r in eligible if r['result'].get('draft') and not r['result'].get('citation_errors'))
        report[stage] = {'quality_completed':len(eligible),'planned':planned,'statuses':dict(counts),
                         'invalid_or_incomplete_review_cases':invalid,
                         'provider_pending':len(records)-len(eligible),
                         'coverage':counts['supported_for_review']/planned}
    report['complete'] = all(report[s]['quality_completed']==n for s,n in [('runs',100),('stress',36)])
    report['interpretation'] = 'New system version on a development benchmark. Not a paired same-draft ablation; not clinical validation. Fault releases indicate a safety regression.'
    save(OUT/'verification_summary.json',report)
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--runs',action='store_true');p.add_argument('--faults',action='store_true');p.add_argument('--summary',action='store_true');p.add_argument('--limit',type=int,default=100)
    a=p.parse_args()
    if a.runs:runs(a.limit)
    if a.faults:faults()
    if a.summary:summarize()
