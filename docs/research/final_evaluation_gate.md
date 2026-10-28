# Development gate before a final research evaluation

The final evaluation is on hold at the user's request. Existing 100-case studies
and small answer pilots are development evidence, not a final or untouched test.
Earlier failures, source exclusions and API-blocked stages remain recorded.

The next candidate must first demonstrate all of the following on development
checks, with its model revisions, prompts, corpus and settings pinned:

- Recall@4 and MRR@4 targeted at 0.80 or higher **for each guideline separately**.
  Conventional Precision@4, nDCG@4, case and scenario-family intervals accompany
  these scores. Precision is not rescaled to conceal its annotation ceiling.
- No known wrong-onset, wrong-gestation or wrong-setting passage reaches a
  patient recommendation. Unknown eligibility stays explicit; missing is not normal.
- At least 90% structurally valid answers and 80% usable, fully reviewed answer
  coverage in a balanced development pilot covering all six families and three
  sources. Complete and partial releases are distinct; empty or irrelevant
  excerpts do not count as useful coverage. Provider failures have separate counts.
- Complete, noncontradictory audits of every emitted claim. No unsafe releases
  in the 36-fault regression suite, and no weakening of dose, quotation or
  stopping-condition checks to raise coverage.
- Remaining failures have case-level explanations and a review queue. Gold-ID
  uncertainty is audited separately; benchmark labels are never changed merely
  to improve a score.
- Relevant backend and app-contract regressions pass. Index migrations, encoder
  identity, scope review and source versions have a documented deployment path.

These are engineering entry criteria for a final research evaluation, not proof
of clinical effectiveness or authorization to treat patients. Clinical readiness
still requires source/gold adjudication and external clinical validation. The
current 100 cases have already been examined and cannot become an untouched test
by renaming a split. Any final report must disclose that exposure and the repeated
templates, retain negative results and avoid claims of superiority when paired
intervals include zero.

Current overall status: **not passed**. The latest source-context development
variant now meets the mean retrieval entry targets: Recall@4 is 0.9167, 1.0000
and 1.0000, and MRR@4 is 0.9125, 1.0000 and 0.8667 for NICE, AAP and WHO.
All 100 exposed synthetic cases are retained. Recall@8 is 0.9917, 1.0000 and
1.0000; nDCG@8 is 0.8885, 0.9394 and 0.8586. Precision@8 remains conventional
at 0.3313, 0.2500 and 0.2500, with annotation ceilings of 0.3344, 0.2500 and
0.2500. Case and family bootstrap intervals and negative preceding variants are
retained. These repeated-template, post-hoc overlap scores do not establish
novel-case generalization, clinical source approval, usable answer coverage or
semantic fault robustness. The balanced answer pilot and fresh semantic fault
suite remain required before final evaluation, app RAG integration or pushing
the candidate. The latest machine-readable gate is in
`output/research/rag_development/structured_context/readiness_gate.json`.

Historical development comparisons follow. The completed consensus regression
has Recall@4 of 0.6792, 0.7500 and 0.8000 for NICE, AAP and WHO; MRR@4 is
0.7875, 0.7083 and 0.8500, respectively. Recall@8 is 0.8333, 0.8333 and 1.0000,
but a larger context budget does not satisfy the unchanged four-passage gate.
The source-specific CSVs include both bootstrap interval types and negative
results. No balanced clinical answer usability pilot is established by these
retrieval scores. The listwise-only variant reduced WHO recall and is not adopted
as an availability gate. These are development results on exposed cases.
No final run or clinical deployment is approved by this document, and no
clinician sign-off is fabricated.

The subsequent balanced patient-conditioned development pilot is complete at
18/18 cases, with six per source. Its consensus Recall@4 is 0.6944, 0.8333 and
0.8333; MRR@4 is 0.8333, 0.7917 and 0.7917 for NICE, AAP and WHO. A source-text
dependency comparison on the same 18 cases does not increase Recall@4 and lowers
AAP MRR@4 to 0.7639. Neither passes the unchanged gate. These pilot populations
must not be confused with the complete 100-case consensus results above.
The free-quotation evidence-set pilot was stopped after two completed contract
rejections. A separate immutable-ID version has six structurally valid NICE
cases saved, but is not a balanced completed study. Its remaining calls are
deferred while source-boundary corrections and local retrieval checks proceed,
conserving Groq tokens. Provider quota stops are pending operational events,
not answer-quality failures. The requested application integration and
push of the newly evaluated pipeline follow final evaluation, not these pilots.

The later source-boundary repair changes 14 NICE passages while preserving all
299 IDs and all 100 cases/golds. Source-topic routing on the corrected, bounded
medical-faceted selector has Recall@4 of 0.6917, 0.6667 and 0.7167 and MRR@4 of
0.8333, 0.7500 and 0.8000 for NICE, AAP and WHO. Its unbounded counterpart has
AAP Recall@4 of 0.7500. No declared variant passes the complete source-specific
gate. A capped three-case primary-model ranking smoke completes three valid
contracts but retains missing gold passages and an empty WHO selection; it is
not promoted. Local full-context attempts time out and remain outside quality
scores. Only three retrieval-only Groq requests were added after the token-saving
instruction, with no generation, semantic-auditor or judge calls at this stage.


## 28 October robustness audit

- NICE plain-wording fixed-plan Recall@4 remains 0.7667 after intent normalization (below 0.8 development target).
- AAP model-approved action prose omits a site-specific-infection exception; agreement does not establish semantic completeness.
- NICE draft mistakes unclear suspicion for reassuring eligibility and adds unsupported escalation; only a different structural issue blocks release.
- WHO model auditors disagree on illness-category conflation.
- Balanced usable-answer coverage and fresh semantic fault suite remain incomplete.
- Clinical source approval, gold adjudication, paraphrase equivalence and independent challenge cases remain unavailable.

Full numerical results and confidence intervals: output/research/rag_development/robustness_audit/all_retrieval_metrics.csv. No unchanged original-query score is evidence of independent generalisation.
