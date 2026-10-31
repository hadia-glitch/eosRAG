#EOS refinements + Testing out different ml models on different datasets for risk prediction

- [Current research paper PDF](output/pdf/neoguard-eos-research-paper.pdf)
- [Deployment runbook](docs/DEPLOYMENT.md)
- [Current RAG development results and negative findings](docs/research/rag_development_report.md)


## Clinical presentation and maternal-model research


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

-[Current results index](docs/research/latest_results.md) distinguishes the latest robustness checks from earlier original-wording results. 
- [Latest RAG development results ZIP](output/research/neoguard-rag-development-results.zip)
- [100-case clinician review bundle ZIP](output/clinician-review/neoguard-100-case-clinician-review.zip)

