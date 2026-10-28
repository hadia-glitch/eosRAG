# NeoGuard EOS: Longitudinal Evidence Representation, Calibrated Neonatal Label Classification and Verified Guideline-Grounded Generation

**Original research software report | Updated 28 October 2026 | Reproducible development experiments**

## Abstract

Early-onset neonatal sepsis support requires a traceable connection between serial observations, statistical estimates and applicable guideline recommendations. NeoGuard EOS is a clinician-facing research application with separate prediction and evidence-generation branches. A temporal findings representation preserves observed measurements, missingness and elapsed-time changes; hybrid retrieval links findings to versioned passages, and a LangGraph workflow subjects generated claims to source and safety auditors. The study evaluates supplied-label classification using a user-provided Kaggle CSV with 100,000 observations and 20,000 identifiers. A data audit exposes conflicting patient/hour records and unstable birth covariates, so these labels are not treated as culture-confirmed EOS and are not used to reconstruct clinical trajectories. Calibrated logistic regression and random forests are trained with patient-disjoint fit, calibration, selection and test partitions. The selected forests achieve test AUROC 0.9996 across supplied neonatal ages and 0.9992 on postnatal days 0-2. Separately, 100 synthetic vignettes (40 NICE, 30 AAP 2018 and 30 WHO 2024) and 36 injected faults examine retrieval, text alignment, model-based judging and release behavior. The generator produces 94/100 structured drafts and verification releases 8/100. Retrieval results are stratified by guideline; concept expansion has lower measured Recall@4 than hybrid retrieval for all three sources in this benchmark, with paired case and scenario-family intervals reported. Lexical and semantic alignment are reported together with abstention coverage, rather than equating text similarity or selective release with clinical correctness. A separate ten-case historical pilot obtains Hybrid exact NDCG@10 0.5503 versus Dense 0.2941, while source-faithfulness proxy ratings remain 2.5-2.7/5 and evaluator errors limit safety conclusions. Subsequent development on the same exposed cases obtains longitudinal source-context Recall@4 of 0.9167, 1.0000, 1.0000 for NICE, AAP and WHO, respectively; these retrieval results clear the mean retrieval entry targets, while answer usability and semantic safety remain unestablished and final evaluation remains on hold. A separate actual-data PIC longitudinal development cohort contains 543 infants and 7 independent positive infants; its best AUROC among the prespecified predictive candidates is 0.5931, so the new model is withheld from clinical risk decisions. A subsequent wording audit on those same cases finds NICE Recall@4 falls from 0.9167 to 0.7667 with plain-language queries; a three-case explanation smoke test also identifies a source-exception omission despite model-auditor agreement, so generalisation and clinical readiness remain unestablished.

**Keywords:** early-onset neonatal sepsis; temporal evidence; calibrated classification; hybrid retrieval; knowledge graph; LangGraph; claim verification; selective generation.

## 1. Introduction

EOS assessment combines maternal risk factors, gestational age, the infant's changing condition, cultures and laboratory findings. NICE NG195 and the AAP gestation-specific reports describe different pathways and population boundaries [1-3]. A useful application must distinguish what was observed, what a statistical model estimates, and what a guideline recommends. A low inflammatory-marker value, a reassuring language model response and an unavailable prediction are different states. Combining them into a single opaque score hides the evidence a clinician needs to assess a case.

The initial application already supported neonatal data entry, serial assessments and guideline search, but relied on a hand-built point score and fallback care-plan text. NeoGuard EOS replaces live score interpretation with a model-artifact contract and an explicit unavailable/abstained state. Its evidence branch uses retrieved passages and verifiable support links. Source availability, model eligibility and authorization are checked independently, and generated content does not become a medication order.

This report addresses three questions. RQ1 asks what can legitimately be learned from the supplied neonatal table after an identity, outcome and timing audit. RQ2 compares sparse, dense, hybrid and concept-linked retrieval on fixed source-based synthetic questions. RQ3 measures how exact support checks and separate auditing roles alter answer coverage, reference alignment and unsupported-claim exposure. The implementation and study deliberately separate concurrent supplied-label classification from the longer-term objective of forecasting culture-confirmed EOS.

The contributions are an auditable temporal evidence representation; a patient-disjoint, calibrated research training workflow with portable JSON inference; a reviewed-source retrieval architecture with optional concept links; an immutable quote-ID generation contract; and a reproducible evaluation reporting negative findings and selective-release denominators. Quality comparisons use completed provider calls; operational logs are retained separately. The experiments are development evidence, and the contribution is an implemented integration and failure analysis rather than a claim that any individual component is a newly invented algorithm.

## 2. Related work and design rationale

Medical retrieval-augmented generation is sensitive to corpus choice, passage relevance and the relationship between retrieved knowledge and a specific question. MIRAGE studies medical RAG components under a common evaluation framework [5]. HippoRAG explores graph-assisted retrieval for multi-hop knowledge access [6]. These approaches motivate separate retrieval ablations here. NeoGuard's optional graph is intentionally narrower: passages are linked to deterministic clinical concept labels. Such links are indexing hints and do not represent causal relationships, verified biomedical facts or patient-specific diagnoses.

The supplied ADRE manuscript frames clinical report generation as reasoning over an explicit intermediate findings document with source-grounded composition [7]. That general design idea is adapted to serial neonatal observations, without reusing its EEG data, reference reports or numerical findings. The representation contains observed clinical measurements and time-aware summaries, and the release mechanism uses source-entailment and safety auditing. This differs from an iterative signal-analysis agent: NeoGuard does not autonomously order tests, reinterpret waveforms or repair a rejected answer until it passes.

BLEU, METEOR, ROUGE and BERTScore provide complementary reference-alignment measures [8-11]. They can reward shared clinical words while missing a dangerous negation, absent condition or wrong population. These metrics are therefore paired with source checks, a fallible model-based judge and deliberate fault injection. TRIPOD+AI motivates transparent reporting of model development, evaluation and intended use [12]; DECIDE-AI motivates distinguishing early software evaluation from evaluation in actual clinical workflows [13]. These frameworks inform reporting, and compliance with their complete checklists is not asserted.

## 3. Data provenance and quality audit

The user supplied a ZIP containing one CSV, Neonatal_Sepsis.csv, and a Kaggle description stating that it contains repeated neonatal observations. No dataset URL, original clinical study, collection institution, patient-recruitment criteria, labeling protocol, license or measurement-availability documentation accompanied the file. The archive member is read by its exact name without extracting arbitrary paths. SHA-256 identifies the analyzed CSV: fe1787c19c929324d2862e5fb66f5cf3945a6ba75a41623a5ba506fa6f9e294d. The audit reports aggregate summaries and does not export source patient rows or identifiers.

Table 1. Supplied CSV integrity and scope.

| Audit item | Measured finding |
| --- | --- |
| Observations / supplied identifiers | 100,000 / 20,000 |
| Positive supplied-label observations | 43,035 (43.035%) |
| Postnatal-age range | 0-28 days |
| Repeated patient/hour rows beyond first | 13,899 |
| Patient/hour pairs with conflicting labels | 6,858 |
| Identifiers with changing gestational age | 13,778 |
| Identifiers with changing birth weight | 7,588 |
| Identifiers with changing sex | 6,830 |
| Birth weight at upper recorded value (4.5 kg) | 67.495% |
| Missing clinical/laboratory entries per field | 3.419%-3.593% |

Observation_Hour takes values 1-5, but cannot be assumed to mean hours since birth or a valid availability timestamp. Conflicting records at the same patient/hour and changing immutable birth covariates prevent defensible reconstruction of a single infant trajectory. The analysis does not silently deduplicate, average contradictory records, invent birth timestamps or assign clinician-adjudicated labels. Patient identifiers remain grouping variables for conservative split isolation, but their integrity as true person identifiers is itself uncertain.

The supplied Sepsis_Label indicates an observation-associated sepsis/non-sepsis state. Culture confirmation, pathogen/contaminant adjudication and event onset are absent. Classification therefore concerns that supplied label at the recorded observation, not a proven future event. A secondary experiment restricts Postnatal_Age to 0, 1 or 2 days to approximate the first-72-hour age window without including ambiguous day-3 records. An age filter cannot convert an unverified label into culture-confirmed EOS. Numeric distributions and high separability motivate investigation of data generation and labeling, but do not establish whether the file is synthetic or clinical.

Six MIMIC-III v1.4 tables were separately supplied: PATIENTS, ADMISSIONS, ICUSTAYS, D_ITEMS, D_LABITEMS and MICROBIOLOGYEVENTS. The local streaming review identified 7,863 candidate newborn admissions and produced protected adjudication materials. CHARTEVENTS and LABEVENTS were unavailable. A culture entry alone does not establish a complete outcome or control, and admission time is not substituted for exact birth time. MIMIC data were not joined into the Kaggle table or used to fit the reported classifiers. The separate adapter requires reviewed birth times, gestation, units, availability assumptions and labels [4].

## 4. System architecture and temporal evidence

[[ARCHITECTURE]]

The application uses Flutter for case entry and timelines, FastAPI for authorized inference and evidence synthesis, Supabase/PostgreSQL for records and passage indexes, and Groq for language generation. Vercel serves the static Flutter build; the model-serving API uses a separate CPU container. Training, source approval, passage ingestion and optional graph synchronization are offline operations. This separation avoids loading training jobs and document ingestion into web request handlers.

### 4.1 Longitudinal findings representation

For a legitimate timestamped cohort, an observation is O=(a,V), where a is age in hours and V is an allowlisted mapping of measurements with known units. A prediction request contains the current observation and strictly earlier, uniquely timed history. Outcomes, culture-result labels and legacy point scores are not predictors. The feature contract extracts current values, missingness and available within-24-hour counts, deltas and least-squares slopes. For measured values v at times t, slope is sum((t-mean(t))*(v-mean(v))) / sum((t-mean(t))^2); it is not a difference per row index. Future observations and duplicate history times are rejected.

The evidence packet contains scoped patient measurements, relative-time history and retrieved passages with document identity, version, section, page and source URL. Names, medical-record numbers, free-text notes and absolute dates are excluded from cloud prompts. Observed trends are described separately from diagnosis and guideline recommendations. A change in CRP is a recorded measurement change; the language model is not allowed to turn that change into an invented calibrated risk probability. The supplied Kaggle table does not exercise the temporal model features because its identity and timing defects make such reconstruction unsound. Synthetic vignettes exercise the history representation in the evidence branch.

### 4.2 Reviewed corpus and retrieval

Production retrieval first requires a current source registry entry with document hash, public URL, reviewer metadata and explicit gestational-age, age and care-setting bounds. A chunk must match the reviewed source version and hash. Unregistered files and unrelated forms are excluded. Full-text PostgreSQL candidates and pgvector candidates are fused using reciprocal rank; an optional Neo4j query adds concept-linked candidate IDs, which must pass the same source and population admission checks. A cross-encoder can rerank admitted candidates. If dense retrieval is unavailable, lexical degradation is explicit; missing reviewed evidence does not trigger a seeded clinical answer.

The synthetic experiment uses separate evaluation-only indexes for NICE NG195 (132 frozen passages), the AAP 2018 report for infants born at least 35 weeks (43 passages), and WHO 2024 serious bacterial infection guidance (141 passages). AAP summary recommendations and complete article paragraphs and WHO recommendations, qualifiers and scope paragraphs retain source-page metadata and SHA-256 identities. WHO cases are restricted to the first 72 hours and preserve hospital, non-hospital and referral-feasibility conditions. The source-gated benchmark contains 100 cases; it does not mark any production source as clinically approved. Paragraph granularity and candidate-pool sizes differ across guidelines; original NICE extraction-boundary concerns remain for clinician adjudication.

### 4.3 Immutable quotations and multi-role verification

The initial generator was asked to reproduce verbatim quotes. It sometimes inserted ellipses, changed wording or joined noncontiguous phrases, causing exact-source validation to fail. The revised contract supplies immutable E#Q# source-span identifiers. The model returns claim text, section and quote IDs; the server materializes exact source text and source labels. Unknown IDs, malformed claims, duplicate claim identifiers and unsupported numeric medication/fluid doses are rejected. Selecting an existing quote proves traceability only; it does not prove that the quote entails the claim.

