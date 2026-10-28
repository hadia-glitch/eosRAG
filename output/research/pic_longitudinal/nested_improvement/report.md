# PIC nested improvement experiment

Eight fixed model/imputation candidates were compared on the unchanged real PIC v1.1.0 cohort: 543 infants, seven positive infants, 1,436 pre-culture landmarks. No Kaggle or synthetic rows were added. Maternal data remain unavailable.

Three outer patient-disjoint folds and two inner folds select by inner patient-weighted AUPRC. Seeds 31, 47 and 83 are all retained. All preprocessing and nearest-neighbour donors are fitted using training-fold data only. The cohort was previously exposed in development; these are not independent final-validation results.

## Results

| Method | Seed | AUROC | AUPRC | Brier |
|---|---:|---:|---:|---:|
|compact_lr_median_C001|31|0.468855|0.029690|0.013438|
|compact_lr_median_C01|31|0.429931|0.053355|0.014208|
|compact_lr_knn_C01|31|0.388075|0.093521|0.012463|
|trend_lr_median_C003|31|0.428406|0.050691|0.014166|
|compact_forest|31|0.559860|0.014814|0.013096|
|compact_balanced_forest|31|0.522994|0.014226|0.049862|
|compact_extra_trees|31|0.429463|0.013904|0.012915|
|compact_native_missing_boost|31|0.415473|0.011900|0.012802|
|nested_selected|31|0.428022|0.016919|0.014603|
|training_prevalence|31|0.451759|0.011839|0.012734|
|compact_lr_median_C001|47|0.293815|0.009317|0.013715|
|compact_lr_median_C01|47|0.251050|0.008862|0.014757|
|compact_lr_knn_C01|47|0.320054|0.009122|0.013125|
|trend_lr_median_C003|47|0.257925|0.008794|0.014615|
|compact_forest|47|0.548771|0.014676|0.013114|
|compact_balanced_forest|47|0.414924|0.010627|0.059904|
|compact_extra_trees|47|0.433924|0.011053|0.012978|
|compact_native_missing_boost|47|0.343348|0.009695|0.012861|
|nested_selected|47|0.405860|0.011146|0.013131|
|training_prevalence|47|0.451759|0.011839|0.012734|
|compact_lr_median_C001|83|0.329298|0.010644|0.012770|
|compact_lr_median_C01|83|0.206770|0.008208|0.012947|
|compact_lr_knn_C01|83|0.210738|0.007958|0.013624|
|trend_lr_median_C003|83|0.256449|0.008747|0.012951|
|compact_forest|83|0.639907|0.019426|0.012871|
|compact_balanced_forest|83|0.545911|0.013888|0.049447|
|compact_extra_trees|83|0.496591|0.013009|0.013200|
|compact_native_missing_boost|83|0.510701|0.012839|0.012799|
|nested_selected|83|0.639907|0.019426|0.012871|
|training_prevalence|83|0.451759|0.011839|0.012734|

## Interpretation

The nested-selected procedure has AUROC 0.4280, 0.4059 and 0.6399 across seeds. Seed-31 AUROC has infant-bootstrap 95% interval [0.1371, 0.7038]; its AUPRC interval is [0.0047, 0.0600]. These results do not establish useful clinical discrimination or a reliable gain over the earlier forest. Selecting the largest outer AUROC or best seed would exaggerate evidence.

The KNN candidate has AUPRC 0.0935 at seed 31, but 0.0091 and 0.0080 at seeds 47 and 83. That isolated gain is not reproducible. Positive-infant omission diagnostics below use fixed predictions and cannot be interpreted as a retrained validation study.

- nested_selected: AUPRC after omitting one of seven positive infants ranges from 0.009696 to 0.017666.
- compact_lr_knn_C01: AUPRC after omitting one of seven positive infants ranges from 0.014628 to 0.106994.

## Data and availability audit

The supplied archive is v1.1.0; the pasted PhysioNet page describes v1.0.0. Source: https://physionet.org/content/picdb/1.1.0/. This is real hospital EHR data, but the present endpoint is an unadjudicated early blood-culture pathogen phenotype, not an independently adjudicated clinical EOS outcome.

LABEVENTS contains CHARTTIME but no verified result-availability timestamp. Laboratory results are therefore not imported into pre-culture prediction as if already available. EMR_SYMPTOMS includes RECORDTIME, but NLP symptom attribution and originating document type need review before using it for clinical forecasting. Discharge diagnoses, culture results, medications and patient identifiers remain excluded as predictors.

The existing seven-positive-infant cohort cannot establish calibration, treatment thresholds or broad clinical reliability. A larger linked maternal-neonatal cohort with result/document availability and EOS outcome adjudication remains the main requirement. More landmarks or synthetic oversampling do not create independent infection outcomes.

## Status

No new candidate is promoted to the app, and the current Kaggle research predictor is unchanged. The final RAG evaluation and publication push remain on hold. No Groq calls or external patient-data transfers were used. Nine relevant regression tests passed (one unchanged authenticated API test excluded from this run). Restricted patient-level predictions stay under ignored data/picdb_private; public files contain aggregate results only.
