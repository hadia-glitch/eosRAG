# NeoGuard: Phase 1 Pilot Evaluation and Model Probability Audit

**Technical research addendum | 25-26 October 2026 | Ten fixed synthetic cases; actual saved rankings and plans; fresh judgments and metrics.**

## 1. Decision and scope

**REVISE.** The saved graph/hybrid rankings show promising retrieval on this small development pilot. They do not establish clinical safety, a controlled multi-agent benefit, or a valid EOS prediction probability. Correct the benchmark/source/citation provenance and establish a defensible clinical model cohort before expansion or clinical release.

The ten cases contain four NICE, three WHO and three AAP scenarios. They include low and critical recorded risk categories, renal-safety, penicillin-allergy, low-birth-weight and recent-hospitalization scenarios, and longitudinal change. Selection was deterministic, metadata-based, and frozen before judging. All 206 unique case/passage judgments were completed and mapped back to the actual top-ten lists.

## 2. Methods and traceability

The canonical 100-case JSON, three historical result CSVs and the benchmark-declared chunks_ingested.csv were hashed. The gold evidence was preserved. Twelve selected historical rows disagree with canonical gold; the manifest lists every mismatch. All selected top-ten and gold chunk IDs resolve in the 489-row corpus. The five named arms are interpreted as saved labels; their Dense/Vector implementation distinction and full controlled-ablation provenance are not established by the CSVs.

The 489 source rows contain 481 distinct identifiers and 8 conflicting-text ID groups. Three colliding IDs affect AAP cases 003, 007 and 011. The frozen input mapping used the last CSV occurrence, which the audit independently verified; all variants are preserved. Exact-ID scores cannot disambiguate conflicting content, and semantic/source scores are conditional on the frozen texts. No input or gold was changed after this discovery. Resolve these identities before a confirmatory experiment.

All ten original selected cases omit postnatal age. That prevents confirmation of EOS age eligibility and some age-specific treatment conditions. Missing age was kept unknown in the evaluator inputs; no corrected case facts were substituted. A high automated clinical rating despite this missing scope information is a limitation of the evaluator, not evidence that eligibility was established.

Exact MRR@10 uses the first canonical gold hit. NDCG@10 uses binary gain and a standard gold-normalized ideal ranking from all canonical gold IDs, capped at ten; missing ranks have zero relevance and duplicates do not receive repeated credit. Expanded context is excluded. Fifty NDCG values independently matched scikit-learn within 1e-12. Anchor recall is normalized exact phrase coverage, not a measure of clinical correctness.

GPT-OSS-120B at temperature zero judged actual chunk text, case, active guideline and gold evidence with arm labels hidden. Grade >=2 defines useful evidence. Semantic NDCG uses graded gains and the same judged union of the five top-ten lists as each case's ideal pool; it is not a corpus-wide ideal. Scores and rationales are retained per chunk. This is an LLM-based clinical usability assessment - not clinician validation.

All four saved plan arms were freshly assessed under a source-separated rubric-4 protocol. The grounding pass receives ONLY actual retrieved plan evidence. A separate clinical-usefulness pass receives the case and wider guideline evidence. Unsupported claims and contradictions select immutable candidate-line IDs, materialized locally as exact quotations; omissions are separate. Exploratory earlier judgments, including a gold-versus-retrieved-context confusion, remain archived and are excluded. Historical MA traces lack a verified E-number-to-passage mapping; the evaluator must not invent one. Saved Dense/Hybrid/MA generations differ, so this is a composite historical comparison, not an identical-draft verification ablation or an estimate of an individual agent's effect.

## 3. Retrieval results

| Arm | Exact MRR@10 | Exact NDCG@10 | Anchor recall | Useful P@10 | Semantic NDCG@10 |
| --- | --- | --- | --- | --- | --- |
| Dense | 0.591 | 0.294 | 0.673 | 0.370 | 0.495 |
| Sparse | 0.602 | 0.282 | 0.668 | 0.330 | 0.459 |
| Vector | 0.632 | 0.271 | 0.659 | 0.360 | 0.514 |
| Graph | 0.900 | 0.523 | 0.829 | 0.490 | 0.639 |
| Hybrid | 0.875 | 0.550 | 0.799 | 0.490 | 0.640 |

Graph ranks the first exact gold hit most effectively; Hybrid ranks the total exact and graded evidence pool slightly better. Graph and Hybrid tie on useful precision. The small sample and dependent source/reference construction preclude a general superiority claim. Semantic and exact results favor graph/hybrid overall but do not give identical arm orderings.

