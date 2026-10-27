"""Freeze inputs and select a stratified ten-case development pilot without editing gold."""
import ast,csv,hashlib,json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/research/phase1_pilot'
SRC=Path.home()/'Downloads'

def rows(name):
    return list(csv.DictReader((SRC/name).open(encoding='utf-8-sig',newline='')))
def parsed(s):
    if not s:return []
    try:return json.loads(s)
    except json.JSONDecodeError:return ast.literal_eval(s)
def save(path,x):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(x,indent=2,ensure_ascii=True)+'\n',encoding='utf8')

def main():
    benchmark=json.loads((SRC/'neoguard_care_plan_eval_dataset_100.json').read_text(encoding='utf8'))
    cases=benchmark['cases'];retrieval=rows('retrieval_only_metrics (14).csv')
    generation=rows('generation_evaluation_dense_hybrid.csv');ma=rows('multi_agent_all_arms_results.csv')
    chunks=rows('chunks_ingested.csv');corpus={r['chunk_id']:r for r in chunks}
    counts={name:dict(Counter(r['arm'] for r in rs)) for name,rs in [('retrieval',retrieval),('generation',generation),('multiagent',ma)]}
    print(json.dumps({'arms':counts,'guidelines':dict(Counter(c['active_guideline'] for c in cases)),
        'generation_cases':[r['case_id'] for r in generation if r['arm']=='dense_only']},indent=2))
    eligible=[]
    for c in cases:
        cid=c['case_id']
        if sum(r['case_id']==cid for r in retrieval)==5 and sum(r['case_id']==cid for r in generation)==2 and sum(r['case_id']==cid for r in ma)==2:
            eligible.append(c)
    # Deterministic greedy coverage uses metadata only, never retrieval/generation scores.
    chosen=[];seen=set()
    quotas={'NICE':4,'WHO':3,'AAP':3}
    def tokens(c):
        return {('guideline',c['active_guideline']),('risk',c['risk_result']['category']),
            ('contraindication',str(c.get('contraindication_type'))),('trend',str(c.get('trend_type'))),
            ('ambiguous',str(c.get('ambiguous')))}
    def family(c):return 'AAP' if c['active_guideline'].startswith('AAP') else c['active_guideline']
    for _ in range(10):
        options=[c for c in eligible if c not in chosen and sum(family(x)==family(c) for x in chosen)<quotas[family(c)]]
        if not options:raise RuntimeError('Cannot satisfy the predeclared guideline quotas.')
        c=sorted(options,key=lambda c:(-sum((3 if k=='contraindication' else 2 if k in ['risk','trend'] else 1) for k,v in tokens(c)-seen),c['case_id']))[0]
        chosen.append(c);seen |= tokens(c)
    chosen.sort(key=lambda c:c['case_id']);ids={c['case_id'] for c in chosen}
    retrieval=[r for r in retrieval if r['case_id'] in ids]
    generation=[r for r in generation if r['case_id'] in ids];ma=[r for r in ma if r['case_id'] in ids]
    missing={i for r in retrieval for i in parsed(r['retrieved_chunk_ids'])[:10] if i not in corpus}
    missing_gold={i for c in chosen for i in c['gold_chunk_ids'] if i not in corpus}
    mismatches=[]
    canonical={c['case_id']:c for c in chosen}
    for kind,rs in [('retrieval',retrieval),('generation',generation),('multiagent',ma)]:
        for r in rs:
            old=parsed(r['gold_chunk_ids']) if 'gold_chunk_ids' in r else r['gold_chunk_ids_joined'].split(',')
            gold=canonical[r['case_id']]['gold_chunk_ids']
            if set(old)!=set(gold):mismatches.append({'file':kind,'case_id':r['case_id'],'arm':r['arm'],'historical_gold_n':len(old),'canonical_gold_n':len(gold),'overlap':len(set(old)&set(gold))})
    inputs=['neoguard_care_plan_eval_dataset_100.json','retrieval_only_metrics (14).csv',
        'generation_evaluation_dense_hybrid.csv','multi_agent_all_arms_results.csv','chunks_ingested.csv']
    manifest={'protocol':'Phase 1 pilot supplied 2026-10-25','analysis_role':'development pilot; historical generated outputs newly evaluated',
        'selection':'Deterministic greedy metadata coverage, case-ID tie-break; quotas NICE4 WHO3 AAP3; eligible only when all five retrieval and four generation/MA arms exist; no outcome scores used',
        'eligible_cases':len(eligible),'selected_case_ids':[c['case_id'] for c in chosen],
        'selected_metadata':[{'case_id':c['case_id'],'guideline':c['active_guideline'],'risk':c['risk_result']['category'],'contraindication':c['contraindication_type'],'trend':c['trend_type'],'ambiguous':c['ambiguous']} for c in chosen],
        'input_hashes':{n:hashlib.sha256((SRC/n).read_bytes()).hexdigest() for n in inputs},
        'corpus_file':'chunks_ingested.csv','corpus_rows':len(chunks),'duplicate_chunk_ids':len(chunks)-len(corpus),
        'missing_top10_chunk_ids':sorted(missing),'missing_gold_chunk_ids':sorted(missing_gold),
        'historical_gold_mismatches':mismatches,'gold_modified':False,
        'canonical_gold':'Original gold_chunk_ids and anchor_phrases in the supplied 100-case JSON',
        'reference_validity':'Template-authored reference; metadata attribution to clinician curation is unverified; old rule-score probabilities are not validated ML outputs',
        'strict_top_k':10,'expanded_context_in_exact_scores':False,
        'semantic_ndcg_ideal':'Ideal DCG over the judged union of top-10 chunks across all five arms, same case, truncated to 10; not corpus-wide recall',
        'missing_numeric_values':'NOT EVALUATED, never zero-imputed'}
    save(OUT/'manifest.json',manifest)
    save(OUT/'inputs.json',{'cases':chosen,'retrieval':retrieval,'generation':generation,'multiagent':ma,'corpus':corpus})
    print(json.dumps({'selected':manifest['selected_metadata'],'missing_chunks':len(missing),'missing_gold':len(missing_gold),'gold_mismatch_rows':len(mismatches)},indent=2))

if __name__=='__main__':main()
