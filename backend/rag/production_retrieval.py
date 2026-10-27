"""Postgres full-text + pgvector + optional Neo4j candidate fusion.

Only source-reviewed, current, hash-matching passages can reach generation.
Retrieval score is a ranking value, never clinical confidence. Failures degrade
to reviewed lexical passages or empty evidence, never seed/synthetic evidence.
"""
from dataclasses import dataclass, field
from functools import lru_cache

from db import get_supabase
from rag.evidence_policy import admit_chunk, approved_document, load_manifest
from rag.knowledge_graph import graph_candidate_ids
from rag.retrieve import EvidenceChunkResult, _to_result
from rag.rrf import reciprocal_rank_fusion
from rag.selection import expand_query
from rag.relevance import focus_query, rerank_scores
from rag.source_scope import retrieval_text
from rag.rank_fusion import fuse_rankings
from rag.faceted_selection import select_facets
from rag.history_queries import observed_queries


@dataclass
class Retrieval:
    chunks: list[EvidenceChunkResult] = field(default_factory=list)
    mode: str = "unavailable"
    warnings: list[str] = field(default_factory=list)
    corpus_version: str = "unavailable"
    graph_status: str = "disabled"
    selection_mode: str = 'exact_deduplication'
    query_expanded: bool = False


@lru_cache(maxsize=2)
def embedding_model(name):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(name)


@lru_cache(maxsize=2)
def reranker_model(name):
    from sentence_transformers import CrossEncoder
    return CrossEncoder(name)


def retrieve(query, guideline, limit, settings, *, db=None, encoder=None, reranker=None, patient=None):
    if not isinstance(limit, int) or not 1 <= limit <= 30:
        raise ValueError('Evidence limit must be between 1 and 30')
    query = focus_query(query)
    documents, version = load_manifest(settings)
    result = Retrieval(corpus_version=version)
    eligible = [d for d in documents if d.get("approved_for_generation") and d.get("source") == guideline and d.get("status") == "current"]
    if not eligible:
        result.warnings.append("No reviewed current source in the selected guideline")
        return result
    db = db or get_supabase()
    lists = []
    base_lists = []
    def lexical_rows(text):
        args={"search_text":text,"guideline":guideline,"match_count":30}
        try:
            return db.rpc('eos_lexical_search_v2',args).execute().data or []
        except Exception:
            warning='Heading-aware lexical index unavailable; legacy reviewed lexical search retained'
            if warning not in result.warnings:result.warnings.append(warning)
            return db.rpc('eos_lexical_search',args).execute().data or []
    enc=None
    encoder_ready=False
    try:
        lexical = lexical_rows(query)
        accepted = [r for r in lexical if admit_chunk(r, settings, guideline, patient)]
        lists.append(accepted);base_lists.append(accepted)
        result.mode = "lexical"
        expanded=expand_query(query)
        if expanded!=query:
            try:
                expanded_rows=lexical_rows(expanded)
                lists.append([r for r in expanded_rows if admit_chunk(r,settings,guideline,patient)])
                result.query_expanded=True
            except Exception:result.warnings.append('Synonym-expanded search unavailable; original query retained')
    except Exception:
        result.warnings.append("Lexical index unavailable")
    try:
        enc = encoder or embedding_model(settings.embedding_model)
        embedding_query = ('query: ' + query) if settings.embedding_model.startswith('intfloat/e5-') else query
        vector = enc.encode(embedding_query, normalize_embeddings=True).tolist()
        if len(vector) != settings.embedding_dim:
            raise ValueError("Embedding dimension mismatch")
        encoder_ready=True
        vector_rows = db.rpc("eos_vector_search_v2", {"query_embedding": vector, "guideline": guideline,
                             "encoder_name": settings.embedding_model, "match_count": 30}).execute().data or []
        # Identical dimensions do not imply an identical embedding space.
        # Missing/unpinned legacy metadata cannot silently pass this boundary.
        matching = [r for r in vector_rows if (r.get('metadata') or {}).get('embedding_model') == settings.embedding_model]
        if len(matching) != len(vector_rows):
            result.warnings.append('Unpinned or incompatible embedding rows excluded; reindex required')
        accepted = [r for r in matching if admit_chunk(r, settings, guideline, patient)]
        lists.append(accepted);base_lists.append(accepted)
        result.mode = "hybrid" if result.mode == "lexical" else "vector"
    except Exception:
        result.warnings.append("Semantic retrieval unavailable; reviewed lexical evidence only")
    try:
        ids, result.graph_status = graph_candidate_ids(query, settings)
    except Exception:
        ids, result.graph_status = [], 'unavailable'
        result.warnings.append('Graph retrieval unavailable')
    graph_rows = []
    if ids:
        try:
            rows = db.table("evidence_chunks").select("*").in_("id", ids[:30]).execute().data or []
            by_id = {str(r["id"]): r for r in rows if admit_chunk(r, settings, guideline, patient)}
            # Candidate expansion only: broad graph degree must not overrule
            # lexical/dense relevance in RRF. Every added row is reranked.
            graph_rows = [by_id[i] for i in ids if i in by_id]
            result.mode += "+graph"
        except Exception:
            result.warnings.append("Graph passage fetch unavailable")
    fused = reciprocal_rank_fusion(lists, k=60, id_fn=lambda r: str(r["id"]))[:60]
    existing = {str(r['id']) for r, _ in fused}
    fused.extend((r, 0.) for r in graph_rows if str(r['id']) not in existing)
    if not fused:
        return result
    candidates = [r for r, _ in fused]
    scores = [score for _, score in fused]
    reranked=False
    try:
        ce = reranker or reranker_model(settings.reranker_model)
        scores = rerank_scores(query, [retrieval_text(r) for r in candidates], ce)
        reranked=True
        result.mode += "+reranked"
    except Exception:
        result.warnings.append("Reranking unavailable; reciprocal-rank order used")
        # Graph-only rows have no lexical/vector ranking and must not enter
        # output merely because a reranker failed.
        kept = [(r, s) for r, s in zip(candidates, scores) if s > 0]
        candidates, scores = ([r for r, _ in kept], [s for _, s in kept])
    ranked = sorted(zip(candidates, scores), key=lambda p: p[1], reverse=True)
    if reranked:
        # CE contributes one ranking vote. It cannot erase both lexical and
        # semantic relevance; synonym/graph candidates do not get extra votes.
        primary = base_lists if any(base_lists) else lists
        rank_lists = [[str(r['id']) for r in rows] for rows in primary]
        rank_lists.append([str(r['id']) for r,_ in ranked])
        order = fuse_rankings(rank_lists,60)
        lookup = {str(r['id']):r for r in candidates}
        fused_scores = {}
        for rank_list in rank_lists:
            for position,cid in enumerate(dict.fromkeys(rank_list),1):
                fused_scores[cid] = fused_scores.get(cid,0.) + 1/(60+position)
        ranked = [(lookup[cid],fused_scores[cid]) for cid in order if cid in lookup]
        result.mode += '+rank-fused'
    # Exact duplicate passages consume one context slot. Keep page provenance.
    seen = set()
    unique=[]
    for row,score in ranked:
        key = " ".join(row["chunk_text"].split())
        if key in seen:
            continue
        seen.add(key)
        unique.append((row,score))
    if encoder_ready and reranked and len(unique)>limit:
        try:
            prefix='passage: ' if settings.embedding_model.startswith('intfloat/e5-') else ''
            vectors=enc.encode([prefix+retrieval_text(r) for r,_ in unique],normalize_embeddings=True)
            # At depth four a 0.1 ordinal diversity penalty could never swap
            # even a duplicate neighbour. Use the bounded selector whose
            # regression checks demonstrate an actual relevance-head swap.
            chosen=select_facets(list(range(len(unique))),vectors,limit,diversity=.15)
            unique=[unique[i] for i in chosen]
            result.selection_mode='relevance-guarded-maximal-marginal-relevance'
            result.mode+='+mmr'
        except Exception:result.warnings.append('MMR unavailable; reranked nonduplicate evidence retained')
    for row,score in unique:
        reviewed = approved_document((row.get("metadata") or {}).get("file_name", ""), settings)
        row = {**row, "source_name": reviewed.get("title", row.get("source_name", "")),
               "metadata": {**(row.get("metadata") or {}), "document_url": reviewed["url"], "source": reviewed["source"]}}
        result.chunks.append(_to_result(row, score))
        if len(result.chunks) == limit:
            break
    return result


