# Neonatal data and model protocol

Six user-downloaded MIMIC-III tables have now been inventoried locally. The review
job found 7,863 candidate newborn admissions and wrote sensitive review materials
under ignored `data/mimic_review/`. CHARTEVENTS and LABEVENTS are still absent.
No MIMIC outcome labels have been adjudicated and no MIMIC model has been fitted.

The supplied Kaggle ZIP was used to fit separate **supplied-label research
classifiers**, described in `RESEARCH_EXPERIMENTS.md`. Its 100,000 rows have
patient/hour conflicts, changing immutable covariates and unverified outcome
provenance. Those artifacts deliberately cannot load through the clinical EOS
model contract. Do not rename their target or approve them by editing metadata.

## Eligibility and outcome

The research target is culture-confirmed early-onset bacterial sepsis within the
first 72 hours after birth, with serial prediction before diagnostic culture
collection. Define contaminants, pathogen inclusion, episode rules, collection
versus result time, transfer status, antibiotic exposure, incomplete follow-up,
death and competing events with a neonatal clinician before extraction.

An ICD sepsis code is not a culture-confirmed label. A missing/negative culture is
not automatically a non-sepsis label. Confirm controls have adequate ascertainment
through 72 hours. Clinical sepsis, mortality, LOS and treatment decisions are
different targets and must not be mixed into the EOS outcome.

