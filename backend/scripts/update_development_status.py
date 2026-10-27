"""Build readiness evidence from measured artifacts; never infer usability."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from scripts.check_development_readiness import check
from scripts.evaluate_rag_improvements import metrics,save


def main(candidate):
    base=ROOT/'output/research'
    cases={c['id']:c for c in json.loads((base/'expanded100/cases.json').read_text())}
    folder=base/('rag_development/medcpt' if candidate=='medcpt' else 'rag_improvement_v3')
    method='hybrid_medcpt_graph_ce_mmr' if candidate=='medcpt' else 'rrf_ce_mmr_guarded'
    runfolder=folder/'runs' if candidate=='medcpt' else folder/'retrieval/sentence-transformers__all-MiniLM-L6-v2'
    grouped={g:[] for g in ['NICE','AAP','WHO']}
    for path in runfolder.glob('*.json'):
        r=json.loads(path.read_text())
        if method not in r.get('rankings',{}):continue
        grouped[r['guideline']].append(metrics(r['rankings'][method],set(cases[r['id']]['gold_chunk_ids'])))
    report={'candidate':candidate,'stage':'development_only','retrieval':{},'generation':{},
            'complete_audits':False,'scope_regressions_passed':False,'backend_regressions_passed':False,
            'config_pinned':(folder/('development_protocol.json' if candidate=='medcpt' else 'retrieval_protocol.json')).exists(),
            'clinical_validation':'pending; never established by synthetic metrics',
            'generation_note':'Release status alone does not establish task completeness or usability. A balanced six-family, three-source development pilot is still required.'}
    planned={'NICE':40,'AAP':30,'WHO':30}
    for g,rows in grouped.items():
        report['retrieval'][g]={'complete':len(rows)==planned[g],'n':len(rows),'planned':planned[g],
            **({m:float(np.mean([r[m] for r in rows])) for m in rows[0]} if rows else {})}
    fault=base/'rag_improvement_v3/fault_equivalence_report.json'
    if fault.exists():
        f=json.loads(fault.read_text());report['safety']={'fault_cases_completed':f['count'],'unsafe_fault_releases':f['unsafe_releases'],
            'evidence_type':'Exact-request replay of 36 saved model outcomes, not an independent repeated clinical test'}
    else:report['safety']={}
    out=base/'rag_development'
    save(out/f'{candidate}_readiness_evidence.json',report)
    result=check(report)
    save(out/f'{candidate}_readiness_gate.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',choices=['generic','medcpt'],default='generic')
    main(p.parse_args().candidate)
