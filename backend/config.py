from functools import lru_cache
from pathlib import Path
from pydantic import Field
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ENV_FILE = Path(__file__).with_name(".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_anon_key: str = ""

    # ── LLM provider chain ────────────────────────────────────────────────────
    # Order: Local LLM (if enabled) -> Gemini -> Groq -> rule-based fallback.
    # See services/llm_provider.py for the actual chain logic.
    #
    # Local LLM (Mistral-7B via Ollama or vLLM) — no data ever leaves your
    # infrastructure when this is the only enabled provider. Point at any
    # OpenAI-compatible chat completions endpoint: Ollama's own
    # (http://localhost:11434/v1) or a production vLLM server
    # (http://<vllm-host>:8000/v1) both work without further code changes.
    # Master switch: true = use local Ollama/vLLM first; false = skip local,
    # use Gemini/Groq cloud chain directly. Flip USE_LOCAL_LLM in .env.
    use_local_llm: bool = False

    local_llm_enabled: bool = True
    local_llm_base_url: str = "http://localhost:11434/v1"
    local_llm_model: str = "qwen3:4b-q4_K_M"
    # 600s (10 min): 300s wasn't enough for a real care-plan prompt (5
    # retrieved chunks + full patient/risk payload + 7-section JSON schema
    # instructions) on CPU-served Qwen-7B — confirmed by an isolated,
    # non-concurrent request still hitting the 300s ceiling. This value is
    # deliberately generous for testing/dev so you can see a real
    # generation complete at least once and get a true sense of actual
    # latency on this hardware, rather than guessing at increasingly larger
    # numbers. Once you have a real completed-generation timestamp, dial
    # this back down to something closer to that measured time + margin —
    # 10 minutes is not a number to ship to production, it's a diagnostic
    # ceiling. Lower substantially once local inference is GPU-backed.
    local_llm_timeout_seconds: int = 30
    # Ollama compatibility aliases: "none" requests no optional thinking.
    # Set empty to retain the installed model's default behavior.
    local_llm_reasoning_effort: str = 'none'
    # How long Ollama/vLLM keeps the model resident in memory after a
    # request before unloading it. Ollama's own default is "5m" — too
    # short for normal dev iteration (edit code, wait for --reload, click
    # around the app), so every gap longer than that pays a full cold
    # reload on the next request. "30m" keeps it warm through a normal
    # dev/testing session; use "-1" to keep it loaded indefinitely (only
    # do this if you have RAM to spare, since it'll never release those
    # ~5GB back to the OS). Passed straight through as the OpenAI-API
    # `keep_alive` field — vLLM ignores it if not applicable.
    local_llm_keep_alive: str = "30m"
    # Grammar-constrained JSON decoding (Ollama/vLLM's response_format=
    # json_object). Stronger guarantee of parseable JSON, but on CPU this
    # commonly costs a 5-10x per-token slowdown, which is almost certainly
    # why a plain `ollama run` chat feels fine while an API call with the
    # full 7-section care-plan schema prompt takes minutes. Default OFF —
    # we rely instead on a strong system-prompt instruction plus
    # llm_provider.py's automatic retry-on-parse-failure. Set
    # LOCAL_LLM_JSON_MODE=true once you're on a GPU, where the per-token
    # overhead is negligible and the stronger guarantee is worth it.
    local_llm_json_mode: bool = False

    # HIPAA-strict mode: when True, Gemini/Groq are NEVER attempted even if
    # API keys are configured — guarantees zero external network calls for
    # any LLM request, regardless of local LLM failures (falls straight to
    # the rule-based fallback instead of ever reaching out to a cloud API).
    # Leave False during development for a working system before your local
    # LLM is fully set up; set True once you're ready to lock it down.
    disable_cloud_llm_fallback: bool = False

    # ── LLM keys (cloud fallback — optional once local_llm_enabled=True) ─────
    # Primary: Gemini (Google AI Studio — free tier, AQ. or AIza keys both work)
    gemini_api_key: str = ""
    # Fallback: Groq (free tier, fast, Llama 3.3 70B)
    # Get key at: https://console.groq.com/keys
    groq_api_key: str = ""

    # ── Model names ──────────────────────────────────────────────────────────
    # Gemini: gemini-1.5-flash or gemini-2.0-flash
    gemini_model: str = "gemini-1.5-flash"
    # Groq fallback model — Llama 3.3 70B is best quality on Groq free tier
    groq_model: str = "openai/gpt-oss-120b"
    llm_provider: str = "groq"
    verifier_model: str = "openai/gpt-oss-120b"
    verifier_provider: str = ''
    ollama_verifier_model: str = ''
    llm_timeout_seconds: float = 25.0
    verification_max_repairs: int = Field(default=1,ge=0,le=1)
    verification_budget_seconds: float = Field(default=80.,ge=10.,le=120.)
    llm_schema_enforcement: bool = True
    cors_origins: str = "http://localhost:3000,http://localhost:8080"
    max_request_bytes: int = 262144
    model_artifact_path: str = str(Path(__file__).parent / "ml/artifacts/model.json")
    model_artifact_sha256: str = ""
    supplied_model_dir: str = str(Path(__file__).parent / 'ml/deployed/supplied_neonatal')
    research_ml_model: Literal['kaggle','pic'] = 'kaggle'
    pic_model_dir: str = str(Path(__file__).resolve().parents[1] / 'data/picdb_private')
    research_prediction_requires_audit: bool = False
    clinical_use_enabled: bool = False
    evidence_manifest_path: str = str(Path(__file__).parent / "guidelines/manifest.json")
    require_reviewed_evidence: bool = True
    enable_knowledge_graph: bool = False
    neo4j_uri: str = ""
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"
    allow_clinical_cloud_processing: bool = False

    # ── Other settings ────────────────────────────────────────────────────────
    guidelines_dir: str = "./guidelines"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Embedding model. Default stays on all-MiniLM-L6-v2 (384-dim) — it's
    # what the current pgvector column and ingested chunks were built with,
    # so switching the default here without a re-ingest + column migration
    # would silently break cosine search (dimension mismatch).
    #
    # BAAI/bge-m3 (1024-dim, multilingual, stronger clinical/medical recall
    # in benchmarks than MiniLM) is a meaningful upgrade and is supported —
    # to switch to it:
    #   1. ALTER TABLE evidence_chunks ALTER COLUMN embedding TYPE vector(1024);
    #      (drop and recreate the ivfflat index after — see rebuild_index.py)
    #   2. Set EMBEDDING_MODEL=BAAI/bge-m3 and EMBEDDING_DIM=1024 in .env
    #   3. Re-run ingestion (rag/ingest.py --clear) so every chunk is
    #      re-embedded at the new dimension — old 384-dim rows are not
    #      compatible and must not be left mixed in the table.
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    # Ablation switch: "fixed" (default) | "semantic" | "proposition"
    chunking_strategy: str = "clinical"
    # Ablation switch: when True, query_refiner runs before retrieval
    enable_query_refinement: bool = False
    chunk_size: int = 512
    chunk_overlap: int = 50
    rrf_k: int = 60
    retrieval_top_k: int = 10
    rerank_top_k: int = 5

    # ── Engineering heuristics — NOT guideline-derived ───────────────────────
    # These two numbers do not trace to NICE/AAP/WHO or any cited source.
    # NICE NG195 and the AAP GBS statement explicitly decline to specify a
    # numeric CRP cutoff (serial trend + clinical picture, not a magic
    # number) — so crp_delta_threshold is a retrieval-query-expansion trigger
    # we chose, not a clinical value. guideline_nudge_weight is a plain IR
    # reranking hyperparameter; no guideline specifies how to break a
    # near-tie between two retrieval sources. Both are named here (not
    # inline magic numbers) specifically so they can be swept in an ablation
    # and reported as deliberate, tested engineering choices in the paper's
    # methods section, rather than left as unexplained constants.
    crp_delta_threshold: float = 2.0
    guideline_nudge_weight: float = 0.15

    # ── Fact-checking judge (Phase 3) ────────────────────────────────────────
    # Gated to HIGH/CRITICAL by default to control latency + LLM cost — see
    # rag/fact_check.py for rationale. Comma-separated list, case-insensitive.
    enable_fact_check: bool = True
    fact_check_categories: str = "HIGH,CRITICAL"

    @property
    def fact_check_category_set(self) -> set[str]:
        return {c.strip().upper() for c in self.fact_check_categories.split(",") if c.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
