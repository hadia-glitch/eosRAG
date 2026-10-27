"""Paired, family-aware uncertainty and honest completion/ceiling accounting."""
import collections
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from scripts.evaluate_rag_improvements import OUT, OLD, metrics, save, summarize
from scripts.summarize_expanded import ci


def write_csv(name, rows):
    if not rows:return
    with (OUT/name).open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    summarize()
    rows=list(csv.DictReader((OUT/'retrieval_per_case.csv').open(encoding='utf8')))
    numeric=list(metrics([],{'x'}))
    for r in rows:
        for k in numeric:r[k]=float(r[k])
    groups=collections.defaultdict(list)
    for r in rows:groups[(r['guideline'],r['model'],r['variant'])].append(r)
    summaries,paired=[],[]
    for (g,model,variant), group in sorted(groups.items()):
        for metric in numeric:
            summaries.append({'guideline':g,'model':model,'variant':variant,'metric':metric,'n':len(group),
                              **ci([r[metric] for r in group],[r['family'] for r in group])})
        if model=='historical_MiniLM':continue
        for baseline in ['hybrid','hybrid_concepts']:
            old={r['id']:r for r in groups[(g,'historical_MiniLM',baseline)]}
            for metric in numeric:
                paired.append({'guideline':g,'model':model,'variant':variant,'baseline':baseline,
                               'metric':metric,'paired_n':len(group),
                               **ci([r[metric]-old[r['id']][metric] for r in group],[r['family'] for r in group])})
    write_csv('retrieval_intervals.csv',summaries)
    write_csv('retrieval_paired_differences.csv',paired)
    cases=json.loads((OLD/'cases.json').read_text())
    ceiling=[]
    for g in ['NICE','AAP','WHO','ALL']:
        selected=[c for c in cases if g=='ALL' or c['gold_chunk_ids'][0].startswith(g)]
        ns=[len(c['gold_chunk_ids']) for c in selected]
        ceiling.append({'guideline':g,'n':len(ns),'gold_passages':sum(ns),'precision_at_4_ceiling':float(np.mean([min(n,4)/4 for n in ns])),
                        'recall_at_4_ceiling':float(np.mean([min(n,4)/n for n in ns])),
                        'f1_at_4_ceiling':float(np.mean([2*min(n,4)/(n+4) for n in ns])),
                        'mrr_at_4_ceiling':1.,'ndcg_at_4_ceiling':1.})
    write_csv('metric_ceilings.csv',ceiling)
    save(OUT/'metric_ceilings.json',ceiling)
    expected={'NICE':40,'AAP':30,'WHO':30}
    status=[{'guideline':g,'model':m,'variant':v,'completed':len(rs),'planned':expected[g]} for (g,m,v),rs in groups.items() if m!='historical_MiniLM']
    complete=len(status)==24 and all(r['completed']==r['planned'] for r in status)
    save(OUT/'retrieval_completion.json',{'complete':complete,'groups':status})
    print('Retrieval study complete:',complete)


if __name__=='__main__':
    import argparse
    from scripts import evaluate_rag_improvements as study
    p=argparse.ArgumentParser();p.add_argument('--version',type=int,choices=[1,2,3],default=1);a=p.parse_args()
    if a.version>=2:
        OUT=ROOT/f'output/research/rag_improvement_v{a.version}'
        OLD=ROOT/'output/research/rag_improvement_v2/inputs'
        study.OUT=OUT;study.OLD=OLD
    if a.version==3:
        def freeze():
            cfg=json.loads((OUT/'retrieval_protocol.json').read_text())
            for path,digest in cfg['code_sha256'].items():
                if study.sha(ROOT/path)!=digest:raise ValueError('Frozen pipeline drift: '+path)
            if study.sha(OLD/'cases.json')!=cfg['cases_sha256'] or study.sha(OLD/'corpus.json')!=cfg['corpus_sha256']:
                raise ValueError('Frozen input drift')
            return cfg
        study.freeze=freeze
    main()
