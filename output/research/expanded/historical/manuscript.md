# NeoGuard EOS: Longitudinal Evidence Representation, Calibrated Neonatal Label Classification and Verified Guideline-Grounded Generation

**Original research software report | Updated 26 October 2026 | Reproducible development experiments**

## Abstract

Early-onset neonatal sepsis support requires a traceable connection between serial observations, statistical estimates and applicable guideline recommendations. We present NeoGuard EOS, a clinician-facing research application with separate prediction and evidence-generation branches. A temporal findings representation preserves observed measurements, missingness and elapsed-time changes; hybrid retrieval links findings to versioned passages, and a LangGraph workflow subjects generated claims to source and safety auditors. We evaluate supplied-label classification using a user-provided Kaggle CSV with 100,000 observations and 20,000 identifiers. A data audit exposes conflicting patient/hour records and unstable birth covariates, so these labels are not treated as culture-confirmed EOS and are not used to reconstruct clinical trajectories. Calibrated logistic regression and random forests are trained with patient-disjoint fit, calibration, selection and test partitions. The selected forests achieve test AUROC 0.9996 across supplied neonatal ages and 0.9992 on postnatal days 0-2. Separately, 18 synthetic vignettes and 12 injected faults examine retrieval, text alignment, model-based judging and release behavior. Hybrid retrieval obtains Recall@4 0.6667; concept expansion obtains 0.5833. The revised generator produces 15/18 structured drafts, of which 4/18 are released after verification. We report lexical and semantic alignment together with abstention coverage, rather than equating text similarity or selective release with clinical correctness. A subsequent ten-case historical pilot obtains Hybrid exact NDCG@10 0.5503 versus Dense 0.2941, while source-faithfulness proxy ratings remain 2.5-2.7/5 and evaluator errors limit safety conclusions.

**Keywords:** early-onset neonatal sepsis; temporal evidence; calibrated classification; hybrid retrieval; knowledge graph; LangGraph; claim verification; selective generation.

## 1. Introduction

EOS assessment combines maternal risk factors, gestational age, the infant's changing condition, cultures and laboratory findings. NICE NG195 and the AAP gestation-specific reports describe different pathways and population boundaries [1-3]. A useful application must distinguish what was observed, what a statistical model estimates, and what a guideline recommends. A low inflammatory-marker value, a reassuring language model response and an unavailable prediction are different states. Combining them into a single opaque score hides the evidence a clinician needs to assess a case.

The initial application already supported neonatal data entry, serial assessments and guideline search, but relied on a hand-built point score and fallback care-plan text. NeoGuard EOS replaces live score interpretation with a model-artifact contract and an explicit unavailable/abstained state. Its evidence branch uses retrieved passages and verifiable support links. Source availability, model eligibility and authorization are checked independently, and generated content does not become a medication order.

This report addresses three questions. RQ1 asks what can legitimately be learned from the supplied neonatal table after an identity, outcome and timing audit. RQ2 compares sparse, dense, hybrid and concept-linked retrieval on fixed source-based synthetic questions. RQ3 measures how exact support checks and separate auditing roles alter answer coverage, reference alignment and unsupported-claim exposure. The implementation and study deliberately separate concurrent supplied-label classification from the longer-term objective of forecasting culture-confirmed EOS.

The contributions are an auditable temporal evidence representation; a patient-disjoint, calibrated research training workflow with portable JSON inference; a reviewed-source retrieval architecture with optional concept links; an immutable quote-ID generation contract; and a reproducible evaluation reporting negative findings and selective-release denominators. Quality comparisons use completed provider calls; operational logs are retained separately. The experiments are development evidence, and the contribution is an implemented integration and failure analysis rather than a claim that any individual component is a newly invented algorithm.

## 2. Related work and design rationale

Medical retrieval-augmented generation is sensitive to corpus choice, passage relevance and the relationship between retrieved knowledge and a specific question. MIRAGE studies medical RAG components under a common evaluation framework [5]. HippoRAG explores graph-assisted retrieval for multi-hop knowledge access [6]. These approaches motivate separate retrieval ablations here. NeoGuard's optional graph is intentionally narrower: passages are linked to deterministic clinical concept labels. Such links are indexing hints and do not represent causal relationships, verified biomedical facts or patient-specific diagnoses.