A LangGraph state machine runs synthesis, then source-entailment and neonatal-safety auditors, followed by release. Auditors receive the same source packet and draft, without generator rationale or each other's decisions. They must cover every claim and reject unsupported inferences, wrong populations, assumed-normal missing data and unsafe reassurance. Unanimous acceptance and successful structural/source checks release the unchanged draft for clinician review. Dissent, malformed verdicts or service outages withhold the complete plan. There is no silent repair loop. The same openai/gpt-oss-120b model supplies all roles, so independence is procedural and correlated errors remain possible.

### 4.4 Application and deployment controls

Supabase bearer tokens establish identity; encounter ownership is checked before loading history. Administrative authorization uses server-controlled app metadata. Body-size limits, request deadlines, no-store responses and append-only decision metadata support operation and audit. Model artifacts are JSON rather than executable pickle and require a configured digest. Client builds contain only public API and Supabase configuration. The web bundle was scanned for environment assets and configured server credentials, with no matches. These engineering controls do not establish an institutional compliance certification.

## 5. Supplied-label model development

Two experiments use the same fixed patient-ID partition assignment: all supplied neonatal ages and postnatal days 0-2. Patient identifiers are sorted and split with seed 31 into fit (55%), calibration (15%), model-selection validation (15%) and final test (15%) groups. This is random patient-ID isolation, not temporal or external validation. The age-restricted cohort inherits those assignments; its retained group proportions can differ. Neither Patient_ID nor Observation_Hour is a predictor.

Table 2. Partition sizes; each cell gives observations / supplied patient identifiers.

| Cohort | Fit | Calibration | Validation | Test |
| --- | --- | --- | --- | --- |
| all neonatal ages | 55,057 / 11,000 | 14,967 / 3,000 | 15,039 / 3,000 | 14,937 / 3,000 |
| postnatal days 0 2 | 5,378 / 1,795 | 1,519 / 498 | 1,640 / 535 | 1,598 / 509 |

Numeric inputs retain the CSV's supplied units. Sex and delivery mode use training-observed category indicators. Median imputation, centering and scaling are fitted only on the fit partition; a missingness indicator accompanies each design column. A logistic classifier uses C=1 and a 150-tree random forest uses maximum depth 10 and minimum leaf size 15. These fixed settings are not optimized on the test set. Observations receive inverse within-patient-frequency weights for fitting and calibration, reducing dominance by identifiers with more rows. Final discrimination and calibration metrics describe observations; the uncertainty analysis clusters resampling by identifier.

Each classifier is calibrated on its separate calibration partition with logistic scaling of clipped probability logits. Model choice minimizes validation Brier score, independently in each cohort. A research threshold is the fifth percentile of positive validation predictions, targeting approximately 95% validation sensitivity without encoding an antibiotic rule. The untouched test partition then provides AUROC, average precision (AUPRC), Brier score, sensitivity, specificity, PPV and calibration bins. A constant training-prevalence predictor is retained as a reference baseline. Three hundred bootstrap replicates resample test identifiers with replacement, retaining all their observations, to estimate percentile 95% intervals for the selected model.

Portable JSON stores preprocessing, calibration parameters and logistic coefficients or tree arrays. Exported predictions match scikit-learn within 1e-7 on the test design matrix. Tree inference explicitly uses float32 inputs before threshold comparisons, matching scikit-learn and preventing boundary disagreements. These research artifacts identify their target as supplied Sepsis_Label and are intentionally incompatible with the clinical eos-landmark-v1 contract. They cannot become eligible EOS models merely by being placed in the application's artifact directory.

## 6. Synthetic RAG experimental protocol

### 6.1 Cases, references and retrieval ablations

One hundred synthetic vignettes include the original 18 unchanged cases and 82 additions: 40 NICE, 30 AAP and 30 WHO cases. The six families remain respiratory deterioration, CRP-only reasoning, incomplete stopping criteria, initial investigations, an isolated known risk factor and missing results. Added cases vary gestation, age, care setting and observation availability. Every gold ID resolves to an indexed passage, and case, source and passage hashes are recorded with seed 31. References are engineering-authored rather than clinician-adjudicated. Related variants share templates; 100 cases do not represent 100 independent clinical scenarios.

Each guideline is searched against its source-only candidate pool. The original BM25, MiniLM-L6-v2 normalized exact-cosine, reciprocal-rank hybrid and hybrid-plus-concepts implementations remain unchanged, with RRF offset 60 and four returned passages. The original 18 retrieval rankings replay exactly. Recall@4 is the fraction of proposed relevant IDs retrieved; MRR@4 is the reciprocal rank of the first relevant ID. WHO exact-text PDF duplicates were removed in a logged structural index amendment. A superseded 114-case retrieval-only prototype remains archived; the user-requested 100-case allocation used predetermined family quotas and case order rather than score-based selection. No retrieval hyperparameter was tuned within this frozen expanded-100 study; the separately labelled post-hoc development in Section 13 changes the index and retrieval configuration after examining these cases.

AAP and WHO source identity and recommendation spans were technically checked, but clinical source approval and gold adjudication remain pending. Passage-level age, gestation and setting annotations are stored for review; the frozen source-gated retriever does not apply those passage-level filters. WHO evidence gaps, referral conditions and treatment-duration statements are not replaced with NICE or AAP rules. Overlapping narrative spans can be relevant even when absent from the proposed gold-ID set, limiting strict ID-based recall interpretation. The experiment measures offline concept expansion rather than live Neo4j or pgvector performance.

### 6.2 Paired verification ablation and provider failures

Generation uses the concept-expanded hybrid packet under the fixed evaluation protocol, even when that variant performs worse in the retrieval ablation. The configured Groq model is openai/gpt-oss-120b, temperature 0, low reasoning effort, JSON response mode and a 3,000-token completion ceiling. One draft per case is paired with an unverified arm that emits that draft and a verified arm that either emits the identical draft or withholds it. This isolates release filtering; it does not test whether a verifier can rewrite a better answer. Both conditional released-only quality and all-case quality are reported.

The first quote-echo run and the revised quote-ID run are retained separately. The same development cases informed the engineering change; they are not relabeled as an untouched held-out test. Cases with incomplete provider execution are excluded from model-quality comparisons, with the same eligible case population used in both paired arms. Completed malformed answers and verifier disagreements remain quality outcomes. Only provider-blocked steps are retried with bounded, paced requests; existing answers, including schema errors and completed dissent, are replayed verbatim. Operational attempts are stored separately. Regression tests prevent an audit of a missing draft being reused for a later draft. This eligibility rule separates model performance from service availability. The historical and current verifier source hashes differ; the expanded study reruns the original cases with the current frozen verifier and logs this runtime drift. Current auditor completions are limited to 1,000 tokens and resolution completions to 2,200 tokens. The retained historical runner used transport defaults rather than forwarding completion options, so exact historical verifier/transport equivalence is not asserted. Model temperature remains zero; no provider sampling seed or immutable model snapshot is available. Completed role responses are checkpointed by prompt hash and audit-round occurrence.

### 6.3 Automatic metrics, model-based judging and fault injection

For a case with G labelled relevant passages and a fixed retrieval depth k, Precision@k = relevant retrieved/k has ceiling min(G,k)/k, whereas Recall@k = relevant retrieved/G has ceiling min(G,k)/G. Consequently, increasing k can increase attainable recall while decreasing the precision ceiling. MRR@k and ideal-normalized nDCG@k have ceiling 1 when the corresponding ideal ordering is attainable. Per-case F1@k has ceiling 2 min(G,k)/(G+k). These ceilings describe the annotation and retrieval-depth design, not an intrinsic limit of clinical relevance or a model-performance excuse. Ceiling-normalizing precision is not used to replace conventional precision; with G <= k, it would reproduce recall rather than provide independent evidence of improvement.

BLEU-4 uses sacreBLEU corpus aggregation, 13a tokenization and exponential smoothing, divided by 100 for a 0-1 scale. METEOR uses NLTK with lowercased WordPunct tokens, Porter stemming and WordNet matching. ROUGE-1, ROUGE-2 and ROUGE-L are stemmed F1. BERTScore uses unrescaled contextual token alignment without IDF: DistilBERT-base-uncased layer 5 and RoBERTa-large layer 17. Versions and BERTScore configuration hashes are saved. Descriptive 95% intervals use 2,000 resamples with seed 31: paired case resampling and whole-scenario-family resampling. Unequal family sizes retain their case weights; six families provide limited cluster-level inference. Token-length truncation is counted. Surface and embedding alignment do not establish medical correctness.

No empirical clinical threshold of 0.8 is justified for BLEU, METEOR, ROUGE or BERTScore. A valid paraphrase need not approach a lexical-overlap ceiling, and a fluent but unsafe answer may have high semantic similarity. All-case generation metrics also depend on release coverage; withheld cases cannot be removed without reporting the conditional denominator. Relevance annotations are not exhaustive clinical judgments, so an unlabelled but valid passage can be counted as a false positive under exact-ID scoring.

A separate prompt, blind to the arm label and previous auditor decisions, judges each available draft against the case, sources and frozen reference. It assigns integer 1-5 scores for grounding, patient fidelity, completeness, actionability and uncertainty handling, plus an unsafe-claim count. The same model is used as generator, auditor and judge; the judge is therefore a dependent semantic proxy with potential shared errors and reference bias. Because the verified arm releases unchanged text, its conditional judge scores reuse the same draft judgment. Withheld answers receive zero all-case alignment but have no meaningful judge score; judge means therefore include an explicit available-case denominator.

Thirty-six injected drafts, twelve per guideline with four fault types and three variants each, test negation reversal, omitted stopping conditions, an invented dose and fabricated normal findings. Their source labels and excerpts are real evaluation-corpus spans, so citation existence alone cannot validate their content. The unverified arm would emit all injected drafts. The verified arm is measured for withholding, with deterministic dose rejection distinguished from semantic-auditor rejection and service-unavailable withholding. These deliberately enriched faults are not an estimate of naturally occurring hallucination prevalence.

## 7. Results

### 7.1 Supplied-label classification and calibration

Table 3. Final test metrics. Thresholds were selected on validation data; neither threshold is a treatment rule.

| Cohort | Model | AUROC | AUPRC | Brier | Sensitivity | Specificity |
| --- | --- | --- | --- | --- | --- | --- |
| All ages | logistic | 0.9993 | 0.9991 | 0.0090 | 0.9478 | 0.9980 |
| All ages | forest | 0.9996 | 0.9994 | 0.0063 | 0.9490 | 0.9992 |
| Days 0-2 | logistic | 0.9990 | 0.9988 | 0.0129 | 0.9361 | 0.9988 |
| Days 0-2 | forest | 0.9992 | 0.9991 | 0.0094 | 0.9306 | 1.0000 |

Both cohorts select the forest by validation Brier score. The all-age test set contains 14,937 observations from 3,000 supplied identifiers; the age-restricted test set contains 1,598 observations from 509 identifiers. These identifiers are disjoint from development groups. The validation operating points do not force test sensitivity to equal the development target: age-restricted forest sensitivity is 0.9306. This distinction matters when describing a high-sensitivity workflow.

Table 4. Selected-forest patient-cluster bootstrap 95% intervals (300 replicates).

| Metric | All ages | Days 0-2 |
| --- | --- | --- |
| AUROC | [0.9994, 0.9997] | [0.9986, 0.9997] |
| AUPRC | [0.9992, 0.9996] | [0.9984, 0.9996] |
| Brier | [0.0055, 0.0071] | [0.0062, 0.0129] |
| Sensitivity | [0.9443, 0.9537] | [0.9125, 0.9457] |
| Specificity | [0.9986, 0.9998] | [1.0000, 1.0000] |

The days-0-2 specificity interval is degenerate at 1 because no false positives occurred at the selected threshold in that supplied-label test set. Resampling the same observed records cannot create unseen errors; the interval does not establish perfect specificity in a new population.

![Figure 2. Held-out supplied-label calibration and Brier scores. The class label and source-data defects constrain interpretation.](output/research/figures/ml_results.png)

The near-perfect discrimination is not taken as proof of a mature EOS forecaster. As a post-hoc separability diagnostic, a depth-3 decision tree using a small laboratory/vital subset obtains accuracy 0.9728 and AUROC 0.9887. Its principal splits involve PCT and CRP, consistent with strongly separable supplied labels. This diagnostic was not part of model selection, does not establish how labels were created, and could reflect either biological selection or data/label-generation mechanisms. Lack of onset and result-availability times also prevents excluding concurrent diagnostic/workflow leakage. Narrow bootstrap intervals quantify sampling variability under the supplied records, not uncertainty about their provenance or outcome validity.

