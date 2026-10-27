# Sentence and table change log

## 1

Old: **Original research software report | Updated 26 October 2026 | Reproducible development experiments**

New: **Original research software report | Updated 27 October 2026 | Reproducible development experiments**

## 2

Old: We present NeoGuard EOS, a clinician-facing research application with separate prediction and evidence-generation branches.

New: NeoGuard EOS is a clinician-facing research application with separate prediction and evidence-generation branches.

## 3

Old: We evaluate supplied-label classification using a user-provided Kaggle CSV with 100,000 observations and 20,000 identifiers.

New: The study evaluates supplied-label classification using a user-provided Kaggle CSV with 100,000 observations and 20,000 identifiers.

## 4

Old: Separately, 18 synthetic vignettes and 12 injected faults examine retrieval, text alignment, model-based judging and release behavior.

New: Separately, 100 synthetic vignettes (40 NICE, 30 AAP 2018 and 30 WHO 2024) and 36 injected faults examine retrieval, text alignment, model-based judging and release behavior.

## 5

Old: Hybrid retrieval obtains Recall@4 0.6667; concept expansion obtains 0.5833.

New: The generator produces 94/100 structured drafts and verification releases 8/100.

## 6

Old: The revised generator produces 15/18 structured drafts, of which 4/18 are released after verification.

New: Retrieval results are stratified by guideline; concept expansion has lower measured Recall@4 than hybrid retrieval for all three sources in this benchmark, with paired case and scenario-family intervals reported.

## 7

Old: We report lexical and semantic alignment together with abstention coverage, rather than equating text similarity or selective release with clinical correctness.

New: Lexical and semantic alignment are reported together with abstention coverage, rather than equating text similarity or selective release with clinical correctness.

## 8

Old: A subsequent ten-case historical pilot obtains Hybrid exact NDCG@10 0.5503 versus Dense 0.2941, while source-faithfulness proxy ratings remain 2.5-2.7/5 and evaluator errors limit safety conclusions.

New: A separate ten-case historical pilot obtains Hybrid exact NDCG@10 0.5503 versus Dense 0.2941, while source-faithfulness proxy ratings remain 2.5-2.7/5 and evaluator errors limit safety conclusions.

## 9

Old: We adapt that general design idea to serial neonatal observations, without reusing its EEG data, reference reports or numerical findings.

New: That general design idea is adapted to serial neonatal observations, without reusing its EEG data, reference reports or numerical findings.

## 10

Old: Our representation contains observed clinical measurements and time-aware summaries, and the release mechanism uses source-entailment and safety auditing.

New: The representation contains observed clinical measurements and time-aware summaries, and the release mechanism uses source-entailment and safety auditing.

## 11

Old: We therefore pair them with source checks, a fallible model-based judge and deliberate fault injection.

New: These metrics are therefore paired with source checks, a fallible model-based judge and deliberate fault injection.

## 12

Old: The synthetic experiment uses a distinct evaluation-only extraction from the user-supplied May 2026 NICE PDF.

New: The synthetic experiment uses separate evaluation-only indexes for NICE NG195 (132 frozen passages), the AAP 2018 report for infants born at least 35 weeks (43 passages), and WHO 2024 serious bacterial infection guidance (141 passages).

## 13

Old: Recommendation-level passages retain conditional lists across page breaks, including all conditions of the 36-hour stopping recommendation.

New: AAP summary recommendations and complete article paragraphs and WHO recommendations, qualifiers and scope paragraphs retain source-page metadata and SHA-256 identities.

## 14

Old: Two risk/indicator boxes supplement these passages, producing 132 chunks.

New: WHO cases are restricted to the first 72 hours and preserve hospital, non-hospital and referral-feasibility conditions.

## 15

Old: The local cropped PDF page number is retained separately from guideline section identifiers.

New: The source-gated benchmark contains 100 cases; it does not mark any production source as clinically approved.

## 16

Old: The experimental extraction does not mark the production registry as clinically approved, and other available PDFs are not silently mixed into this benchmark.

