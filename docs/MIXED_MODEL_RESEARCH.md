# Maternal and neonatal mixture: feasibility study

 Simulation research only; no clinical validation or app-model replacement.

## Decision

The supplied African datasets can support a reproducible synthetic maternal-plus-neonatal ensemble. They cannot supply missing maternal observations for the older patients or validate clinical EOS risk. The sources have different, unverified target definitions; concatenating them does not create an adjudicated EOS cohort. Keep the original app model and this experimental artifact separate.

The source card explicitly identifies literature-parameterized synthetic observations and cautions against empirical/policy inference. Its catalog has missing upstream-publisher/country metadata. A filename or literature-derived odds ratio does not establish patient-level clinical evidence. [Dataset card](https://huggingface.co/datasets/electricsheepafrica/africa-synth-neonatal-sepsis-dataset-all).

## Data handling and locked experiment

The supplied development file has 5,000 rows and the test file 2,000. Both reuse 2,000 IDs, with no identical non-ID rows or predictor vectors. Conservatively remove all development IDs appearing in the test file before fitting. This leaves 3,000 development records. Exclude late-onset positives rather than relabeling them as controls. The conditional synthetic Early-onset-versus-Negative experiment has 1,694 fit records, 424 validation records and 1,446 test records, including 845 synthetic positive labels. Fit/test ID overlap is zero. Negative records lack a documented postnatal assessment age, so this is not a prospective EOS incidence cohort.

Use one kg birth-weight field and omit duplicated gram/weight flags. The kg values are rounded to 0.01 kg; compare the gram representation using a 5.01 g rounding tolerance, not exact equality. Omit IDs, sepsis status as an input, onset, culture confirmation, pathogen, final outcome, hospital days and the supplied probability score. Also omit untimed WBC/CRP, whose definitions cannot be safely aligned with the earlier CSV by guessing conversions.

The maternal/perinatal branch uses gestation, kg birth weight, maternal age, PROM, maternal infection, delivery category, 1- and 5-minute Apgar and resuscitation. The neonatal branch uses fever, hypothermia, respiratory distress, poor feeding, lethargy and jaundice. These are concurrent synthetic findings; their availability before diagnosis is unverified.

Fit a regularized logistic maternal/perinatal branch and a shallow forest neonatal branch. Five-fold out-of-fold predictions from the fit partition train a regularized logistic stacking model. Preprocessing is fitted within each fold. Refit base branches on fit data only; validation chooses each arm's threshold targeting 90% sensitivity. The test file is not used to select models, tune hyperparameters, calibrate probabilities or choose thresholds. It was profiled descriptively before the experiment. The protocol, seeds, source hashes and package versions are recorded with the results. The portable JSON ensemble reproduces estimator predictions within 1e-7.

## Measured synthetic holdout results

| Arm | AUC | Brier | Sensitivity | Specificity | Accuracy |
| --- | --- | --- | --- | --- | --- |
| Maternal/perinatal logistic | 0.8031 | 0.1731 | 0.9053 | 0.3727 | 0.6840 |
| Neonatal clinical forest | 0.9970 | 0.0087 | 0.9077 | 1.0000 | 0.9461 |
| Mixed stacked ensemble | 0.9984 | 0.0050 | 0.8994 | 1.0000 | 0.9412 |
| Flat combined logistic | 0.9982 | 0.0047 | 0.9101 | 1.0000 | 0.9474 |

The mixed AUC descriptive bootstrap interval is [0.9964, 0.9997], using 500 row resamples with a fixed seed. It describes this synthetic holdout, not uncertainty across hospitals or generators. The stacked model does not outperform the flat model on Brier, sensitivity or accuracy at the separately validation-chosen cutoffs. The mixed cutoff is 0.99794; it is a research cutoff, not a clinical treatment threshold.

A post-hoc diagnostic explains the extreme discrimination: all negative test records have zero of the six clinical signs. An untrained sign count gives AUC 0.99704. Thus high performance can reproduce label-conditional generation rather than discover generalizable clinical physiology. This also explains why merely adding more of these synthetic cases would not repair clinical validity. Three shuffled-training-label controls give test AUCs 0.6201, 0.4187 and 0.4890; all are retained, including the non-chance value. These three descriptive controls are not a formal permutation test or proof of no leakage.

## Combining the older source

No patients were joined across datasets, and no missing maternal facts were invented. Only gestational age, kg birth weight and mapped delivery category were used for transfer. The original Apgar column lacks a confirmed timepoint, so it was not equated to either Apgar column in the new source. The original source retains its fixed patient-ID split and supplied observation labels at recorded days 0-2. Its identity, outcome and timing limitations still apply.

| Three-feature training source | Original supplied-label test AUC | Synthetic early-label test AUC |
| --- | --- | --- |
| Original only | 0.5812 | 0.5944 |
| Synthetic only | 0.5993 | 0.6004 |
| Hypothetical source-balanced pool | 0.5927 | 0.5977 |

The pooled experiment gives each source equal total logistic fitting weight and does not use source identity as a predictor. It is an explicit endpoint-compatibility stress test. It does not establish compatible outcomes, missing-at-random assumptions or clinical transportability. Results do not show consistent improvement from pooling.

## Research basis and next defensible study

TRIPOD-Cluster calls for semantic harmonization of predictors/outcomes, explicit missing-data handling and assessment across source clusters. Internal-external validation should hold out entire clinical sites or cohorts; a random split of one simulator is not external clinical validation. [TRIPOD-Cluster checklist](https://www.bmj.com/content/380/bmj-2022-071018), [explanation](https://pmc.ncbi.nlm.nih.gov/articles/PMC9903176/).

Published approaches to systematically missing predictors include common-predictor restriction, imputation that respects study clustering, and multi-study prediction ensembles. Their assumptions must be checked; maternal information absent from an entire cohort is not equivalent to a few sporadic missing measurements. The cited ensemble study primarily concerns continuous outcomes, so it is methodological motivation rather than validation of this binary neonatal application. [Seo et al., 2023](https://pubmed.ncbi.nlm.nih.gov/36755407/).

For a clinically interpretable combined model, obtain cohorts with compatible adjudicated EOS endpoints, postnatal landmarks, measurement/result availability, units and intended care settings. Evaluate source-specific calibration and discrimination, then perform site-held-out validation. Joint calibration or learned fusion of the old and new models requires patients with verified outcomes and the necessary observed predictors; averaging unaligned model probabilities is not a validated alternative. [Riley et al., external validation across datasets](https://www.bmj.com/content/353/bmj.i3140).

## Reproduction

From `backend/`, using the research dependencies:

```powershell
python -m scripts.evaluate_maternal_mixture --development PATH_TO_5000.csv --test PATH_TO_2000.csv --archive PATH_TO_ORIGINAL_ARCHIVE.zip --output ../output/research/cross_source
```

The artifact is `output/research/cross_source/mixed_model.json`; measured outputs are in `results.json`, the source audit in `source_audit.json`, and the pre-fit specification in `protocol.json`. The cross-source models are separate in `shared_feature_models.json`. Raw supplied files remain outside Git. The application does not install or silently switch to this simulation artifact.
