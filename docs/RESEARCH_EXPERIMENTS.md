# Reproducing the neonatal research experiments

The Kaggle archive is read in place; raw rows and patient identifiers are not
copied to public outputs. The supplied description does not identify an original
clinical study, collection sites, license, culture confirmation or onset times.
Its labels support concurrent classification experiments, not a claim of future
EOS prediction. Concentration at the upper birth-weight value and very high separability warrant source
investigation; they do not by themselves prove synthetic origin.

From `backend/`:

```powershell
python -m ml.research_cohort --archive 'C:\Users\hadia\Downloads\archive (1).zip' --output ..\output\research
python -m ml.prepare_mimic review --root C:\Users\hadia\Downloads --output ..\data\mimic_review
```

The trainer uses fixed patient-ID-disjoint 55/15/15/15 fit/calibration/validation/
test partitions, training-only preprocessing, patient-weighted fitting and Platt
calibration, selection by validation Brier, and 300 patient-cluster bootstrap
replicates for the selected model. Observation_Hour and Patient_ID are excluded
from predictors. No artificial birth timestamps or adjudicated labels are made.
All ages and postnatal days 0-2 are separate experiments. The latter age filter
does not establish culture-confirmed EOS or a pre-onset forecast.

`output/research/` contains audit, evaluation, model JSON and SHA-256 files.
`ml.predict_research_csv` provides digest-checked batch inference with explicit
supplied-label output. It is deliberately separate from the clinical API. The
clinical API requires the different `eos-landmark-v1` feature contract and reviewed
EOS artifact. CLINICAL_USE_ENABLED remains false.

Synthetic RAG evaluation commands:

```powershell
python -m scripts.evaluate_generation prepare --output ..\output\research\rag_v2
python -m scripts.evaluate_generation run --output ..\output\research\rag_v2
python -m scripts.evaluate_generation run --output ..\output\research\rag_v2 --retry-transport-failures
python -m scripts.evaluate_generation stress --output ..\output\research\rag_v2
python -m scripts.evaluate_generation judge --output ..\output\research\rag_v2
..\.venv\Scripts\python.exe -m scripts.evaluate_generation score --output ..\output\research\rag_v2
```

Do not rerun prepare over a completed experiment after editing its cases. Keep
each revision in its own directory. Initial quote-echo raw attempts, runs and
judgments are retained in `output/operational/quote_echo/`; the original cases,
corpus and retrieval protocol stay in `output/research/rag/`. `rag_v2/` uses immutable quote IDs with
server-side exact-text materialization. Transport retries retain existing drafts
and completed auditor disagreements; old attempts are archived. API keys never
appear in result files. The synthetic benchmark never approves production sources.

The benchmark has 18 vignettes in six related families, engineering-authored
references frozen before inference, and 12 injected faults. It is a development
evaluation, not an independent test of generalization. BLEU/METEOR/ROUGE and two
BERTScore backbones measure reference alignment. A same-model, arm-blinded judge
provides fallible grounding, fidelity, completeness, actionability and uncertainty
proxies. Report judge availability, release coverage and withheld responses.
Report all-case and released-only metrics together; filtering is not rewriting.

Install optional metric dependencies using `requirements-evaluation.txt` in an
isolated CPU environment. The local `.venv` has working CPU PyTorch; the system
Python's PyTorch DLL import fails. Recorded package versions in metric outputs
take precedence over assumptions about either environment. WordNet and model
weights must be available; HF_HUB_OFFLINE=1 can enforce cached-only scoring.

Offline retrieval compares BM25, exact dense cosine, reciprocal-rank hybrid, and
concept expansion. These measurements do not benchmark live pgvector or Neo4j.
Clinical source approval and database migration remain separate deployment work.

## Extended audit, backbones and application fixtures

`output/research/leakage_audit/audit.json` records partition overlaps,
preprocessing reconstruction, shuffled-label controls, feature ablations and
sampled nearest-neighbor checks. `ml.ensemble_experiment` records exploratory
GB/XGBoost/linear-SVM/forest and equal-average comparisons on the previously
exposed partitions. The application remains pinned to its original calibrated
days-0-2 forest; these exploratory results do not silently replace it.

`output/research/backbones/` and `backbones_resolution/` retain the same three
declared cases for GPT-OSS-20B and Qwen3.8-27B with zero and at most one revision.
All three cases completed provider execution for each model. Completed schema
errors and dissent remain in denominators. Primary `rag_v2` has eighteen
completed provider executions; the historic quote-echo comparison has eight.
`quality_population.json` records the quality population. Operational exclusions
and archived retry attempts are separate, with successful role outputs reused.
No API outage is counted as a model-quality error or given a zero text score.

Those numerical experiments used their frozen JSON-object protocols. The later
provider-enforced strict schemas were tested with synthetic Groq and local
Ollama controls and are not retrospectively credited with benchmark improvements.

`scripts/package_test_data.py` creates the local ignored data ZIP: the exact
supplied CSV, synthetic cases/references, source passages, retrieval labels,
protocol and application fixtures (including SHAP, plan and patient replay).
Its manifest records file hashes. MIMIC source hashes are inventoried but patient
rows are not bundled or used in reported training. Source redistribution rights
remain unverified; the ZIP is a private reproduction artifact.

The opt-in Flutter screen capture and MP4 use actual widgets with recorded
synthetic fixture responses. See `output/demo/README.md` for reproduction and
the limits of that replay.
