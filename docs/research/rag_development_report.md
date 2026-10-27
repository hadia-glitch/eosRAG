## 13. Subsequent retrieval development and readiness boundary

This section is a post-hoc development extension on the same 100 previously examined synthetic cases, not a final evaluation or an untouched test. The original Sections 6-7 and their results remain a frozen historical study. No proposed gold identifier or engineering reference answer enters query planning, candidate retrieval, cross-encoder scoring or language-model passage ranking. Source and case adjudication remain pending.

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
