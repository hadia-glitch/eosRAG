# Run NeoGuard locally and reproduce the current research checkpoint

The application remains research decision support. Source review and clinician
validation are incomplete. The current generation/audit rerun has **100/100** saved
synthetic cases: **67 reference-complete, 33 incomplete, 0 pending execution**.
The remaining cases completed after a key update; the separate v23 fresh pilot
then encountered exhausted named-account quotas. Those incomplete
outputs are retained, and neither heading presence nor reference completeness
establishes clinical usefulness. Existing ML weights were not changed.

## Local application

1. Install Flutter and Python 3.11 or a compatible tested runtime.
2. Create a virtual environment. From `backend/`, install
   `python -m pip install -r requirements-runtime.txt`.
3. Copy `backend/.env.example` to `backend/.env`. Supply your own Supabase URL,
   service/anonymous keys and server-only `GROQ_API_KEY`. Apply the database setup
   in [DEPLOYMENT.md](DEPLOYMENT.md). Register/sign in through your Supabase project.
4. Keep `CLINICAL_USE_ENABLED=false`. Cloud case processing remains disabled unless
   `ALLOW_CLINICAL_CLOUD_PROCESSING` is explicitly enabled under your data policy.
   Set `CORS_ORIGINS` to the exact Flutter web origin. Configure/review the source
   manifest and ingestion as described in the deployment runbook; an unreviewed
   corpus or unavailable provider must not be treated as evidence approval.
5. Start the backend from `backend/`: `python -m uvicorn main:app --reload --port 8000`.
6. From the repository root run `flutter pub get`, then
   `flutter run -d chrome --web-port 8080 --dart-define=API_BASE_URL=http://localhost:8000`.
   The backend serves the configured public Supabase bootstrap values. For Android
   emulator access use `http://10.0.2.2:8000` as the API base URL.
7. Select `RESEARCH_ML_MODEL=kaggle` or `pic` in the backend environment and restart
   the backend. PIC requires the privately obtained model/data artifacts described
   in the model runbook; restricted patient tables are not included in this repo.

For Ollama set `LLM_PROVIDER=ollama`, `VERIFIER_PROVIDER=ollama`,
`LOCAL_LLM_BASE_URL` to the OpenAI-compatible `/v1` endpoint and configure
`LOCAL_LLM_MODEL`/`OLLAMA_VERIFIER_MODEL`. Provider-routing regression fixtures pass;
this update does not claim a new live Ollama benchmark.

## What is integrated

The existing app source-selection workflow now uses bounded four-claim audit
batches with schema/ID checks and one contract retry. Incomplete audits still
withhold release. Audit requests share a hard time budget aligned with the mobile response deadline.
Care plans and explanations include recorded criterion states and current RR, SpO2 and CRP,
missing-observation actions, uncertainty and caregiver communication. Numeric and
boolean snapshots are range/type checked. Unicode microgram dose spellings are
blocked. Numbered action steps remain numbered in both plain and citation-linked
Flutter text; decimal measurements and quoted conditions are preserved.

The new v23 proposal-filtering research candidate is included for reproducibility;
its fresh pilot remains pending quota (an actual attempt stopped before a valid completed case). It is **not** substituted for the live
app's evidence selector and is not a clinically approved model.

## Research results and resume

- [Measured checkpoint](../output/research/rag_development/care_plan_100_v22/results.md)
- [100-case CSV with gold passages and all generated/held plans](../output/clinician-review/case_exports/neoguard_100_case_rerun_v22.csv)
- [100-case clinician bundle](../output/clinician-review/neoguard-100-case-care-plan-review.zip)

The checkpoint covers NICE 40/40, AAP 30/30 and WHO 30/30. Reference completeness is
39/40, 21/30 and 7/30 respectively; these are coverage counts, not clinical accuracy.
No new retrieval Recall/MRR/nDCG/Precision is inferred from generation results.
The benchmark was already exposed during development and is not an independent
clinical holdout. Reviewer forms are blank; no clinician ratings are fabricated.

The 100-case v22 run is complete; the following command safely skips completed cases.
For future authorized model calls, configure `GROQ_API_KEY` or optional `grok1` through
`grok5` in **backend/.env only**, then run:

```powershell
$env:PYTHONPATH='backend'
python backend/scripts/rerun_care_plans_100_v22.py
python scripts/summarize_care_plan_100_v22.py
python scripts/export_care_plan_100_v22.py --write-csv
```

Completed cases and model stages are reused only from the same pinned protocol.
Do not edit pinned research code and silently resume under the old protocol.
Operational key/rate-limit failures remain separate; completed poor-quality
outputs remain in the quality counts. The study uses GPT-OSS-120B and Qwen-27B
for distinct audit roles; the live app's verifier is selected by environment.
The private duplicate role cache is omitted from GitHub; completed per-case records
retain the successful call history. An interrupted stage may need recomputation
from a fresh clone even though the local checkout can resume more granularly.

Once available, run the separately pinned three-case v23 development check:
`python backend/scripts/pilot_offline_candidate_v23.py`. Its results must not be
merged into the original v22 population or treated as proof of clinical usability.

## Verification for this update

68 targeted backend tests and six Flutter presentation/explanation tests passed.
Flutter static analysis had no application errors; one informational unused import
was in the excluded demo-only integration test. No deployed infrastructure was
changed. Run the checks again on your configured host before deployment.