New: Paragraph granularity and candidate-pool sizes differ across guidelines; original NICE extraction-boundary concerns remain for clinician adjudication.

## 17

Old: Eighteen synthetic vignettes cover six families with three parameter variants each: respiratory deterioration, CRP-only reasoning, incomplete stopping criteria, initial investigations, an isolated known risk factor, and missing results.

New: One hundred synthetic vignettes include the original 18 unchanged cases and 82 additions: 40 NICE, 30 AAP and 30 WHO cases.

## 18

Old: Histories contain two earlier assessments and a current assessment, with known gestation, age and hospital setting.

New: The six families remain respiratory deterioration, CRP-only reasoning, incomplete stopping criteria, initial investigations, an isolated known risk factor and missing results.

## 19

Old: All cases and engineering-authored source-based references were written before inference and are stored with a fixed SHA-256.

New: Added cases vary gestation, age, care setting and observation availability.

## 20

Old: The references are not clinical reports from the CSV or MIMIC.

New: Every gold ID resolves to an indexed passage, and case, source and passage hashes are recorded with seed 31.

## 21

Old: Related variants share questions and references, so the effective scenario diversity is six families rather than eighteen independent clinical presentations.

New: References are engineering-authored rather than clinician-adjudicated.

## 22

Old: For each query, BM25 ranks tokenized passages and MiniLM-L6-v2 ranks normalized passage embeddings by exact cosine similarity.

New: Related variants share templates; 100 cases do not represent 100 independent clinical scenarios.

## 23

Old: Hybrid ranks use reciprocal-rank fusion with offset 60.

New: Each guideline is searched against its source-only candidate pool.

## 24

Old: The concept variant adds reciprocal ranks from deterministic passage-concept links.

New: The original BM25, MiniLM-L6-v2 normalized exact-cosine, reciprocal-rank hybrid and hybrid-plus-concepts implementations remain unchanged, with RRF offset 60 and four returned passages.

## 25

Old: Each method returns four passages.

New: The original 18 retrieval rankings replay exactly.

## 26

Old: Gold relevant section/box IDs are manually specified in the engineering fixture; Recall@4 is the retrieved fraction of those IDs and MRR@4 uses the rank of the first relevant ID.

New: Recall@4 is the fraction of proposed relevant IDs retrieved; MRR@4 is the reciprocal rank of the first relevant ID.

## 27

Old: These are offline exact-search and concept-expansion ablations, not throughput or accuracy measurements of deployed pgvector or Neo4j services.

New: WHO exact-text PDF duplicates were removed in a logged structural index amendment.

## 28

Old: [added]

New: A superseded 114-case retrieval-only prototype remains archived; the user-requested 100-case allocation used predetermined family quotas and case order rather than score-based selection.

## 29

Old: [added]

New: No retrieval hyperparameter was tuned after results were observed.

## 30

Old: [added]

New: AAP and WHO source identity and recommendation spans were technically checked, but clinical source approval and gold adjudication remain pending.

## 31

Old: [added]

New: Passage-level age, gestation and setting annotations are stored for review; the frozen source-gated retriever does not apply those passage-level filters.

## 32

Old: [added]

New: WHO evidence gaps, referral conditions and treatment-duration statements are not replaced with NICE or AAP rules.

## 33

Old: [added]

New: Overlapping narrative spans can be relevant even when absent from the proposed gold-ID set, limiting strict ID-based recall interpretation.

## 34

Old: [added]

New: The experiment measures offline concept expansion rather than live Neo4j or pgvector performance.

## 35

Old: [added]

New: The historical and current verifier source hashes differ; the expanded study reruns the original cases with the current frozen verifier and logs this runtime drift.

## 36

Old: [added]

New: Current auditor completions are limited to 1,000 tokens and resolution completions to 2,200 tokens.

## 37

Old: [added]

New: The retained historical runner used transport defaults rather than forwarding completion options, so exact historical verifier/transport equivalence is not asserted.

## 38

Old: [added]

New: Model temperature remains zero; no provider sampling seed or immutable model snapshot is available.

## 39

Old: [added]

