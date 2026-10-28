# New neonatal cohort model experiments

Separate exploratory diagnostic studies; not a pooled or validated EOS risk model. No app model is replaced. Original files remain unchanged. No Groq calls or external patient-data transfers were used.

## Cohorts

- Workbook: 138 preterm infants, 69 culture-positive cases and 69 controls. The codebook defines CASE=2 and CONTROL=1. Twelve features include maternal age, sex, gestation, delivery mode, birth weight, growth category and five blood-count measures. Identifiers and SEPSIS SIGNS (an exact copy of the outcome) are excluded. Six redundant derived indices and category duplicates are excluded. Weeks+days are parsed using days/7; counts are log-transformed where specified, without silently repairing source outliers.
- CHOP: 580 evaluations in 472 infants aged <28 days; 53 bacteremic evaluations in 52 infants. Bacteremia is compared with sepsis-group-2 culture-negative rule-out episodes; other clinical/fungal/viral/indeterminate and non-blood-culture-positive groups are excluded. Fourteen baseline/evaluation-time features are used. IDs, culture results, treatment timing, mortality, length of stay, future support-free days and evaluation-day maximum temperature are excluded. Repeated episodes remain grouped by infant. This is not a clinical EOS cohort; the age-0–2-day subset contains only one bacteremic infant.
- The supplementary ZIP contains two R scripts for the same CHOP study and no additional training records. No script from the attachment is executed.

## Validation

Five outer patient-separated folds with three inner folds. Candidate selection uses inner AUROC; decision thresholds maximize inner balanced accuracy on a fixed 0.05–0.95 grid. Outer outcomes do not select a model or threshold. Median imputation, indicators and scaling are fitted in training folds. Each infant has equal total loss/evaluation weight. Candidates are two regularized logistic regressions, Random Forest, Extra Trees and shallow gradient boosting. A demographic-only baseline is retained. Seeds 31/47/83 and all fixed-candidate results remain reported. This is internal development, not independent external validation.

## Nested-selected results

| Dataset | Seed | AUROC | Accuracy | Sensitivity | Specificity | Precision | AUPRC |
|---|---:|---:|---:|---:|---:|---:|---:|
|workbook|31|0.8109|74.64%|76.81%|72.46%|73.61%|0.8103|
|workbook|47|0.7921|72.46%|71.01%|73.91%|73.13%|0.7590|
|workbook|83|0.7663|70.29%|75.36%|65.22%|68.42%|0.7291|
|chop|31|0.8049|61.47%|92.25%|58.21%|18.94%|0.2931|
|chop|47|0.8027|58.78%|90.04%|55.47%|17.63%|0.2539|
|chop|83|0.8235|56.15%|98.89%|51.63%|17.79%|0.2741|

## Primary-seed 95% intervals

2,000 infant-level bootstrap resamples of fixed out-of-fold predictions. These intervals do not capture all model-refitting, phenotype or between-site uncertainty.

| Dataset | Metric | Lower | Upper |
|---|---|---:|---:|
|workbook|auroc|0.7371|0.8765|
|workbook|auprc|0.7204|0.8902|
|workbook|accuracy|0.6667|0.8116|
|workbook|sensitivity|0.6623|0.8592|
|workbook|specificity|0.6164|0.8219|
|workbook|precision|0.6338|0.8308|
|workbook|brier|0.1470|0.2111|
|chop|auroc|0.7505|0.8532|
|chop|auprc|0.1953|0.4196|
|chop|accuracy|0.5770|0.6551|
|chop|sensitivity|0.8410|0.9891|
|chop|specificity|0.5400|0.6241|
|chop|precision|0.1428|0.2417|
|chop|brier|0.0603|0.0944|

## Added signal versus demographics

- workbook: paired AUROC difference +0.0373, 95% interval [-0.0177, +0.0910].
- chop: paired AUROC difference +0.0525, 95% interval [+0.0021, +0.1058].

The workbook interval includes zero, and the baseline is higher at seeds 47 and 83. Thus an incremental blood-count benefit is not established consistently. CHOP has a positive primary-seed interval in this internal comparison, but low precision and specificity remain material limits. Its evaluation-time features may reflect an already unwell infant and are not pre-symptom forecasts.

## Comparison and limitations

These AUROCs are more encouraging than the earlier PIC nested-selected values (0.4280/0.4059/0.6399), but the cohorts and outcomes differ. This is not a paired improvement of the PIC EOS model. The Kaggle near-perfect label-reproduction score is not a clinical performance target.

The workbook is a selected 50:50 preterm case-control sample: precision and absolute probability do not transfer to routine EOS prevalence. No individual postnatal/onset or result-availability times establish an EOS-only subgroup. CHOP is conditioned on sepsis evaluation and a treatment-duration-informed rule-out phenotype; controls are not adjudicated healthy infants. CHOP includes evaluation-time support features, no raw serial vital-sign/laboratory histories and no linked maternal GBS/fever/rupture/antibiotic history. Neither experiment validates longitudinal EOS prediction or treatment decisions. No clinical verification has been performed.

Source units and extreme workbook values require review before deployment. The source TOTAL COUNT value 163000 is retained, not silently changed to 16300. Log transformation limits leverage without claiming a correction. No observed result justifies excluding difficult rows or redefining outcomes to improve scores.

Five gestational-age parsing regression tests passed. Feature/source hashes, saved protocols, all 30 outer fold separations and private prediction checkpoints were verified. Model weights and individual predictions remain under ignored data/new_neonatal_cohorts. The public bundle includes only aggregate metrics, methods and code.

Sources: https://doi.org/10.6084/m9.figshare.28395161.v1 ; https://f1000research.com/articles/14-390/v4 ; https://data.mendeley.com/datasets/5vdz5cftz7/1 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC6881601/
