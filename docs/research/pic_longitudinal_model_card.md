# PIC longitudinal research model — clinical prediction withheld

Actual local cohort: 543 infants, 7 positive infants, 1436 pre-culture prediction landmarks.
Endpoint: a documented named bacterial pathogen from blood collected before 72 hours. This is not an adjudicated EOS diagnosis.
Repeated landmarks stay in the same patient fold. Three patient-stratified folds, training-only preprocessing, equal total patient weight. No independent final test.

|Method|AUROC|AUPRC|Brier|
|---|---:|---:|---:|
|snapshot_logistic|0.295756|0.009588|0.012814|
|trend_logistic|0.417659|0.048171|0.014243|
|binned_logistic|0.300808|0.009045|0.012938|
|trend_forest|0.593083|0.017074|0.013345|
|training_prevalence|0.451759|0.011839|0.012734|
|age_only|0.507965|0.015135|0.012731|
|missingness_only|0.617147|0.045004|0.012751|
|longitudinal_mean_ensemble|0.491526|0.022058|0.013014|

The candidate fails the clinical quality gate. A competitive missingness-only control raises concern about care-recording signals. No 99.9% clinical probability is inferred from these experiments.
The model stores and uses real elapsed-time changes, slopes, extrema, measurement recency, missingness and/or fixed temporal bins. Snapshot-only and history-augmented representations and a shallow forest are compared. No deep recurrent model is justified by the independent event count.
Every predictor must have both measurement and availability times at or before the landmark. No outcome, culture result, diagnosis, death, discharge, shifted calendar date or patient identifier enters the design.
Real-data model weights, individual predictions, cohort rows and patient partitions remain in ignored data/picdb_private. Only aggregate results belong in research/publication bundles.
The application research-input preview reviews measurements and trends but returns no new PIC score. It does not replace the existing research classifier or promote the improved RAG candidate.

## Maternal input status

The selected PIC tables lack linked maternal GBS, intrapartum temperature, rupture duration and antibiotic timing. These are not invented or imputed from unrelated synthetic individuals.
The existing Africa synthetic experiment combines maternal/perinatal and clinical features on the same synthetic rows. Its near-perfect mixed discrimination is not real-patient evidence: the prior source audit found no clinical signs in its negative rows, and symptom count alone has AUROC 0.9970.
GBS, numeric intrapartum temperature, numeric rupture duration and antibiotic timing are guideline-context fields, not established learned effects in either current dataset. The form labels that distinction.

## Dataset needed for a valid combined model

Provide a de-identified linked obstetric–neonatal EHR cohort or birth registry with neonatal follow-up, not separate unrelated maternal and infant datasets. Required linked tables are described in docs/research/linked_cohort_template/README.md. Culture-negative clinical sepsis must remain distinct from adjudicated uninfected controls.
MIMIC-III CHARTEVENTS and LABEVENTS were not found in Downloads at this audit. The supplied D_ITEMS contains gestational age but does not establish the requested maternal predictor set. Completing those tables could enlarge a neonatal study, but does not guarantee linked maternal data.
A neonatal cohort from another source requires its own outcome/scope audit; general pediatric or adult sepsis labels cannot validate neonatal EOS. Clinical source and outcome adjudication remain pending.


## Paper-inspired Bayesian comparison

The attached Nguyen et al. paper (https://doi.org/10.21037/tp-22-510) studies broad paediatric diagnosis, not the same pre-culture neonatal endpoint. Its AUROC 0.866 and sensitivity 0.463 do not validate this model. A local naive-Bayes/TAN comparison retains the strict cohort, training-only discretization and structure learning, patient-disjoint folds, equal infant weights, and all seeds 31/47/83. Missingness has an explicit state, not an assumed normal value.

At seed 31 snapshot TAN AUROC is 0.575012 (patient-bootstrap 95% CI 0.389438–0.750369). Longitudinal TAN AUROC is 0.403278, 0.430975 and 0.453482 for the three declared seeds. All 12 arms/seeds are retained in output/research/pic_longitudinal/paper_inspired_bayes/metrics.csv, with 2,000-resample infant-level and paired intervals. No favourable seed, posterior extreme or architecture is promoted as a clinical EOS risk. Calibration is unestablished; all new models remain withheld. Seven independent positive infants are insufficient to establish a robust clinical model through further architecture search.


## Nested imputation and model-selection experiment

Eight candidates including distance-weighted five-neighbour imputation, compact temporal features, regularized logistic regression, forests, Extra Trees and native-missingness boosting were tested with three outer/two inner patient-separated folds at three seeds. Nested-selected AUROC was 0.4280, 0.4059 and 0.6399; primary-seed 95% CI [0.1371, 0.7038]. The KNN AUPRC gain was unstable across seeds. No candidate is promoted. Full results: output/research/pic_longitudinal/nested_improvement/report.md.
