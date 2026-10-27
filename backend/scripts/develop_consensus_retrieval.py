"""Keep listwise scores as a rank vote, never as an evidence availability gate.

Development regression only. The fixed RRF60 design consumes saved requests;
no new API calls, gold labels or reference answers enter ranking/context code.
"""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from rag.rank_fusion import fuse_rankings
from rag.context_graph import context_for
from scripts.evaluate_rag_improvements import save

OUT=ROOT/'output/research/rag_development/consensus'


def main():
    base=ROOT/'output/research/rag_development';source=base/'listwise'
    inputs=[p for p in sorted((source/'runs').glob('*.json'))]
    if len(inputs)!=100:raise ValueError('Incomplete saved listwise study')
    cases={c['id']:c['patient'] for c in json.loads((ROOT/'output/research/expanded100/cases.json').read_text())}
    graph=json.loads((base/'definition_context_graph.json').read_text())
    protocol={'stage':'development_only','final_evaluation':False,'rrf_k':60,'depths':[4,8],
        'design':'Equal RRF of upstream candidate order and validated listwise prefix; an empty prefix contributes no vote.',
        'safety':'Relevance ranking does not imply semantic support or eligibility. Audit and admission gates remain separate.',
        'definition_context_budget':4,'new_api_calls':0,
        'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'input_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        'graph_sha256':hashlib.sha256((base/'definition_context_graph.json').read_bytes()).hexdigest()}
    p=OUT/'development_protocol.json'
    if p.exists() and json.loads(p.read_text())!=protocol:raise ValueError('Consensus configuration drift')
    save(p,protocol)
    for p in inputs:
        r=json.loads(p.read_text());llm=r['selected_ids'] if r['available'] else []
        order=fuse_rankings([r['candidate_ids'],llm],60)
        ranks={str(k):order[:k] for k in [4,8]}
        contexts={k:[n['chunk_id'] for n in context_for(ids,graph,cases[r['id']])] for k,ids in ranks.items()}
        save(OUT/'runs'/p.name,{'id':r['id'],'guideline':r['guideline'],'family':r['family'],
            'stage':'development_only','rankings':ranks,'definition_context_ids':contexts,
            'available':r['available'],'listwise_empty':not llm,'candidate_ids':r['candidate_ids']})
    print('100 consensus development rankings saved; no final generation or new API calls.')


if __name__=='__main__':main()