The supplied ADRE manuscript frames clinical report generation as reasoning over an explicit intermediate findings document with source-grounded composition [7]. We adapt that general design idea to serial neonatal observations, without reusing its EEG data, reference reports or numerical findings. Our representation contains observed clinical measurements and time-aware summaries, and the release mechanism uses source-entailment and safety auditing. This differs from an iterative signal-analysis agent: NeoGuard does not autonomously order tests, reinterpret waveforms or repair a rejected answer until it passes.

BLEU, METEOR, ROUGE and BERTScore provide complementary reference-alignment measures [8-11]. They can reward shared clinical words while missing a dangerous negation, absent condition or wrong population. We therefore pair them with source checks, a fallible model-based judge and deliberate fault injection. TRIPOD+AI motivates transparent reporting of model development, evaluation and intended use [12]; DECIDE-AI motivates distinguishing early software evaluation from evaluation in actual clinical workflows [13]. These frameworks inform reporting, and compliance with their complete checklists is not asserted.

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

The synthetic experiment uses a distinct evaluation-only extraction from the user-supplied May 2026 NICE PDF. Recommendation-level passages retain conditional lists across page breaks, including all conditions of the 36-hour stopping recommendation. Two risk/indicator boxes supplement these passages, producing 132 chunks. The local cropped PDF page number is retained separately from guideline section identifiers. The experimental extraction does not mark the production registry as clinically approved, and other available PDFs are not silently mixed into this benchmark.

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

Eighteen synthetic vignettes cover six families with three parameter variants each: respiratory deterioration, CRP-only reasoning, incomplete stopping criteria, initial investigations, an isolated known risk factor, and missing results. Histories contain two earlier assessments and a current assessment, with known gestation, age and hospital setting. All cases and engineering-authored source-based references were written before inference and are stored with a fixed SHA-256. The references are not clinical reports from the CSV or MIMIC. Related variants share questions and references, so the effective scenario diversity is six families rather than eighteen independent clinical presentations.

For each query, BM25 ranks tokenized passages and MiniLM-L6-v2 ranks normalized passage embeddings by exact cosine similarity. Hybrid ranks use reciprocal-rank fusion with offset 60. The concept variant adds reciprocal ranks from deterministic passage-concept links. Each method returns four passages. Gold relevant section/box IDs are manually specified in the engineering fixture; Recall@4 is the retrieved fraction of those IDs and MRR@4 uses the rank of the first relevant ID. These are offline exact-search and concept-expansion ablations, not throughput or accuracy measurements of deployed pgvector or Neo4j services.

### 6.2 Paired verification ablation and provider failures

Generation uses the concept-expanded hybrid packet under the fixed evaluation protocol, even when that variant performs worse in the retrieval ablation. The configured Groq model is openai/gpt-oss-120b, temperature 0, low reasoning effort, JSON response mode and a 3,000-token completion ceiling. One draft per case is paired with an unverified arm that emits that draft and a verified arm that either emits the identical draft or withholds it. This isolates release filtering; it does not test whether a verifier can rewrite a better answer. Both conditional released-only quality and all-case quality are reported.

The first quote-echo run and the revised quote-ID run are retained separately. The same development cases informed the engineering change; they are not relabeled as an untouched held-out test. Cases with incomplete provider execution are excluded from model-quality comparisons, with the same eligible case population used in both paired arms. Completed malformed answers and verifier disagreements remain quality outcomes. Only provider-blocked steps are retried with bounded, paced requests; existing answers, including schema errors and completed dissent, are replayed verbatim. Operational attempts are stored separately. Regression tests prevent an audit of a missing draft being reused for a later draft. This eligibility rule separates model performance from service availability.

### 6.3 Automatic metrics, model-based judging and fault injection

BLEU-4 uses sacreBLEU corpus aggregation, 13a tokenization and exponential smoothing, divided by 100 for a 0-1 scale. METEOR uses NLTK with lowercased WordPunct tokens, Porter stemming and WordNet matching. ROUGE-1, ROUGE-2 and ROUGE-L are stemmed F1. BERTScore uses unrescaled contextual token alignment without IDF: DistilBERT-base-uncased layer 5 and RoBERTa-large layer 17. Versions and BERTScore configuration hashes are saved. Token-length truncation is counted. Surface and embedding alignment do not establish medical correctness.