New: Completed role responses are checkpointed by prompt hash and audit-round occurrence.

## 40

Old: [added]

New: Descriptive 95% intervals use 2,000 resamples with seed 31: paired case resampling and whole-scenario-family resampling.

## 41

Old: [added]

New: Unequal family sizes retain their case weights; six families provide limited cluster-level inference.

## 42

Old: Twelve injected drafts, four fault types with three variants each, test negation reversal, omitted stopping conditions, an invented dose and fabricated normal findings.

New: Thirty-six injected drafts, twelve per guideline with four fault types and three variants each, test negation reversal, omitted stopping conditions, an invented dose and fabricated normal findings.

## 43

Old: Retrieval ablation over 18 synthetic queries and 132 evaluation passages.

New: Source-stratified retrieval; brackets show paired-case bootstrap 95% intervals for each estimate.

## 44

Old: | Retriever | Recall@4 | MRR@4 |

New: Full scenario-family intervals and paired method contrasts are provided in the CSV tables.

## 45

Old: | --- | --- | --- |

New: | Guideline (N) | Retriever | Recall@4 [95% CI] | MRR@4 [95% CI] |

## 46

Old: | lexical | 0.3611 | 0.7500 |

New: | --- | --- | --- | --- |

## 47

Old: | dense | 0.4722 | 0.5833 |

New: | NICE (40) | lexical | 0.2583 [0.1792, 0.3417] | 0.5000 [0.3583, 0.6375] |

## 48

Old: | hybrid | 0.6667 | 0.8333 |

New: | NICE (40) | dense | 0.2792 [0.1917, 0.3708] | 0.4000 [0.2875, 0.5250] |

## 49

Old: | hybrid concepts | 0.5833 | 0.7778 |

New: | NICE (40) | hybrid | 0.3792 [0.2750, 0.4833] | 0.4938 [0.3624, 0.6230] |

## 50

Old: Sparse and dense methods are complementary in this fixture: reciprocal-rank hybrid has the highest measured recall.

New: | NICE (40) | hybrid concepts | 0.3750 [0.2875, 0.4667] | 0.4604 [0.3375, 0.5833] |

## 51

Old: Adding broad concept links reduces Recall@4 from 0.6667 to 0.5833.

New: | AAP (30) | lexical | 0.6167 [0.5000, 0.7333] | 0.7306 [0.6027, 0.8500] |

## 52

Old: Common terms such as antibiotics, culture and serial assessment connect passages from different neonatal contexts, which can dilute precise recommendation matching.

New: | AAP (30) | dense | 0.4167 [0.3000, 0.5500] | 0.4389 [0.2944, 0.5889] |

## 53

Old: This result supports leaving optional production graph expansion disabled by default until independently evaluated; it does not support a blanket claim that a graph improves this application.

New: | AAP (30) | hybrid | 0.5500 [0.4333, 0.6667] | 0.6722 [0.5278, 0.8111] |

## 54

Old: [added]

New: | AAP (30) | hybrid concepts | 0.3833 [0.2667, 0.5167] | 0.3750 [0.2500, 0.5083] |

## 55

Old: [added]

New: | WHO (30) | lexical | 0.1667 [0.0833, 0.2500] | 0.2167 [0.0972, 0.3584] |

## 56

Old: [added]

New: | WHO (30) | dense | 0.2333 [0.1333, 0.3333] | 0.2500 [0.1306, 0.3833] |

## 57

Old: [added]

New: | WHO (30) | hybrid | 0.3333 [0.2167, 0.4667] | 0.2694 [0.1556, 0.4056] |

## 58

Old: [added]

New: | WHO (30) | hybrid concepts | 0.1667 [0.0333, 0.3000] | 0.1667 [0.0333, 0.3000] |

## 59

Old: [added]

New: For hybrid-plus-concepts minus hybrid, Recall@4 differences are: NICE -0.0042 (case [-0.0583, 0.0458], family [-0.0935, 0.0667]); AAP -0.1667 (case [-0.2500, -0.0833], family [-0.3333, 0.0000]); WHO -0.1667 (case [-0.2500, -0.0833], family [-0.3333, -0.0167]).

