"""Source-stratified development metrics at four and eight passages."""
import argparse
import csv
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from scripts.summarize_faceted_development import scores
from scripts.summarize_expanded import ci
from scripts.evaluate_rag_improvements import save

OUT=ROOT/'output/research/rag_development/semantic_guidance'


def write(name,rows):
    if not rows:return
    with (OUT/name).open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main(partial=False,study='semantic_guidance'):
    global OUT
    OUT=ROOT/'output/research/rag_development'/study
    base=ROOT/'output/research/rag_development'
    cases={c['id']:c for c in json.loads((ROOT/'output/research/expanded100/cases.json').read_text())}
    corpus={c['chunk_id']:c for c in json.loads((base/'recommendation_units/corpus.json').read_text())['chunks']}
    graph={n['chunk_id']:n for n in json.loads((base/'definition_context_graph.json').read_text())['nodes']}
    records=[json.loads(p.read_text()) for p in sorted((OUT/'runs').glob('*.json'))]
    if len(records)!=100 and not partial:raise SystemExit('Development run incomplete; no complete scores emitted')
    baseline={}
    with (base/'recommendation_units/topic_scope/per_case.csv').open(encoding='utf8') as f:
        for r in csv.DictReader(f):
            if (r['parent'],r['method'],r['arm'])==('guarded_facets','medical_faceted','topic_scope'):
                baseline[(r['id'],int(r['depth']))]=r
    rows=[];summary=[];paired=[]
    methods=json.loads((OUT/'development_protocol.json').read_text())['methods']
    control=methods[0]
    for r in records:
        gold=set(cases[r['id']]['gold_chunk_ids'])
        if not gold<=corpus.keys():raise ValueError('Gold ID absent from corpus')
        for method in methods:
            for depth in [4,8]:
                ids=r['rankings'][method][str(depth)]
                texts={corpus[i]['text_sha256'] for i in ids}
                context=[]
                if method=='ce_definition_graph' or study=='structured_context':
                    for cid in ids:
                        for nid in r['definition_context_ids'][cid]:
                            n=graph[nid]
                            if n['text_sha256'] not in texts:
                                context.append(nid);texts.add(n['text_sha256'])
                rows.append({'id':r['id'],'guideline':r['guideline'],'family':r['family'],'method':method,
                    'depth':depth,**scores(ids,gold,depth),'candidate_count':r['eligible_candidates'],
                    'source_words':sum(len(corpus[i]['raw_text'].split()) for i in ids),
                    'additional_definition_nodes':len(context),'additional_definition_words':sum(len(graph[i]['raw_text'].split()) for i in context),
                    'ranked_ids':'|'.join(ids),'gold_ids':'|'.join(sorted(gold))})
    for g,total in [('NICE',40),('AAP',30),('WHO',30)]:
        for method in methods:
            for depth in [4,8]:
                selected=[r for r in rows if (r['guideline'],r['method'],r['depth'])==(g,method,depth)]
                if not selected:continue
                for metric in ['recall','precision','mrr','ndcg','f1','precision_ceiling','source_words','additional_definition_nodes','additional_definition_words']:
                    summary.append({'guideline':g,'method':method,'depth':depth,'metric':metric,'completed':len(selected),'total':total,
                                    **ci([r[metric] for r in selected],[r['family'] for r in selected])})
                for metric in ['recall','precision','mrr','ndcg','f1']:
                    paired.append({'guideline':g,'method':method,'depth':depth,'metric':metric,
                        'contrast':'new method minus prior medical-faceted topic scope','paired_n':len(selected),
                        **ci([r[metric]-float(baseline[(r['id'],depth)][metric]) for r in selected],[r['family'] for r in selected])})
                controls=[] if method==control else [control]
                if method=='longitudinal_context_graph':controls.append('qualifier_graph')
                for baseline_method in controls:
                    comp={r['id']:r for r in rows if (r['guideline'],r['method'],r['depth'])==(g,baseline_method,depth)}
                    for metric in ['recall','precision','mrr','ndcg']:
                        paired.append({'guideline':g,'method':method,'depth':depth,'metric':metric,
                            'contrast':method+' minus '+baseline_method,'paired_n':len(selected),
                            **ci([r[metric]-comp[r['id']][metric] for r in selected],[r['family'] for r in selected])})
    prefix='partial_' if len(records)!=100 else ''
    write(prefix+'per_case.csv',rows);write(prefix+'intervals.csv',summary);write(prefix+'paired_differences.csv',paired)
    save(OUT/(prefix+'summary.json'),{'stage':'development_only','final_evaluation':False,'complete':len(records)==100,
         'completed':len(records),'total':100,'statistics':summary,'paired':paired,
         'new_groq_calls':0,'additional_definition_context':'Explicitly counted; not a hidden top-k passage or clinical finding'})
    lines=['# Source-context retrieval development','',f'Study: {study}. Completed {len(records)}/100 previously examined synthetic cases. No final evaluation or clinical validation.',
           '', '|Source|Method|Depth|Complete / N|Recall|Precision|MRR|nDCG|', '|---|---|---:|---:|---:|---:|---:|---:|']
    for g,total in [('NICE',40),('AAP',30),('WHO',30)]:
        for method in methods:
            for depth in [4,8]:
                selected=[r for r in rows if (r['guideline'],r['method'],r['depth'])==(g,method,depth)]
                if not selected:continue
                avg=lambda m:sum(r[m] for r in selected)/len(selected)
                lines.append(f'|{g}|{method}|{depth}|{len(selected)}/{total}|{avg("recall"):.6f}|{avg("precision"):.6f}|{avg("mrr"):.6f}|{avg("ndcg"):.6f}|')
    lines+=['','All case-level and scenario-family bootstrap intervals use 2,000 resamples, seed 31. Cases, golds and RRF offset 60 are unchanged. Negative outcomes are retained. Definition context word/node budgets are in the CSVs. Clinical source/genre review remains pending.']
    (OUT/(prefix+'results.md')).write_text('\n'.join(lines)+'\n',encoding='utf8')
    print('\n'.join(lines),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--partial',action='store_true');parser.add_argument('--study',choices=['semantic_guidance','structured_context'],default='semantic_guidance');args=parser.parse_args();main(args.partial,args.study)