A separate prompt, blind to the arm label and previous auditor decisions, judges each available draft against the case, sources and frozen reference. It assigns integer 1-5 scores for grounding, patient fidelity, completeness, actionability and uncertainty handling, plus an unsafe-claim count. The same model is used as generator, auditor and judge; the judge is therefore a dependent semantic proxy with potential shared errors and reference bias. Because the verified arm releases unchanged text, its conditional judge scores reuse the same draft judgment. Withheld answers receive zero all-case alignment but have no meaningful judge score; judge means therefore include an explicit available-case denominator.

Twelve injected drafts, four fault types with three variants each, test negation reversal, omitted stopping conditions, an invented dose and fabricated normal findings. Their source labels and excerpts are real evaluation-corpus spans, so citation existence alone cannot validate their content. The unverified arm would emit all injected drafts. The verified arm is measured for withholding, with deterministic dose rejection distinguished from semantic-auditor rejection and service-unavailable withholding. These deliberately enriched faults are not an estimate of naturally occurring hallucination prevalence.

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

Table 5. Retrieval ablation over 18 synthetic queries and 132 evaluation passages.

| Retriever | Recall@4 | MRR@4 |
| --- | --- | --- |
| lexical | 0.3611 | 0.7500 |
| dense | 0.4722 | 0.5833 |
| hybrid | 0.6667 | 0.8333 |
| hybrid concepts | 0.5833 | 0.7778 |

Sparse and dense methods are complementary in this fixture: reciprocal-rank hybrid has the highest measured recall. Adding broad concept links reduces Recall@4 from 0.6667 to 0.5833. Common terms such as antibiotics, culture and serial assessment connect passages from different neonatal contexts, which can dilute precise recommendation matching. This result supports leaving optional production graph expansion disabled by default until independently evaluated; it does not support a blanket claim that a graph improves this application.

### 7.3 Generation, verification and coverage

Among the 8 eligible completed cases in the initial quote-echo run, 8 produced parsed drafts, none were released, and 8 failed exact-source checks. The revised run has 18 eligible cases, 15 parsed drafts and 4 releases. These different completed populations preclude attributing the change in overall draft yield solely to quote IDs. A valid quote ID eliminates quote-echo errors for that support span, but does not prevent unsupported text or guarantee that both auditors accept a complete plan.

Table 6. Paired lexical alignment. Verified all-case scores count each withheld response as empty; conditional scores describe a selected subset.

| Arm | N | Coverage | BLEU-4 | METEOR | ROUGE-1 | ROUGE-2 | ROUGE-L |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Unverified, all cases | 18 | 0.833 | 0.0220 | 0.2110 | 0.2407 | 0.0564 | 0.1416 |
| Verified, all cases | 18 | 0.222 | <0.0001 | 0.0330 | 0.0608 | 0.0131 | 0.0415 |
| Verified, released only | 4 | 1.000 | 0.0116 | 0.1486 | 0.2735 | 0.0590 | 0.1868 |
| Unverified, generated only | 15 | 1.000 | 0.0220 | 0.2532 | 0.2888 | 0.0677 | 0.1699 |

Table 7. Semantic alignment with fixed BERTScore configurations.

| Arm | DistilBERT P | DistilBERT R | DistilBERT F1 | RoBERTa F1 |
| --- | --- | --- | --- | --- |
| Unverified, all cases | 0.6449 | 0.6845 | 0.6635 | 0.7109 |
| Verified, all cases | 0.1755 | 0.1692 | 0.1722 | 0.1878 |
| Verified, released only | 0.7896 | 0.7612 | 0.7750 | 0.8450 |
| Unverified, generated only | 0.7739 | 0.8214 | 0.7962 | 0.8530 |

Among the 15 available unverified drafts, DistilBERT F1 is 0.7962 and RoBERTa F1 is 0.8530. Among the four released drafts, these values are 0.7750 and 0.8450. Thus verification does not improve conditional semantic alignment in this fixture. Higher released-subset judge grounding, when observed, is a different, fallible metric and accompanies a large loss of coverage. The study does not support a general answer-quality improvement claim.

The all-case verified-minus-unverified DistilBERT F1 difference is -0.4913, with a descriptive paired-case bootstrap interval [-0.6701, -0.3110] over 2,000 resamples. Resampling the six scenario families instead gives [-0.7131, -0.2667]. This difference reflects gating the same draft and cannot demonstrate improved wording. Related variants make case-level resampling optimistic; the family interval acknowledges dependence but still rests on only six clusters. No confirmatory significance claim is made. 0 candidate/reference pairs exceeded the primary encoder's token limit. Conditional semantic scores must be interpreted together with release count.

