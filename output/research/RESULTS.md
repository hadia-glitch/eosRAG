# Measured research results

These are supplied-label classification and synthetic engineering results. The artifacts are not approved EOS predictors.

| Cohort | Selected model | Test n | AUROC | AUPRC | Brier |
| --- | --- | --- | --- | --- | --- |
| all_neonatal_ages | forest | 14937 | 0.9996 | 0.9994 | 0.0063 |
| postnatal_days_0_2 | forest | 1598 | 0.9992 | 0.9991 | 0.0094 |

| Generation arm | N | Coverage | BLEU-4 | METEOR | ROUGE-L | DistilBERT F1 | RoBERTa F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Unverified, all cases | 18 | 0.833 | 0.0220 | 0.2110 | 0.1416 | 0.6635 | 0.7109 |
| Verified, all cases | 18 | 0.222 | <0.0001 | 0.0330 | 0.0415 | 0.1722 | 0.1878 |
| Verified, released only | 4 | 1.000 | 0.0116 | 0.1486 | 0.1868 | 0.7750 | 0.8450 |
| Unverified, generated only | 15 | 1.000 | 0.0220 | 0.2532 | 0.1699 | 0.7962 | 0.8530 |

Injected faults: 12; emitted without verification: 12; emitted with verification: 0.

See rag_v2/summary.json, per_case_metrics.json, cases.json, runs/, judges/ and attempts/ for complete denominators, raw outputs and failure provenance.