## 60

Old: [added]

New: The measured concept-expansion scores do not support a blanket graph benefit.

## 61

Old: [added]

New: The original 18 rankings are unchanged; differences between the old NICE average and the expanded NICE average reflect the additional queries rather than a changed retrieval algorithm.

## 62

Old: [added]

New: Source-stratified counts, candidate-pool asymmetry and engineering-authored relevance judgments limit generalization; no source-pooled headline retrieval score is used.

## 63

Old: Among the 8 eligible completed cases in the initial quote-echo run, 8 produced parsed drafts, none were released, and 8 failed exact-source checks.

New: All 100 declared cases completed provider execution.

## 64

Old: The revised run has 18 eligible cases, 15 parsed drafts and 4 releases.

New: Parsed discussion drafts were produced for 94/100 cases and 8/100 were released.

## 65

Old: These different completed populations preclude attributing the change in overall draft yield solely to quote IDs.

New: Structural failures and completed auditor dissent remain quality outcomes.

## 66

Old: A valid quote ID eliminates quote-echo errors for that support span, but does not prevent unsupported text or guarantee that both auditors accept a complete plan.

New: The paired arms share the same initial draft; verification changes release rather than wording.

## 67

Old: Paired lexical alignment.

New: Source-stratified alignment and emission coverage.

## 68

Old: Verified all-case scores count each withheld response as empty; conditional scores describe a selected subset.

New: Conditional scores retain source-population coverage rather than displaying conditional coverage as 100%.

## 69

Old: | Arm | N | Coverage | BLEU-4 | METEOR | ROUGE-1 | ROUGE-2 | ROUGE-L |

New: All-case withheld responses have zero alignment.

## 70

Old: | --- | --- | --- | --- | --- | --- | --- | --- |

New: Full lexical/semantic estimates and both bootstrap interval types appear in CSV tables.

## 71

Old: | Unverified, all cases | 18 | 0.833 | 0.0220 | 0.2110 | 0.2407 | 0.0564 | 0.1416 |

New: | Guideline | Arm | Scored N | Emitted / quality N | BLEU-4 | METEOR | ROUGE-L | DistilBERT F1 | RoBERTa F1 |

## 72

Old: | Verified, all cases | 18 | 0.222 | <0.0001 | 0.0330 | 0.0608 | 0.0131 | 0.0415 |

New: | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 73

Old: | Verified, released only | 4 | 1.000 | 0.0116 | 0.1486 | 0.2735 | 0.0590 | 0.1868 |

New: | NICE | without verification | 40 | 34/40 | 0.0287 | 0.2336 | 0.1524 | 0.6775 | 0.7231 |

## 74

Old: | Unverified, generated only | 15 | 1.000 | 0.0220 | 0.2532 | 0.2888 | 0.0677 | 0.1699 |

New: | NICE | verified all cases | 40 | 5/40 | 2.37e-06 | 0.0280 | 0.0287 | 0.1004 | 0.1078 |

## 75

Old: [added]

New: | NICE | released only | 5 | 5/40 | 0.0217 | 0.2240 | 0.2293 | 0.8030 | 0.8624 |

## 76

Old: [added]

New: | NICE | generated only | 34 | 34/40 | 0.0287 | 0.2748 | 0.1793 | 0.7971 | 0.8506 |

## 77

Old: [added]

New: | AAP | without verification | 30 | 30/30 | 0.0138 | 0.2738 | 0.1574 | 0.8007 | 0.8464 |

## 78

Old: [added]

New: | AAP | verified all cases | 30 | 1/30 | 1.57e-09 | 0.0108 | 0.0082 | 0.0281 | 0.0293 |

## 79

Old: [added]

New: | AAP | released only | 1 | 1/30 | 0.0428 | 0.3251 | 0.2471 | 0.8425 | 0.8802 |

## 80

Old: [added]

New: | AAP | generated only | 30 | 30/30 | 0.0138 | 0.2738 | 0.1574 | 0.8007 | 0.8464 |