### 7.2 Retrieval and concept expansion

Table 5. Source-stratified retrieval; brackets show paired-case bootstrap 95% intervals for each estimate. Full scenario-family intervals and paired method contrasts are provided in the CSV tables.

| Guideline (N) | Retriever | Recall@4 [95% CI] | MRR@4 [95% CI] |
| --- | --- | --- | --- |
| NICE (40) | lexical | 0.2583 [0.1792, 0.3417] | 0.5000 [0.3583, 0.6375] |
| NICE (40) | dense | 0.2792 [0.1917, 0.3708] | 0.4000 [0.2875, 0.5250] |
| NICE (40) | hybrid | 0.3792 [0.2750, 0.4833] | 0.4938 [0.3624, 0.6230] |
| NICE (40) | hybrid concepts | 0.3750 [0.2875, 0.4667] | 0.4604 [0.3375, 0.5833] |
| AAP (30) | lexical | 0.6167 [0.5000, 0.7333] | 0.7306 [0.6027, 0.8500] |
| AAP (30) | dense | 0.4167 [0.3000, 0.5500] | 0.4389 [0.2944, 0.5889] |
| AAP (30) | hybrid | 0.5500 [0.4333, 0.6667] | 0.6722 [0.5278, 0.8111] |
| AAP (30) | hybrid concepts | 0.3833 [0.2667, 0.5167] | 0.3750 [0.2500, 0.5083] |
| WHO (30) | lexical | 0.1667 [0.0833, 0.2500] | 0.2167 [0.0972, 0.3584] |
| WHO (30) | dense | 0.2333 [0.1333, 0.3333] | 0.2500 [0.1306, 0.3833] |
| WHO (30) | hybrid | 0.3333 [0.2167, 0.4667] | 0.2694 [0.1556, 0.4056] |
| WHO (30) | hybrid concepts | 0.1667 [0.0333, 0.3000] | 0.1667 [0.0333, 0.3000] |

For hybrid-plus-concepts minus hybrid, Recall@4 differences are: NICE -0.0042 (case [-0.0583, 0.0458], family [-0.0935, 0.0667]); AAP -0.1667 (case [-0.2500, -0.0833], family [-0.3333, 0.0000]); WHO -0.1667 (case [-0.2500, -0.0833], family [-0.3333, -0.0167]).

The measured concept-expansion scores do not support a blanket graph benefit. The original 18 rankings are unchanged; differences between the old NICE average and the expanded NICE average reflect the additional queries rather than a changed retrieval algorithm. Source-stratified counts, candidate-pool asymmetry and engineering-authored relevance judgments limit generalization; no source-pooled headline retrieval score is used.

Table 5a. Annotation-dependent macro-average ceilings at four retrieved passages. Each case has two or three labelled relevant passages; Recall@4, MRR@4 and nDCG@4 can each reach 1.0000. Source-specific ceilings must accompany conventional precision and F1 scores.

| Source (cases) | Labelled passages | Precision@4 ceiling | F1@4 ceiling | Recall / MRR / nDCG ceiling |
| --- | --- | --- | --- | --- |
| NICE (40) | 107 | 0.6688 | 0.7952 | 1.0000 / 1.0000 / 1.0000 |
| AAP (30) | 60 | 0.5000 | 0.6667 | 1.0000 / 1.0000 / 1.0000 |
| WHO (30) | 60 | 0.5000 | 0.6667 | 1.0000 / 1.0000 / 1.0000 |
| All cases (100; design only) | 227 | 0.5675 | 0.7181 | 1.0000 / 1.0000 / 1.0000 |

The all-case row describes the benchmark design rather than a pooled retrieval-performance claim. A Precision@4 target of 0.8 is unattainable with these fixed gold sets even if every labelled relevant passage is returned. Recall@4 and MRR@4 targets near 0.8 remain attainable and require measurement rather than a ceiling adjustment. Re-adjudication should examine potentially relevant unlabelled passages without changing gold labels merely to improve system scores.

### 7.3 Generation, verification and coverage

All 100 declared cases completed provider execution. Parsed discussion drafts were produced for 94/100 cases and 8/100 were released. Structural failures and completed auditor dissent remain quality outcomes. The paired arms share the same initial draft; verification changes release rather than wording.

Table 6. Source-stratified alignment and emission coverage. Conditional scores retain source-population coverage rather than displaying conditional coverage as 100%. All-case withheld responses have zero alignment. Full lexical/semantic estimates and both bootstrap interval types appear in CSV tables.

| Guideline | Arm | Scored N | Emitted / quality N | BLEU-4 | METEOR | ROUGE-L | DistilBERT F1 | RoBERTa F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NICE | without verification | 40 | 34/40 | 0.0287 | 0.2336 | 0.1524 | 0.6775 | 0.7231 |
| NICE | verified all cases | 40 | 5/40 | 2.37e-06 | 0.0280 | 0.0287 | 0.1004 | 0.1078 |
| NICE | released only | 5 | 5/40 | 0.0217 | 0.2240 | 0.2293 | 0.8030 | 0.8624 |
| NICE | generated only | 34 | 34/40 | 0.0287 | 0.2748 | 0.1793 | 0.7971 | 0.8506 |
| AAP | without verification | 30 | 30/30 | 0.0138 | 0.2738 | 0.1574 | 0.8007 | 0.8464 |
| AAP | verified all cases | 30 | 1/30 | 1.57e-09 | 0.0108 | 0.0082 | 0.0281 | 0.0293 |
| AAP | released only | 1 | 1/30 | 0.0428 | 0.3251 | 0.2471 | 0.8425 | 0.8802 |
| AAP | generated only | 30 | 30/30 | 0.0138 | 0.2738 | 0.1574 | 0.8007 | 0.8464 |
| WHO | without verification | 30 | 30/30 | 0.0109 | 0.2407 | 0.1336 | 0.7835 | 0.8389 |
| WHO | verified all cases | 30 | 2/30 | 7.31e-12 | 0.0136 | 0.0130 | 0.0555 | 0.0580 |
| WHO | released only | 2 | 2/30 | 0.0435 | 0.2039 | 0.1946 | 0.8323 | 0.8705 |
| WHO | generated only | 30 | 30/30 | 0.0109 | 0.2407 | 0.1336 | 0.7835 | 0.8389 |

Corpus BLEU brevity penalties strongly reflect withheld output length; very small all-case values do not measure a rewriting effect.

Table 7. Paired all-case verified-minus-unverified DistilBERT F1; negative values reflect the coverage cost of withholding the same draft.

| Guideline | Paired N | Released / N | Difference | Case 95% CI | Family 95% CI |
| --- | --- | --- | --- | --- | --- |
| NICE | 40 | 5/40 | -0.5771 | [-0.6786, -0.4742] | [-0.7185, -0.4455] |
| AAP | 30 | 1/30 | -0.7726 | [-0.8036, -0.7157] | [-0.8032, -0.7223] |
| WHO | 30 | 2/30 | -0.7280 | [-0.7819, -0.6489] | [-0.7803, -0.6285] |

Released-only comparisons are selected-population comparisons. A released draft has identical wording in both arms, so verification cannot improve that draft through rewriting in this experiment. Alignment and release counts do not establish clinical correctness.

![Figure 3. Source-stratified retrieval, emission coverage and the paired semantic-alignment cost of withholding the same draft.](output/research/figures/rag_expanded_results.png)

### 7.4 Model-based semantic and usability proxies

Table 8. Dependent model-judge means with judged-output coverage. These are automated proxies rather than clinician usability observations.

| Guideline | Arm | Judged / quality N | Grounding | Fidelity | Completeness | Actionability | Uncertainty | Unsafe claims |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NICE | without verification | 34/40 | 3.8529 | 3.9118 | 3.7059 | 3.8235 | 3.7647 | 15 |
| NICE | with verification | 5/40 | 4.8000 | 3.8000 | 3.4000 | 3.4000 | 4.2000 | 0 |
| AAP | without verification | 30/30 | 4.3333 | 4.2333 | 3.9667 | 4.5333 | 4.2333 | 5 |
| AAP | with verification | 1/30 | 5.0000 | 5.0000 | 5.0000 | 5.0000 | 5.0000 | 0 |
| WHO | without verification | 30/30 | 4.5000 | 4.5000 | 4.2000 | 4.3333 | 4.6000 | 3 |
| WHO | with verification | 2/30 | 5.0000 | 5.0000 | 4.5000 | 3.5000 | 5.0000 | 0 |

The same model supplies generation, audit and judge roles. Released-only judge means describe a selected subset, and shared-model agreement does not establish independent clinical correctness. Completed invalid judge outputs remain unavailable ratings rather than favorable imputations. Source-specific intervals and rating denominators are retained in the CSV tables.

### 7.5 Injected faults, failure cases and runtime

Table 9. Deliberately injected errors, separated by guideline; invalid verdicts are not credited as semantic detection.

| Guideline | Injected | Unverified emitted | Verified emitted | Structural reject | Semantic reject | Invalid verdict |
| --- | --- | --- | --- | --- | --- | --- |
| NICE | 12 | 12 | 0 | 3 | 9 | 0 |
| AAP | 12 | 12 | 0 | 3 | 8 | 1 |
| WHO | 12 | 12 | 0 | 3 | 9 | 0 |

These 36 intentionally enriched drafts test negation reversal, missing conditions, invented doses and fabricated normal findings. Counts are not estimates of naturally occurring hallucination prevalence. Per-case and fault-family bootstrap contrasts are provided in the CSV tables.

Latency is not treated as a quality result because operational wall time includes minute-rate waits and checkpoint replay. Provider outages are retained in operational logs and excluded from quality populations; completed malformed answers and clinical disagreement remain outcomes.

## 8. Discussion and limitations

The experiments illustrate why model discrimination, evidence retrieval, generation quality and release safety require separate claims. A classifier can nearly reproduce a supplied label while the data remain unsuitable for the intended clinical forecast. A retrieved quote can be authentic while the generated sentence misstates its meaning. A verification gate can reduce emitted unsupported content by withholding almost everything, without producing a useful answer. Reporting the label definition, all-case metrics and release coverage makes these distinctions visible.

The supplied CSV has unresolved identity, unit, provenance and outcome defects. Patient-ID isolation mitigates direct grouping leakage but cannot repair incorrect grouping or guarantee that related records represent distinct people. The secondary age subset is not an external cohort. Availability timestamps are absent, so forecasting lead time and early-warning benefit cannot be computed. The study does not compare a clinically validated EOS calculator with the research classifier, and the previously used hand-built point score is not presented as an accepted clinical baseline.

The RAG fixture contains 100 synthetic English-language cases across NICE, AAP and WHO rather than an external patient cohort. References and gold passages were proposed by the engineering workflow, repeated variants share templates and clinical adjudication remains pending. The original 18 cases informed earlier quote-ID development; a superseded retrieval-only expansion also preceded the user-requested size amendment, preventing an untouched-test interpretation. Different guideline populations, recommendation styles and candidate-pool sizes limit cross-source comparisons. WHO covers 0-59-day infections and resource-dependent referral pathways, while only its first-72-hour subset is tested; AAP cases remain within the at-least-35-week report. The graph ablation uses deterministic concept expansion without a live graph database, and the dense experiment uses exact similarity without a deployed vector service. These controlled measurements inform engineering choices but do not establish production retrieval coverage across all neonatal subpopulations or institutions.

No clinician review of generated care plans, clinical validation, prospective deployment study or clinical usability study was performed; this work reports supplied-label modeling and synthetic engineering evaluation only.

A subsequent study should establish a culture-adjudicated cohort with true birth/onset/availability times; compare snapshot and causal longitudinal predictors; test calibration across sites and prevalence shifts; create independently authored cases and reference answers; evaluate graph relations and source scope; and assess abstention, omissions and workflow fit under realistic workloads. Different model families for auditing and judging would help investigate shared-error dependence, but would not by themselves establish correctness. An actual clinical release requires evidence outside the scope of this development benchmark.

## 9. Conclusion

