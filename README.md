# EOS refinement (October 2026)

[Latest app safety integration, completed 100-case research run, run instructions and clinician review bundle](docs/RAG_REVIEW_UPDATE.md). All 100 generation/audit cases are saved: 67 are reference-complete and 33 are incomplete. Clinical usefulness remains unvalidated; the separate v23 candidate fresh pilot is pending API quota.

The current ASGI entry point uses authenticated, source-reviewed EOS workflows.
The live app's hand-built point score has been retired. The bundled calibrated
forest is connected through an eighteen-field research input review and actual
SHAP explanations. Clinical validation and source
approval remain required; this repository is not a clinically cleared product.

- [Deployment runbook](docs/DEPLOYMENT.md)
- [Data and model protocol](docs/DATA_AND_MODEL.md)
- [Research paper](docs/research/manuscript.md)
- [Experiment reproduction and measured artifacts](docs/RESEARCH_EXPERIMENTS.md)
- [Connected model, input mapping and limitations](docs/MODEL_APP_INTEGRATION.md)
- [Implementation and validation status](docs/IMPLEMENTATION_STATUS.md)
- [Current RAG development results and negative findings](docs/research/rag_development_report.md)
- [Gate before final evaluation](docs/research/final_evaluation_gate.md)

Supplied-label neonatal research classifiers have now been trained on the provided
Kaggle archive. Data-integrity and outcome-provenance findings keep them separate
from the clinical EOS predictor. Synthetic RAG experiments retain drafts, reviews,
per-case metric results under `output/research/`. Provider execution failures are
excluded from model-quality denominators and retained separately under
`output/operational/`. Completed malformed responses and auditor dissent remain
in the quality evaluation.

## Published scope

This repository contains the Flutter application, FastAPI backend, pinned research
model, database migrations, application tests, research methods, measured outputs,
synthetic research fixtures and final papers. Native demo entry points, capture
scripts, videos, APKs, scratch tools, operational logs, credentials and private data
archives are excluded. The local full-data bundle is not a public data release.

The seven Phase 1 result CSVs are in `output/research/phase1_pilot/`. Final reports
are in `output/pdf/`. Historical paper and audit records retain their original
measurements and references, including the separate local integration controls;
those controls and private source files are not published here. Research scores
do not establish clinical readiness.

Obtain guideline PDFs and restricted clinical datasets through their original
providers. The guideline manifest records candidate hashes and review gates;
copyrighted source PDFs and MIMIC patient tables are not included. Training accepts
the original privately obtained CSV archive; synthetic fixtures are for evaluation.

Run `pytest backend/tests -q`, `flutter analyze --no-fatal-infos`, and `flutter test`.
Use the deployment runbook to configure Supabase, the backend host and Vercel.

## Clinical presentation and maternal-model research

Clinical output uses spaced paragraphs, bold labels, separate bullet lines and
tappable evidence citations. The thirteen care-plan sections have distinct
colors and text labels. SHAP explanations include a waterfall whose signed
contributions reconcile to the displayed research-model score. The model input
screen keeps a concise research label and essential measurement guidance.

[Maternal/neonatal mixture methods and measured results](docs/MIXED_MODEL_RESEARCH.md)
describe the separate synthetic stacking model and common-feature transfer study.
The simulation artifact is not installed as the app's predictor. All source,
target, timing and clinical-validation limitations remain explicit.

## Run locally

Requirements: Flutter compatible with Dart >=3.12.1, Python 3.13, and a Supabase project with pgvector. Android needs an Android SDK/emulator; web needs Chrome. Run commands from the repository root unless stated otherwise.

1. Create `backend/.env` from `backend/.env.example`. Set Supabase URL, public anon key, server-only service key, and Groq configuration. Keep `CLINICAL_USE_ENABLED=false`. Set `RESEARCH_ML_MODEL=kaggle` or `pic`; see [model selection](docs/research/model_selection.md). PIC requires separately provisioned restricted artifacts and timed observations; they are not included in Git.
2. Apply the migrations and source-review setup in [the deployment runbook](docs/DEPLOYMENT.md). Create a Supabase Auth account. The authenticated app requires the database/auth service; an empty or unapproved guideline index deliberately withholds clinical generation. Source PDFs must be obtained separately and reviewed before ingestion.
3. Start the API (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python -m pip install -r backend/requirements-runtime.txt
.\.venv\Scripts\python -m uvicorn production_api:app --app-dir backend --host 0.0.0.0 --port 8000
```

4. In a second terminal, start Flutter with public configuration only:

```powershell
flutter pub get
flutter run -d chrome --web-port 8080 --dart-define=API_BASE_URL=http://127.0.0.1:8000 --dart-define=SUPABASE_URL=https://YOUR-PROJECT.supabase.co --dart-define=SUPABASE_ANON_KEY=YOUR-PUBLIC-KEY
```

Add `http://localhost:8080` and/or the actual browser origin to backend `CORS_ORIGINS`, then restart the API. For Android, use `flutter devices`, replace `-d chrome --web-port 8080` with `-d DEVICE_ID`, and use `http://10.0.2.2:8000` for the standard Android emulator's host API. Physical devices require a reachable host address. Native HTTP is for local development; deploy with HTTPS.

Only the public Supabase key belongs in Flutter. Never pass Groq or service-role keys to the client. `/health` is liveness, not clinical approval. Vercel serves Flutter web; host FastAPI separately as described in the runbook.

## Latest research results and clinician review

[Current results index](docs/research/latest_results.md) distinguishes the latest robustness checks from earlier original-wording results. The final research evaluation and promotion of the experimental RAG candidate remain on hold; publishing this development snapshot does not pass those gates. Both ML choices remain research-only.

- [Latest RAG development results ZIP](output/research/neoguard-rag-development-results.zip)
- [Latest robustness metrics CSV, including intervals and depths 4/8](output/research/rag_development/robustness_audit/all_retrieval_metrics.csv)
- [Development clinician review bundle ZIP](output/clinician-review/neoguard-development-clinician-review.zip)
- [100-case clinician review bundle ZIP](output/clinician-review/neoguard-100-case-clinician-review.zip)
- [Clinician instructions and blank review forms](output/clinician-review/neoguard-development-review/README.md)
- [Current research paper PDF](output/pdf/neoguard-eos-research-paper.pdf)

The review bundles contain synthetic cases, evidence panels and blank ratings. No clinician sign-off or clinical validation has been completed. Operational rate-limit failures are recorded separately from answer-quality results. Demo recordings and capture machinery are excluded from GitHub.
