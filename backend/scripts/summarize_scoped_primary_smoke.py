"""Descriptive case-level smoke scoring, not source-level performance inference."""
import csv
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from scripts.summarize_faceted_development import scores
from scripts.evaluate_rag_improvements import save

OUT=ROOT/'output/research/rag_development/recommendation_units/scoped_primary_smoke'


def main():
    protocol=json.loads((OUT/'development_protocol.json').read_text())
    records={p.stem:json.loads(p.read_text()) for p in (OUT/'runs').glob('*.json')}
    if set(records)!=set(protocol['case_ids']):raise SystemExit('Capped smoke incomplete; no quality zeros imputed')
    cases={c['id']:c for c in json.loads((ROOT/'output/research/expanded100/cases.json').read_text())}
    corpus={c['chunk_id']:c for c in json.loads((OUT.parent/'corpus.json').read_text())['chunks']}
    rows=[]
    for case_id in protocol['case_ids']:
        r=records[case_id];gold=set(cases[case_id]['gold_chunk_ids'])
        if not gold<=corpus.keys():raise ValueError('Missing corpus gold')
        for method,key in [('selected','selected_ids'),('consensus','consensus_ids'),('candidate_order','candidate_ids')]:
            for k in [4,8]:
                ranked=r[key][:k]
                rows.append({'id':case_id,'guideline':r['guideline'],'family':r['family'],'method':method,'depth':k,
                    'completed':1,'total':1,'selector_valid':r['available'],'gold_count':len(gold),
                    'gold_in_candidate_pool':len(gold&set(r['candidate_ids'])),
                    **scores(ranked,gold,k),'ranked_ids':'|'.join(ranked),'gold_ids':'|'.join(sorted(gold))})
    with (OUT/'per_case.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    save(OUT/'summary.json',{'stage':'development_only','final_evaluation':False,'completed':3,'total':3,
         'selector_valid':sum(r['available'] for r in records.values()),'maximum_unique_model_requests':3,
         'generation_or_auditor_calls':0,'statistics':rows,
         'limitations':'Three deliberately selected previously exposed difficult cases, one per source. No source-level inference, clinical-usability claim or final-evaluation permission. No meaningful sampling intervals inferred from one case per source.'})
    print('\n'.join(f"{r['id']} {r['method']} Recall@4={r['recall']:.6f} MRR@4={r['mrr']:.6f}" for r in rows if r['depth']==4))


if __name__=='__main__':main()