NeoGuard EOS provides an implemented architecture for joining serial observed findings to statistical models and source-linked explanations while preserving separate eligibility and release boundaries. Actual experiments train calibrated classifiers on the supplied neonatal labels and expose serious source-data limitations. Synthetic experiments quantify retrieval differences and the cost of complete-plan verification, including service failure, abstention and unsupported inferences. Immutable quote IDs improve citation mechanics; concept expansion has lower measured Recall@4 than hybrid retrieval in each source-specific cohort. The resulting artifacts support reproducible research and further refinement while keeping unsupported EOS and deployment claims out of the application.

## 10. Reproducibility and artifact availability

The repository contains training/audit code, patient-cluster bootstrap output, JSON research artifacts with digests, fixed synthetic cases/references, evaluation-corpus hashes, retrieval rankings, generated drafts, auditor decisions, archived attempts, model-based judgments and per-case metric outputs. Raw CSV and MIMIC patient tables are not bundled in the public research report. The Kaggle source URL and original study remain unavailable, so provenance verification is an explicit unresolved item. Credentials remain in local ignored environment files and are not copied into the paper or web bundle. Reproduction commands are documented in docs/RESEARCH_EXPERIMENTS.md.

Classifier runtime versions: numpy 2.2.6, pandas 2.3.1, scikit-learn 1.7.0. Metric runtime versions: torch 2.12.1, transformers 5.12.1, bert-score 0.3.13, nltk 3.9.4, sacrebleu 2.6.0, rouge-score 0.1.2. Primary BERTScore hash: distilbert-base-uncased_L5_no-idf_version=0.3.12(hug_trans=5.12.1). Secondary hash: roberta-large_L17_no-idf_version=0.3.12(hug_trans=5.12.1). The experiments use different existing Python environments for training and CPU text scoring; these recorded versions make that difference explicit.

## 11. Additional model audit and application integration

### 11.1 Post-hoc leakage and separability checks

The original patient-ID partitions were retained for additional diagnostics. All six pairwise ID overlaps and all exact predictor-vector overlaps between partitions are zero. Fit-only medians, means and scales were recomputed and matched the stored preprocessing. Identifiers, observation sequence and labels are excluded from predictors. These checks address direct implementation leakage; inconsistent source identities and unknown outcome-availability times prevent a broader claim that leakage has been eliminated.

Table 10. Additional diagnostics on the original partitions; these are not independent external evaluations.

| Cohort | Forest fit AUC | Forest test AUC | Fit-test gap | Shuffled-label AUC range | Baseline-only AUC | Labs-only AUC |
| --- | --- | --- | --- | --- | --- | --- |
| All ages | 0.9998 | 0.9996 | 0.000250 | 0.5014-0.5031 | 0.5835 | 0.9959 |
| Days 0-2 | 0.9998 | 0.9992 | 0.000566 | 0.5027-0.5169 | 0.5758 | 0.9966 |

Each negative control independently shuffles fit and test labels for three fixed seeds; the resulting AUC ranges are descriptive, not a permutation significance test. Scores of the same random fits against the original labels are also retained, including non-chance values; they are not substituted for the negative-control result. Standardized nearest-neighbor checks on 1,000 sampled test rows per cohort found no effectively identical fit rows, but are not exhaustive. Strong laboratory-only separation and high discrimination after removing CRP/PCT leave the source-label construction question unresolved. Deliberate 1,000-fold unit errors can preserve high AUC, demonstrating why discrimination cannot validate an input mapping. The serving boundary rejects invalid scales and values outside fit support.

### 11.2 Four-estimator comparison and SHAP

A post-hoc comparison fits Gradient Boosting (150 trees, depth 3), XGBoost (200 trees, depth 4), a linear SVM (C=0.5), and the original Random Forest (150 trees, depth 10). Each component is calibrated on the separate original calibration group; their fixed equal mean forms a probability ensemble. Validation Brier score selects XGBoost in the all-age cohort and the ensemble in days 0-2. This uses the previously reported partition and is explicitly an exploratory extension, not a newly untouched test. It does not replace the pinned application forest automatically.

Table 11. Days-0-2 exploratory comparison on the same 1,598 test observations.

| Estimator | AUROC | Brier | Sensitivity | Specificity |
| --- | --- | --- | --- | --- |
| gradient boosting | 0.9996 | 0.0076 | 0.9388 | 0.9977 |
| xgboost | 0.9996 | 0.0076 | 0.9361 | 1.0000 |
| svm | 0.9990 | 0.0130 | 0.9401 | 0.9977 |
| forest | 0.9992 | 0.0094 | 0.9306 | 1.0000 |
| equal probability ensemble | 0.9995 | 0.0078 | 0.9333 | 1.0000 |

The portable ensemble export matches the fitted calibrated components within 1e-5. Local SHAP KernelExplainer is evaluated with 256 coalition samples, seed 31, and an aggregate fit-median/modal reference; the offline ensemble report uses eight test examples, not a population-level explanation study. The application separately explains its served calibrated forest using the same bounded method and checks prediction parity and additive reconstruction before returning attributions. Contributions are reference-dependent associations, not causal effects, and the initial lightweight median-replacement effects are explicitly labeled as a different method.

### 11.3 Connected application and current refinement boundary

The Flutter Risk tab now discovers the bundled days-0-2 calibrated forest through authenticated model metadata, presents its exact eighteen-field contract, saves the reviewed inputs and calls the research prediction endpoint. Only birth weight has an automatic quantity conversion (grams to kilograms); laboratory and numeric-oxygen fields with undocumented dataset units remain separate from clinical laboratory fields. Baseline fields are mandatory. More than three unknown measurements, the fit-partition 99.5th-percentile missing-count limit, cause withholding. Numeric ranges, categories, completed postnatal age and model age below 72 hours are validated. Research probability is not translated into a clinical risk category or an antibiotic decision. Assessment/review timestamps prevent older research vitals being re-dated as new measurements in a later assessment.

The release client excludes private environment files and authenticates model requests with the current user session. Contract, persistence, routing, prediction parity, missingness, out-of-support and identifier-rejection tests cover this connection. Actual hosted authentication/database access and deployment remain separate operational checks. Production retrieval also now implements bounded synonym expansion, finer recommendation concepts and optional MMR diversity after cross-encoder reranking; the synthetic retrieval results in Section 7 use the frozen broad-concept evaluation configuration and do not measure these additional production refinements. An explicit Ollama-compatible local transport is implemented without automatic cloud fallback. A local Qwen3:4b-q4_K_M call passed a constrained-JSON transport check; this establishes local connectivity and response formatting, not care-plan quality or clinical validity.

### 11.4 Additional backbones and bounded resolution

The same 100 cases are evaluated with the two original additional Groq backbones. Each one-revision arm reuses its paired initial draft and completed audits, including malformed output and dissent. At most one revision is permitted after completed disagreement; both auditors freshly assess any revision. The original 120-second budget and 20-second minimum cloud-call gap are retained, with initial elapsed time deducted during replay. The primary paired experiment remains a zero-repair release-filtering study.

Table 12. Source-stratified bounded-resolution release counts and paired release-fraction differences.

| Backbone | Guideline | Paired N | Baseline released | One-repair arm released | Attempts | Difference | Case 95% CI | Family 95% CI |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| openai/gpt-oss-20b | NICE | 40 | 1 | 2 | 2 | 0.0250 | [0.0000, 0.0750] | [0.0000, 0.0789] |
| openai/gpt-oss-20b | AAP | 30 | 0 | 0 | 2 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| openai/gpt-oss-20b | WHO | 30 | 0 | 0 | 5 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| qwen/qwen3.8-27b | NICE | 40 | 23 | 24 | 1 | 0.0250 | [0.0000, 0.0750] | [0.0000, 0.0750] |
| qwen/qwen3.8-27b | AAP | 30 | 26 | 26 | 0 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| qwen/qwen3.8-27b | WHO | 30 | 27 | 27 | 0 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |

Release is an engineering gate, not a clinical correctness label. Models audit their own backbone outputs, elapsed-time constraints can prevent resolution, and the synthetic fixtures do not establish independent expert acceptance. The existing budget is a preflight admission condition rather than a hard wall-clock deadline; provider waits can exceed it. Source code, settings, role responses and revision traces remain archived. The deployed schema-enforced application is distinct from these fixed JSON-object research runs.

After the historical JSON-object experiments, the application was further constrained with provider-enforced JSON schemas for drafts, audits and revisions. The runtime restricts quote identifiers to the supplied evidence packet and auditor identifiers to the actual draft claims; Pydantic checks semantic constraints after decoding. Unsupported Groq schema/model combinations fail explicitly. The same schema format is sent to the Ollama-compatible endpoint. A synthetic GPT-OSS-120B control completed generation and both audits with one supported claim, and the local Ollama format check passed. These are integration controls, not additional benchmark cases. Tables 4-12 retain their recorded experimental protocols and are not presented as measurements of this later schema refinement.

## 12. Frozen ten-case pilot and saturated-score investigation

### 12.1 Protocol and provenance

A subsequent Phase 1 pilot analyzes ten cases from a separately supplied synthetic 100-case care-plan benchmark. Eligibility requires all five historical retrieval arms and all four saved plan arms. Deterministic metadata coverage selects four NICE, three AAP and three WHO cases from thirty eligible cases without inspecting outcomes. The original gold is preserved; twelve selected historical rows disagree with the canonical JSON gold. Every selected top-ten and gold ID resolves in the benchmark-declared 489-passage corpus. The exact cases, source hashes and discrepancies are available in the pilot manifest. This pilot evaluates saved outputs, not the later application refinements.

All ten selected original cases omit postnatal age. EOS eligibility and age-specific treatment conditions therefore cannot be confirmed. This fact remains unknown in the fresh prompts; corrected development-case facts are never substituted. A high automated clinical rating cannot establish that the missing eligibility conditions were met.

The 489 corpus rows have 481 distinct IDs: eight identifiers map to conflicting texts. Three colliding IDs affect selected AAP cases 003, 007 and 011. The frozen dictionary used the last CSV occurrence; a separate audit verifies this and preserves every variant. Exact-ID metrics cannot resolve content identity, and semantic/source scores are conditional on these frozen texts. This source ambiguity was not repaired by altering original gold or substituting favorable passages.

Exact MRR@10 and gold-normalized binary NDCG@10 use the actual first ten retrieved IDs, excluding expanded context. Fifty NDCG values independently match scikit-learn within 1e-12. Fresh GPT-OSS-120B judgments cover 206 unique case/passage pairs; opaque aliases hide arms. Relevance grades are 0-3 and useful precision uses grade >=2. Semantic NDCG uses gains 2^grade-1 and a shared ideal from each case's judged five-arm union, not a corpus-wide ideal. Four grade/applicability/usefulness inconsistencies are retained. Dense and Vector are historical labels; their implementation distinction and controlled ablation provenance cannot be established from the CSVs.

### 12.2 Exact and semantic retrieval

| Arm | Exact MRR@10 | Exact NDCG@10 | Useful P@10 | Semantic MRR@10 | Semantic NDCG@10 |
| --- | --- | --- | --- | --- | --- |
| Dense | 0.5910 | 0.2941 | 0.3700 | 0.5443 | 0.4950 |
| Sparse | 0.6017 | 0.2817 | 0.3300 | 0.5293 | 0.4590 |
| Vector | 0.6317 | 0.2706 | 0.3600 | 0.6093 | 0.5141 |
| Graph | 0.9000 | 0.5229 | 0.4900 | 0.7500 | 0.6388 |
| Hybrid | 0.8750 | 0.5503 | 0.4900 | 0.7250 | 0.6404 |

Graph ranks the first canonical hit most effectively; Hybrid has the highest exact and semantic NDCG, and both tie on useful precision. Hybrid minus Dense exact NDCG is 0.2562, with a descriptive paired case-bootstrap 95% percentile interval [0.1243, 0.3998] (20,000 resamples, seed 20261025). Template/source dependence limits interpretation. Exact and semantic arm-mean NDCG rank correlation is 0.70. A historical Graph ranking does not establish that a live Neo4j service was benchmarked.

### 12.3 Source-separated plan assessment

Each of forty saved outputs receives two fresh rubric-4 passes: grounding/citation assessment sees only that plan's retrieved evidence, while clinical usefulness/completeness sees case facts and wider guideline evidence. All eighty stage responses are retained. Findings select immutable candidate-line IDs, materialized locally as exact quotations; omissions are separate. Earlier exploratory rubrics exposed dose-omission and gold/context confusion and are archived outside final scores. MA traces do not establish E-number mapping, which the evaluator must not invent. These automated ratings are fallible proxies. Different saved generations prevent causal attribution to verification agents.

