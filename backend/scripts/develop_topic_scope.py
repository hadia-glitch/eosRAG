"""Topic-routing ablation on saved orders; no new model calls or case changes."""
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from rag.topic_scope import current_case_topic
from scripts.evaluate_rag_improvements import save
from scripts.summarize_faceted_development import scores
from scripts.summarize_expanded import ci

BASE=ROOT/'output/research/rag_development/recommendation_units'
OUT=BASE/'topic_scope'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def write(name,rows):
    with (OUT/name).open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    corpusfile=BASE/'corpus.json'
    corpus={c['chunk_id']:c for c in json.loads(corpusfile.read_text())['chunks']}
    # Relevance labels are read separately for scoring/conflict detection only.
    source=json.loads((ROOT/'output/research/expanded100/cases.json').read_text())
    cases={c['id']:{k:c[k] for k in ['id','query','patient','family']} for c in source}
    golds={c['id']:set(c['gold_chunk_ids']) for c in source}
    parents=['faceted','guarded_facets']
    protocol={'stage':'development_only','final_evaluation':False,'cases':100,'new_model_calls':0,
        'corpus_sha256':sha(corpusfile),'parent_protocols':{p:sha(BASE/p/'development_protocol.json') for p in parents},
        'code_sha256':{p:sha(ROOT/p) for p in ['backend/rag/topic_scope.py','backend/scripts/develop_topic_scope.py']},
        'design':'Keep each saved top-k order, remove task-mismatched source topics, refill from that method\'s saved depth-12 order; preserve all cases and golds. Both preceding selectors retained.',
        'clinical_review_status':'pending; topic exclusions are engineering proposals, not clinical severity judgments'}
    p=OUT/'development_protocol.json'
    if p.exists() and json.loads(p.read_text())!=protocol:raise ValueError('Topic-routing protocol drift')
    save(p,protocol)
    rows=[];audit=[];summaries=[];paired=[]
    for parent in parents:
        paths=list((BASE/parent/'runs').glob('*.json'))
        if len(paths)!=100:raise ValueError('Incomplete saved parent comparison')
        for path in paths:
            r=json.loads(path.read_text());c=cases[r['id']]
            decisions={cid:current_case_topic(chunk,c['query'],c['patient']) for cid,chunk in corpus.items() if chunk['guideline_id']==r['guideline']}
            conflicts=[cid for cid in golds[r['id']] if not decisions[cid][0]]
            if conflicts:raise ValueError('Topic/gold conflict requires adjudication; no labels changed: '+str(conflicts))
            for method,depths in r['rankings'].items():
                for k in [4,8]:
                    order=list(dict.fromkeys(depths[str(k)]+depths['12']))
                    selected=[cid for cid in order if decisions[cid][0]][:k]
                    for cid in order:
                        if not decisions[cid][0]:audit.append({'id':r['id'],'guideline':r['guideline'],'parent':parent,'method':method,'depth':k,'chunk_id':cid,'reason':decisions[cid][1],'text':corpus[cid]['raw_text'],'clinical_review':''})
                    for arm,ids in [('topic_scope',selected),('parent',depths[str(k)])]:
                        rows.append({'id':r['id'],'guideline':r['guideline'],'family':c['family'],'parent':parent,'method':method,'arm':arm,'depth':k,
                                     **scores(ids,golds[r['id']],k)})
    for g in ['NICE','AAP','WHO']:
        for parent in parents:
            for method in sorted({r['method'] for r in rows}):
                for k in [4,8]:
                    left=[r for r in rows if (r['guideline'],r['parent'],r['method'],r['arm'],r['depth'])==(g,parent,method,'topic_scope',k)]
                    right={r['id']:r for r in rows if (r['guideline'],r['parent'],r['method'],r['arm'],r['depth'])==(g,parent,method,'parent',k)}
                    for metric in ['recall','precision','mrr','ndcg','f1','returned_passages']:
                        summaries.append({'guideline':g,'parent':parent,'method':method,'depth':k,'metric':metric,'completed':len(left),'total':len(left),**ci([r[metric] for r in left],[r['family'] for r in left])})
                        paired.append({'guideline':g,'parent':parent,'method':method,'depth':k,'metric':metric,'contrast':'topic scope minus parent','paired_n':len(left),**ci([r[metric]-right[r['id']][metric] for r in left],[r['family'] for r in left])})
    write('per_case.csv',rows);write('intervals.csv',summaries);write('paired_differences.csv',paired)
    if audit:write('source_topic_review.csv',audit)
    save(OUT/'summary.json',{'stage':'development_only','final_evaluation':False,'complete':True,'cases':100,'new_model_calls':0,'gold_conflicts':0,'statistics':summaries,'paired':paired})
    for r in summaries:
        if r['depth']==4 and r['method']=='medical_faceted' and r['metric'] in ['recall','mrr']:
            print(r['guideline'],r['parent'],r['metric'],r['mean'])


if __name__=='__main__':main()