![Figure 3. Retrieval ablations and the semantic-alignment/coverage trade-off of verification. NA denotes an empty released subset.](output/research/figures/rag_results.png)

### 7.4 Model-based semantic and usability proxies

Table 8. Arm-blinded judge means (1-5, higher is better). These are automated proxies, not measured clinician usability.

| Judge dimension | Unverified | Verified released |
| --- | --- | --- |
| Grounding | 4.133 | 5.000 |
| Patient Fidelity | 4.133 | 4.750 |
| Completeness | 3.933 | 4.250 |
| Actionability | 3.600 | 3.250 |
| Uncertainty | 4.267 | 5.000 |
| Judged outputs | 15 | 4 |
| Judge-flagged unsafe claims | 4 | 0 |

The judge rates readability-related actionability, explicit uncertainty and factual fidelity only within the supplied fixture. Its ratings may disagree with the release auditors because the prompts, decision thresholds and references differ. Shared-model judging cannot replace independent entailment review or observation of clinicians using the interface. Missing judge responses are retained with their failure reasons and excluded from means rather than imputed as favorable ratings. Comparisons of released-only judge means are selection comparisons and cannot establish that verification improved an identical draft.

### 7.5 Injected faults, failure cases and runtime

Table 9. Deliberately unsafe injected drafts: emissions without versus with verification.

| Fault type | Injected | Structural reject | Semantic reject | Invalid verdict | Emitted |
| --- | --- | --- | --- | --- | --- |
| false normal | 3 | 0 | 3 | 0 | 0 |
| invented dose | 3 | 3 | 0 | 0 | 0 |
| missing conditions | 3 | 0 | 3 | 0 | 0 |
| negation | 3 | 0 | 3 | 0 | 0 |

The verified workflow withholds 12/12 injected faults, while the unverified arm would emit 12/12. Numeric dose faults exercise deterministic structural checks; other faults target semantic entailment or patient assumptions. Raw verdicts distinguish completed disagreement from service unavailability, and an unavailable auditor is not credited as detecting the semantic error. This result concerns a small constructed challenge set, not a real-world sensitivity or hallucination-reduction percentage.

Representative failures expose different layers. A deterioration draft can correctly observe low oxygen saturation yet wrongly call ordinary indicators red flags; source traceability cannot rescue that inference. A CRP discussion can correctly reject a single-test decision while inventing a testing interval absent from the retrieved guidance. Auditors also make errors: in one deterioration review, both treated the treatment framework as requiring a red flag, overlooking its alternative of two or more non-red-flag factors or indicators. An incomplete stopping case can omit a conjunctive criterion despite a genuine citation. Missing-result cases can drift into reassurance. Withholding reduces answer availability, and auditor agreement alone does not resolve shared interpretive errors.

Latency is not reported as a model-quality result because archived operational timings mix provider waits, new calls and replayed steps. The CPU container's no-network, read-only, non-root startup/authentication smoke test passed, and cached MiniLM weights completed the offline retrieval evaluation. The final application still requires hosted end-to-end checks after its database and reviewed corpus are provisioned.

## 8. Discussion and limitations

The experiments illustrate why model discrimination, evidence retrieval, generation quality and release safety require separate claims. A classifier can nearly reproduce a supplied label while the data remain unsuitable for the intended clinical forecast. A retrieved quote can be authentic while the generated sentence misstates its meaning. A verification gate can reduce emitted unsupported content by withholding almost everything, without producing a useful answer. Reporting the label definition, all-case metrics and release coverage makes these distinctions visible.

The supplied CSV has unresolved identity, unit, provenance and outcome defects. Patient-ID isolation mitigates direct grouping leakage but cannot repair incorrect grouping or guarantee that related records represent distinct people. The secondary age subset is not an external cohort. Availability timestamps are absent, so forecasting lead time and early-warning benefit cannot be computed. The study does not compare a clinically validated EOS calculator with the research classifier, and the previously used hand-built point score is not presented as an accepted clinical baseline.

The RAG fixture is small, synthetic, English-language and based on one guideline extraction. References were written by the engineering workflow, and repeated variants share templates. The same cases informed the quote-ID refinement, preventing an untouched-test interpretation. The graph ablation uses deterministic concept expansion without a live graph database, and the dense experiment uses exact similarity without a deployed vector service. These controlled measurements inform engineering choices but do not establish production retrieval coverage across all neonatal subpopulations or institutions.

