"""Paired scoring of the saved consensus development intervention."""
import csv
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from scripts.summarize_faceted_development import scores
from scripts.summarize_expanded import ci
from scripts.evaluate_rag_improvements import save
from scripts.check_development_readiness import check

OUT=ROOT/'output/research/rag_development/consensus'


def write(name,rows):
    with (OUT/name).open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    data=ROOT/'output/research';cases={c['id']:c for c in json.loads((data/'expanded100/cases.json').read_text())}
    corpus={c['chunk_id']:c for c in json.loads((data/'rag_development/medcpt/corpus.json').read_text())['chunks']}
    graph={c['chunk_id']:c for c in json.loads((data/'rag_development/definition_context_graph.json').read_text())['nodes']}
    records=[json.loads(p.read_text()) for p in (OUT/'runs').glob('*.json')]
    if len(records)!=100:raise ValueError('Incomplete development consensus')
    rows=[];summary=[];paired=[]
    for r in records:
        old=json.loads((data/'rag_development/listwise/runs'/f'{r["id"]}.json').read_text())
        gold=set(cases[r['id']]['gold_chunk_ids'])
        for k in [4,8]:
            for m,ids in [('consensus',r['rankings'][str(k)]),('listwise',old['selected_ids'][:k]),('upstream_fusion',old['candidate_ids'][:k])]:
                context=r['definition_context_ids'][str(k)] if m=='consensus' else []
                rows.append({'id':r['id'],'guideline':r['guideline'],'family':r['family'],'method':m,'depth':k,
                    **scores(ids,gold,k),'source_words':sum(len(corpus[i]['raw_text'].split()) for i in ids),
                    'additional_definition_nodes':len(context),'additional_definition_words':sum(len(graph[i]['raw_text'].split()) for i in context)})
    evidence={'candidate':'consensus','retrieval':{},'generation':{},'safety':{},'config_pinned':True,
        'complete_audits':False,'scope_regressions_passed':False,'backend_regressions_passed':False}
    validation=data/'rag_development/validation_status.json'
    if validation.exists():
        v=json.loads(validation.read_text())
        pinned=v.get('tested_source_sha256',{})
        current=bool(pinned) and all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in pinned.items())
        passed=current and v.get('backend',{}).get('passed')==85 and v['backend'].get('failed')==0
        evidence['backend_regressions_passed']=passed
        evidence['scope_regressions_passed']=passed
        evidence['validation_artifact']='output/research/rag_development/validation_status.json'
    for g in ['NICE','AAP','WHO']:
        for m in ['consensus','listwise','upstream_fusion']:
            for k in [4,8]:
                selected=[r for r in rows if (r['guideline'],r['method'],r['depth'])==(g,m,k)]
                for metric in ['recall','precision','mrr','ndcg','f1','source_words','additional_definition_nodes','additional_definition_words']:
                    summary.append({'guideline':g,'method':m,'depth':k,'metric':metric,'completed':len(selected),'total':len(selected),
                                    **ci([r[metric] for r in selected],[r['family'] for r in selected])})
        for base in ['listwise','upstream_fusion']:
            for k in [4,8]:
                left=[r for r in rows if (r['guideline'],r['method'],r['depth'])==(g,'consensus',k)]
                right={r['id']:r for r in rows if (r['guideline'],r['method'],r['depth'])==(g,base,k)}
                for metric in ['recall','precision','mrr','ndcg']:
                    paired.append({'guideline':g,'contrast':'consensus minus '+base,'depth':k,'metric':metric,'paired_n':len(left),
                        **ci([r[metric]-right[r['id']][metric] for r in left],[r['family'] for r in left])})
        def avg(metric,k=4):return next(r['mean'] for r in summary if (r['guideline'],r['method'],r['depth'],r['metric'])==(g,'consensus',k,metric))
        evidence['retrieval'][g]={'recall_at_4':avg('recall'),'mrr_at_4':avg('mrr'),'complete':True}
        print(g,'Recall@4',avg('recall'),'MRR@4',avg('mrr'),'Recall@8',avg('recall',8))
    write('per_case.csv',rows);write('intervals.csv',summary);write('paired_differences.csv',paired)
    save(OUT/'summary.json',{'stage':'development_only','complete':True,'final_evaluation':False,'statistics':summary,'paired':paired})
    save(OUT/'readiness_evidence.json',evidence);save(OUT/'readiness_gate.json',check(evidence))


if __name__=='__main__':main()
