"""Source-stratified budget curves and paired uncertainty for development."""
import argparse
import csv
import json
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
OUT=ROOT/'output/research/rag_development/faceted'
from scripts.summarize_expanded import ci
from scripts.evaluate_rag_improvements import save


def scores(ids,gold,k):
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate ranking IDs')
    hits=[int(i in gold) for i in ids[:k]]
    count=sum(hits);g=len(gold)
    return {'recall':count/g,'precision':count/k,'f1':2*count/(g+k),
        'mrr':next((1/(r+1) for r,h in enumerate(hits) if h),0.),
        'ndcg':float(sum(h/np.log2(r+2) for r,h in enumerate(hits))/sum(1/np.log2(r+2) for r in range(min(g,k)))),
        'precision_ceiling':min(g,k)/k,'recall_ceiling':min(g,k)/g,'returned_passages':len(ids[:k])}


def write(name,rows):
    if not rows:return
    with (OUT/name).open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main(partial):
    cases={c['id']:c for c in json.loads((ROOT/'output/research/expanded100/cases.json').read_text())}
    records=[json.loads(p.read_text()) for p in (OUT/'runs').glob('*.json')]
    if len(records)!=100 and not partial:raise SystemExit('Development retrieval incomplete; no complete summary emitted')
    corpus={c['chunk_id']:c for c in json.loads((ROOT/'output/research/rag_development/medcpt/corpus.json').read_text())['chunks']}
    rows=[]
    for r in records:
        c=cases[r['id']]
        for method,depths in r['rankings'].items():
            for depth,ids in depths.items():
                k=int(depth)
                rows.append({'id':r['id'],'guideline':r['guideline'],'family':r['family'],'method':method,'depth':k,
                    **scores(ids,set(c['gold_chunk_ids']),k),
                    'source_words':sum(len(corpus[i]['raw_text'].split()) for i in ids[:k])})
    groups={}
    for r in rows:groups.setdefault((r['guideline'],r['method'],r['depth']),[]).append(r)
    summary=[];paired=[]
    for (g,m,k),rs in sorted(groups.items()):
        for metric in ['recall','precision','f1','mrr','ndcg','precision_ceiling','recall_ceiling','returned_passages','source_words']:
            summary.append({'guideline':g,'method':m,'depth':k,'metric':metric,'n':len(rs),
                            **ci([r[metric] for r in rs],[r['family'] for r in rs])})
    contrasts=[('generic_faceted','generic_single'),('medical_faceted','medical_single'),('medical_faceted_graph','medical_faceted')]
    for g in ['NICE','AAP','WHO']:
        for left,right in contrasts:
            for k in [4,8]:
                a=groups.get((g,left,k),[]);b={r['id']:r for r in groups.get((g,right,k),[])}
                for metric in ['recall','precision','mrr','ndcg']:
                    paired.append({'guideline':g,'contrast':left+' minus '+right,'depth':k,'metric':metric,'paired_n':len(a),
                                   **ci([r[metric]-b[r['id']][metric] for r in a],[r['family'] for r in a])})
        for method in ['generic_faceted','medical_faceted_graph']:
            a=groups.get((g,method,8),[]);b={r['id']:r for r in groups.get((g,method,4),[])}
            for metric in ['recall','precision','mrr','ndcg','source_words']:
                paired.append({'guideline':g,'contrast':method+' depth 8 minus depth 4','depth':8,'metric':metric,'paired_n':len(a),
                               **ci([r[metric]-b[r['id']][metric] for r in a],[r['family'] for r in a])})
    prefix='partial_' if len(records)!=100 else ''
    write(prefix+'per_case.csv',rows);write(prefix+'intervals.csv',summary);write(prefix+'paired_differences.csv',paired)
    save(OUT/(prefix+'summary.json'),{'stage':'development_only','final_evaluation':False,'complete':len(records)==100,
          'completed_cases':len(records),'planned_cases':100,'statistics':summary,'paired':paired})
    lines=['# Faceted guidance retrieval: development results','',
        'Final evaluation remains on hold. Cases and gold IDs are unchanged. Results reuse a previously examined synthetic benchmark.',
        '', '|Source|Method|Depth|N|Recall|Precision (ceiling)|MRR|nDCG|Mean source words|',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for (g,m,k),rs in sorted(groups.items()):
        if k not in [4,8]:continue
        avg=lambda field:float(np.mean([r[field] for r in rs]))
        lines.append(f"|{g}|{m}|{k}|{len(rs)}|{avg('recall'):.4f}|{avg('precision'):.4f} ({avg('precision_ceiling'):.4f})|{avg('mrr'):.4f}|{avg('ndcg'):.4f}|{avg('source_words'):.1f}|")
    lines+=['','All five methods and all six depths are retained in the CSVs. Case and whole-family intervals use 2,000 resamples and seed 31. Repeated query templates limit independence.',
        '','Larger evidence budgets trade precision and context size for recall. A small WHO recommendation pool makes high-depth recall easier; these results are not directly comparable to a large mixed background index without disclosing that change.',
        '','Source roles come from publisher structure, not gold labels. Background evidence remains indexed separately. Technical scope extraction and engineering references still require clinician adjudication. No clinical usability or safety claim follows from retrieval overlap alone.']
    (OUT/(prefix+'results.md')).write_text('\n'.join(lines)+'\n',encoding='utf8')
    print('\n'.join(lines),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--partial',action='store_true');a=p.parse_args();main(a.partial)