## 81

Old: [added]

New: | WHO | without verification | 30 | 30/30 | 0.0109 | 0.2407 | 0.1336 | 0.7835 | 0.8389 |

## 82

Old: [added]

New: | WHO | verified all cases | 30 | 2/30 | 7.31e-12 | 0.0136 | 0.0130 | 0.0555 | 0.0580 |

## 83

Old: [added]

New: | WHO | released only | 2 | 2/30 | 0.0435 | 0.2039 | 0.1946 | 0.8323 | 0.8705 |

## 84

Old: [added]

New: | WHO | generated only | 30 | 30/30 | 0.0109 | 0.2407 | 0.1336 | 0.7835 | 0.8389 |

## 85

Old: [added]

New: Corpus BLEU brevity penalties strongly reflect withheld output length; very small all-case values do not measure a rewriting effect.

## 86

Old: Semantic alignment with fixed BERTScore configurations.

New: Paired all-case verified-minus-unverified DistilBERT F1; negative values reflect the coverage cost of withholding the same draft.

## 87

Old: | Arm | DistilBERT P | DistilBERT R | DistilBERT F1 | RoBERTa F1 |

New: | Guideline | Paired N | Released / N | Difference | Case 95% CI | Family 95% CI |

## 88

Old: | --- | --- | --- | --- | --- |

New: | --- | --- | --- | --- | --- | --- |

## 89

Old: | Unverified, all cases | 0.6449 | 0.6845 | 0.6635 | 0.7109 |

New: | NICE | 40 | 5/40 | -0.5771 | [-0.6786, -0.4742] | [-0.7185, -0.4455] |

## 90

Old: | Verified, all cases | 0.1755 | 0.1692 | 0.1722 | 0.1878 |

New: | AAP | 30 | 1/30 | -0.7726 | [-0.8036, -0.7157] | [-0.8032, -0.7223] |

## 91

Old: | Verified, released only | 0.7896 | 0.7612 | 0.7750 | 0.8450 |

New: | WHO | 30 | 2/30 | -0.7280 | [-0.7819, -0.6489] | [-0.7803, -0.6285] |

## 92

Old: | Unverified, generated only | 0.7739 | 0.8214 | 0.7962 | 0.8530 |

New: Released-only comparisons are selected-population comparisons.

## 93

Old: Among the 15 available unverified drafts, DistilBERT F1 is 0.7962 and RoBERTa F1 is 0.8530.

New: A released draft has identical wording in both arms, so verification cannot improve that draft through rewriting in this experiment.

## 94

Old: Among the four released drafts, these values are 0.7750 and 0.8450.

New: Alignment and release counts do not establish clinical correctness.

## 95

Old: Thus verification does not improve conditional semantic alignment in this fixture.

New: [deleted]

## 96

Old: Higher released-subset judge grounding, when observed, is a different, fallible metric and accompanies a large loss of coverage.

New: [deleted]

## 97

Old: The study does not support a general answer-quality improvement claim.

New: [deleted]

## 98

Old: The all-case verified-minus-unverified DistilBERT F1 difference is -0.4913, with a descriptive paired-case bootstrap interval [-0.6701, -0.3110] over 2,000 resamples.

New: [deleted]

## 99

Old: Resampling the six scenario families instead gives [-0.7131, -0.2667].

New: [deleted]

## 100

Old: This difference reflects gating the same draft and cannot demonstrate improved wording.

New: [deleted]

## 101

Old: Related variants make case-level resampling optimistic; the family interval acknowledges dependence but still rests on only six clusters.

New: [deleted]

## 102

Old: No confirmatory significance claim is made.

New: [deleted]

## 103

Old: 0 candidate/reference pairs exceeded the primary encoder's token limit.

New: [deleted]

## 104

Old: Conditional semantic scores must be interpreted together with release count.

New: [deleted]

## 105

Old: Retrieval ablations and the semantic-alignment/coverage trade-off of verification.

New: Source-stratified retrieval, emission coverage and the paired semantic-alignment cost of withholding the same draft.](output/research/figures/rag_expanded_results.png)