| LLM rating (1-5) | Dense | Hybrid |
| --- | --- | --- |
| Faithfulness | 2.500 | 2.700 |
| Citation Correctness | 2.000 | 2.200 |
| Citation Completeness | 2.000 | 2.200 |
| Clinical Correctness | 3.700 | 4.000 |
| Clinical Completeness | 3.100 | 3.500 |
| Clinical Utility | 3.600 | 4.000 |
| Safety | 4.000 | 4.300 |

| Saved arm (n=10) | Regimen incomplete | Ungrounded dose | LLM-reported unsupported-claim plan |
| --- | --- | --- | --- |
| dense_only | 0.700 | 0.100 | 0.900 |
| hybrid | 0.600 | 0.100 | 1.000 |
| dense_only_multiagent | 0.700 | 0.400 | 0.800 |
| hybrid_multiagent | 0.800 | 0.000 | 0.800 |

The evaluator-quality audit flags 32 heading/empty/very-short-line findings for independent review. They remain in the raw ratings and rates rather than being deleted or regraded. Thus these findings cannot certify safety or support a precise hallucination-reduction claim. Regimen completeness and safe withholding are separate. Full case-level findings and denominators accompany the seven numbered CSVs.

| Fresh similarity metric | Dense | Hybrid |
| --- | --- | --- |
| bleu | 0.2007 | 0.1886 |
| meteor | 0.4287 | 0.4199 |
| bertscore_f1 | 0.8453 | 0.8417 |
| anchor_grounding_recall | 0.3466 | 0.3736 |

The references are historical deterministic templates, not independent clinical gold. BLEU is sentence BLEU-4/100 with 13a tokenization and exponential smoothing. METEOR uses lowercased WordPunct tokens and Porter/WordNet matching. DistilBERT BERTScore uses layer 5 without IDF or baseline rescaling; fourteen of twenty pairs exceed its standard 512-token window. Full plans are still used by the usability judge. Fresh ROUGE-L F1 is 0.3258 for Dense and 0.3167 for Hybrid. Similarity does not establish correct care. The separate metric environment and backbone hash are recorded in generation_metrics.json; they do not replace versions from the earlier experiment.

### 12.4 Why the demonstration score exceeded 99.9%

The pinned days-0-2 forest returns raw score 0.9982920927203368. Its fitted calibration applies sigmoid(3.267761146142852 * logit(raw) + 0.9684784989483102), producing 0.9999999996547169. Internal Brier improves from 0.01817 to 0.00938 on the supplied labels. This numerical sharpening explains the display, but does not calibrate clinical EOS risk. PCT alone yields oriented test AUC 0.98599, oxygen 0.96877 and CRP 0.95427; these associations and unresolved timing/identity defects raise source-label and workflow-leakage questions. A small fit-test gap is insufficient reassurance. The training CSV was not confirmed synthetic; only the RAG benchmark was.

Before calibration, the demo already closely matches strongly separating dataset patterns: PCT=2 is near the positive-label fit median 1.9855, compared with negative-label median 0.31; CRP=20 is at the 99.34th fit percentile. The reached tree-leaf probability quartiles are all 1.0. These explain model saturation statistically without establishing a clinical diagnosis or validating the dataset's measurement units.

![Figure 4. Probability audit of the unchanged fitted model: calibration, internal reliability, single-variable label separation and non-causal input sensitivity.](output/research/figures/probability_audit.png)

Across 250 deterministic local measurement perturbations, 153 are within support, 94 are withheld and three invalid inputs are rejected. Accepted scores remain saturated. Replacing the elevated laboratory values alone changes the demo score to 0.61025; replacing vital signs alone gives 0.89437; replacing both gives 0.00004782. These are sensitivity diagnostics, not causal treatment effects or external validation. No arbitrary clipping or synthetic outcome relabeling is used to manufacture plausible risk.

### 12.5 Refinement and decision

The application now exposes raw/calibrated scores and a saturation interpretation. Previously unused patient-context queries now reach plan retrieval, along with allergy/renal/history queries. Stored encounter age, gestation and weight reach population filtering. Missing, future or invalid historical timestamps withhold automated synthesis. Graph and diversity modes propagate across domain queries. All 110 backend tests pass and the updated Flutter widgets pass static analysis. These changes are subsequent engineering refinements and are not credited with the historical scores.

The current thirteen-section review workflow selects immutable guideline recommendation IDs and materializes actual source wording, while displaying patient observations and longitudinal summaries separately. Both audit roles check the selected claims. This reduces quotation/paraphrase defects but does not create missing evidence, dosing authority or an individualized medication order.

The selection model view omits repeated file/URL/page metadata while retaining every actual quote, source, version and section; original citation records remain intact on the server. Patient-state instructions are conditional on recorded findings, with a regression check against inventing respiratory illness for a well infant. The local demo now uses packaged container code rather than a Windows-mounted source tree. These are subsequent runtime refinements, not retrospective changes to pilot scores.

Subsequent visual PDF checks found two application passages with trailing headings from the next section. Only those verified extraction boundaries were corrected, preserving the original application corpus and a versioned change record. NICE 1.5.1 applies to babies who have not received antibiotics; it is excluded from this fixed case with unknown treatment status. Conditional future handover instead uses NICE 1.1.4. The care-plan resolution request now selects immutable quote IDs without duplicating full previous passages and citation metadata; both auditors must freshly recheck the revision. Tests retain source conditions and unrelated clinical notes. These fixes do not alter frozen pilot sources, gold or scores.

A subsequent fixed synthetic application control completed three fresh provider calls, generating 11 source-selected claims and displaying thirteen sections, nine with supported guidance. GPT-OSS-120B performed generation/source review and Qwen3.8-27B performed safety review. This integration control is separate from the historical pilot and does not change its scores or establish independent clinical quality. The preserved first control predates the boundary corrections and does not validate those later changes.

A separate corrected development set contains one hundred cases and three hundred chronological observations across ten template families, with immutable demographics, explicit units/availability/unknowns and gestation-specific guideline scope. It contains no invented EOS labels or newly manufactured gold care plans; it does not replace the original pilot. Template variants are dependent and need independent source mapping.

The pilot decision is REVISE. First establish a defensible culture-adjudicated, time-aware EOS cohort and external calibration. Second independently review benchmark gold, source scope, references and citation provenance. Third freeze an identical-draft verification ablation and independent evaluation set, with evaluator-disagreement and workflow checks. Provider execution failures remain operational logs outside all quality means. The present research artifact does not justify clinical release.

## 13. Subsequent retrieval development and readiness boundary

This section is a post-hoc development extension on the same 100 previously examined synthetic cases, not a final evaluation or an untouched test. The original numerical results and tables in Sections 6-7 remain historical results; methodological scope and annotation-ceiling clarifications do not rerun that study. No proposed gold identifier or engineering reference answer enters query planning, candidate retrieval, cross-encoder scoring or language-model passage ranking. Source and case adjudication remain pending.

### 13.1 Index structure, medical encoders and question coverage

Source headings and explicit age, gestation and care-setting limits are applied before retrieval. Seventeen explicitly late-only NICE passages are excluded in the logged structural index amendment. The remaining source index contains 299 passages. Publisher structure separates normative guidance from research background, leaving 115 NICE, 30 AAP and 16 WHO passages in the guidance lane; background remains separately available. This pool reduction is an engineering intervention and contributes to comparisons with the original index. The small WHO pool makes high-depth recall easier.

The NCBI MedCPT query, article and cross encoders are evaluated with frozen weights [16], alongside MiniLM/MS-MARCO controls. Medical pretraining does not establish clinical validity. Medical synonym expansion, RRF offset 60, overlapping cross-encoder windows (180 words, 40-word overlap), multi-question planning and bounded MMR are retained in logged ablations. MMR diversity 0.15 operates within the top twice-the-return-budget candidate set; a regression test demonstrates a near-duplicate neighbour swap. The earlier 0.1 ordinal weighting could be inert at four passages, so merely enabling that earlier option did not establish a diversity benefit. All five faceted methods and depths 1, 2, 4, 6, 8 and 12 remain in the result CSVs.

The planner produces 24 unique source/question requests. The known EOS system age scope is recognized in a logged offline validation amendment; 23 plans pass and one retains the original question. A second, bounded listwise stage receives the original focused question and up to 24 full candidate passages formed by fixed fusion of four upstream rankings. It returns only existing identifiers, with at most eight passages; missing, duplicate or invented identifiers fail validation. No source text is rewritten. Identical question/candidate requests are cached exactly, so the case count does not equal the number of independent model requests.

### 13.2 Measured retrieval changes and negative results

Table 20. Development retrieval at four passages, with complete source populations. Precision remains conventional and is not ceiling-normalized. All case and family intervals, nDCG, F1 and evidence-word budgets are available in the corresponding CSV files.

| Source | Method | Complete / N | Recall@4 | Case 95% CI | Family 95% CI | MRR@4 | Precision@4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NICE | Medical faceted | 40/40 | 0.6417 | [0.5375, 0.7375] | [0.4127, 0.8455] | 0.7083 | 0.4125 |
| NICE | Bounded listwise | 40/40 | 0.6792 | [0.5750, 0.7750] | [0.4658, 0.8875] | 0.7562 | 0.4375 |
| NICE | RRF consensus | 40/40 | 0.6792 | [0.5707, 0.7750] | [0.4167, 0.9065] | 0.7875 | 0.4375 |
| AAP | Medical faceted | 30/30 | 0.7500 | [0.6667, 0.8333] | [0.5833, 0.9167] | 0.7222 | 0.3750 |
| AAP | Bounded listwise | 30/30 | 0.7500 | [0.6000, 0.8833] | [0.4167, 1.0000] | 0.7222 | 0.3750 |
| AAP | RRF consensus | 30/30 | 0.7500 | [0.6000, 0.8833] | [0.4167, 1.0000] | 0.7083 | 0.3750 |
| WHO | Medical faceted | 30/30 | 0.7167 | [0.6000, 0.8167] | [0.4833, 0.9167] | 0.8000 | 0.3583 |
| WHO | Bounded listwise | 30/30 | 0.6333 | [0.4833, 0.7833] | [0.3000, 0.9167] | 0.6833 | 0.3167 |
| WHO | RRF consensus | 30/30 | 0.8000 | [0.6833, 0.9000] | [0.5500, 1.0000] | 0.8500 | 0.4000 |

Table 21. Medical faceted minus original frozen hybrid retrieval. Old paper values are quoted explicitly. These are combined index/model/query changes, not isolated causal component effects.

| Source | Metric | Old paper value | Development value | Paired change | Case 95% CI | Family 95% CI |
| --- | --- | --- | --- | --- | --- | --- |
| NICE | recall_at_4 | 0.3792 | 0.6417 | 0.2625 | [0.1750, 0.3584] | [0.1500, 0.3496] |
| NICE | mrr_at_4 | 0.4938 | 0.7083 | 0.2146 | [0.0875, 0.3542] | [-0.0264, 0.4680] |
| AAP | recall_at_4 | 0.5500 | 0.7500 | 0.2000 | [0.1167, 0.2833] | [0.0333, 0.3667] |
| AAP | mrr_at_4 | 0.6722 | 0.7222 | 0.0500 | [-0.0779, 0.1889] | [-0.2222, 0.3389] |
| WHO | recall_at_4 | 0.3333 | 0.7167 | 0.3833 | [0.2333, 0.5500] | [0.0667, 0.7167] |
| WHO | mrr_at_4 | 0.2694 | 0.8000 | 0.5306 | [0.4111, 0.6500] | [0.2722, 0.7806] |

Recall@4 is higher in this development benchmark for all three sources. Both paired interval types exclude zero for those recall changes. The MRR differences for NICE and AAP do not exclude zero under scenario-family resampling, so a general superiority claim is unsupported. Bootstrap intervals use 2,000 resamples and seed 31; only six scenario families and repeated templates limit independence.

The listwise-only intervention lowers WHO recall and can produce an empty evidence selection for a question about a source limitation. It is therefore not adopted as an evidence-availability gate. A subsequent fixed RRF60 consensus treats its output as one relevance vote alongside the upstream ranking; an empty list contributes no vote. The consensus preserves reviewed candidate evidence for downstream assessment without declaring that it supports a treatment claim. Its negative and positive paired changes remain in separate CSVs; no new API calls are needed for this saved-request development regression.

