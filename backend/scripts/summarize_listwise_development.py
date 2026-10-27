"""Score completed development reranking without sending labels to a model."""
import csv
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from scripts.summarize_expanded import ci
from scripts.summarize_faceted_development import scores
from scripts.evaluate_rag_improvements import save
from scripts.check_development_readiness import check

OUT=ROOT/'output/research/rag_development/listwise'


def write(name,rows):
    if not rows:return
    with (OUT/name).open('w',newline='',encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    cases={c['id']:c for c in json.loads((ROOT/'output/research/expanded100/cases.json').read_text())}
    records=[json.loads(p.read_text()) for p in (OUT/'runs').glob('*.json')]
    if len(records)!=100:raise SystemExit('Incomplete development study; no complete results emitted')
    corpus={c['chunk_id']:c for c in json.loads((ROOT/'output/research/rag_development/medcpt/corpus.json').read_text())['chunks']}
    rows=[];aggregated=[];paired=[];coverage=[]
    for r in records:
        gold=set(cases[r['id']]['gold_chunk_ids'])
        for method,ids in [('upstream_fusion',r['baseline_ids']),('listwise',r['selected_ids'])]:
            for k in [4,8]:
                rows.append({'id':r['id'],'guideline':r['guideline'],'family':r['family'],
                    'method':method,'depth':k,'selection_available':r['available'],
                    'candidate_recall_ceiling':len(set(r['candidate_ids'])&gold)/len(gold),
                    **scores(ids,gold,k),'source_words':sum(len(corpus[i]['raw_text'].split()) for i in ids[:k])})
    for source in ['NICE','AAP','WHO']:
        source_records=[r for r in records if r['guideline']==source]
        coverage.append({'guideline':source,'completed':len(source_records),'total':len(source_records),
            'valid_selection':sum(r['available'] for r in source_records),
            'empty_selection':sum(not r['selected_ids'] for r in source_records),
            'unique_model_requests':len({r['request_key'] for r in source_records})})
        for method in ['upstream_fusion','listwise']:
            for k in [4,8]:
                selected=[r for r in rows if (r['guideline'],r['method'],r['depth'])==(source,method,k)]
                for metric in ['recall','precision','mrr','ndcg','f1','precision_ceiling',
                               'candidate_recall_ceiling','source_words','returned_passages']:
                    aggregated.append({'guideline':source,'method':method,'depth':k,'metric':metric,
                        'completed':len(selected),'total':len(source_records),
                        **ci([r[metric] for r in selected],[r['family'] for r in selected])})
        for k in [4,8]:
            left=[r for r in rows if (r['guideline'],r['method'],r['depth'])==(source,'listwise',k)]
            right={r['id']:r for r in rows if (r['guideline'],r['method'],r['depth'])==(source,'upstream_fusion',k)}
            for metric in ['recall','precision','mrr','ndcg','f1']:
                paired.append({'guideline':source,'contrast':'listwise minus upstream_fusion','depth':k,'metric':metric,
                    'paired_n':len(left),**ci([r[metric]-right[r['id']][metric] for r in left],[r['family'] for r in left])})
    write('per_case.csv',rows);write('intervals.csv',aggregated);write('paired_differences.csv',paired);write('coverage.csv',coverage)
    save(OUT/'summary.json',{'stage':'development_only','final_evaluation':False,'complete':True,
         'statistics':aggregated,'paired_differences':paired,'coverage':coverage})
    evidence={'candidate':'bounded listwise selection','stage':'development_only','retrieval':{},'generation':{},
              'config_pinned':True,'complete_audits':False,'scope_regressions_passed':False,
              'backend_regressions_passed':False,'safety':{},
              'note':'Passage ranking is not a clinical answer. Generation coverage/usability and current fault audits remain unmeasured.'}
    lines=['# Bounded listwise reranking: development results','',
        'All 100 previously exposed synthetic cases are retained. This is development, not final evaluation or clinical validation.',
        'Gold identifiers and engineering reference answers enter this scoring script only; they never enter ranking prompts.',
        '', '|Source|Method|Depth|Completed/total|Recall|MRR|Precision (ceiling)|nDCG|Mean source words|',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    def avg(g,m,k,metric):return next(r['mean'] for r in aggregated if (r['guideline'],r['method'],r['depth'],r['metric'])==(g,m,k,metric))
    for g in ['NICE','AAP','WHO']:
        for m in ['upstream_fusion','listwise']:
            for k in [4,8]:
                n=next(r['total'] for r in coverage if r['guideline']==g)
                lines.append(f'|{g}|{m}|{k}|{n}/{n}|{avg(g,m,k,"recall"):.4f}|{avg(g,m,k,"mrr"):.4f}|'
                    f'{avg(g,m,k,"precision"):.4f} ({avg(g,m,k,"precision_ceiling"):.4f})|{avg(g,m,k,"ndcg"):.4f}|{avg(g,m,k,"source_words"):.1f}|')
        evidence['retrieval'][g]={'complete':True,'recall_at_4':avg(g,'listwise',4,'recall'),'mrr_at_4':avg(g,'listwise',4,'mrr')}
    lines+=['','Both case-level and whole-scenario-family bootstrap intervals (2,000 resamples, seed 31) and all paired changes are in CSVs.',
        'The selection-validity counts are in coverage.csv. No provider-blocked case is imputed as an answer failure. Completed malformed model outputs remain failures.',
        'The candidate-recall ceiling is the fraction of annotated gold passages present in the fixed upstream pool, not a theoretical ceiling for all retrieval.',
        'WHO has a small guidance pool. The language model also adds latency and shares a backbone with existing answer experiments; independent clinical assessment remains necessary.',
        'No answer generation, fault regression or usability result is inferred from these retrieval scores. The final evaluation stays on hold.']
    save(OUT/'readiness_evidence.json',evidence);save(OUT/'readiness_gate.json',check(evidence))
    (OUT/'results.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print('\n'.join(lines))


if __name__=='__main__':main()