## 106

Old: NA denotes an empty released subset.](output/research/figures/rag_results.png)

New: [deleted]

## 107

Old: Arm-blinded judge means (1-5, higher is better).

New: Dependent model-judge means with judged-output coverage.

## 108

Old: These are automated proxies, not measured clinician usability.

New: These are automated proxies rather than clinician usability observations.

## 109

Old: | Judge dimension | Unverified | Verified released |

New: | Guideline | Arm | Judged / quality N | Grounding | Fidelity | Completeness | Actionability | Uncertainty | Unsafe claims |

## 110

Old: | --- | --- | --- |

New: | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 111

Old: | Grounding | 4.133 | 5.000 |

New: | NICE | without verification | 34/40 | 3.8529 | 3.9118 | 3.7059 | 3.8235 | 3.7647 | 15 |

## 112

Old: | Patient Fidelity | 4.133 | 4.750 |

New: | NICE | with verification | 5/40 | 4.8000 | 3.8000 | 3.4000 | 3.4000 | 4.2000 | 0 |

## 113

Old: | Completeness | 3.933 | 4.250 |

New: | AAP | without verification | 30/30 | 4.3333 | 4.2333 | 3.9667 | 4.5333 | 4.2333 | 5 |

## 114

Old: | Actionability | 3.600 | 3.250 |

New: | AAP | with verification | 1/30 | 5.0000 | 5.0000 | 5.0000 | 5.0000 | 5.0000 | 0 |

## 115

Old: | Uncertainty | 4.267 | 5.000 |

New: | WHO | without verification | 30/30 | 4.5000 | 4.5000 | 4.2000 | 4.3333 | 4.6000 | 3 |

## 116

Old: | Judged outputs | 15 | 4 |

New: | WHO | with verification | 2/30 | 5.0000 | 5.0000 | 4.5000 | 3.5000 | 5.0000 | 0 |

## 117

Old: | Judge-flagged unsafe claims | 4 | 0 |

New: The same model supplies generation, audit and judge roles.

## 118

Old: The judge rates readability-related actionability, explicit uncertainty and factual fidelity only within the supplied fixture.

New: Released-only judge means describe a selected subset, and shared-model agreement does not establish independent clinical correctness.

## 119

Old: Its ratings may disagree with the release auditors because the prompts, decision thresholds and references differ.

New: Completed invalid judge outputs remain unavailable ratings rather than favorable imputations.

## 120

Old: Shared-model judging cannot replace independent entailment review or observation of clinicians using the interface.

New: Source-specific intervals and rating denominators are retained in the CSV tables.

## 121

Old: Missing judge responses are retained with their failure reasons and excluded from means rather than imputed as favorable ratings.

New: [deleted]

## 122

Old: Comparisons of released-only judge means are selection comparisons and cannot establish that verification improved an identical draft.

New: [deleted]

## 123

Old: Deliberately unsafe injected drafts: emissions without versus with verification.

New: Deliberately injected errors, separated by guideline; invalid verdicts are not credited as semantic detection.

## 124

Old: | Fault type | Injected | Structural reject | Semantic reject | Invalid verdict | Emitted |

New: | Guideline | Injected | Unverified emitted | Verified emitted | Structural reject | Semantic reject | Invalid verdict |

## 125

Old: | --- | --- | --- | --- | --- | --- |

New: | --- | --- | --- | --- | --- | --- | --- |

## 126

Old: | false normal | 3 | 0 | 3 | 0 | 0 |

New: | NICE | 12 | 12 | 0 | 3 | 9 | 0 |

## 127

Old: | invented dose | 3 | 3 | 0 | 0 | 0 |

New: | AAP | 12 | 12 | 0 | 3 | 8 | 1 |

## 128

Old: | missing conditions | 3 | 0 | 3 | 0 | 0 |

New: | WHO | 12 | 12 | 0 | 3 | 9 | 0 |

## 129

Old: | negation | 3 | 0 | 3 | 0 | 0 |

