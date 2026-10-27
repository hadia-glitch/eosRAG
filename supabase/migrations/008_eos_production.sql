-- Apply in staging first, after ALL existing migrations. Reviewed evidence and
-- explicit owner policies replace permissive legacy policies (policies OR).
BEGIN;

CREATE TABLE IF NOT EXISTS public.decision_audits (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id uuid NOT NULL REFERENCES auth.users(id),
  encounter_id uuid REFERENCES public.patient_encounters(id),
  operation text NOT NULL,
  model_version text NOT NULL,
  corpus_version text NOT NULL,
  status text NOT NULL,
  response_sha256 text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.decision_audits ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.decision_audits FROM anon, authenticated;
GRANT SELECT, INSERT ON public.decision_audits TO service_role;
REVOKE UPDATE, DELETE ON public.decision_audits FROM service_role;

ALTER TABLE public.patient_encounters ADD COLUMN IF NOT EXISTS birth_date_time timestamptz;
ALTER TABLE public.guideline_documents ADD COLUMN IF NOT EXISTS approved_for_generation boolean NOT NULL DEFAULT false;
ALTER TABLE public.guideline_documents ADD COLUMN IF NOT EXISTS content_sha256 text;
ALTER TABLE public.guideline_documents ADD COLUMN IF NOT EXISTS reviewed_by text;
ALTER TABLE public.guideline_documents ADD COLUMN IF NOT EXISTS reviewed_at timestamptz;
ALTER TABLE public.guideline_documents ADD COLUMN IF NOT EXISTS storage_path text;
ALTER TABLE public.guideline_documents ADD COLUMN IF NOT EXISTS storage_url text;

-- Existing imported content remains unapproved until a recorded review.
ALTER TABLE public.evidence_chunks ADD COLUMN IF NOT EXISTS search_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(chunk_text, ''))) STORED;
CREATE INDEX IF NOT EXISTS evidence_chunks_search_tsv_idx ON public.evidence_chunks USING gin(search_tsv);
CREATE INDEX IF NOT EXISTS evidence_chunks_document_idx ON public.evidence_chunks(document_id);

DO $$
DECLARE p record; t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['patient_encounters','clinical_assessments','risk_results','alerts','patient_records','guideline_documents','evidence_chunks','llm_explanations','rag_queries','audit_logs'] LOOP
    IF to_regclass('public.' || t) IS NOT NULL THEN
      EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
      FOR p IN SELECT policyname FROM pg_policies WHERE schemaname='public' AND tablename=t LOOP
        EXECUTE format('DROP POLICY %I ON public.%I', p.policyname, t);
      END LOOP;
    END IF;
  END LOOP;
END $$;

CREATE POLICY encounters_owner ON public.patient_encounters FOR ALL TO authenticated
  USING (owner_user_id = (SELECT auth.uid())) WITH CHECK (owner_user_id = (SELECT auth.uid()));
CREATE POLICY records_owner ON public.patient_records FOR ALL TO authenticated
  USING (owner_user_id = (SELECT auth.uid())) WITH CHECK (owner_user_id = (SELECT auth.uid()));

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['clinical_assessments','risk_results','alerts'] LOOP
    EXECUTE format('CREATE POLICY encounter_owner ON public.%I FOR ALL TO authenticated
      USING (EXISTS (SELECT 1 FROM public.patient_encounters e WHERE e.id = encounter_id AND e.owner_user_id = (SELECT auth.uid())))
      WITH CHECK (EXISTS (SELECT 1 FROM public.patient_encounters e WHERE e.id = encounter_id AND e.owner_user_id = (SELECT auth.uid())))', t);
  END LOOP;
END $$;

CREATE POLICY reviewed_documents ON public.guideline_documents FOR SELECT TO authenticated
  USING (active AND approved_for_generation AND content_sha256 IS NOT NULL AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL);
CREATE POLICY reviewed_passages ON public.evidence_chunks FOR SELECT TO authenticated
  USING (EXISTS (SELECT 1 FROM public.guideline_documents d WHERE d.id = document_id AND d.active AND d.approved_for_generation
    AND d.content_sha256 = metadata->>'document_sha256'));
-- Legacy prompt/case caches, query logs and audit rows have no client policy.
-- Only the service role may read them. The new API does not populate PHI caches.

CREATE OR REPLACE FUNCTION public.eos_lexical_search(search_text text, guideline text, match_count int DEFAULT 30)
RETURNS SETOF public.evidence_chunks LANGUAGE sql STABLE SECURITY INVOKER SET search_path = public, pg_temp AS $$
  WITH q AS (
    SELECT to_tsquery('english', coalesce(nullif(array_to_string(tsvector_to_array(to_tsvector('english', left(search_text,4000))), ' | '),''),'eos')) AS query
  ) SELECT c.* FROM public.evidence_chunks c
  JOIN public.guideline_documents d ON d.id = c.document_id
  CROSS JOIN q
  WHERE d.active AND d.approved_for_generation AND d.source = guideline
    AND d.content_sha256 = c.metadata->>'document_sha256'
    AND c.search_tsv @@ q.query
  ORDER BY ts_rank_cd(c.search_tsv, q.query) DESC, c.id
  LIMIT greatest(1, least(match_count, 50));
$$;

-- Unconstrained vector input supports the configured column dimension. A
-- dimension mismatch raises and is reported as lexical degradation by API.
CREATE OR REPLACE FUNCTION public.eos_vector_search(query_embedding vector, guideline text, match_count int DEFAULT 30)
RETURNS SETOF public.evidence_chunks LANGUAGE sql STABLE SECURITY INVOKER SET search_path = public, pg_temp AS $$
  SELECT c.* FROM public.evidence_chunks c
  JOIN public.guideline_documents d ON d.id = c.document_id
  WHERE d.active AND d.approved_for_generation AND d.source = guideline
    AND d.content_sha256 = c.metadata->>'document_sha256' AND c.embedding IS NOT NULL
  ORDER BY c.embedding <=> query_embedding, c.id
  LIMIT greatest(1, least(match_count, 50));
$$;
REVOKE ALL ON FUNCTION public.eos_lexical_search(text,text,int) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.eos_vector_search(vector,text,int) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.eos_lexical_search(text,text,int) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.eos_vector_search(vector,text,int) TO authenticated, service_role;

-- Views normally execute with their owner's permissions. Preserve RLS.
DO $$ BEGIN
  IF to_regclass('public.assessment_deltas') IS NOT NULL THEN
    ALTER VIEW public.assessment_deltas SET (security_invoker = true);
  END IF;
END $$;

COMMIT;
