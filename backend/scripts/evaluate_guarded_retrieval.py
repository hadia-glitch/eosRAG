"""V3 full-pipeline candidate after retaining failed reranking ablations."""
import argparse
import json
import re
from pathlib import Path
import numpy as np
from backend.scripts import evaluate_rag_improvements as study
from backend.scripts import resume_retrieval_cached as cached
from rag.relevance import focus_query,rerank_scores
from rag.selection import expand_query
from rag.rank_fusion import fuse_rankings,guarded_mmr


def search(query,texts,bm,encoder,vectors,ce,config,model):
    query=focus_query(query);tokens=lambda t:re.findall(r'[a-z0-9]+',t.lower())
    lexical=bm.get_scores(tokens(query));expanded=bm.get_scores(tokens(expand_query(query)))
    vector=vectors@encoder.encode(('query: ' if 'e5-' in model else '')+query,normalize_embeddings=True)
    lexrank=[int(i) for i in np.argsort(-lexical,kind='stable') if lexical[i]>0]
    exprank=[int(i) for i in np.argsort(-expanded,kind='stable') if expanded[i]>0]
    denserank=[int(i) for i in np.argsort(-vector,kind='stable')]
    base=fuse_rankings([lexrank,denserank],60)
    candidates=fuse_rankings([lexrank[:60],denserank[:60],exprank[:60]],60)[:60]
    values=rerank_scores(query,[texts[i] for i in candidates],ce)
    cerank=[i for i,_ in sorted(zip(candidates,values),key=lambda p:(-p[1],p[0]))]
    # Synonyms expand candidate recall without adding a second correlated
    # lexical vote to final ranking. CE is one vote, not a total override.
    fused=fuse_rankings([lexrank,denserank,cerank],60)
    return {'focused_hybrid':base[:4],'expanded_rrf_ce':cerank[:4],
            'rrf_ce_mmr_guarded':guarded_mmr(fused,vectors,4,diversity=.1),
            'rrf_ce_no_mmr':guarded_mmr(fused,vectors,4,diversity=0.)}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);a=p.parse_args()
    study.OUT=study.ROOT/'output/research/rag_improvement_v3'
    study.OLD=study.ROOT/'output/research/rag_improvement_v2/inputs'
    protocol={'candidate':'v3 relevance-guarded full pipeline','based_on':'source-heading v2 index',
              'methods':{'focused_hybrid':'BM25+dense RRF60','expanded_rrf_ce':'Synonym candidate expansion then CE only',
                         'rrf_ce_mmr_guarded':'BM25+dense+CE rank fusion RRF60, relevance-head MMR diversity 0.1',
                         'rrf_ce_no_mmr':'No-MMR ablation of the same three-rank fusion'},
              'note':'Development refinement after v1/v2 scores were observed; no untouched-test claim.',
              'code_sha256':{str(p.relative_to(study.ROOT)).replace('\\','/'):study.sha(p) for p in [Path(__file__).resolve(),study.ROOT/'backend/rag/rank_fusion.py']}}
    path=study.OUT/'candidate_protocol.json'
    if path.exists() and json.loads(path.read_text())!=protocol:raise ValueError('Candidate protocol drift')
    study.save(path,protocol)
    def freeze():
        cfg=json.loads((study.ROOT/'output/research/rag_improvement_v2/retrieval_protocol.json').read_text())
        cfg.update({'variants':list(protocol['methods']),'mmr_diversity':.1,
                    'code_sha256':{**cfg['code_sha256'],**protocol['code_sha256']},'design':protocol['note']})
        target=study.OUT/'retrieval_protocol.json'
        if target.exists() and json.loads(target.read_text())!=cfg:raise ValueError('Frozen guarded-retrieval drift')
        study.save(target,cfg)
        return cfg
    study.freeze=freeze
    study.search=search
    cached.main(a.model)