Hybrid minus Dense exact NDCG is 0.256; a descriptive paired case bootstrap (20,000 resamples, seed 20261025) gives a 95% percentile interval [0.124, 0.400]. This interval does not resolve template/source dependence or imply clinical generalizability. Exact and semantic arm-mean NDCG ranks have Spearman correlation 0.70.

| Case | Guideline | Dense exact NDCG | Hybrid exact NDCG | Dense useful P@10 | Hybrid useful P@10 |
| --- | --- | --- | --- | --- | --- |
| cp_case_001 | NICE | 0.697 | 0.655 | 0.500 | 0.500 |
| cp_case_002 | NICE | 0.353 | 0.655 | 0.400 | 0.700 |
| cp_case_003 | AAP | 0.225 | 0.711 | 0.600 | 0.700 |
| cp_case_004 | WHO | 0.188 | 0.280 | 0.300 | 0.400 |
| cp_case_007 | AAP | 0.167 | 0.853 | 0.400 | 0.500 |
| cp_case_009 | NICE | 0.140 | 0.467 | 0.100 | 0.600 |
| cp_case_011 | AAP | 0.225 | 0.711 | 0.400 | 0.600 |
| cp_case_014 | NICE | 0.396 | 0.463 | 0.600 | 0.600 |
| cp_case_025 | WHO | 0.275 | 0.354 | 0.200 | 0.000 |
| cp_case_026 | WHO | 0.275 | 0.354 | 0.200 | 0.300 |

The fresh evaluator produced 4 recorded relevance/applicability/usefulness inconsistencies. Protocol usefulness is computed from grade >=2; raw conflicting booleans and rationales remain available. Relevant treatment text can still be inapplicable to a particular infant, and model judgments must not override population or safety gates.

## 4. Generated-plan usability and similarity

| Fresh 1-5 assessment | Dense | Hybrid |
| --- | --- | --- |
| Faithfulness | 2.500 | 2.700 |
| Citation Correctness | 2.000 | 2.200 |
| Citation Completeness | 2.000 | 2.200 |
| Clinical Correctness | 3.700 | 4.000 |
| Clinical Completeness | 3.100 | 3.500 |
| Clinical Utility | 3.600 | 4.000 |
| Safety | 4.000 | 4.300 |

| Case | Guideline | Dense utility | Hybrid utility | Dense safety | Hybrid safety |
| --- | --- | --- | --- | --- | --- |
| cp_case_001 | NICE | 3.0 | 3.0 | 3.0 | 4.0 |
| cp_case_002 | NICE | 3.0 | 3.0 | 3.0 | 2.0 |
| cp_case_003 | AAP | 4.0 | 4.0 | 5.0 | 5.0 |
| cp_case_004 | WHO | 5.0 | 5.0 | 5.0 | 5.0 |
| cp_case_007 | AAP | 4.0 | 5.0 | 5.0 | 5.0 |
| cp_case_009 | NICE | 3.0 | 3.0 | 3.0 | 3.0 |
| cp_case_011 | AAP | 4.0 | 5.0 | 5.0 | 5.0 |
| cp_case_014 | NICE | 4.0 | 5.0 | 4.0 | 5.0 |
| cp_case_025 | WHO | 2.0 | 4.0 | 2.0 | 5.0 |
| cp_case_026 | WHO | 4.0 | 3.0 | 5.0 | 4.0 |

| Fresh metric | Dense | Hybrid |
| --- | --- | --- |
| bleu | 0.201 | 0.189 |
| meteor | 0.429 | 0.420 |
| bertscore_f1 | 0.845 | 0.842 |
| anchor_grounding_recall | 0.347 | 0.374 |

Fresh ROUGE-L F1 is 0.3258 for Dense and 0.3167 for Hybrid.

BLEU is sentence BLEU-4 divided by 100 with the 13a tokenizer and exponential smoothing. METEOR uses lowercased WordPunct tokens and default Porter/WordNet matching. DistilBERT BERTScore uses layer 5, no IDF and no baseline rescaling. Standard backbone truncation affects 14/20 pairs. Full plan text is retained for usability review. The reference is a deterministic template, not independent clinical ground truth; Dense's slightly higher similarity scores do not establish better care.

## 5. Multi-agent results and safety interpretation

| Measure | Dense-MA | Hybrid-MA |
| --- | --- | --- |
| Reported trace verification rate | 0.700 | 0.700 |
| Reported trace mean confidence | 0.695 | 0.695 |
| Reported mean resolution steps | 3.600 | 3.700 |
| Fresh regimen-incomplete rate | 0.700 | 0.800 |
| Fresh ungrounded-dose rate | 0.400 | 0.000 |
| Fresh unsupported-claim plan rate | 0.800 | 0.800 |