New: These 36 intentionally enriched drafts test negation reversal, missing conditions, invented doses and fabricated normal findings.

## 130

Old: The verified workflow withholds 12/12 injected faults, while the unverified arm would emit 12/12.

New: Counts are not estimates of naturally occurring hallucination prevalence.

## 131

Old: Numeric dose faults exercise deterministic structural checks; other faults target semantic entailment or patient assumptions.

New: Per-case and fault-family bootstrap contrasts are provided in the CSV tables.

## 132

Old: Raw verdicts distinguish completed disagreement from service unavailability, and an unavailable auditor is not credited as detecting the semantic error.

New: Latency is not treated as a quality result because operational wall time includes minute-rate waits and checkpoint replay.

## 133

Old: This result concerns a small constructed challenge set, not a real-world sensitivity or hallucination-reduction percentage.

New: Provider outages are retained in operational logs and excluded from quality populations; completed malformed answers and clinical disagreement remain outcomes.

## 134

Old: Representative failures expose different layers.

New: [deleted]

## 135

Old: A deterioration draft can correctly observe low oxygen saturation yet wrongly call ordinary indicators red flags; source traceability cannot rescue that inference.

New: [deleted]

## 136

Old: A CRP discussion can correctly reject a single-test decision while inventing a testing interval absent from the retrieved guidance.

New: [deleted]

## 137

Old: Auditors also make errors: in one deterioration review, both treated the treatment framework as requiring a red flag, overlooking its alternative of two or more non-red-flag factors or indicators.

New: [deleted]

## 138

Old: An incomplete stopping case can omit a conjunctive criterion despite a genuine citation.

New: [deleted]

## 139

Old: Missing-result cases can drift into reassurance.

New: [deleted]

## 140

Old: Withholding reduces answer availability, and auditor agreement alone does not resolve shared interpretive errors.

New: [deleted]

## 141

Old: Latency is not reported as a model-quality result because archived operational timings mix provider waits, new calls and replayed steps.

New: [deleted]

## 142

Old: The CPU container's no-network, read-only, non-root startup/authentication smoke test passed, and cached MiniLM weights completed the offline retrieval evaluation.

New: [deleted]

## 143

Old: The final application still requires hosted end-to-end checks after its database and reviewed corpus are provisioned.

New: [deleted]

## 144

Old: The RAG fixture is small, synthetic, English-language and based on one guideline extraction.

New: The RAG fixture contains 100 synthetic English-language cases across NICE, AAP and WHO rather than an external patient cohort.

## 145

Old: References were written by the engineering workflow, and repeated variants share templates.

New: References and gold passages were proposed by the engineering workflow, repeated variants share templates and clinical adjudication remains pending.

## 146

Old: The same cases informed the quote-ID refinement, preventing an untouched-test interpretation.

New: The original 18 cases informed earlier quote-ID development; a superseded retrieval-only expansion also preceded the user-requested size amendment, preventing an untouched-test interpretation.

## 147

Old: [added]

New: Different guideline populations, recommendation styles and candidate-pool sizes limit cross-source comparisons.

## 148

Old: [added]

New: WHO covers 0-59-day infections and resource-dependent referral pathways, while only its first-72-hour subset is tested; AAP cases remain within the at-least-35-week report.

## 149

Old: Immutable quote IDs improve citation mechanics; concept expansion does not improve this benchmark.

New: Immutable quote IDs improve citation mechanics; concept expansion has lower measured Recall@4 than hybrid retrieval in each source-specific cohort.

## 150

Old: Production retrieval also now implements bounded synonym expansion, finer recommendation concepts and optional MMR diversity after cross-encoder reranking; the numerical retrieval results in Section 7 remain those of the frozen earlier experiment and are not attributed to these unbenchmarked refinements.

New: Production retrieval also now implements bounded synonym expansion, finer recommendation concepts and optional MMR diversity after cross-encoder reranking; the synthetic retrieval results in Section 7 use the frozen broad-concept evaluation configuration and do not measure these additional production refinements.

## 151

