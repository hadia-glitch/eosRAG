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