Reported verifier confidence is an uncalibrated historical self-report. A verified flag may coexist with flagged claims in those traces. Fresh unsupported-claim rate means the fraction of plans with at least one quote-checked finding, not the fraction of all individual claims. Safe withholding and regimen completeness are distinct outcomes. The CSVs retain case-level findings and denominators. No composite difference is assigned to a particular generator, judge or resolver.

| Saved arm (n=10) | Regimen incomplete | Ungrounded dose | LLM-reported unsupported claim |
| --- | --- | --- | --- |
| dense_only | 0.700 | 0.100 | 0.900 |
| hybrid | 0.600 | 0.100 | 1.000 |
| dense_only_multiagent | 0.700 | 0.400 | 0.800 |
| hybrid_multiagent | 0.800 | 0.000 | 0.800 |

An automatic evaluator audit flagged 32 findings that select a heading, an empty quotation or a very short line. These are retained and marked for independent review; line-ID validity alone does not establish a correct claim judgment. Consequently, reported unsupported-claim findings and aggregate ratings carry unresolved evaluator error and cannot certify clinical safety. No unfavorable completed response was discarded or regraded to improve the numerical results.

## 6. Why the ML score approaches 100%

| Supplied-label test measure | Value |
| --- | --- |
| auroc | 0.99921 |
| auprc | 0.99913 |
| accuracy | 0.96809 |
| sensitivity | 0.93061 |
| specificity | 1.00000 |
| brier | 0.00938 |
| f1 | 0.96406 |

Thresholded measures in this table use the original validation-selected research cutoff 0.963643, not a clinical treatment threshold. At a fixed 0.5 cutoff the same calibrated model has accuracy 0.98811. Different cutoffs explain the two accuracy values; neither establishes prospective clinical performance.

The pinned 150-tree forest is a concurrent supplied-label classifier using eighteen reviewed inputs and missingness indicators. The days-0-2 test has n=1598. The synthetic demo's raw forest score is 0.9982920927. Calibration applies sigmoid(3.2677611461 * logit(raw) + 0.9684784989), producing 0.999999999655. The app's >99.9% display is therefore numerical saturation of this dataset model, not diagnostic certainty.

The raw score is already extreme because the demo follows the dataset's strongly separating patterns. Its PCT value of 2 is close to the positive-label fit median of 1.9855, versus 0.31 for negative labels. CRP of 20 is at approximately the 99.34th percentile of all observed fit values. The first, second and third quartiles of the demo's reached tree-leaf probabilities are all 1.0. These are dataset associations with undocumented clinical timing/units, not diagnostic likelihoods.

![Figure 1. Unchanged fitted calibration, internal supplied-label reliability, single-variable separability and synthetic input sensitivity. These diagnostics do not validate clinical EOS risk.](output/research/figures/probability_audit.png)

| Input to fitted calibration | Output dataset score |
| --- | --- |
| 0.100000 | 0.0020021558 |
| 0.500000 | 0.7248161265 |
| 0.700000 | 0.9767345509 |
| 0.900000 | 0.9997109101 |
| 0.998292 | 0.9999999997 |

Calibration improves the internal Brier score from 0.01817 to 0.00938. That assesses the same supplied-label population, not a clinical EOS population. The source has 13,899 repeated patient/hour rows, 6,858 conflicting-label patient/hour pairs and 6,830 IDs with changing sex. Birth weight is at its upper recorded value in 67.5% of rows. Its identity, unit, onset and result-availability provenance remain unresolved.

| Diagnostic predictor/feature set | Audit AUC |
| --- | --- |
| PCT | 0.986 |
| Oxygen | 0.969 |
| CRP | 0.954 |
| Lactate | 0.864 |
| Baseline-only logistic | 0.576 |
| Vitals without laboratory logistic | 0.935 |

All direct patient-ID and exact predictor-vector overlaps across partitions were zero, fit-only preprocessing was reconstructed, and shuffled-label controls were near chance. The small forest fit-test AUC gap does not suggest ordinary training memorization alone. However, source identities are inconsistent, concurrent laboratory/treatment variables strongly separate the supplied label, and measurement availability relative to diagnosis is unknown. Prospective diagnostic-workflow leakage, label construction artifacts and lack of external validity cannot be ruled out. The training CSV was not confirmed synthetic by the user; only the RAG benchmark was.

In 250 deterministic local measurement perturbations, 153 inputs were within development support, 94 were withheld and 3 were invalid and rejected. Accepted scores remained highly saturated. This is an engineering sensitivity check, not proof of correct risk estimates. Replacing elevated laboratory/vital values changes the score substantially, but these synthetic counterfactuals are not causal treatment effects. Neither arbitrary probability clipping nor relabeling synthetic cases would repair the missing clinical target.

