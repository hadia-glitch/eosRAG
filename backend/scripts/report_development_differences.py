"""Retain historical values and paired changes without replacing frozen results."""
import csv
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from scripts.summarize_expanded import ci
from scripts.evaluate_rag_improvements import save
from scripts.summarize_faceted_development import scores
from rag.context_graph import build_context_graph


def main():
    base=ROOT/'output/research';out=base/'rag_development'
    cases={c['id']:c for c in json.loads((base/'expanded100/cases.json').read_text())}
    old={r['id']:r for r in json.loads((base/'expanded100/retrieval.json').read_text())['cases']}
    records=[json.loads(p.read_text()) for p in (out/'faceted/runs').glob('*.json')]
    if len(records)!=100:raise ValueError('Incomplete development retrieval')
    differences=[]
    for source in ['NICE','AAP','WHO']:
        rs=[r for r in records if r['guideline']==source]
        for metric,oldkey in [('recall','recall_at_4'),('mrr','mrr_at_4')]:
            historical=[];current=[]
            for r in rs:
                gold=set(cases[r['id']]['gold_chunk_ids'])
                historical.append(scores(old[r['id']]['rankings']['hybrid'],gold,4)[metric])
                current.append(scores(r['rankings']['medical_faceted']['4'],gold,4)[metric])
            deltas=[a-b for a,b in zip(current,historical)]
            differences.append({'guideline':source,'metric':oldkey,'old_paper_method':'frozen hybrid',
                'new_method':'development medical_faceted','depth':4,'paired_n':len(rs),
                'old_paper_value':sum(historical)/len(rs),'new_value':sum(current)/len(rs),
                **ci(deltas,[r['family'] for r in rs]),
                'interpretation':'Combined index/model/query changes on exposed cases; not an isolated causal component effect.'})
    with (out/'paper_retrieval_differences.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(differences[0]));w.writeheader();w.writerows(differences)
    corpus=json.loads((out/'medcpt/corpus.json').read_text())['chunks']
    graph=build_context_graph(corpus)
    source={c['chunk_id']:c for c in corpus}
    for n in graph['nodes']:
        parent=source[n['parent_chunk_id']];span=n['source_span']
        if n['raw_text']!=parent['raw_text'][span['start']:span['end']]:raise ValueError('Non-exact graph text')
        if hashlib.sha256(n['raw_text'].encode()).hexdigest()!=n['text_sha256']:raise ValueError('Graph text hash drift')
    save(out/'definition_context_graph.json',graph)
    save(out/'definition_context_audit.json',{'nodes':len(graph['nodes']),'edges':len(graph['edges']),
         'all_text_exact_source_spans':True,'clinical_review':'pending',
         'ranking_effect_measured':False,'final_evaluation':False})
    print(json.dumps({'paired_changes':differences,'graph_definition_nodes':len(graph['nodes']),
                     'graph_definition_edges':len(graph['edges'])},indent=2))


if __name__=='__main__':main()
