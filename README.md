**UPDATED RESEARCH PAPER:** https://drive.google.com/file/d/1yqYmS4B5Aia3irZY26Eluns2DE1bnBqc/view?usp=sharing
# NeoGuard — Evidence-Grounded RAG for Neonatal Early-Onset Sepsis

> Research software for retrieving EOS guideline evidence, assembling patient-specific evidence packets, and producing structured, safety-gated care-plan drafts. **It is not a clinically validated or regulated medical device.**

**Continuity of work:** NeoGuard extends the earlier [AI-EOS research repository](https://github.com/hadia-glitch/AI-EOS/). Initial experiments remain historically documented there; this repository reports the current versioned RAG and verification work.

## What this repository contains

NeoGuard is an end-to-end research application consisting of a Flutter client and FastAPI backend. Its primary contribution is the RAG pipeline: it uses structured patient context to retrieve, rank, assemble and verify guideline evidence before a care-plan draft is released.

## System architecture

```text
Structured patient history + longitudinal changes
        ↓
Guideline / scope routing and clinical synonym expansion
        ↓
Sparse + dense retrieval → RRF fusion (k = 60)
        ↓
Medical cross-encoder reranking + MMR diversity selection
        ↓
Bounded recommendation / definition graph context
        ↓
Claim-level evidence mapping, safety checks and agentic verification
        ↓
13-section evidence-grounded care-plan draft
```



## Retrieval-arm implementation

| Arm | Implementation role in NeoGuard |
|---|---|
| Sparse | BM25-style lexical evidence retrieval for exact guideline terminology. |
| Dense | Embedding similarity retrieval for paraphrase-tolerant matching. |
| Hybrid | Sparse and dense rankings fused with RRF (`k=60`). |
| Vector | Source-scoped full-pool ranking with frozen medical and MiniLM cross-encoders. |
| Graph | The vector configuration with validated publisher-definition / recommendation context appended to the cross-encoder input view. |

The later source-scoped cross-encoder protocol deliberately scores every admitted passage. Consequently, sparse, dense and hybrid candidate signals do not override its final cross-encoder ranking; their control rows are score-equivalent. 
## Latest saved RAG results

The current development snapshot evaluates 100 synthetic vignettes: 40 NICE, 30 AAP and 30 WHO. Results below are from the latest saved plain-language / canonical-selector robustness run, with all 100 retrieval tasks completed. They are development results on an exposed synthetic benchmark—not independent test performance, clinician validation, or evidence of clinical benefit.

| Guideline | Recall@4 | MRR@4 | Recall@8 | Precision@8 | nDCG@8 | Coverage |
|---|---:|---:|---:|---:|---:|---:|
| NICE | 0.7667 | 0.8000 | 0.9375 | 0.3156 | 0.7791 | 40/40 |
| AAP | 1.0000 | 0.9167 | 1.0000 | 0.2500 | 0.9017 | 30/30 |
| WHO | 1.0000 | 0.8667 | 1.0000 | 0.2500 | 0.8515 | 30/30 |

Precision@8 must be interpreted against the annotation ceilings: 0.3344 for NICE and 0.2500 for AAP and WHO, because the available gold evidence per case is limited. Metrics use 2,000 case-level and scenario-family bootstrap resamples with seed 31. The wording robustness audit found query-sensitivity for NICE and AAP; this is retained in the results rather than hidden.

### Source-scoped cross-encoder controls at k=4

| Arm | NICE R@4 | NICE MRR@4 | AAP R@4 | AAP MRR@4 | WHO R@4 | WHO MRR@4 | All R@4 | All MRR@4 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Sparse candidate signal + CE | 0.717 | 0.963 | 0.583 | 0.625 | 0.717 | 0.850 | 0.677 | 0.828 |
| Dense candidate signal + CE | 0.717 | 0.963 | 0.583 | 0.625 | 0.717 | 0.850 | 0.677 | 0.828 |
| Hybrid RRF candidate signal + CE | 0.717 | 0.963 | 0.583 | 0.625 | 0.717 | 0.850 | 0.677 | 0.828 |
| Vector full-pool CE | 0.717 | 0.963 | 0.583 | 0.625 | 0.717 | 0.850 | 0.677 | 0.828 |
| Graph definition-view CE | 0.717 | 0.913 | 0.583 | 0.514 | 0.833 | 0.867 | 0.712 | 0.779 |

### Graph-RAG development results

The bounded `ce_definition_graph` configuration adds guideline-definition and recommendation relationships after retrieval. It is **not** proven superior to the vector full-pool arm across all guidelines, so it is presented as an implemented context mechanism rather than a universal performance claim.

| Guideline | Recall@4 | MRR@4 | Recall@8 | Precision@8 | nDCG@8 |
|---|---:|---:|---:|---:|---:|
| NICE | 0.7167 | 0.9125 | 0.8417 | 0.2750 | 0.7320 |
| AAP | 0.5833 | 0.5139 | 0.8333 | 0.2083 | 0.6651 |
| WHO | 0.8333 | 0.8667 | 0.9167 | 0.2292 | 0.8030 |

Do not compare the Graph-RAG table directly with the preceding robustness table: they were produced by distinct development configurations. The graph method improved early WHO retrieval in that development run, but did not consistently exceed the vector full-pool configuration.

## Verification-system implementation

The application separates generation from review. A plan is constructed from immutable source passages, then checked claim by claim for evidence identity, scope, patient-fit, exception coverage, category labels, drug-dose statements and missing required sections. Invalid verifier responses require schema-valid retries and cannot approve a claim. Rejected claims are removed without discarding unrelated supported material. Deterministic checks then enforce source identity, input bounds, missing-data signalling and no unsupported dosing. This is an engineering safety design, not proof of clinical safety.

## RAG innovations

- **Guideline-aware retrieval:** source and scope filters prevent evidence from the wrong guideline or setting being used to justify a claim.
- **Heterogeneous retrieval:** BM25, dense vectors and reciprocal-rank fusion capture complementary lexical and semantic signals.
- **Clinical query expansion:** controlled synonym and terminology expansion improves matching without silently changing the requested clinical question.
- **Medical reranking and diversity:** medical cross-encoder reranking prioritizes relevance; MMR reduces duplicate evidence in the final packet.
- **Bounded Graph RAG:** recommendation and definition relationships add only traced, source-linked contextual evidence; graph context is not treated as causal clinical knowledge.
- **Patient-conditioned evidence assembly:** the system records patient facts, missing observations, trends and evidence scope for each recommendation.
- **Claim-level verification:** verifier checks are designed to test grounding, guideline category labels, missing exceptions, patient-fit contradictions and unsupported dose statements before release.
- **Structured safety presentation:** plans render as a 13-section workflow with evidence identifiers, uncertainty handling and a caregiver note. Missing evidence is surfaced rather than guessed.



## ML-model transition and current testing configuration

The earlier AI-EOS/Track-A phase used a separate calibrated, SHAP-explainable synthetic-label research model. NeoGuard does not use that historical result as validation of the current configuration. The current app selects a research model using `RESEARCH_ML_MODEL`:

- `kaggle`: a tabular neonatal research classifier built around neonatal demographics, observations and laboratory features.
- `pic`: a longitudinal paediatric intensive-care research pipeline for timestamped observations.

Additional supplied neonatal data were reviewed during model development, including a small Figshare research dataset and synthetic maternal/neonatal data. They are not silently merged into the current predictor. The switch keeps risk prediction as optional contextual input: it cannot alter guideline scope, replace missing observations or justify a treatment claim. These models are research-only, require local artefacts and are **not** validated for clinical prediction, diagnosis or treatment decisions.

## Running locally

Prerequisites: Flutter/Dart, Python 3.13, a Supabase project with pgvector, and an approved guideline index. Configure `backend/.env` from `backend/.env.example`; keep `CLINICAL_USE_ENABLED=false` unless all local governance requirements have been met.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements-runtime.txt
.\.venv\Scripts\python -m uvicorn production_api:app --app-dir backend --host 0.0.0.0 --port 8000
```

In another terminal:

```powershell
flutter pub get
flutter run -d chrome --web-port 8080 --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

For full configuration, Supabase setup, deployment boundaries and model selection, see the [deployment runbook](docs/DEPLOYMENT.md), [model/data protocol](docs/DATA_AND_MODEL.md) and [model-selection notes](docs/research/model_selection.md). Never expose a Groq or Supabase service-role key to Flutter.

## Latest RAG outputs

Only the current RAG outputs are linked here:

- [Results index and interpretation](docs/research/latest_results.md)
- [Robustness metrics, intervals and declared variants (CSV)](output/research/rag_development/robustness_audit/all_retrieval_metrics.csv)
- [Bounded Graph-RAG development results](output/research/rag_development/semantic_guidance/results.md)





