# EOS refinement (October 2026)

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
