# RAG robustness audit and paper-inspired ML comparison

Final evaluation, candidate app integration and GitHub push remain on hold.

### 13.10 Benchmark dependence and wording robustness

The 100 exposed synthetic base cases contain only 24 distinct focused question templates: NICE 12, AAP 6 and WHO 6. Parameter variants do not establish independent clinical reasoning coverage. Renaming all passage identifiers and graph endpoints preserves rankings for 100/100 cases; this excludes literal identifier dependence in this check but does not exclude conceptual or benchmark overfitting. A query-agnostic publisher-summary ordering and 1,000 within-source gold permutations are reported as diagnostics, not clinical retrieval performance. The query-agnostic WHO MRR@4 is 0.9167 compared with contextual MRR@4 of 0.8667, indicating that common summary passages and coarse relevance sets can inflate apparent ranking success.

Two deterministic wording-transform slots per base case preserve standalone numeric values and explicit negation/unknown markers. Of 200 slots, 152 change the focused wording and 48 are identical controls (NICE 13, AAP 5 and WHO 30); these slots are not independent additional cases. Clinical equivalence remains unreviewed. The fresh stress test reruns both pinned cross encoders on changed questions, with RRF k=60 and bounded MMR diversity 0.15. The fixed-facet arm explicitly retains earlier facet questions; a separate question-only arm omits those facets. Original-wording replay matches the previous pipeline for 100/100 cases. Neither arm is a fresh LLM-planned final evaluation or an independent patient cohort. Complete source-separated R/P/MRR/nDCG at 4 and 8, paired case-level and scenario-family 95% intervals from 2,000 resamples, and query-only negatives are retained in CSV. No new Groq calls are used for these retrieval checks.

Bounded terminology normalization is added to the intent selector after observing the wording failure. Original clinical questions, patient facts, units, negation and indexed source text are preserved. This is a post-hoc development repair, not independent validation.

Table 34. Fresh fixed-facet wording stress and post-hoc routing repair. Each NICE row covers 40/40 cases; each AAP or WHO row covers 30/30. Coverage denotes retrieval completion, not released clinical answers. P@8 has annotation ceilings of 0.3344, 0.2500 and 0.2500 for NICE, AAP and WHO; raw precision is not rescaled. Supplemental definitions are outside the eight recommendation slots.

| Guideline | Wording / selector | R@4 | MRR@4 | R@8 | P@8 | nDCG@8 |
| --- | --- | --- | --- | --- | --- | --- |
| NICE | Original / legacy | 0.9167 | 0.9125 | 0.9917 | 0.3312 | 0.8885 |
| NICE | Plain / legacy | 0.7667 | 0.8000 | 0.9375 | 0.3156 | 0.7791 |
| NICE | Plain / canonical | 0.7667 | 0.8000 | 0.9375 | 0.3156 | 0.7791 |
| AAP | Original / legacy | 1.0000 | 1.0000 | 1.0000 | 0.2500 | 0.9394 |
| AAP | Plain / legacy | 0.8333 | 0.6667 | 0.9167 | 0.2292 | 0.7368 |
| AAP | Plain / canonical | 1.0000 | 0.9167 | 1.0000 | 0.2500 | 0.9017 |
| WHO | Original / legacy | 1.0000 | 0.8667 | 1.0000 | 0.2500 | 0.8586 |
| WHO | Plain / legacy | 1.0000 | 0.8667 | 1.0000 | 0.2500 | 0.8515 |
| WHO | Plain / canonical | 1.0000 | 0.8667 | 1.0000 | 0.2500 | 0.8515 |

Table 35. Paired plain-minus-original Recall@4 differences before repair. The same 100 base cases are used; family bootstrap has only six scenario families per source.

| Guideline | Difference | Case 95% CI | Family 95% CI |
| --- | --- | --- | --- |
| NICE | -0.1500 | [-0.2125, -0.0917] | [-0.2991, -0.0317] |
| AAP | -0.1667 | [-0.3000, -0.0333] | [-0.5000, 0.0000] |
| WHO | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |

