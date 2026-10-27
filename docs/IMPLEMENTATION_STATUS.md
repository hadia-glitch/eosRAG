# Implementation and validation status

This change is a research/staging implementation. It is not a completed clinical
release, and no live deployment or database migration was performed.

## Current RAG development boundary (28 October 2026)

Final evaluation remains on hold. The latest consensus regression on the same
100 exposed cases has Recall@4 / MRR@4 of NICE 0.6792 / 0.7875, AAP 0.7500 /
0.7083 and WHO 0.8000 / 0.8500. All source-specific confidence intervals and
unsuccessful variants remain in the development CSVs. These are retrieval
results, not clinical answer-usability measurements or a hosted-index validation.
The paper adds a labelled development section and explicit metric ceilings.

The prepared publication checkout passed 85 targeted backend regression tests
and all 26 included Flutter tests. The checks cover source scope, input contracts,
audit contracts, formatting, SHAP presentation and the RAG care-setting bridge.
This is a separate current checkpoint from the historical counts below.
The new clinician bundle has 100 synthetic cases, shuffled evidence panels and
blank source/relevance review forms. Clinical review and source approval are pending.

| Component | Implemented | Still required |
| --- | --- | --- |
| EOS prediction | Actual pinned days-0-2 calibrated forest connected to the app's eighteen-field review; digest checks, missingness/support checks, real local Kernel SHAP | Valid EOS outcomes, documented dataset units/provenance, event tables, cohort review, external and prospective validation |
| Patient history | Recorded-measurement timeline, real elapsed-time trends, missing values preserved | Continuous monitor integration and measurement-availability audit |
| RAG | Reviewed registry, source/version/digest/scope checks, text+pgvector fusion, reranking, degradation reporting | Source approval, ingestion, actual database migration, clinician-labelled retrieval evaluation |
| Knowledge graph | Parameterized Neo4j concept-to-passage indexing and expansion | Provision Neo4j and evaluate graph ablations; no medical causal graph is claimed |
| Verification | LangGraph generator plus source/safety auditors, provider-enforced schemas, exact quote/claim IDs, one bounded revision with fresh audits; thirteen review sections | EOS-specific expert adjudication; shared-model correlated-error analysis |
| Security | Auth and owner checks, admin separation, request bounds, no-store responses, client secret exclusion, decision provenance | Live RLS/migration verification, operational hosting review, applicable institutional compliance work |
| Web deployment | Vercel config, pinned Flutter build script, successful local release build | Actual API host, CORS/auth redirects, Vercel deployment and hosted integration checks |
| Container | Final CPU image built; non-root/read-only/offline inference, SHAP, authentication, cached encoder/reranker and strict-schema checks passed | Hosted integration and operational checks |
| Research | Actual supplied-label training, patient-cluster bootstrap, synthetic retrieval and generation ablations | Validated EOS cohort and an independent evaluation set |

The earlier research report has twelve tables and three figures. Measured
results and reproducible raw synthetic outputs are indexed in
`output/research/RESULTS.md` and `docs/RESEARCH_EXPERIMENTS.md`. The revised run
produced 15/18 drafts and released 4/18; all 12 injected faults were withheld
(nine semantic rejections and three deterministic dose rejections). Conditional
BERTScore did not improve with verification, and concept expansion reduced
retrieval recall. These negative findings remain in the report.

Verification checkpoints: 110 backend tests and 21 Flutter tests passed. Flutter
analysis reports no issues. The earlier web release build and opt-in fixture
capture passed; the current native mobile workflow and its separate demo APK
are excluded from this public repository. Synthetic
Groq strict-schema generation and complete LangGraph verification passed with openai/gpt-oss-120b.
A local Ollama Qwen3:4b-q4_K_M constrained-JSON transport check passed without
cloud fallback; local care-plan quality has not been benchmarked.
A synthetic source-scope mismatch was also withheld. These are engineering and
integration tests, not clinical validation. The release bundle was scanned for
environment assets and configured server keys with no matches found.