Old: Three previously exposed cases (deterioration-1, crp_alone-1 and initial_investigation-1) are reused as a small compatibility and development comparison for two additional Groq backbones.

New: The same 100 cases are evaluated with the two original additional Groq backbones.

## 152

Old: The baseline preserves each completed draft and audit, including malformed answers and dissent.

New: Each one-revision arm reuses its paired initial draft and completed audits, including malformed output and dissent.

## 153

Old: The resolution arm reuses that same initial output and permits at most one source-grounded revision of a structurally valid draft after completed reviewer disagreement.

New: At most one revision is permitted after completed disagreement; both auditors freshly assess any revision.

## 154

Old: Both auditors must freshly review every revised claim; an outage cannot be resolved into release, and repeated dissent cannot trigger further attempts.

New: The original 120-second budget and 20-second minimum cloud-call gap are retained, with initial elapsed time deducted during replay.

## 155

Old: Request budgets bound whether a revision is attempted.

New: The primary paired experiment remains a zero-repair release-filtering study.

## 156

Old: The original eighteen-case paired experiment remains the unchanged-draft release-filtering experiment with zero resolution passes.

New: [deleted]

## 157

Old: Completed-case backbone comparison; release is an engineering gate, not a clinical correctness label.

New: Source-stratified bounded-resolution release counts and paired release-fraction differences.

## 158

Old: | Backbone | Paired cases | Parsed drafts | Released, baseline | Released, one revision |

New: | Backbone | Guideline | Paired N | Baseline released | One-repair arm released | Attempts | Difference | Case 95% CI | Family 95% CI |

## 159

Old: | --- | --- | --- | --- | --- |

New: | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 160

Old: | openai/gpt-oss-20b | 3 | 2 | 0 | 1 |

New: | openai/gpt-oss-20b | NICE | 40 | 1 | 2 | 2 | 0.0250 | [0.0000, 0.0750] | [0.0000, 0.0789] |

## 161

Old: | qwen/qwen3.8-27b | 3 | 3 | 1 | 2 |

New: | openai/gpt-oss-20b | AAP | 30 | 0 | 0 | 2 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |

## 162

Old: All three declared cases completed provider execution for each backbone in this comparison.

New: | openai/gpt-oss-20b | WHO | 30 | 0 | 0 | 5 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |

## 163

Old: The improvement in release count is descriptive: the fixture is small, was previously exposed, and the models also supply their own source/safety audit roles.

New: | qwen/qwen3.8-27b | NICE | 40 | 23 | 24 | 1 | 0.0250 | [0.0000, 0.0750] | [0.0000, 0.0750] |

## 164

Old: It does not establish improved clinical accuracy or independent expert acceptance.

New: | qwen/qwen3.8-27b | AAP | 30 | 26 | 26 | 0 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |

## 165

Old: Raw drafts, revised claims, prior dissent, final verdicts, exact case IDs and source-code hashes are retained.

New: | qwen/qwen3.8-27b | WHO | 30 | 27 | 27 | 0 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |

## 166

Old: Provider execution attempts remain outside the quality tables.

New: Release is an engineering gate, not a clinical correctness label.

## 167

Old: Current application responses have thirteen review sections; absent evidence is marked undetermined or withheld, and the research model estimate remains separate from clinical treatment decisions.

New: Models audit their own backbone outputs, elapsed-time constraints can prevent resolution, and the synthetic fixtures do not establish independent expert acceptance.

## 168

Old: Mixed-population source documents additionally require reviewed passage-level onset scope for patient-specific retrieval.

New: The existing budget is a preflight admission condition rather than a hard wall-clock deadline; provider waits can exceed it.

## 169

Old: After these frozen JSON-object experiments, the application was further constrained with provider-enforced JSON schemas for drafts, audits and revisions.

New: Source code, settings, role responses and revision traces remain archived.

## 170

Old: [added]

New: The deployed schema-enforced application is distinct from these fixed JSON-object research runs.

## 171

Old: [added]

New: After the historical JSON-object experiments, the application was further constrained with provider-enforced JSON schemas for drafts, audits and revisions.