PLAN_QUERIES=(
    'perform an immediate clinical assessment review maternal neonatal history physical examination vital signs',
    'early onset neonatal infection clinical indicators respiratory distress hypoxia abnormal heart rate temperature immediate assessment',
    'perform a blood culture before giving the first dose of antibiotics to a baby',
    'measure baseline C reactive protein concentration when starting antibiotic treatment in babies',
    'risk factors early onset infection preterm birth before 37 weeks maternal group B streptococcus prolonged rupture membranes',
    'suspected early onset neonatal infection guideline recommended empirical antibiotic options local resistance and treatment review',
    'regularly reassess clinical condition results investigations newborn antibiotic treatment review',
    'explain reason concern options management parents carers observations investigations antibiotic benefits',
    'breastfeed breastfeeding expressing breast milk temporarily unable to breastfeed neonatal infection',
    'early onset infection inform parents and GP verbally and in writing when baby discharged point of contact follow up handover',
    'early onset infection antibiotic treatment duration and stopping conditions negative blood culture clinical condition inflammatory marker limitations')

def retrieve_plan(guideline,settings,patient,*,retriever=None,context_query=None,history=()):
    """Retrieve across plan domains; one generic query cannot cover a full plan."""
    retriever=retriever or retrieve
    merged=Retrieval();seen=set();queries=[];modes=[];graphs=[];selections=[]
    if context_query:queries.append(context_query)
    if patient.get('penicillin_allergy') is True:
        queries.append('neonatal penicillin beta lactam hypersensitivity allergy contraindication specialist antibiotic advice')
    if any(patient.get(k) is not None for k in ['creatinine_mg_dl','urine_output_ml_kg_hr']):
        queries.append('neonatal gentamicin aminoglycoside renal function therapeutic monitoring safety expert advice')
    if history:
        queries.append('serial neonatal observations respiratory rate oxygen saturation C reactive protein trends clinical condition reassessment')
        queries.extend(observed_queries(patient,history))
    queries=list(dict.fromkeys([*queries,*PLAN_QUERIES]))
    for query in queries:
        part=retriever(query,guideline,2,settings,patient=patient)
        modes.append(part.mode);graphs.append(part.graph_status);selections.append(part.selection_mode)
        merged.corpus_version=part.corpus_version
        merged.warnings.extend(part.warnings)
        for chunk in part.chunks:
            if chunk.chunk_id not in seen:
                merged.chunks.append(chunk);seen.add(chunk.chunk_id)
    merged.warnings=list(dict.fromkeys(merged.warnings))
    merged.mode='+'.join(dict.fromkeys(modes))+':plan-domain-coverage'
    merged.graph_status=','.join(dict.fromkeys(graphs))
    merged.selection_mode='per-domain:'+','.join(dict.fromkeys(selections))
    return merged
