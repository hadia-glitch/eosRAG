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
from rag.selection import expand_query,mmr_indices


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
    documents, version = load_manifest(settings)
    result = Retrieval(corpus_version=version)
    eligible = [d for d in documents if d.get("approved_for_generation") and d.get("source") == guideline and d.get("status") == "current"]
    if not eligible:
        result.warnings.append("No reviewed current source in the selected guideline")
        return result
    db = db or get_supabase()
    lists = []
    enc=None
    encoder_ready=False
    try:
        lexical = db.rpc("eos_lexical_search", {"search_text": query, "guideline": guideline, "match_count": 30}).execute().data or []
        lists.append([r for r in lexical if admit_chunk(r, settings, guideline, patient)])
        result.mode = "lexical"
        expanded=expand_query(query)
        if expanded!=query:
            try:
                expanded_rows=db.rpc('eos_lexical_search',{'search_text':expanded,'guideline':guideline,'match_count':30}).execute().data or []
                lists.append([r for r in expanded_rows if admit_chunk(r,settings,guideline,patient)])
                result.query_expanded=True
            except Exception:result.warnings.append('Synonym-expanded search unavailable; original query retained')
    except Exception:
        result.warnings.append("Lexical index unavailable")
    try:
        enc = encoder or embedding_model(settings.embedding_model)
        vector = enc.encode(query, normalize_embeddings=True).tolist()
        if len(vector) != settings.embedding_dim:
            raise ValueError("Embedding dimension mismatch")
        encoder_ready=True
        vector_rows = db.rpc("eos_vector_search", {"query_embedding": vector, "guideline": guideline, "match_count": 30}).execute().data or []
        lists.append([r for r in vector_rows if admit_chunk(r, settings, guideline, patient)])
        result.mode = "hybrid" if result.mode == "lexical" else "vector"
    except Exception:
        result.warnings.append("Semantic retrieval unavailable; reviewed lexical evidence only")
    ids, result.graph_status = graph_candidate_ids(query, settings)
    if ids:
        try:
            rows = db.table("evidence_chunks").select("*").in_("id", ids[:30]).execute().data or []
            by_id = {str(r["id"]): r for r in rows if admit_chunk(r, settings, guideline, patient)}
            lists.append([by_id[i] for i in ids if i in by_id])
            result.mode += "+graph"
        except Exception:
            result.warnings.append("Graph passage fetch unavailable")
    fused = reciprocal_rank_fusion(lists, k=60, id_fn=lambda r: str(r["id"]))[:40]
    if not fused:
        return result
    candidates = [r for r, _ in fused]
    scores = [score for _, score in fused]
    reranked=False
    try:
        ce = reranker or reranker_model(settings.reranker_model)
        scores = [float(v) for v in ce.predict([(query, r["chunk_text"]) for r in candidates])]
        reranked=True
        result.mode += "+reranked"
    except Exception:
        result.warnings.append("Reranking unavailable; reciprocal-rank order used")
    ranked = sorted(zip(candidates, scores), key=lambda p: p[1], reverse=True)
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
            vectors=enc.encode([r['chunk_text'] for r,_ in unique],normalize_embeddings=True)
            chosen=mmr_indices([s for _,s in unique],vectors,limit,diversity=.2)
            unique=[unique[i] for i in chosen]
            result.selection_mode='maximal_marginal_relevance'
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
    'empirical suspected early onset infection first choice intravenous benzylpenicillin sodium gentamicin local resistance treatment',
    'regularly reassess clinical condition results investigations newborn antibiotic treatment review',
    'explain reason concern options management parents carers observations investigations antibiotic benefits',
    'breastfeed breastfeeding expressing breast milk temporarily unable to breastfeed neonatal infection',
    'early onset infection inform parents and GP verbally and in writing when baby discharged point of contact follow up handover',
    'early onset antibiotic stopping conditions 36 hours negative blood culture clinical condition C reactive protein results alone')

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