Table 22. Explicit-reference graph variant minus medical faceted retrieval at four passages. Negative effects are retained.

| Source | Recall difference | Case 95% CI | Family 95% CI |
| --- | --- | --- | --- |
| NICE | -0.0250 | [-0.0500, 0.0000] | [-0.0750, 0.0000] |
| AAP | -0.0833 | [-0.1500, -0.0167] | [-0.2500, 0.0000] |
| WHO | -0.0833 | [-0.1500, -0.0167] | [-0.2500, 0.0000] |

Graph candidate expansion does not improve the four-passage recall estimate in these three cohorts. A separate typed source-context graph links recommendations to exact definition sentences in the same publisher section. Every definition retains its parent passage, offsets and text/source hashes; engineering extraction is not clinical approval. Such context is an additional, explicitly counted evidence budget, not a hidden top-four slot. Its effect on answer quality is unmeasured. No live Neo4j deployment benefit is claimed from this offline graph.

Increasing the return budget can recover more annotated passages while lowering the precision ceiling and increasing context length; it does not turn Recall@8 into Recall@4. The fixed gold sets contain only two or three passages per case, so the conventional Precision@4 ceilings in Table 5a remain binding. Incomplete relevance annotation may also mark other useful evidence as irrelevant, but that possibility requires blinded clinician adjudication rather than a retrospective label change. Reference-alignment scores have no comparable demonstrated task-specific numeric ceiling; weak text alignment cannot be dismissed as an inevitable ceiling.

### 13.3 Application changes, clinical review and evaluation hold

The active application now passes the recorded care setting to RAG separately from ML predictors. The explicit positive or negative culture result selected in the Flutter form is also preserved; pending or unrecorded results remain unknown. The API distinguishes culture status, culture-incubation time and antibiotic-exposure time; patient age cannot substitute for either treatment clock. Passage-level scope is enforced in addition to document approval. Hospital-only eligibility and cloud-processing authorization are checked before retrieval, and the exact clinical task reaches both auditors. Missing eligibility, audit dissent and incomplete evidence remain explicit.

The medical/faceted and listwise experiments are separate development adapters. Their results must not be attributed automatically to the active Supabase index, whose complete-recommendation chunking and encoder identity still require a controlled deployment reconciliation. The current clinical source registry remains unapproved; benchmark engineering references are not a substitute for source review.

The final evaluation remains on hold. The readiness check requires source-specific Recall@4 and MRR@4 near 0.80, a balanced development answer pilot covering six families and three sources, explicit usable-answer coverage, complete audits and fault regressions. A passage-ranking score does not establish those answer-generation criteria. The earlier task-aware generation run was stopped after three saved cases, and those cases are not reported as a completed final study. The clinician bundle provides shuffled evidence panels, blank relevance and scope forms, a source-linked casebook and a separate engineering triage queue. Clinical verification and clinical usability remain unperformed.

### 13.4 Additional cross-encoder ablation

An additional BAAI bge-reranker-v2-m3 cross encoder [17] is tested without changing the candidate pools, cases or labels. Three declared variants use its direct ordering, RRF60 with the upstream order plus bounded MMR, and RRF60 with the saved consensus order plus bounded MMR. Inference uses overlapping windows, frozen weights and CPU execution. This stage makes no additional Groq calls. The model revision, all ranks, candidate-recall ceilings, four- and eight-passage results and paired case/family intervals are retained. It does not constitute final evaluation or answer usability validation.

Table 23. Additional cross-encoder development results. All declared four-passage variants are shown; previous consensus values remain in Table 20.

| Source | Method | Complete / N | Recall@4 | Case 95% CI | Family 95% CI | MRR@4 | Precision@4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NICE | BGE CE | 40/40 | 0.5875 | [0.4792, 0.6833] | [0.3415, 0.8255] | 0.7375 | 0.3688 |
| NICE | BGE upstream RRF/MMR | 40/40 | 0.6250 | [0.5083, 0.7250] | [0.3504, 0.8731] | 0.7375 | 0.3875 |
| NICE | BGE consensus RRF/MMR | 40/40 | 0.6583 | [0.5417, 0.7500] | [0.3833, 0.9024] | 0.7875 | 0.4125 |
| AAP | BGE CE | 30/30 | 0.4167 | [0.2667, 0.5667] | [0.0833, 0.7500] | 0.4167 | 0.2083 |
| AAP | BGE upstream RRF/MMR | 30/30 | 0.5000 | [0.4000, 0.6000] | [0.2500, 0.7500] | 0.5833 | 0.2500 |
| AAP | BGE consensus RRF/MMR | 30/30 | 0.5000 | [0.3667, 0.6500] | [0.1667, 0.8333] | 0.5833 | 0.2500 |
| WHO | BGE CE | 30/30 | 0.8333 | [0.7500, 0.9167] | [0.6667, 1.0000] | 0.7556 | 0.4167 |
| WHO | BGE upstream RRF/MMR | 30/30 | 0.7500 | [0.6667, 0.8333] | [0.5833, 0.9167] | 0.7833 | 0.3750 |
| WHO | BGE consensus RRF/MMR | 30/30 | 0.8000 | [0.6833, 0.9000] | [0.5500, 1.0000] | 0.7667 | 0.4000 |

An additional model or rank vote is not assumed to improve retrieval. Negative changes remain in the paired-difference CSVs. Model-selection comparisons reuse exposed development cases and cannot establish independent generalization.

None of the three additional cross-encoder variants reaches both Recall@4 and MRR@4 of 0.80 in every guideline source; it is not promoted as the deployment candidate.

A separate care-plan contract regression rejects all 36 original free-text fault challenges at the quote-ID selection schema, before any auditor call. The original faults are materialized claims rather than valid source selections; this is a structural contract result and does not measure the revised semantic auditors. The interpretation amendment, original records and counts are retained.

### 13.5 Balanced patient-context and dependency pilots

A subsequent development pilot selects one existing case per source and scenario family, giving 18 cases and six per source. The original 100 cases and proposed gold identifiers remain unchanged. This is a complete 18-case pilot, not a completed new 100-case study. The patient-conditioned ranker receives unchanged recorded current findings and longitudinal observations alongside the original question; proposed golds and reference answers are excluded. Its validated identifier selection contributes one fixed RRF60 vote alongside the upstream candidate order.

A source-text dependency graph adds candidates linked to explicit diagnostic limitations, sampling prerequisites or serial-measurement context through shared diagnostic concepts. These lexical edges retain passage hashes and scope checks, are unreviewed engineering retrieval hints and do not assert causality or clinical approval. Up to four new candidates are appended within the same maximum 24-passage budget, trimming the upstream tail if needed. The patient-conditioned prompt is unchanged in this comparison. Identical unchanged requests reuse their exact saved responses.

Table 24. Balanced development pilots at four passages. The question-only baseline is rescored on the same 18 cases, rather than compared to the different 100-case population in Table 20. Case and whole-family intervals each use 2,000 resamples and seed 31.

| Source | Method | Complete / N | Recall@4 | Case 95% CI | Family 95% CI | MRR@4 | Precision@4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NICE | Question consensus | 6/6 | 0.6944 | [0.5000, 0.8889] | [0.5000, 0.8889] | 0.8333 | 0.4583 |
| NICE | Patient consensus | 6/6 | 0.6944 | [0.5000, 0.8889] | [0.5000, 0.8889] | 0.8333 | 0.4583 |
| NICE | Dependency consensus | 6/6 | 0.6944 | [0.5000, 0.8889] | [0.5000, 0.8889] | 0.8333 | 0.4583 |
| AAP | Question consensus | 6/6 | 0.7500 | [0.4167, 1.0000] | [0.4167, 1.0000] | 0.7083 | 0.3750 |
| AAP | Patient consensus | 6/6 | 0.8333 | [0.6667, 1.0000] | [0.6667, 1.0000] | 0.7917 | 0.4167 |
| AAP | Dependency consensus | 6/6 | 0.8333 | [0.6667, 1.0000] | [0.6667, 1.0000] | 0.7639 | 0.4167 |
| WHO | Question consensus | 6/6 | 0.7500 | [0.4167, 1.0000] | [0.4167, 1.0000] | 0.7500 | 0.3750 |
| WHO | Patient consensus | 6/6 | 0.8333 | [0.6667, 1.0000] | [0.6667, 1.0000] | 0.7917 | 0.4167 |
| WHO | Dependency consensus | 6/6 | 0.8333 | [0.6667, 1.0000] | [0.6667, 1.0000] | 0.7917 | 0.4167 |

No variant in Table 24 meets both 0.80 retrieval entry targets for all sources. The dependency variant does not increase four-passage recall over patient consensus and has lower AAP MRR and lower NICE Recall@8; the negative changes remain in the paired CSV files. It is not promoted on the basis of candidate coverage alone. With only one case per family per source, these intervals cannot establish broad generalization.

Table 25. Scoring-only candidate-pool coverage audit on all 100 existing cases, before and after dependency expansion. A candidate recall ceiling is a limitation of this retrieval stage, not a natural metric ceiling or a basis for normalizing reported recall.

| Source | Complete / N | Cases missing gold: before | After | Candidate recall ceiling: before | After |
| --- | --- | --- | --- | --- | --- |
| NICE | 40/40 | 10 | 7 | 0.8833 | 0.9083 |
| AAP | 30/30 | 5 | 0 | 0.9167 | 1.0000 |
| WHO | 30/30 | 0 | 0 | 1.0000 | 1.0000 |

Missing annotated passages cannot be recovered by a downstream ranker when they are absent from its candidate pool. Recovering them does not guarantee correct ordering or clinical usefulness. Proposed gold sets may omit other useful passages or include conditional recommendations whose patient prerequisites are unknown; independent adjudication remains necessary. Transport blocks are pending operational events rather than scored clinical failures. Final evaluation and integration of a newly evaluated application pipeline remain pending the declared readiness criteria.

A further evidence-set pilot requests a relevance purpose, essential/supporting distinction and exact source quotation for every choice. It is stopped after 2 completed responses, with 2 contract rejections; abbreviated or altered quotations are not repaired into successful model outputs. A separate version returns immutable passage identifiers and materializes full source text in application code. That old-corpus pilot has 6 completed NICE cases and 6 structurally valid selections. It is not a balanced completed experiment or clinical quality evaluation. Remaining calls are deferred while source-boundary corrections and local retrieval checks are completed, conserving cloud tokens.

### 13.6 Source-boundary correction and bounded facet anchors

A source-traceable structural amendment changes 14 NICE passages without changing the 299 passage identifiers, original 100 cases or gold identifiers. Numbered recommendations are separated from following risk-factor or clinical-indicator boxes, Box 1 starts at its own title, and Box 2 includes its continuation on the next supplied-PDF page. Trailing numbered section headings are removed. Each repaired unit retains supplied-PDF pages, offsets in a declared footer-stripped extraction stream and hashes of the text and PDF. Four unnumbered trailing major headings remain flagged as extraction context; this is not a claim of a perfect PDF parser or clinical source approval.

NICE retrieval is recomputed with the preceding model/query settings. AAP and WHO source payloads are exactly unchanged and retain their preceding saved rankings in this source-boundary comparison, explicitly labelled as replays rather than independent replication. The amendment uses no new Groq calls. It is retained for source completeness even when annotation-overlap scores decrease.

Table 26. NICE source-boundary amendment, all 40 cases. Prior values are quoted from the preceding faceted development CSVs; the paired interval describes corrected minus prior Recall@4. All five declared variants and both interval types are retained.

| Method | Complete / N | Prior Recall@4 | Corrected Recall@4 | Change | Case 95% CI | Family 95% CI | Corrected MRR@4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Generic single | 40/40 | 0.5125 | 0.5125 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] | 0.7500 |
| Medical single | 40/40 | 0.5000 | 0.5000 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] | 0.7188 |
| Generic faceted | 40/40 | 0.5167 | 0.5250 | 0.0083 | [-0.0333, 0.0500] | [0.0000, 0.0250] | 0.4521 |
| Medical faceted | 40/40 | 0.6417 | 0.5958 | -0.0458 | [-0.1083, 0.0083] | [-0.1491, 0.0500] | 0.7458 |
| Medical faceted graph | 40/40 | 0.6167 | 0.5958 | -0.0208 | [-0.0876, 0.0417] | [-0.1417, 0.1000] | 0.7458 |