[MIMIC-III](https://physionet.org/content/mimiciii/1.4/) has historical neonatal ICU
records, but the available cohort and maternal-variable completeness need audit.
NICU selection does not represent all live births. Date shifts preserve relative
within-patient intervals, not real calendar order across patients; the training
script therefore uses deterministic patient hashing for MIMIC and reports that
this is not temporal validation. A separate external cohort remains necessary.

## Local files and extraction

Recommended table set: PATIENTS, ADMISSIONS, ICUSTAYS, D_ITEMS, D_LABITEMS,
LABEVENTS, CHARTEVENTS and MICROBIOLOGYEVENTS, as CSV or CSV.GZ. Keep the files
outside version control and follow the PhysioNet data-use agreement. The supplied
adapter currently consumes ADMISSIONS, MICROBIOLOGYEVENTS, both item dictionaries,
and the mapped event tables. PATIENTS/ICUSTAYS support cohort review, not automatic
ground truth. The large CHARTEVENTS table is streamed rather than loaded wholesale.

From backend/:

```powershell
python -m ml.prepare_mimic review --root C:\PATH\TO\MIMIC --output ..\data\review
```

This creates a neonatal-admission candidate list, blood-culture review extracts
and item catalog. These outputs remain sensitive research data. The template
deliberately leaves exact birth time, gestation, label and reviewer unfilled:
admission time and a midnight DOB cannot silently substitute for an exact birth
time. Verify newborn eligibility using the additional tables and source records.

Fill the adjudication CSV with subject_id, hadm_id, reviewed birth_time,
gestational_age_weeks, birth_weight_g if known, binary label, label_adjudicated,
culture_collection_age_hours, followup_hours, and reviewer. The reviewer field
records provenance; the software cannot establish that a person is qualified or
that the label is correct. Document adjudicator disagreement and resolution.

Copy ml/item_map.example.json and map reviewed item IDs to feature names from
ml/features.py. Each mapping has feature, unit, and optional factor/offset.
Document reviewed_by and reviewed_at. Do not guess units from numeric magnitude.
Example **shape only**, not a real MIMIC item ID:

```json
{"CHARTEVENTS": {"REVIEWED_ITEM_ID": {"feature": "neonatal_temperature", "unit": "Deg C", "factor": 1, "offset": 0}}, "LABEVENTS": {}, "reviewed_by": "REVIEWER", "reviewed_at": "ISO_TIMESTAMP"}
```

CHARTEVENTS uses the later of CHARTTIME and STORETIME as availability. LABEVENTS
does not provide a reliable result-availability timestamp; it is excluded unless
an explicitly reviewed availability_delay_hours is specified. Such a latency
assumption is a sensitivity-analysis choice and must not be called observed truth.
Measurements older than six hours are not carried into a later landmark. The
adapter uses available measurements at 6, 12, 24, 36 and 48 hours and reconstructs
earlier three-hour observations causally. It excludes landmarks at/after diagnostic
culture collection. Inspect admission transfers, invalid values and missingness.

```powershell
python -m ml.prepare_mimic build --root C:\PATH\TO\MIMIC --adjudications ..\data\review\adjudicated.csv --item-map ..\data\review\item-map.json --output ..\data\eos.jsonl
python -m ml.train --data ..\data\eos.jsonl --output ml\artifacts
```

## Feature and estimator contract

PredictionRequest contains an index observation and strictly earlier observations,
each with age_hours and a whitelist of measurements. Normalized units include CRP
mg/L, creatinine mg/dL, weight grams and temperature Celsius. Blood-culture result,
outcome labels, clinician risk category and legacy scores are excluded predictors.
Current values, explicit missingness, 24-hour deltas/counts and time-based slopes
share one implementation between fitting and inference. Missing remains unknown;
median imputation and standardization are fitted on the training partition only.

Four patient-disjoint sets allocate approximately 55/15/15/15 percent to fitting,
calibration, model selection and final testing. For unshifted birth times, boundaries
must be strictly temporal; tied boundaries fail rather than leak. Predictor
selection is training-only. Candidates are regularized logistic regression and a
depth-limited random forest. Each receives separate Platt calibration. Validation
Brier score selects the exported candidate; the test set is reported once. Patient
weights reduce domination by repeated landmarks during fitting/calibration.

Outputs: portable model.json, model.sha256 and evaluation.json. No executable
pickle is loaded. Numeric parity with scikit-learn is checked before export. The
runtime requires an exact digest pin, checks cohort scope and missingness, and
abstains outside training support. LR contributions are standardized log-odds;
forest contributions are median-replacement probability differences, not SHAP,
causal attribution or additive percentages. Do not interpret them as treatment
effects. The app presents research probability without a made-up treatment category.

## Required evaluation beyond the implemented trainer

Report EOS prevalence, patients/episodes/landmarks, culture positives, exclusions,
site/gestation/sex groups where appropriate, missingness and treatment timing.
Report AUROC, AUPRC, Brier score, calibration curves/intercept/slope, sensitivity,
specificity, PPV and decision-curve net benefit. The trainer currently reports
landmark AUROC/AUPRC/Brier, calibration bins and threshold operating metrics.
Add patient-cluster bootstrap confidence intervals, episode-level sensitivity,
time-to-detection, external/site validation and clinically chosen acceptable
miss rates before release. Five positive/negative examples per partition is only
an engineering floor in the script; it is nowhere near a clinical sample-size
justification. Record prevalence corrections if case-control sampling is used.

Perform ablations for snapshot-only versus serial features; LR versus forest;
calibrated versus uncalibrated estimates; measured availability versus assumed
lab delays; and NICU versus intended deployment population. Evaluate subgroup
calibration and abstention coverage. An apparent gain from CRP measured after
clinical suspicion may reflect workflow leakage rather than earlier detection.

The trainer always writes validation_status=research_only. Promotion requires a
separately reviewed artifact and a documented clinical validation/safety case.
Changing that string or CLINICAL_USE_ENABLED is not evidence of clinical safety.

## Installed supplied-label application model

The separately gated research endpoint now serves the pinned days-0-2 calibrated
forest from the supplied CSV. The client collects its eighteen-field contract;
see `MODEL_APP_INTEGRATION.md`. Its default lightweight explanation remains a
median-replacement effect. The separate **Explain with SHAP** action computes
actual bounded local Kernel SHAP with prediction-parity and additive checks.
These are associations in the supplied-label classifier, not causal evidence or
a validated EOS probability. The post-hoc four-estimator comparison and leakage
diagnostics are reported in the paper; they do not promote a clinical artifact
or silently change the application's pinned model.

## Saturated-score audit, 25 October 2026

The fresh post-hoc audit is `output/research/probability_audit/audit.json`.
The demonstration's raw forest score is 0.9982920927203368. The unchanged fitted
calibration is `sigmoid(3.267761146142852 * logit(raw) + 0.9684784989483102)`,
which produces 0.9999999996547169. The endpoint and Flutter research card now
expose the raw score and explain the calibrated score's numerical saturation.
Neither quantity is a validated clinical EOS probability.

The supplied patient identifiers change immutable characteristics, and the
source has 13,899 repeated patient/hour rows and 6,858 conflicting-label
patient/hour pairs. Zero ID overlap and shuffled-label controls cannot exclude
workflow leakage or a target-construction artifact. PCT alone has an oriented
test AUC of 0.98599; oxygen and CRP also strongly separate the supplied label.
The source's concurrent labels and unavailable measurement/diagnosis timestamps
prevent a prospective early-warning claim. Only the 100-case RAG benchmark was
confirmed synthetic; the provenance of the training CSV remains unverified.

The corrected synthetic development cases contain no invented EOS labels and
are not used to retrain, calibrate or validate this classifier. See
`PHASE1_PILOT.md` for the frozen retrieval/plan pilot and source limitations.