The original NICE Recall@4 of 0.9167 becomes 0.7667 under plain wording; the original AAP Recall@4 and MRR@4 of 1.0000 become 0.8333 and 0.6667 before repair. The canonical selector restores AAP plain Recall@4 to 1.0000 and MRR@4 to 0.9167, while NICE plain Recall@4 remains 0.7667. Aggregate original-wording retrieval targets therefore do not establish robustness. A locked, independently authored clinical challenge set and adjudicated relevance labels remain necessary; further adaptation to these exposed variants cannot supply independent evidence.

### 13.11 Patient-specific explanation safety smoke test

Three of 18 planned development cases are attempted, one each from NICE, AAP and WHO. All 3 attempts complete without an unresolved provider failure. The structural checks accept 2/3 drafts; complete two-model audits occur for 2/3, and 1/3 is released by the research graph. Attempted release coverage is 1/3 (0.3333), with planned-population coverage 1/18 (0.0556); the other 15 cases are unattempted, not quality failures. No alignment metric or clinical utility score is inferred from these counts. Completed failures remain saved.

The NICE draft incorrectly treats unclear initial suspicion as satisfying a reassuring stopping condition and adds unsupported treatment escalation. It is withheld before semantic auditing because a numerical-unit guard rejects another claim; this is not evidence that semantic auditors detected its clinical errors. The WHO evidence auditor rejects conflation of all PSBI signs with the narrower clinical-severe-infection category, whereas the safety auditor accepts the draft. The AAP draft passes both auditors, yet its action prose omits the site-specific-infection exception present in its cited stopping recommendation. These are engineering source-comparison findings awaiting clinician adjudication, not a clinical error rate. Separate prompts using the same model backbone are not independent clinical assessors.

A constrained evidence-brief research fallback renders unchanged recorded findings and unknowns separately from complete indexed passages. Exact text/hash checks preserve every condition and exception in the selected source units, and chronological-history checks reject future records. No free-form model statement or patient treatment eligibility is released by this fallback. Source fidelity is an engineering property and does not establish relevance, sufficient context or clinical usefulness. The fallback is not presented as a fully working care-plan generator. The prototype is not integrated into the clinical app. Final evaluation, candidate app integration and publication push remain on hold.

### 13.12 Paper-inspired Bayesian longitudinal comparison

Nguyen et al. [19] use the same PIC database for a different task: sepsis diagnosis in 3,014 paediatric admissions, including 134 sepsis admissions, using first-24-hour clinical and laboratory information. Their best full-information TAN AUROC is 0.866 (95% CI 0.826–0.906), with sensitivity 0.463, specificity 0.949 and accuracy 0.930. The under-30-day subgroup AUROC is 0.783 (95% CI 0.716–0.850), with sensitivity 0.338; that subgroup is still not an EOS pre-culture forecasting cohort. A constant-negative classifier has accuracy 2880/3014 (0.9555) in the reported overall cohort, illustrating why accuracy alone is unsuitable. The reported admission-level cross-validation does not establish patient-disjoint grouping from the available description. Actual leakage in that study is not asserted.

The transferable ideas are conditional-dependence modelling, explicit missingness, clinician-informed feature selection and comparison with simpler probabilistic baselines. Culture and retrospectively available first-day laboratory values are not imported as pre-culture predictors. A smoothed discrete naive Bayes and tree-augmented naive Bayes (TAN) [20] are implemented for snapshot and actual-time longitudinal features. Discretization, variable selection, priors, conditional probabilities and TAN structure are learned only within each training fold. Missing values occupy an explicit state, which can encode recording practices and is not an imputed normal measurement. Equal total infant weights and three patient-disjoint folds are retained. Seeds 31, 47 and 83 and smoothing equivalent sample size 10 are declared before these runs. All 12 comparisons remain reported; the cohort remains 543 infants with seven positive infants and 1,436 landmarks.

