# Remaining boundaries before a final research evaluation

The current pipeline is still in development. Retrieval scores on the exposed
100-case fixture do not establish clinical readiness.

The latest longitudinal source-context variant meets the mean source-specific
retrieval targets on all 100 exposed cases. Provenance hardening reproduces all
rankings without new model calls. Generation coverage, fresh semantic fault
testing and source/gold adjudication remain pending; the full gate remains false.

The newly requested PIC longitudinal ML comparison is separate from RAG. Only
seven independent positive infants remain under the strict pre-culture phenotype;
the resulting discrimination is inadequate. A new research input screen captures
maternal context and timed observations but withholds the PIC prediction. Raw
patient data and real-data weights remain local. This work does not integrate or
publish the improved RAG candidate before its final evaluation.

- Use the unchanged source-specific entry criteria in `final_evaluation_gate.md`.
  Do not replace Recall@4 with Recall@8, discard difficult cases, or rescale
  precision to reach a target. Preserve unsuccessful model and graph variants.
- Reconcile the research recommendation corpus with the production index. The
  production chunker can split long recommendation/remark units, whereas the
  research corpus retains complete recommendations. Conditions must reach the
  generator and both auditors together. Encoder identity and migration 009 alone
  do not establish that equivalence. No hosted reindex has been performed.
- Review the proposed source and relevance annotations using the clinician pack.
  Other retrieved passages may be relevant even when absent from the proposed
  gold set. Keep the existing labels fixed until independent adjudication is
  recorded; neither an agent nor a bootstrap interval is a clinical reviewer.
- Run a small, balanced answer-quality pilot after retrieval is adequate. Verify
  task completeness and patient fidelity, not just quote identity or release
  status. Include retained unknowns, persistent symptoms, the separate culture
  and treatment clocks, and source-specific stopping/referral conditions.
- The API supports culture-incubation and antibiotic-exposure durations, but the
  current form does not capture those clocks. The form's explicit culture result
  and care setting now reach requests and saved assessments. Neither a negative
  result nor baby age establishes a known incubation or treatment interval.
- Distinguish CPAP from mechanical ventilation before asserting ventilation-based
  eligibility: the existing combined support category cannot establish which was
  used. WHO feeding/activity criteria are also not a complete app intake schema.
  The active deployment deliberately withholds outpatient plans.
- Investigate numeric-guard false positives, including a source-supported blood
  culture specimen volume. Specimen volume is different from a drug dose. Any
  change requires a versioned validator and regression coverage; do not bypass
  the guard by rewriting claims or inventing patient measurements.
  A separate `support_validation_v5.py` prototype now distinguishes narrowly
  defined, verbatim culture-inoculum text from therapeutic dosing and passes
  seven focused regressions. It is not wired into the active verification graph
  and has not undergone new semantic fault evaluation.
- Repeat relevant fault regressions when task-aware prompts change. Saved exact
  request replays demonstrate equivalence only, not new independent safety data.
  Source and safety roles sharing a backbone can share errors.

Source approval, clinical outcome validation, prospective workflow evaluation and
actual hosted integration are separate from this engineering gate. They remain
unestablished by the synthetic benchmark. The paper must retain these limits.


## 28 October robustness audit

- NICE plain-wording fixed-plan Recall@4 remains 0.7667 after intent normalization (below 0.8 development target).
- AAP model-approved action prose omits a site-specific-infection exception; agreement does not establish semantic completeness.
- NICE draft mistakes unclear suspicion for reassuring eligibility and adds unsupported escalation; only a different structural issue blocks release.
- WHO model auditors disagree on illness-category conflation.
- Balanced usable-answer coverage and fresh semantic fault suite remain incomplete.
- Clinical source approval, gold adjudication, paraphrase equivalence and independent challenge cases remain unavailable.

Full numerical results and confidence intervals: output/research/rag_development/robustness_audit/all_retrieval_metrics.csv. No unchanged original-query score is evidence of independent generalisation.
