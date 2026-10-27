# Remaining boundaries before a final research evaluation

The current pipeline is still in development. Retrieval scores on the exposed
100-case fixture do not establish clinical readiness.

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
- Repeat relevant fault regressions when task-aware prompts change. Saved exact
  request replays demonstrate equivalence only, not new independent safety data.
  Source and safety roles sharing a backbone can share errors.

Source approval, clinical outcome validation, prospective workflow evaluation and
actual hosted integration are separate from this engineering gate. They remain
unestablished by the synthetic benchmark. The paper must retain these limits.
