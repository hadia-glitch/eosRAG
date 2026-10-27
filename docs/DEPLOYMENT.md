# EOS deployment and release runbook

Status: research/staging implementation. Supplied-label neonatal research models
have been trained; they are not eligible EOS artifacts. No live deployment has
been made. See `RESEARCH_EXPERIMENTS.md` for measured results and provenance.

## Architecture

Vercel serves the compiled Flutter web app. A separately hosted, authenticated
FastAPI container performs inference, retrieval and Groq generation. Supabase
stores patient records and reviewed guideline passages with pgvector and text
indexes. An optional external Neo4j instance indexes passage-to-concept links.
Training, source ingestion and graph synchronization are offline jobs.

The API is intentionally not bundled into a Vercel Python function: local
embedding/reranking models, model caches and ingestion have different resource
needs from the static app. See [Vercel's Python runtime documentation](https://vercel.com/docs/functions/runtimes/python).

## Configuration

Keep credentials in the backend host's secret manager. The existing backend/.env
is used locally and was preserved. Both .env files are now ignored and untracked.
Untracking does not erase old Git history. Rotate any key previously pushed to a
remote. Never publish service-role or Groq keys in Flutter build arguments.

Backend required variables:

| Variable | Purpose |
| --- | --- |
| SUPABASE_URL | Database/auth project URL |
| SUPABASE_ANON_KEY | Token validation through Supabase Auth |
| SUPABASE_SERVICE_KEY | Server-only evidence/history access; ownership is checked first |
| GROQ_API_KEY | Server-only generation credential |
| GROQ_MODEL | Current local selection: openai/gpt-oss-120b |
| VERIFIER_MODEL | Separate Groq verifier selection; openai/gpt-oss-120b; isolated roles share model weights |
| DISABLE_CLOUD_LLM_FALLBACK | false to enable the requested Groq workflow |
| ALLOW_CLINICAL_CLOUD_PROCESSING | Deployment policy switch for structured case context |
| CORS_ORIGINS | Comma-separated exact frontend origins; include the approved Vercel deployment |
| CLINICAL_USE_ENABLED | false until clinical release approval; does not claim regulatory clearance |
| MODEL_ARTIFACT_PATH | Read-only path to the trained portable JSON artifact |
| MODEL_ARTIFACT_SHA256 | Required digest of that exact reviewed file |
| EVIDENCE_MANIFEST_PATH | Reviewed source manifest location |

If enabling the graph, also set ENABLE_KNOWLEDGE_GRAPH=true, NEO4J_URI,
NEO4J_USERNAME, NEO4J_PASSWORD and NEO4J_DATABASE. Neo4j is not installed or
provisioned by this repository. A graph outage degrades to non-graph retrieval.
Keep LANGSMITH_TRACING and LANGCHAIN_TRACING_V2 false; the entry point also forces
them off so patient packets are not exported by ambient tracing settings.

## Database migration

1. Back up staging. Apply the existing migrations in dependency order, including
   both 002 files, 003, 004, 005, the existing 006 AKI script, and 007.
2. Review and apply `supabase/migrations/008_eos_production.sql` in staging.
   It replaces legacy policies on patient/evidence/cache tables, introduces
   reviewed-document metadata, and adds bounded lexical/vector RPCs.
3. Test two separate clinician accounts. Each must see only owned encounters;
   one account must not read the other's assessments, alerts or risk results.
4. Set administrative authorization through Supabase **app_metadata** on a
   server-managed account. Self-editable user_metadata is never authorization.

Migration 008 was authored but not applied to your live Supabase project. It
requires PostgreSQL with pgvector and security_invoker view support. Preserve the
existing embedding dimension: the repository contains a previous BGE migration;
inspect the actual column before choosing 384 or 1024. An embedding dimension
change requires re-embedding and index rebuilding. The API reports semantic
failure as degraded retrieval rather than pretending vector search succeeded.

## Review and ingest sources

`backend/guidelines/manifest.json` registers four candidate guideline PDFs with
SHA-256 digests. All are pending review. Forms and unidentified PDFs are excluded.

A neonatal reviewer must verify source identity, edition/currentness, licensing,
population, hospital applicability and page offsets. Fill min_ga, max_ga,
min_age_hours, max_age_hours, care_setting, pdf_page_offset, reviewed_by and
reviewed_at; use `status: current` and `approved_for_generation: true` only after
review. The public URL must resolve to the corresponding document, including the
correct AAP term/preterm companion. Cropped PDFs can have different page numbers
from the original guideline. Match the manifest digest to the local file.

From the backend directory, with a development environment installed:

```powershell
python -m rag.ingest --dir guidelines
python -m scripts.sync_knowledge_graph
```

The graph command is optional. Ingestion refuses unreviewed or hash-mismatched
files before uploading or clearing anything. Avoid `--clear` unless explicitly
rebuilding the full staging corpus. Reruns currently create document versions;
deactivate the old version after checking the replacement. Do not run overlapping
ingestion jobs. The API serves no seed passages when the reviewed corpus is empty.

## Train the EOS model

Follow `docs/DATA_AND_MODEL.md`. Mount model.json read-only in the container and
set its digest. The training CLI always exports `research_only`; it cannot approve
its own model. Keep research estimates separate from treatment thresholds.

## Backend container

```powershell
docker build -t neoguard-eos:staging backend
docker run --rm -p 8000:8000 --env-file backend/.env neoguard-eos:staging
```

The Docker build downloads CPU embedding models once and disables model-hub
network access at runtime. It excludes .env files, tests, guideline PDFs and model
training artifacts from its build context. It includes the pinned supplied-label
research forest and scope manifest. Mount an approved clinical artifact and reviewed manifest
using your host's deployment configuration. The default image tag and transitive
dependencies are not digest-locked: capture an image digest, SBOM and dependency
scan before production promotion. The staging image was built successfully and
passed a non-root, read-only, network-disabled startup/authentication smoke test.
The cached CPU embedding model also completed the offline retrieval benchmark.
The final image additionally passed bundled-forest inference, actual SHAP,
cached encoder/reranker and strict-schema checks with networking disabled.

Use an HTTPS ingress with a request deadline above the API's bounded model calls,
per-user rate limiting, concurrency limits and a maximum body size. The app also
bounds streamed request bodies. Configure backups, retention, access reviews,
incident response, monitoring and vendor/data-residency agreements for the intended
clinical deployment. These are operational responsibilities, not established by
adding configuration files.

`/health` is public liveness. `/ready` is admin-only and distinguishes dependencies,
model availability and clinical eligibility. Dependency readiness is not clinical
approval. Test expired sessions, provider rate limits and database outages.

## Vercel web

Import this repository into Vercel as an Other project. vercel.json invokes the
pinned Flutter build and serves build/web with SPA routing. Set only these public
variables in the Vercel project: API_BASE_URL (HTTPS), SUPABASE_URL, and
SUPABASE_ANON_KEY. Add the exact Vercel origin to backend CORS_ORIGINS and the
appropriate Supabase auth redirect allowlist. Preview origins need an explicit
policy; wildcard authenticated access is not enabled.

For a local release build on Windows:

```powershell
.\scripts\build_web.ps1 -ApiBaseUrl https://YOUR-API-HOST -SupabaseUrl https://YOUR-PROJECT.supabase.co -SupabaseAnonKey YOUR-PUBLIC-KEY
```

The app no longer loads .env as an asset. Existing native/dev workflows must
also supply the three public values with --dart-define. Never supply provider or
service keys. A web release build is verified locally, but the Vercel remote build,
auth redirect behavior and hosted browser workflow still need deployment testing.

## Verification and release

```powershell
pytest backend\tests -q
flutter analyze --no-fatal-infos
flutter test
```

From backend/:

```powershell
python -m scripts.smoke_groq
python -m scripts.smoke_verification
python -m scripts.evaluate_retrieval --vignettes ../data/reviewed_vignettes.jsonl --output ../output/retrieval-evaluation.json
```

Live smoke scripts use synthetic content only. They are integration checks, not
clinical validation. The retrieval evaluator requires clinician-labelled gold
passage IDs from the exact reviewed corpus; no fabricated gold answers ship here.

Before clinical release, require external/local cohort validation, calibration,
clinician-adjudicated RAG safety evaluation, prospective silent use, human-factors
testing, an approved clinical safety case and applicable governance/regulatory
review. The current implementation does not satisfy those conditions by itself.

## Current research model and generation configuration

The application discovers the installed research forest through authenticated
model status and collects its exact eighteen-field contract before prediction.
See `MODEL_APP_INTEGRATION.md` for units, missingness and out-of-support handling.
It does not activate the separate unavailable clinical EOS model. Set
RESEARCH_PREDICTION_REQUIRES_AUDIT=true when research estimates must also require
durable database audit availability.

LLM_SCHEMA_ENFORCEMENT defaults to true. Generation, source audit, safety audit
and resolution use provider-enforced JSON schemas plus server validation. Use
a supported Groq structured-output model; unsupported combinations fail explicitly.
VERIFICATION_MAX_REPAIRS defaults to one, within VERIFICATION_BUDGET_SECONDS.
Only completed reviewer dissent on a valid draft can initiate a revision. Both
auditors review the revised claims again. Missing sections of the thirteen-section
review stay undetermined; this workflow never invents content to fill a template.

To use Ollama explicitly, set LLM_PROVIDER=ollama, LOCAL_LLM_MODEL to an installed
model, LOCAL_LLM_BASE_URL=http://127.0.0.1:11434/v1, VERIFIER_PROVIDER=ollama,
and VERIFIER_MODEL to that installed model. For Docker Desktop, use
http://host.docker.internal:11434/v1 instead of the container's loopback address.
Keep the Ollama service private. Set LOCAL_LLM_REASONING_EFFORT=none only if the
selected model supports it. There is no automatic provider fallback. Fully local
generation does not need cloud-processing consent. A Qwen3:4b local JSON-schema
transport check passed; local care-plan quality was not benchmarked.

For mixed-population guidelines, patient-specific passages additionally need
reviewed onset-scope metadata: population early_onset_neonatal or
neonatal_all_onset, scope_reviewed_by and scope_reviewed_at. Document-level
approval alone does not admit late-onset or unreviewed mixed-scope passages.