The preceding facet selector can force an anchor outside the original-question relevance head. A separate bounded variant admits a facet anchor only if it belongs to both the fused and original-question top twice-the-return-budget heads. RRF offset 60, model weights, queries, cases, golds and MMR diversity remain unchanged. All 100 orders are recomputed using exact cached cross-encoder scores; query embeddings are recomputed locally, with no new cross-encoder or Groq calls.

Table 27. Bounded-anchor development on the corrected corpus. Paired change is bounded minus unguarded Recall@4. Negative changes remain visible, and these estimates reuse the exposed development cases.

| Source | Method | Complete / N | Prior Recall@4 | Bounded Recall@4 | Change | Case 95% CI | Family 95% CI | Bounded MRR@4 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NICE | Generic faceted | 40/40 | 0.5250 | 0.6083 | 0.0833 | [0.0333, 0.1500] | [0.0000, 0.2500] | 0.6333 |
| NICE | Medical faceted | 40/40 | 0.5958 | 0.6292 | 0.0333 | [0.0083, 0.0667] | [0.0000, 0.0976] | 0.7958 |
| NICE | Medical faceted graph | 40/40 | 0.5958 | 0.5958 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] | 0.7958 |
| AAP | Generic faceted | 30/30 | 0.6667 | 0.6667 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] | 0.8056 |
| AAP | Medical faceted | 30/30 | 0.7500 | 0.6667 | -0.0833 | [-0.1500, -0.0167] | [-0.2500, 0.0000] | 0.7500 |
| AAP | Medical faceted graph | 30/30 | 0.6667 | 0.5833 | -0.0833 | [-0.1500, -0.0167] | [-0.2500, 0.0000] | 0.7222 |
| WHO | Generic faceted | 30/30 | 0.7167 | 0.7167 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] | 0.8000 |
| WHO | Medical faceted | 30/30 | 0.7167 | 0.7167 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] | 0.8000 |
| WHO | Medical faceted graph | 30/30 | 0.6333 | 0.6333 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] | 0.8000 |

The bounded medical-faceted variant has higher NICE Recall@4 than its unguarded corrected-corpus counterpart, but lower AAP Recall@4; WHO is unchanged. No declared variant meets both retrieval targets for every guideline. These structural repairs and mixed retrieval changes do not establish usable care-plan coverage, semantic fault robustness or clinical validation. Local-model development and transport compatibility are separate from a completed final generation evaluation. The final evaluation remains on hold, followed by integration of the evaluated pipeline and publication.

### 13.7 Source-topic routing and capped primary-model smoke

A separate source-topic routing ablation removes unrequested future-pregnancy counselling, maternal labour-management topics and CSF-result interpretation without requested or recorded CSF context from the current-case lane. It preserves explicit searches for those topics. These engineering topic labels remain subject to clinical review; they do not infer patient eligibility or grant source approval. All 100 cases and golds are retained, with zero topic/gold exclusion conflicts. Vacated slots are refilled from the same method's saved depth-12 order. No new model calls are used.

Table 28. Medical-faceted topic-routing results. Both preceding selector variants are retained. The paired change is topic routing minus its corresponding parent Recall@4; all methods, eight-passage results and uncertainty estimates remain in CSVs.

| Source | Parent | Complete / N | Recall@4 | Change | Case 95% CI | Family 95% CI | MRR@4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NICE | faceted | 40/40 | 0.6583 | 0.0625 | [0.0208, 0.1167] | [0.0000, 0.1447] | 0.7833 |
| NICE | guarded facets | 40/40 | 0.6917 | 0.0625 | [0.0208, 0.1167] | [0.0000, 0.1447] | 0.8333 |
| AAP | faceted | 30/30 | 0.7500 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] | 0.7222 |
| AAP | guarded facets | 30/30 | 0.6667 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] | 0.7500 |
| WHO | faceted | 30/30 | 0.7167 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] | 0.8000 |
| WHO | guarded facets | 30/30 | 0.7167 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] | 0.8000 |

Source-topic routing has higher NICE overlap estimates in this benchmark, but does not meet the complete per-source retrieval gate. It is not evidence that every topic exclusion is clinically correct; the excluded source passages are exported for review.

A capped primary-model smoke check makes at most three unique retrieval-ranking requests, one deliberately selected difficult case per source. It uses the corrected corpus and source-topic routing with GPT-OSS-120B, temperature zero, completion budget 2,000 and RRF offset 60. No generator, claim-auditor or answer-judge calls are made. All 3/3 requests complete, with 3 structurally valid selections; validity includes an empty selection and is not answer usability. No population interval is inferred from one selected case per source.

Table 29. Descriptive capped smoke results, preserving unsuccessful reranking. Candidate order is the baseline from the same source packet, not a different cohort.

| Case | Complete / N | Candidate Recall@4 | Selected Recall@4 | Consensus Recall@4 | Selected MRR@4 |
| --- | --- | --- | --- | --- | --- |
| single_risk-1 | 1/1 | 1.0000 | 0.5000 | 0.5000 | 0.3333 |
| aap-expanded-missing_results-01 | 1/1 | 0.5000 | 0.5000 | 0.5000 | 1.0000 |
| who-expanded-incomplete_stop-01 | 1/1 | 0.5000 | 0.0000 | 0.5000 | 0.0000 |

The language-model ranking stage is not promoted: a valid identifier contract does not prevent omission of annotated evidence or an empty selection on a source-limitation question. Completed model outcomes remain in quality results; local inference timeouts and provider rate limits remain pending operational events. Final evaluation remains on hold rather than interpreting three valid contracts as clinical readiness.

### 13.8 Publisher hierarchy, qualification links and recorded history

A subsequent offline comparison scores all source-, population- and topic-admitted guidance candidates with the existing medical and generic cross encoders. RRF offset 60 combines their rankings; weak lexical and dense votes no longer displace high cross-encoder candidates in this ablation. Source-extracted definitions enrich scoring text while original recommendation wording remains immutable. The full-pool, genre-plus-facet and definition variants are retained, including negative results. Genre and facet anchoring change together and cannot be interpreted as an isolated genre effect. WHO definition-graph Recall@4 is 0.8333, compared with 0.7167 for genre-plus-facet selection; AAP remains below the retrieval target in that comparison.

The next selector prioritizes explicit publisher conclusion paragraphs by the information needs expressed in the question. A source-context graph connects a serial-marker recommendation to its interpretation limitation, a shared treatment-start sampling condition, or reassessment guidance under the same publisher heading. These are engineering context links, not causal relationships or clinician-approved treatment rules. A separate history ablation adds context only when actual prior marker observations are available and the question requests uncertainty or serial interpretation. Missing, duplicate and future observation times cannot establish a serial history. Every selected recommendation consumes a top-k slot; supplemental definition nodes and their word counts are reported separately in CSVs. A single stable ordering is used at four and eight passages.

Table 30. Source-context development ablation on unchanged cases and golds. All retrieval runs complete; answer release coverage is not measured by this table.

| Source | Complete / N | Hierarchy R@4 | Qualification R@4 | History R@4 | History MRR@4 | History nDCG@4 |
| --- | --- | --- | --- | --- | --- | --- |
| NICE | 40/40 | 0.7167 | 0.8917 | 0.9167 | 0.9125 | 0.8548 |
| AAP | 30/30 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9394 |
| WHO | 30/30 | 1.0000 | 1.0000 | 1.0000 | 0.8667 | 0.8586 |

Table 31. Conventional eight-passage metrics for the longitudinal source-context variant.

| Source | Complete / N | Recall@8 | Precision@8 | MRR@8 | nDCG@8 |
| --- | --- | --- | --- | --- | --- |
| NICE | 40/40 | 0.9917 | 0.3312 | 0.9125 | 0.8885 |
| AAP | 30/30 | 1.0000 | 0.2500 | 1.0000 | 0.9394 |
| WHO | 30/30 | 1.0000 | 0.2500 | 0.8667 | 0.8586 |

Table 32. Recall uncertainty and explicitly quoted preceding paper values. Changes compare the new longitudinal variant with the preceding corrected-corpus medical-faceted topic selector, not a controlled same-index component effect. All intervals use 2,000 resamples, seed 31.

| Source | Old R@4 | New R@4 | Paired change | Case 95% CI | Family 95% CI |
| --- | --- | --- | --- | --- | --- |
| NICE | 0.6917 | 0.9167 | 0.2250 | [0.1333, 0.3333] | [0.0167, 0.5084] |
| AAP | 0.6667 | 1.0000 | 0.3333 | [0.2500, 0.4167] | [0.1667, 0.5000] |
| WHO | 0.7167 | 1.0000 | 0.2833 | [0.1833, 0.4000] | [0.0833, 0.5167] |

The NICE history-minus-qualification Recall@4 difference is 0.0250 (case 95% interval [0.0000, 0.0583]; family 95% interval [0.0000, 0.0789]). The history contribution is not a demonstrated general improvement when its interval includes zero. The hierarchy accounts for the AAP overlap increase; it must not be attributed to history or graph traversal. All source-specific MRR, nDCG and precision intervals and remaining misses are preserved in the per-case and paired-result CSVs.

The annotation-defined mean Precision@8 ceiling is 0.3344 for NICE and 0.2500 for AAP and WHO, because the gold sets contain few relevant identifiers. Precision is not rescaled to one. Unlabelled passages may still be clinically relevant and require adjudication. Recall, MRR and nDCG can reach one in these cases; they have no corresponding low annotation ceiling. Perfect AAP/WHO recall and degenerate bootstrap bounds reflect these repeated templates, broad publisher-summary golds and small source pools, not perfect clinical retrieval.

This candidate clears the prespecified mean retrieval entry targets on the exposed development cases, but the complete readiness gate remains unmet. Balanced answer usability, complete semantic audits, fresh semantic fault injection, source/gold adjudication and external validation remain pending. No new Groq calls are used in the source-context comparison. Subsequent source-hash, heading, role and cross-document-edge hardening reproduces all 100 cases across three methods and both depths without changed rankings. The candidate is not a final evaluated or deployed pipeline.

### 13.9 Actual-data longitudinal model development and maternal-data gap

A separate local PIC v1.1.0 analysis [18] yields 543 infants, 7 independent positive infants and 1436 eligible prediction landmarks. The research endpoint is a documented named bacterial pathogen in blood collected before 72 hours, not adjudicated clinical EOS. Explicit bacterial no-growth reports define controls; missing, fungal-only, preliminary and possible-contaminant reports are not labelled as negative. Predictions precede the first early blood culture. Measurement availability uses the later of chart and storage time; both must precede the landmark. Untimed discharge diagnoses, organisms, medication orders and later outcomes are excluded as predictors. Laboratory values are excluded because result availability cannot be established from collection time alone.

Snapshot logistic regression is compared with actual elapsed-time trends, six four-hour history bins, a shallow trend forest and an equal-weight longitudinal ensemble. Training-only median imputation, scaling, missingness indicators and variable-feature selection are repeated within three patient-stratified folds. Each infant has equal total landmark weight. Candidate selection uses cross-validated AUPRC and has no independent test. A recurrent network is not fitted below the declared engineering event floor. More landmarks from the same infant do not supply additional independent positive outcomes.

Table 33. PIC development comparison. The patient count is 543 and the positive-infant count is 7 for every row. Patient-bootstrap intervals use 2,000 resamples; single-class draws are omitted and their counts are recorded.

| Method | AUROC | AUROC 95% CI | AUPRC | Brier |
| --- | --- | --- | --- | --- |
| snapshot logistic | 0.2958 | [0.0711, 0.5364] | 0.0096 | 0.0128 |
| trend logistic | 0.4177 | [0.1040, 0.7338] | 0.0482 | 0.0142 |
| binned logistic | 0.3008 | [0.1011, 0.5089] | 0.0090 | 0.0129 |
| trend forest | 0.5931 | [0.4440, 0.7338] | 0.0171 | 0.0133 |
| training prevalence | 0.4518 | [0.2344, 0.6652] | 0.0118 | 0.0127 |
| age only | 0.5080 | [0.2642, 0.7473] | 0.0151 | 0.0127 |
| missingness only | 0.6171 | [0.3796, 0.8378] | 0.0450 | 0.0128 |
| longitudinal mean ensemble | 0.4915 | [0.2229, 0.7553] | 0.0221 | 0.0130 |