## 7. Application refinements and corrected development data

The model endpoint now exposes raw and calibrated scores, calibration parameters and an explicit saturation interpretation; original fitted weights and scores are preserved. Patient-specific retrieval now receives observed symptom/trend queries and allergy/renal-safety queries in addition to broad plan-domain queries. Stored encounter age, gestation and weight reach population filtering. Missing, invalid or future historical timestamps withhold automated synthesis rather than becoming prior observations. Graph and selection modes are propagated rather than reporting only the last query's mode. All 110 backend tests pass; updated Flutter widgets pass static analysis.

These later implementation fixes are not credited with the historical pilot scores. Production adapters support pgvector and Neo4j; the local demo uses a local concept-to-passage graph. The pilot CSV arm called Graph is a historical saved ranking, not evidence that a live Neo4j service was benchmarked. Current runtime dose restrictions and dual audits are engineering safeguards, not proof of clinical acceptability.

For the current thirteen-section care-plan workflow, the model selects immutable recommendation quote IDs. The server displays their actual wording, separately from observed patient measurements and longitudinal summaries, and both auditors check source and patient applicability. This source-selection workflow limits unsupported paraphrase; it does not fill absent evidence or manufacture individualized medication orders.

The selection prompt now retains full guideline quotes while omitting repeated URLs, filenames and page metadata from the model view; those records remain intact for server-side citations. Patient-state instructions are conditional on recorded findings rather than asserting respiratory illness for every case. The metadata/source-preservation and well-infant regression checks pass. The local demonstration also runs packaged application code inside its container, rather than importing it from a Windows-mounted source tree.

A later application-source review found two recommendations contaminated by following-section headings. Visual PDF checks corrected only those boundaries, with the original corpus archived and source revision recorded. The no-antibiotic-exposure restriction on NICE 1.5.1 is preserved: that pathway is excluded from the fixed case because treatment status is unknown, and conditional handover uses NICE 1.1.4. The bounded care-plan resolver also selects immutable quote IDs through a compact request, followed by fresh source and safety audits. Regression tests preserve unrecognized clinical notes and conditions. Neither the frozen pilot inputs nor its reported scores are changed by these subsequent fixes.

A subsequent fixed synthetic application control completed 3 fresh provider calls and 11 source-selected claims. It displayed 13 sections, including 9 supported guidance sections. The source auditor used GPT-OSS-120B and the safety auditor Qwen3.8-27B; the generator shared the source auditor's weights. This is a development integration control, separate from the forty historical pilot outputs, not an independent quality or clinical validation study. This preserved first control predates the boundary corrections and does not validate those later changes.

A separate corrected development set contains 100 synthetic cases and 300 chronological observations across ten template families, with immutable demographics, units, availability times, explicit missing data, gestational-age source scope, renal/allergy/referral scenarios, and no invented EOS outcomes. The original gold was untouched. No new gold care plans were manufactured; independent source mapping is still needed. Template variants are dependent and cannot serve as an external clinical validation cohort.

## 8. Priorities before expansion

First, obtain a defensible culture-adjudicated EOS cohort with true birth/onset/result-availability times and verified units; pre-specify calibration and external validation. Keep the current classifier outside clinical decision-making. Second, independently map and review the synthetic benchmark's gold passages, references, guideline scope and citation-number provenance, using the corrected cases without rewriting original results. Third, freeze an identical-draft multi-agent ablation and an independent evaluation set, quantify uncertainty and evaluator disagreement, and test workflow integration before a full 100-case quality claim.

## References

[1] NICE. Neonatal infection: antibiotics for prevention and treatment, NG195. https://www.nice.org.uk/guidance/ng195

[2] AAP. Management of neonates born at >=35 0/7 weeks with suspected or proven early-onset bacterial sepsis (2018). https://publications.aap.org/pediatrics/article/142/6/e20182894/37522

[3] AAP. Management of neonates born at <=34 6/7 weeks with suspected or proven early-onset bacterial sepsis (2018). https://publications.aap.org/pediatrics/article/142/6/e20182896/37519

[4] WHO. Management of serious bacterial infections in infants aged 0-59 days. https://www.who.int/publications/i/item/9789240102903

[5] Collins et al. TRIPOD+AI. BMJ 385:e078378 (2024). https://www.bmj.com/content/385/bmj-2023-078378

[6] Papineni et al. BLEU (2002); Banerjee and Lavie. METEOR (2005); Zhang et al. BERTScore (2020). Metric package versions and backbone hash are recorded with the reproducible outputs.
