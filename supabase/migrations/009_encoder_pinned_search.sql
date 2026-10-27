-- Do not infer encoder identity from dimensions: MiniLM and E5-small both
-- produce 384 values but occupy incompatible semantic spaces. Existing rows
-- must be re-embedded by a reviewed offline ingestion job, not relabelled.
CREATE OR REPLACE FUNCTION public.eos_vector_search_v2(
    query_embedding vector, guideline text, encoder_name text,
    match_count int DEFAULT 30
)
RETURNS SETOF public.evidence_chunks
LANGUAGE sql STABLE SECURITY INVOKER SET search_path = public, pg_temp AS $$
  SELECT c.* FROM public.evidence_chunks c
  JOIN public.guideline_documents d ON d.id = c.document_id
  WHERE d.active AND d.approved_for_generation AND d.source = guideline
    AND d.content_sha256 = c.metadata->>'document_sha256'
    AND c.metadata->>'embedding_model' = encoder_name
    AND c.embedding IS NOT NULL
    AND vector_dims(c.embedding) = vector_dims(query_embedding)
  ORDER BY c.embedding <=> query_embedding, c.id
  LIMIT greatest(1, least(match_count, 50));
$$;
REVOKE ALL ON FUNCTION public.eos_vector_search_v2(vector,text,text,int) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.eos_vector_search_v2(vector,text,text,int) TO authenticated, service_role;

-- Index source-derived headings while keeping immutable quotation text intact.
ALTER TABLE public.evidence_chunks ADD COLUMN IF NOT EXISTS search_tsv_v2 tsvector
GENERATED ALWAYS AS (
  setweight(to_tsvector('english',coalesce(chunk_text,'')),'A') ||
  setweight(to_tsvector('english',coalesce(metadata->>'retrieval_parent_heading','') || ' ' ||
                                    coalesce(metadata->>'retrieval_section_heading','')),'B')
) STORED;
CREATE INDEX IF NOT EXISTS evidence_chunks_search_tsv_v2_idx
ON public.evidence_chunks USING gin(search_tsv_v2);

CREATE OR REPLACE FUNCTION public.eos_lexical_search_v2(
    search_text text, guideline text, match_count int DEFAULT 30
)
RETURNS SETOF public.evidence_chunks
LANGUAGE sql STABLE SECURITY INVOKER SET search_path = public, pg_temp AS $$
  WITH q AS (
    SELECT to_tsquery('english',coalesce(nullif(array_to_string(
      tsvector_to_array(to_tsvector('english',left(search_text,4000))),' | '),''),'eos')) AS query
  ) SELECT c.* FROM public.evidence_chunks c
  JOIN public.guideline_documents d ON d.id=c.document_id CROSS JOIN q
  WHERE d.active AND d.approved_for_generation AND d.source=guideline
    AND d.content_sha256=c.metadata->>'document_sha256'
    AND c.search_tsv_v2 @@ q.query
  ORDER BY ts_rank_cd(c.search_tsv_v2,q.query) DESC,c.id
  LIMIT greatest(1,least(match_count,50));
$$;
REVOKE ALL ON FUNCTION public.eos_lexical_search_v2(text,text,int) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.eos_lexical_search_v2(text,text,int) TO authenticated, service_role;