The new real-data model is withheld from clinical risk decisions because discrimination is inadequate and the event count is small. The missingness-only comparator is competitive, raising concern about recording-process signals. No probability is labelled a calibrated EOS risk, and no treatment threshold is endorsed. The raw model and individual predictions remain local under the credentialed data agreement; public outputs contain aggregate statistics only.

PIC does not provide the required linked maternal predictor set in the selected structured tables. The earlier maternal/perinatal and clinical synthetic experiment remains separate from PIC. No synthetic maternal record is attached to a real infant and no blended real/synthetic EOS probability is produced. The synthetic combined score can reproduce label-conditional symptom generation and does not resolve the real-data performance gap. GBS, intrapartum temperature, rupture duration and antibiotic timing require linked obstetric-neonatal observations before their joint predictive effects can be estimated. A research input contract retains unknown values, explicit measurement/availability times and an auditable field-use distinction; input completeness is not model validation. Clinical verification has not been performed.

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

### 13.14 Separate preterm biomarker and neonatal bloodstream-infection studies

Two newly supplied real-data cohorts are evaluated separately. The workbook [21] contains 138 preterm infants, 69 culture-proven cases and 69 controls. Its file checksum matches the public Figshare record. Twelve maternal/perinatal and blood-count features are retained; the exact outcome-copy SEPSIS SIGNS, identifiers, duplicate categories and six redundant derived indices are excluded. Gestation uses weeks plus days/7. Extreme source counts are not silently corrected; selected counts use log1p. Individual onset and availability times are unavailable, so EOS-only and longitudinal forecasting claims cannot be established.

The CHOP registry [22] supplies 580 eligible evaluations in 472 infants aged under 28 days, with 53 bacteremic evaluations in 52 infants. Bacteremia is compared with the registry rule-out group; other outcome categories and non-blood-culture-positive cases are excluded. Fourteen demographic and at/before-evaluation features are retained. Culture/outcome fields, IDs, treatment timing, future support-free days, length of stay and calendar-day maximum temperature are excluded. Only one bacteremic infant appears in the recorded age-0–2-day subset, precluding meaningful EOS training there. The companion R scripts contain no additional cohort or raw longitudinal measurements.

Both comparisons use five outer patient-separated folds and three inner folds. Five fixed candidates compare regularized logistic regression, Random Forest, Extra Trees and shallow gradient boosting. Model selection maximizes inner AUROC; thresholds maximize inner balanced accuracy over a fixed 0.05–0.95 grid. Training-fold median imputation, missing indicators and scaling are fitted without outer-test patients. Each infant has equal total loss/evaluation weight. All seeds 31, 47 and 83 and fixed-candidate results are retained, with demographic-only controls.

Table 38. Primary-seed nested-selected diagnostic development results. All 138/138 workbook infants and 580/580 CHOP episodes are scored. CHOP episodes remain grouped by infant. Percentages use fold-specific inner-selected thresholds, not a threshold optimized on outer outcomes; these are not clinical action thresholds.

| Dataset | AUROC [95% CI] | Accuracy | Sensitivity | Specificity | Precision |
| --- | --- | --- | --- | --- | --- |
| workbook | 0.8109 [0.7371, 0.8765] | 74.64% | 76.81% | 72.46% | 73.61% |
| chop | 0.8049 [0.7505, 0.8532] | 61.47% | 92.25% | 58.21% | 18.94% |

Confidence intervals use 2,000 infant-level resamples of fixed out-of-fold predictions; they do not include all refitting, phenotype and external-transport uncertainty. The primary-seed paired AUROC difference against demographics is +0.0373 (95% CI [-0.0177, +0.0910]) for the workbook and +0.0525 [0.0021, 0.1058] for CHOP. Workbook demographic baselines are higher at seeds 47 and 83; added blood-count value is therefore not consistently established. CHOP has an internal discrimination gain in the primary comparison, while low specificity and precision remain material limitations.

These results show more encouraging discrimination than the earlier PIC comparisons on different cohorts and targets; they do not establish improvement of the PIC EOS forecasting model. The selected 50:50 preterm sample cannot establish population prevalence, predictive values at routine EOS prevalence or calibrated absolute EOS probabilities. CHOP is conditioned on sepsis evaluation and a treatment-duration-informed rule-out phenotype; evaluation-time support can reflect an already ill infant. Neither study supplies raw serial histories or the required linked maternal infection/antibiotic factors. No model is promoted to the app; independent clinical/external validation remains unavailable.

### 13.15 BMJ paper-inspired Boruta and sensitivity-first forest comparison

Kainth et al. [23] report a Boruta/Random Forest EOS model developed on 2,924 neonates with 548 culture-positive outcomes, with a separate 147-neonate validation cohort. Their public repository provides training code but no supplied fitted model or original study cohort. The local comparison therefore adapts the approach to available features rather than reproducing the published model or externally validating its weights. Original maternal/clinical, centre and pre-suspicion device-exposure inputs are not fabricated.

The adaptation uses BorutaPy 0.4.3 with 1,000 shallow selection trees and a 30-iteration cap, one latest training observation per infant, and training-only absolute Pearson correlation pruning above 0.7. This differs from R Boruta; repository calls also specify 10,000 trees and 2,000 runs, whereas the paper prose describes 1,000 trees. Final forests use 120 trees, maximum depth 8 and up to five split candidates. Training-only class-balanced infant-normalized loss weights replace ROSE oversampling, preserving mixed Kaggle labels without inventing an infant-level outcome. All-feature unbalanced and balanced forests are controls. Three forest seeds share fixed patient splits and one selector per fit fold; this is forest-randomization stability, not independent clinical replication.

Kaggle retains the original patient-disjoint fit, threshold and test partitions, leaving the original calibration partition unused. PIC retains three original patient-level outer folds, reserving threshold-selection infants within each outer training fold. Only three or four positive infants remain for fitting and one positive infant per threshold set. Thresholds maximize specificity while attaining at least 90% sensitivity on threshold patients only; held-out outcomes never select or revise the threshold.

Table 39. Primary forest-seed results. Kaggle covers 1,598/1,598 test observations in 509 IDs; PIC covers 1,436/1,436 landmarks in 543 infants. Each infant has equal total metric weight, unlike historical row-unweighted Kaggle tables. The 90% threshold-set sensitivity target does not imply 90% sensitivity on held-out infants.

| Dataset / arm | AUROC | Accuracy | Sensitivity | Specificity | Precision |
| --- | --- | --- | --- | --- | --- |
| kaggle / all features rf | 0.9996 | 93.11% | 83.56% | 100.00% | 100.00% |
| kaggle / balanced rf | 0.9998 | 92.68% | 82.53% | 100.00% | 100.00% |
| kaggle / boruta balanced rf | 0.9975 | 93.60% | 85.09% | 99.73% | 99.56% |
| pic / all features rf | 0.6236 | 38.23% | 85.71% | 37.61% | 1.76% |
| pic / balanced rf | 0.5902 | 16.66% | 95.24% | 15.64% | 1.45% |
| pic / boruta balanced rf | 0.4580 | 30.70% | 71.43% | 30.17% | 1.32% |

PIC Boruta retains three, two and one features across fit folds, with age and observation recency selected in the first fold. Such recording-process signals and small event counts limit biological interpretation. Its AUROC is 0.4580 (infant-bootstrap 95% CI [0.3821, 0.5489]) and held-out sensitivity is 0.7143, below the target. The paired AUROC difference versus the all-feature balanced forest has 95% interval [-0.3383, 0.0633]; superiority is not established. Kaggle Boruta AUROC is 0.9975 [0.9960, 0.9986], with a paired difference interval [-0.0037, -0.0012] versus the balanced forest. Its held-out sensitivity remains below 90% across all three forest seeds. These exposed-case internal results do not improve source label provenance or establish clinical EOS reliability. Thresholds are not retuned on these test failures. No candidate replaces the app model.

## References

[1] NICE. Neonatal infection: antibiotics for prevention and treatment (NG195). Updated 13 May 2026. https://www.nice.org.uk/guidance/ng195

[2] Puopolo KM, Benitz WE, Zaoutis TE. Management of neonates born at >=35 0/7 weeks' gestation with suspected or proven early-onset bacterial sepsis. Pediatrics 142(6), e20182894 (2018). https://doi.org/10.1542/peds.2018-2894

[3] Puopolo KM, Benitz WE, Zaoutis TE. Management of neonates born at <=34 6/7 weeks' gestation with suspected or proven early-onset bacterial sepsis. Pediatrics 142(6), e20182896 (2018). https://doi.org/10.1542/peds.2018-2896

[4] Johnson AEW et al. MIMIC-III, a freely accessible critical care database. Scientific Data 3, 160035 (2016); dataset v1.4. https://physionet.org/content/mimiciii/1.4/

[5] Xiong G et al. Benchmarking retrieval-augmented generation for medicine. arXiv:2402.13178 (2024). https://arxiv.org/abs/2402.13178

[6] Gutierrez BJ et al. HippoRAG: Neurobiologically inspired long-term memory for large language models. arXiv:2405.14831 (2024). https://arxiv.org/abs/2405.14831

[7] Masood H et al. Agentic Document Reasoning for Evidence-Grounded Clinical Report Generation. User-supplied ADRE ICDAR 2026 camera-ready manuscript; used for structural inspiration, not as an EOS evaluation source.

[8] Papineni K et al. BLEU: a method for automatic evaluation of machine translation. ACL (2002). https://aclanthology.org/P02-1040/

[9] Banerjee S, Lavie A. METEOR: an automatic metric for MT evaluation with improved correlation with human judgments. ACL Workshop (2005). https://aclanthology.org/W05-0909/

[10] Lin CY. ROUGE: a package for automatic evaluation of summaries. ACL Workshop (2004). https://aclanthology.org/W04-1013/

[11] Zhang T et al. BERTScore: evaluating text generation with BERT. ICLR (2020). https://arxiv.org/abs/1904.09675

[12] Collins GS et al. TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. BMJ 385, e078378 (2024). https://www.bmj.com/content/385/bmj-2023-078378

[13] Vasey B et al. Reporting guideline for the early-stage clinical evaluation of decision support systems driven by artificial intelligence: DECIDE-AI. Nature Medicine 28, 924-933 (2022). https://www.nature.com/articles/s41591-022-01772-9

[14] LangChain. LangGraph graph API documentation. https://docs.langchain.com/oss/python/langgraph/graph-api

[15] Groq. Structured outputs and API documentation. https://console.groq.com/docs/structured-outputs

[16] Jin Q et al. MedCPT: Contrastive Pre-trained Transformers with large-scale PubMed search logs for zero-shot biomedical information retrieval. Bioinformatics 39(11), btad651 (2023). https://doi.org/10.1093/bioinformatics/btad651

[17] BAAI. bge-reranker-v2-m3 model card and inference documentation. https://huggingface.co/BAAI/bge-reranker-v2-m3

[18] Li H, Zeng X, Yu G. Paediatric Intensive Care database (version 1.1.0). PhysioNet (2020). https://doi.org/10.13026/32x9-wv38

[19] Nguyen et al. Effective diagnosis of sepsis in critically ill children using probabilistic graphical model. Translational Pediatrics 12(4):538–551 (2023). https://doi.org/10.21037/tp-22-510

[20] Friedman N, Geiger D, Goldszmidt M. Bayesian Network Classifiers. Machine Learning 29:131–163 (1997). https://ai.stanford.edu/~nir/Abstracts/FrGG1.html

[21] GM S, Renganathan G, D'sa S. Accuracy of Systemic Inflammatory Indices in identifying Neonatal Sepsis in preterms in a tertiary care hospital in Mangalore. F1000Research 14:390, version 4. https://f1000research.com/articles/14-390/v4 ; underlying dataset https://doi.org/10.6084/m9.figshare.28395161.v1

[22] Ostapenko S et al. Neonatal sepsis registry: Time to antibiotic dataset. Data in Brief 27:104788 (2019). https://doi.org/10.1016/j.dib.2019.104788

[23] Kainth D et al. A machine learning model for prediction of early-onset neonatal sepsis in low-income and middle-income countries: development and validation study. BMJ Paediatrics Open 10:e003561 (2026). https://doi.org/10.1136/bmjpo-2025-003561
