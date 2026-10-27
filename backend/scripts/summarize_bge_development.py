"""Score all declared BGE development variants, including negative results."""
import csv
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from scripts.summarize_faceted_development import scores
from scripts.summarize_expanded import ci
from scripts.evaluate_rag_improvements import save

OUT=ROOT/'output/research/rag_development/bge_reranker'


def write(name,rows):
    with (OUT/name).open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    data=ROOT/'output/research';cases={c['id']:c for c in json.loads((data/'expanded100/cases.json').read_text())}
    corpus={c['chunk_id']:c for c in json.loads((data/'rag_development/medcpt/corpus.json').read_text())['chunks']}
    records=[json.loads(p.read_text()) for p in (OUT/'runs').glob('*.json')]
    if len(records)!=100:raise SystemExit('BGE development incomplete; no complete summary emitted')
    rows=[];summary=[];paired=[]
    methods=['bge_only','bge_upstream_rrf_mmr','bge_consensus_rrf_mmr','previous_consensus']
    for r in records:
        gold=set(cases[r['id']]['gold_chunk_ids']);ranks=dict(r['rankings'])
        ranks['previous_consensus']=json.loads((data/'rag_development/consensus/runs'/f'{r["id"]}.json').read_text())['rankings']
        for m,depths in ranks.items():
            for depth,ids in depths.items():
                k=int(depth)
                rows.append({'id':r['id'],'guideline':r['guideline'],'family':r['family'],'method':m,'depth':k,
                    **scores(ids,gold,k),'candidate_recall_ceiling':len(set(r['candidate_ids'])&gold)/len(gold),
                    'source_words':sum(len(corpus[i]['raw_text'].split()) for i in ids)})
    for g in ['NICE','AAP','WHO']:
        for m in methods:
            for k in [4,8]:
                rs=[r for r in rows if (r['guideline'],r['method'],r['depth'])==(g,m,k)]
                for metric in ['recall','precision','mrr','ndcg','f1','precision_ceiling','candidate_recall_ceiling','source_words']:
                    summary.append({'guideline':g,'method':m,'depth':k,'metric':metric,'completed':len(rs),'total':len(rs),
                        **ci([r[metric] for r in rs],[r['family'] for r in rs])})
        for m in methods[:-1]:
            for k in [4,8]:
                left=[r for r in rows if (r['guideline'],r['method'],r['depth'])==(g,m,k)]
                right={r['id']:r for r in rows if (r['guideline'],r['method'],r['depth'])==(g,'previous_consensus',k)}
                for metric in ['recall','precision','mrr','ndcg']:
                    paired.append({'guideline':g,'contrast':m+' minus previous_consensus','depth':k,'metric':metric,'paired_n':len(left),
                        **ci([r[metric]-right[r['id']][metric] for r in left],[r['family'] for r in left])})
    write('per_case.csv',rows);write('intervals.csv',summary);write('paired_differences.csv',paired)
    save(OUT/'summary.json',{'stage':'development_only','final_evaluation':False,'complete':True,'statistics':summary,'paired':paired})
    lines=['# Additional cross-encoder development ablation','',
        'Same exposed 100 synthetic cases and frozen candidate pools. All declared variants are retained. No new Groq calls or final evaluation.',
        '', '|Source|Method|Depth|Completed/total|Recall|MRR|Precision|nDCG|', '|---|---|---:|---:|---:|---:|---:|---:|']
    for g in ['NICE','AAP','WHO']:
        for m in methods:
            for k in [4,8]:
                rs=[r for r in rows if (r['guideline'],r['method'],r['depth'])==(g,m,k)]
                avg=lambda f:sum(r[f] for r in rs)/len(rs)
                lines.append(f'|{g}|{m}|{k}|{len(rs)}/{len(rs)}|{avg("recall"):.4f}|{avg("mrr"):.4f}|{avg("precision"):.4f}|{avg("ndcg"):.4f}|')
    lines+=['','Case and whole-family bootstrap intervals use 2,000 resamples, seed 31. Candidate recall ceilings, source-word budgets and negative paired effects remain in CSVs.',
        'These are relevance-ranking outcomes, not clinical answer-usability, safety, or effectiveness results. Model weights remain outside the repository.']
    (OUT/'results.md').write_text('\n'.join(lines)+'\n',encoding='utf8');print('\n'.join(lines))


if __name__=='__main__':main()
