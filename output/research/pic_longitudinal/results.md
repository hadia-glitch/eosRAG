# PIC longitudinal development comparison

543 infants, 7 independent positive infants, 1436 pre-culture landmarks. Three patient-disjoint folds; no independent final test.

|Method|AUROC|AUPRC|Brier|
|---|---:|---:|---:|
|snapshot_logistic|0.2958|0.0096|0.0128|
|trend_logistic|0.4177|0.0482|0.0142|
|binned_logistic|0.3008|0.0090|0.0129|
|trend_forest|0.5931|0.0171|0.0133|
|training_prevalence|0.4518|0.0118|0.0127|
|age_only|0.5080|0.0151|0.0127|
|missingness_only|0.6171|0.0450|0.0128|
|longitudinal_mean_ensemble|0.4915|0.0221|0.0130|

Selected for development by cross-validated AUPRC: trend_logistic. The artifact is local-only and not clinically approved.
Patient-bootstrap 95% intervals (2,000 resamples), paired history comparisons and descriptive operating points are in the CSV/JSON outputs. Negative outcomes are preserved.
The outcome is a documented named bacterial pathogen in a blood culture collected before 72 hours, not adjudicated clinical EOS. Maternal predictors are unavailable in this real cohort. No synthetic maternal history is joined to these infants.
A recurrent neural model is not fitted because independent infection events are below the prespecified engineering floor. A more complex model is not justified by more rows from the same few infants.
