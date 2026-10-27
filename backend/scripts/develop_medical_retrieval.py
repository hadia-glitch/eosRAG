"""Development-only medical IR ablations; this never starts final generation.

Scope and corpus structure are derived from sources, not relevance labels.
Gold IDs and references reach scoring only. All declared methods are retained.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
OUT=ROOT/'output/research/rag_development/medcpt'
from rag.clinical_scope import applicable
from rag.relevance import focus_query,passage_windows,rerank_scores
from rag.rank_fusion import fuse_rankings,guarded_mmr
from rag.selection import expand_query
from scripts.evaluate_rag_improvements import save,metrics


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def explicit_edges(chunks):
    ids={c['chunk_id'] for c in chunks};edges={c['chunk_id']:[] for c in chunks}
    for c in chunks:
        text=c['raw_text'];targets=[]
        if c['guideline_id']=='NICE':
            targets += ['NICE-box'+m for m in re.findall(r'\bbox\s+([12])\b',text,re.I)]
            targets += ['NICE-'+m for m in re.findall(r'\brecommendations?\s+(1\.\d+\.\d+)\b',text,re.I)]
        if c['guideline_id']=='WHO':
            targets += ['WHO2024-'+m for m in re.findall(r'\brecommendations?\s+([AB]\.\d+[ab]?)\b',text,re.I)]
        edges[c['chunk_id']]=sorted({t for t in targets if t in ids and t!=c['chunk_id']})
    return edges


def main():
    import torch
    from rank_bm25 import BM25Okapi
    from sentence_transformers import SentenceTransformer,CrossEncoder
    from rag.medical_models import MedCPT
    torch.set_num_threads(4)
    cases_path=ROOT/'output/research/expanded100/cases.json'
    cases=json.loads(cases_path.read_text())
    manifest_path=ROOT/'output/research/expanded100/manifest.json'
    routes={r['id']:r['guideline'] for r in json.loads(manifest_path.read_text())['cases']}
    chunks=json.loads((OUT/'corpus.json').read_text())['chunks']
    methods=['lexical_scoped','medcpt_dense_dot','medcpt_dense_cosine','medcpt_hybrid',
             'hybrid_medcpt_ce_mmr','hybrid_medcpt_graph_ce_mmr','generic_scoped_control']
    protocol={'stage':'development_only','final_evaluation':False,'cases_sha256':digest(cases_path),
              'routing_manifest_sha256':digest(manifest_path),
              'corpus_sha256':digest(OUT/'corpus.json'),'seed':31,'rrf_k':60,'top_k':4,'candidate_limit':60,
              'mmr_diversity':.1,'scope_filter':'Explicit passage metadata and patient age/gestation/setting before ranking',
              'methods':methods,'query_encoder':'ncbi/MedCPT-Query-Encoder','article_encoder':'ncbi/MedCPT-Article-Encoder',
              'medical_reranker':'ncbi/MedCPT-Cross-Encoder','control_encoder':'sentence-transformers/all-MiniLM-L6-v2',
              'control_reranker':'cross-encoder/ms-marco-MiniLM-L-6-v2',
              'pooling':'Official CLS; dot-product dense primary; cosine ablation. Maximum over overlapping source windows.',
              'graph':'Explicit recommendation references only; source/age/setting admissibility retained; candidate expansion only.',
              'code_sha256':{p:digest(ROOT/p) for p in ['backend/scripts/develop_medical_retrieval.py','backend/rag/medical_models.py',
                  'backend/rag/clinical_scope.py','backend/rag/relevance.py','backend/rag/rank_fusion.py']}}
    path=OUT/'development_protocol.json'
    if path.exists() and json.loads(path.read_text())!=protocol:raise ValueError('Development config drift; create a new candidate directory')
    save(path,protocol)
    medical=MedCPT()
    generic=SentenceTransformer(protocol['control_encoder'])
    reranker=CrossEncoder(protocol['control_reranker'])
    save(OUT/'model_revisions.json',medical.revisions)
    edges=explicit_edges(chunks);save(OUT/'explicit_source_graph.json',edges)
    byid={c['chunk_id']:i for i,c in enumerate(chunks)}
    texts=[c['text'] for c in chunks]
    # Hierarchy is encoded as title; all immutable source wording is retained
    # in overlapping windows and remains separate from index representations.
    pairs=[];owners=[]
    for i,c in enumerate(chunks):
        title=' / '.join(s for s in [c['source'],c.get('retrieval_headings',{}).get('parent_heading'),
                                   c.get('retrieval_headings',{}).get('section_heading')] if s)
        for span in passage_windows(c['raw_text']):pairs.append([title,span]);owners.append(i)
    document_vectors=medical.article_vectors(pairs)
    docnorm=document_vectors/(np.linalg.norm(document_vectors,axis=1,keepdims=True)+1e-12)
    mmr_vectors=np.array([document_vectors[np.array(owners)==i].mean(axis=0) for i in range(len(chunks))])
    generic_vectors=generic.encode(texts,normalize_embeddings=True,show_progress_bar=False)
    tokens=lambda t:re.findall(r'[a-z0-9]+',t.lower())
    cache={};scope_conflicts=[]
    for case in cases:
        dest=OUT/'runs'/f'{case["id"]}.json'
        if dest.exists():continue
        # Guideline routing is case metadata, not a relevance signal.
        source=routes[case['id']]
        eligible=[i for i,c in enumerate(chunks) if c['guideline_id']==source and applicable(c['scope'],case['patient'])]
        bad=[g for g in case['gold_chunk_ids'] if byid[g] not in eligible]
        if bad:scope_conflicts.append({'id':case['id'],'incompatible_gold_ids':bad})
        query=focus_query(case['query'])
        key=(query,tuple(eligible))
        if key not in cache:
            bm=BM25Okapi([tokens(texts[i]) for i in eligible])
            lex=bm.get_scores(tokens(query));exp=bm.get_scores(tokens(expand_query(query)))
            lexrank=[eligible[j] for j in np.argsort(-lex,kind='stable') if lex[j]>0]
            exprank=[eligible[j] for j in np.argsort(-exp,kind='stable') if exp[j]>0]
            q=medical.query_vectors([query])[0]
            raw=document_vectors@q;cos=docnorm@(q/(np.linalg.norm(q)+1e-12))
            dot=np.array([raw[np.array(owners)==i].max() for i in eligible])
            cosine=np.array([cos[np.array(owners)==i].max() for i in eligible])
            dense=[eligible[j] for j in np.argsort(-dot,kind='stable')]
            cosrank=[eligible[j] for j in np.argsort(-cosine,kind='stable')]
            hybrid=fuse_rankings([lexrank,dense],60)
            pool=fuse_rankings([lexrank[:60],exprank[:60],dense[:60]],60)[:60]
            added={byid[t] for i in hybrid[:5] for t in edges[chunks[i]['chunk_id']] if byid[t] in eligible}
            graph_pool=list(dict.fromkeys([*pool,*sorted(added)]))
            values=rerank_scores(query,[texts[i] for i in graph_pool],medical)
            ranked=sorted(zip(graph_pool,values),key=lambda p:(-p[1],p[0]))
            ce=[i for i,_ in ranked if i in pool];gce=[i for i,_ in ranked]
            med_fused=fuse_rankings([lexrank,dense,ce],60)
            graph_fused=fuse_rankings([lexrank,dense,gce],60)
            gv=generic_vectors[eligible]@generic.encode(query,normalize_embeddings=True)
            gdense=[eligible[j] for j in np.argsort(-gv,kind='stable')]
            gpool=fuse_rankings([lexrank[:60],exprank[:60],gdense[:60]],60)[:60]
            gs=rerank_scores(query,[texts[i] for i in gpool],reranker)
            grank=[i for i,_ in sorted(zip(gpool,gs),key=lambda p:(-p[1],p[0]))]
            generic_fused=fuse_rankings([lexrank,gdense,grank],60)
            cache[key]={'lexical_scoped':lexrank[:4],'medcpt_dense_dot':dense[:4],'medcpt_dense_cosine':cosrank[:4],
                'medcpt_hybrid':hybrid[:4],'hybrid_medcpt_ce_mmr':guarded_mmr(med_fused,mmr_vectors,4),
                'hybrid_medcpt_graph_ce_mmr':guarded_mmr(graph_fused,mmr_vectors,4),
                'generic_scoped_control':guarded_mmr(generic_fused,generic_vectors,4)}
        save(dest,{'id':case['id'],'family':case['family'],'guideline':source,'stage':'development_only',
             'eligible_passages':len(eligible),'scope_incompatible_gold_ids':bad,
             'scope_constrained_recall_at_4_ceiling':min(4,len(case['gold_chunk_ids'])-len(bad))/len(case['gold_chunk_ids']),
             'rankings':{m:[chunks[i]['chunk_id'] for i in ranks] for m,ranks in cache[key].items()}})
        print('development',case['id'],'eligible',len(eligible),flush=True)
    save(OUT/'scope_conflicts.json',scope_conflicts)
    summarize(cases)


def summarize(cases):
    import csv
    from scripts.summarize_expanded import ci
    lookup={c['id']:c for c in cases};rows=[]
    for path in sorted((OUT/'runs').glob('*.json')):
        r=json.loads(path.read_text());c=lookup[r['id']]
        for method,ids in r['rankings'].items():
            rows.append({'id':r['id'],'guideline':r['guideline'],'family':r['family'],'method':method,
                         **metrics(ids,set(c['gold_chunk_ids']))})
    groups={}
    for r in rows:groups.setdefault((r['guideline'],r['method']),[]).append(r)
    stats=[]
    for (g,m),group in sorted(groups.items()):
        for metric in metrics([],{'x'}):
            stats.append({'guideline':g,'method':m,'metric':metric,'n':len(group),
                **ci([r[metric] for r in group],[r['family'] for r in group])})
    for name,data in [('development_per_case.csv',rows),('development_intervals.csv',stats)]:
        with (OUT/name).open('w',newline='',encoding='utf8') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    save(OUT/'development_summary.json',stats)
    print('Development retrieval completed; final evaluation remains on hold.',flush=True)


if __name__=='__main__':main()
