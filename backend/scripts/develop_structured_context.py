"""Source hierarchy, qualifier-graph and longitudinal-context development ablation."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from rag.guidance_lanes import guidance_role
from rag.rank_fusion import fuse_rankings
from rag.workflow_context_graph import admission,build_graph,select_context
from scripts.evaluate_rag_improvements import save

BASE=ROOT/'output/research/rag_development'
OUT=BASE/'structured_context'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    source=BASE/'recommendation_units/corpus.json'
    chunks=[c for c in json.loads(source.read_text())['chunks'] if guidance_role(c)]
    corpus={c['chunk_id']:c for c in chunks}
    graph=build_graph(chunks)
    save(OUT/'workflow_context_graph.json',graph)
    data=json.loads((ROOT/'output/research/expanded100/cases.json').read_text())
    cases={c['id']:{k:c[k] for k in ['id','query','patient','history']} for c in data}
    golds={c['id']:set(c['gold_chunk_ids']) for c in data}
    parents=sorted((BASE/'semantic_guidance/runs').glob('*.json'))
    if len(parents)!=100:raise ValueError('Parent comparison incomplete')
    protocol={'stage':'development_only','final_evaluation':False,'cases':100,'new_model_calls':0,
        'corpus_sha256':sha(source),'parent_protocol_sha256':sha(BASE/'semantic_guidance/development_protocol.json'),
        'graph_sha256':sha(OUT/'workflow_context_graph.json'),'rrf_k':60,'depths':[4,8],
        'methods':['publisher_hierarchy','qualifier_graph','longitudinal_context_graph'],
        'design':'Publisher summary coverage plus source-derived condition/qualification companions; separate available-history ablation. Prefix-stable first-four priorities and extension to eight.',
        'source_budget':'Every selected recommendation consumes a top-k slot. Publisher definition nodes are supplemental, separately counted, identical to the parent definition graph.',
        'clinical_review_status':'pending; ontology/context routing developed after examining the same exposed benchmark, not external validation',
        'code_sha256':{p:sha(ROOT/p) for p in ['backend/rag/workflow_context_graph.py','backend/scripts/develop_structured_context.py']}}
    p=OUT/'development_protocol.json'
    if p.exists() and json.loads(p.read_text())!=protocol:raise ValueError('Structured-context protocol drift')
    save(p,protocol)
    audits=[]
    for p in parents:
        r=json.loads(p.read_text());case=cases[r['id']]
        original=r['component_original_rankings']['definitions']
        remainder=fuse_rankings([original['medical'],original['generic']],60)
        order=list(dict.fromkeys(r['rankings']['ce_definition_graph']['4']+r['rankings']['ce_definition_graph']['8']+remainder))
        allowed={i for i in order if admission(corpus[i],case['query'],case['patient'])[0]}
        excluded=golds[r['id']]-allowed
        if excluded:
            save(OUT/'scope_gold_conflict.json',{'id':r['id'],'excluded':sorted(excluded)})
            raise ValueError('Clinical scope/gold conflict; no labels changed')
        for cid in order:
            accepted,reason=admission(corpus[cid],case['query'],case['patient'])
            if not accepted:audits.append({'id':r['id'],'chunk_id':cid,'reason':reason})
        methods={};traces={}
        for method,graph_on,history_on in [('publisher_hierarchy',False,False),('qualifier_graph',True,False),('longitudinal_context_graph',True,True)]:
            selected,trace=select_context(order,corpus,graph,case['query'],case['patient'],case['history'],use_graph=graph_on,include_history=history_on)
            methods[method]={str(k):selected[:k] for k in [4,8]};traces[method]=trace
            if methods[method]['8'][:4]!=methods[method]['4']:raise ValueError('Unstable evidence prefix')
        save(OUT/'runs'/p.name,{'id':r['id'],'guideline':r['guideline'],'family':r['family'],'stage':'development_only',
            'rankings':methods,'selection_trace':traces,'eligible_candidates':len(allowed),
            'definition_context_ids':r['definition_context_ids'],'evidence_genres':r['evidence_genres']})
    save(OUT/'source_topic_audit.json',audits)
    print('100 structured-context development rankings saved; zero new model calls.')


if __name__=='__main__':main()