No clinician review of generated care plans, clinical validation, prospective deployment study or clinical usability study was performed; this work reports supplied-label modeling and synthetic engineering evaluation only.

A subsequent study should establish a culture-adjudicated cohort with true birth/onset/availability times; compare snapshot and causal longitudinal predictors; test calibration across sites and prevalence shifts; create independently authored cases and reference answers; evaluate graph relations and source scope; and assess abstention, omissions and workflow fit under realistic workloads. Different model families for auditing and judging would help investigate shared-error dependence, but would not by themselves establish correctness. An actual clinical release requires evidence outside the scope of this development benchmark.

## 9. Conclusion

NeoGuard EOS provides an implemented architecture for joining serial observed findings to statistical models and source-linked explanations while preserving separate eligibility and release boundaries. Actual experiments train calibrated classifiers on the supplied neonatal labels and expose serious source-data limitations. Synthetic experiments quantify retrieval differences and the cost of complete-plan verification, including service failure, abstention and unsupported inferences. Immutable quote IDs improve citation mechanics; concept expansion does not improve this benchmark. The resulting artifacts support reproducible research and further refinement while keeping unsupported EOS and deployment claims out of the application.

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

The release client excludes private environment files and authenticates model requests with the current user session. Contract, persistence, routing, prediction parity, missingness, out-of-support and identifier-rejection tests cover this connection. Actual hosted authentication/database access and deployment remain separate operational checks. Production retrieval also now implements bounded synonym expansion, finer recommendation concepts and optional MMR diversity after cross-encoder reranking; the numerical retrieval results in Section 7 remain those of the frozen earlier experiment and are not attributed to these unbenchmarked refinements. An explicit Ollama-compatible local transport is implemented without automatic cloud fallback. A local Qwen3:4b-q4_K_M call passed a constrained-JSON transport check; this establishes local connectivity and response formatting, not care-plan quality or clinical validity.

### 11.4 Additional backbones and bounded resolution

Three previously exposed cases (deterioration-1, crp_alone-1 and initial_investigation-1) are reused as a small compatibility and development comparison for two additional Groq backbones. The baseline preserves each completed draft and audit, including malformed answers and dissent. The resolution arm reuses that same initial output and permits at most one source-grounded revision of a structurally valid draft after completed reviewer disagreement. Both auditors must freshly review every revised claim; an outage cannot be resolved into release, and repeated dissent cannot trigger further attempts. Request budgets bound whether a revision is attempted. The original eighteen-case paired experiment remains the unchanged-draft release-filtering experiment with zero resolution passes.

Table 12. Completed-case backbone comparison; release is an engineering gate, not a clinical correctness label.

| Backbone | Paired cases | Parsed drafts | Released, baseline | Released, one revision |
| --- | --- | --- | --- | --- |
| openai/gpt-oss-20b | 3 | 2 | 0 | 1 |
| qwen/qwen3.8-27b | 3 | 3 | 1 | 2 |

All three declared cases completed provider execution for each backbone in this comparison. The improvement in release count is descriptive: the fixture is small, was previously exposed, and the models also supply their own source/safety audit roles. It does not establish improved clinical accuracy or independent expert acceptance. Raw drafts, revised claims, prior dissent, final verdicts, exact case IDs and source-code hashes are retained. Provider execution attempts remain outside the quality tables. Current application responses have thirteen review sections; absent evidence is marked undetermined or withheld, and the research model estimate remains separate from clinical treatment decisions. Mixed-population source documents additionally require reviewed passage-level onset scope for patient-specific retrieval.

After these frozen JSON-object experiments, the application was further constrained with provider-enforced JSON schemas for drafts, audits and revisions. The runtime restricts quote identifiers to the supplied evidence packet and auditor identifiers to the actual draft claims; Pydantic checks semantic constraints after decoding. Unsupported Groq schema/model combinations fail explicitly. The same schema format is sent to the Ollama-compatible endpoint. A synthetic GPT-OSS-120B control completed generation and both audits with one supported claim, and the local Ollama format check passed. These are integration controls, not additional benchmark cases. Tables 4-12 retain their recorded experimental protocols and are not presented as measurements of this later schema refinement.

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