Table 36. Paper-inspired Bayesian development results; no held-out patient row is used for fitting its fold model. Seed-31 patient-bootstrap intervals and paired comparisons versus the prior snapshot logistic model are in CSV; no seed is selected for deployment.

| Method | Seed | AUROC | AUPRC | Brier |
| --- | --- | --- | --- | --- |
| snapshot nb | 31 | 0.4117 | 0.0128 | 0.0129 |
| snapshot tan | 31 | 0.5750 | 0.0190 | 0.0137 |
| longitudinal nb | 31 | 0.4680 | 0.0191 | 0.0177 |
| longitudinal tan | 31 | 0.4033 | 0.0112 | 0.0134 |
| snapshot nb | 47 | 0.3551 | 0.0100 | 0.0132 |
| snapshot tan | 47 | 0.6065 | 0.0204 | 0.0132 |
| longitudinal nb | 47 | 0.2618 | 0.0084 | 0.0215 |
| longitudinal tan | 47 | 0.4310 | 0.0119 | 0.0135 |
| snapshot nb | 83 | 0.2888 | 0.0090 | 0.0132 |
| snapshot tan | 83 | 0.5599 | 0.0164 | 0.0136 |
| longitudinal nb | 83 | 0.2696 | 0.0085 | 0.0187 |
| longitudinal tan | 83 | 0.4535 | 0.0132 | 0.0129 |

Snapshot TAN at seed 31 has AUROC 0.5750 with patient-bootstrap 95% CI [0.3894, 0.7504]. Longitudinal TAN has AUROC 0.4033, 0.4310 and 0.4535 at the three declared seeds. These results do not establish adequate discrimination, calibration or superiority to earlier candidates. Large individual posterior scores remain uncalibrated research outputs; neither architectural complexity nor a favourable seed justifies a clinical EOS probability. A larger linked maternal-neonatal cohort with timestamped result availability and adjudicated early-onset outcomes is required. No new Bayesian model is installed as an app predictor.

### 13.13 Nested imputation and model-selection experiment

Eight additional fixed candidates compare compact temporal features, median versus distance-weighted five-neighbour imputation, regularized logistic regression, forests, Extra Trees and native-missingness gradient boosting. The unchanged cohort contains 543 infants, seven positive infants and 1,436 landmarks. Three outer patient-separated folds contain two inner folds for candidate selection by patient-weighted AUPRC. Feature selection, scaling, imputation donors and estimators are fitted within each training fold. Observed-feature eligibility requires five distinct infants. All seeds 31, 47 and 83 and all candidate scores are retained; no favourable outer result is selected for deployment. The already exposed cohort remains development data, despite nested selection.

Table 37. Nested selection and KNN-imputation candidate results; 543/543 infants and 1,436/1,436 landmarks scored for every row. This is prediction coverage, not clinical validation or generated-answer release coverage.

| Method | Seed | AUROC | AUPRC | Brier |
| --- | --- | --- | --- | --- |
| compact lr knn C01 | 31 | 0.3881 | 0.0935 | 0.0125 |
| nested selected | 31 | 0.4280 | 0.0169 | 0.0146 |
| compact lr knn C01 | 47 | 0.3201 | 0.0091 | 0.0131 |
| nested selected | 47 | 0.4059 | 0.0111 | 0.0131 |
| compact lr knn C01 | 83 | 0.2107 | 0.0080 | 0.0136 |
| nested selected | 83 | 0.6399 | 0.0194 | 0.0129 |

Primary-seed nested-selected AUROC has an infant-bootstrap 95% interval of [0.1371, 0.7038]. The KNN AUPRC increase at seed 31 does not persist at the other two declared seeds. Omitting one positive infant from fixed seed-31 KNN predictions gives AUPRC values ranging from 0.0146 to 0.1070; this is a fixed-prediction influence diagnostic, not a retrained leave-one-out study. A reliable performance improvement is not established. No new PIC predictor is promoted to the application. Missing maternal predictors are not invented, and laboratory results without verified availability timestamps remain excluded.