The current local .env files were preserved and removed from Git tracking. No
credentials are embedded in the new client build. Existing Git history is not
rewritten by this operation.

Provider execution failures are excluded from model-quality populations; their
operational records are separate. Completed malformed responses and reviewer
dissent remain quality outcomes. The original quote-echo comparison has eight
completed cases, the revised primary comparison eighteen, and each additional
backbone three. On the same three cases, one bounded revision changed release
counts from 0 to 1 for GPT-OSS-20B and from 1 to 2 for Qwen3.8-27B. These small,
previously exposed development comparisons do not establish clinical benefit.

The 0.9992 days-0-2 test AUC remains suspiciously high. Direct overlap and
preprocessing checks passed, and shuffled-label controls were near chance;
unknown label construction, measurement timing and source identity prevent a
claim of leakage-free clinical EOS prediction. See the paper's additional audit.
The exploratory four-estimator ensemble comparison does not replace the pinned
application forest automatically.

The local dataset ZIP includes a hash manifest, the exact supplied CSV and all
synthetic application/evaluation fixtures. Its Phase 1 addition preserves the
original 100-case inputs, frozen ten-case pilot, fresh judgments and seven result
CSVs, the probability audit, and a separate corrected 100-case / 300-observation
development set without invented EOS outcomes. Check the bundled progress.json
for completion; unfinished judgments remain NOT EVALUATED. It contains
no MIMIC patient rows and has no verified public redistribution license. The
older 62-second H.264 MP4 uses actual Flutter widgets with recorded synthetic responses;
it does not demonstrate live authentication, storage, graph access or deployment.
Unrelated documents, personal PDFs, old inventories and a duplicate environment
were moved recoverably outside the repository; see CLEANUP_MANIFEST.json.

## Project concepts adapted from the supplied descriptions

| Inspiration | Adaptation and limit |
| --- | --- |
| 53459: Personalized digital health app | Serial observations and patient-specific evidence context; no neonatal gamification or persuasion logic |
| 54550: Independent medical verification | Separate generator and auditor prompts/roles, complete claim coverage and explicit dissent; no claim of independent model errors |
| 54496: AI Hospital | Safety-review role and staged-case evaluation design; autonomous hospital agents and clinical orders are not implemented |
| Evidence-grounded research assistant | Claim-to-quote-to-passage links and unsupported-claim withholding |
| 51904: Cultural-HALO | Evidence sensitivity and language/subgroup robustness are evaluation requirements; multilingual clinical validity is not claimed |
| 52817: Readable safety procedures | Plain-language status and uncertainty messages; clinician approval remains necessary for simplified medical instructions |
| 53947 / patient-provider communication work | Clinician-facing explanations and human-factors evaluation; private conversation models or datasets were not imported |
| 51780: Agentic data engineering | Reproducible offline cohort, model, source and graph jobs; no LLM-generated SQL executes against patient data |

The supplied MIMIC files in Downloads were inventoried; 7,863 newborn admission
candidates require review. Event tables, exact birth times, gestation and reviewed
EOS outcomes remain necessary. See `RESEARCH_EXPERIMENTS.md`, `DATA_AND_MODEL.md`
and `DEPLOYMENT.md` for reproducible commands and the remaining release gates.

Demo recordings, packages and related implementation helpers are excluded from this public app/research repository.

Phase 1 is complete: ten frozen cases, fifty rankings, 206 unique passage
judgments, eighty source-separated plan-review stages covering forty outputs,
and twenty freshly scored reference pairs. The seven result CSVs and complete
decision record are in `output/research/phase1_pilot/`; the full paper includes
the measured pilot and score-saturation audit. The decision is REVISE. Historical
plan grounding and evaluator errors remain material limitations. Provider
failures were excluded from quality means. A subsequent fixed synthetic control
made three fresh calls and produced eleven accepted source-selected claims,
thirteen review sections and nine supported guidance sections; it is an
integration control, separate from the historical experiment.
