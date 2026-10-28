# NeoGuard development review pack

This pack requests independent clinical adjudication; no clinical review has been performed or implied.
It contains 100 synthetic cases (NICE 40, AAP 30, WHO 30), no real patient records.
The same cases have informed engineering iterations. Repeated variants share question templates.

1. Open review_cases.html locally. Assess both evidence panels against the patient and question.
2. Complete panel_ratings.csv. Panel labels are shuffled per case; the method key is outside this bundle.
3. Use passage_relevance_review.csv to adjudicate the proposed candidate passages. Golds are not shown there.
4. Review source_scope_review.csv against original publisher documents. All approval fields start blank.
5. Only after independent relevance review, inspect engineering_priority_queue.csv. Its missed-gold counts
   are an engineering triage signal, not a clinical severity rating or evidence that existing labels are correct.
6. Use definition_context_review.csv to check exact publisher definitions and their section relations.
   Those supplemental definitions are not silently included as original top-four passages in the panels.
7. Open pilot_cases.html for 18 balanced development cases with three shuffled evidence panels.
   Complete pilot_panel_ratings.csv and dependency_candidate_review.csv. These pilots did not pass
   the engineering readiness gate. Assess future maternal counselling versus current infant actions,
   complete conditional frameworks and diagnostic limitations; do not force a preferred metric result.
   synthetic_case_inputs.json contains all 100 synthetic input cases and their recorded histories.
8. Review source_boundary_review.csv against the NICE publisher document. It proposes 14 structural
   corrections: separating risk-factor/indicator boxes from adjacent recommendations, restoring the
   cross-page Box 2 continuation and removing trailing numbered section headings. The existing
   evidence panels still describe their original development corpus; this separate amendment is not
   implicitly approved by those panels. Extraction offsets refer to a declared text stream, not PDF bytes.
9. Review source_topic_exclusion_review.csv: determine whether the proposed current-case topic routing
   removes useful conditional evidence. Its engineering exclusions have not received clinical approval.
10. Open corrected_smoke_cases.html and complete corrected_smoke_panel_ratings.csv. These three
    deliberately difficult cases use the corrected corpus and three shuffled evidence panels.
    Adjudicate useful alternative passages and omissions before comparing against engineering golds.

Priority clinical issues include CRP-alone reasoning, persistent symptoms with a negative culture,
separate culture-incubation and antibiotic-exposure clocks, critical illness versus isolated fast breathing,
missing observations, AAP gestational eligibility, WHO hospital/referral conditions and complete qualifiers.
Check whether unlabelled retrieved passages are also relevant; do not accept or reject a gold solely to raise a metric.

These panels evaluate retrieval only. Do not use their ratings as care-plan usability or treatment-safety results.
The separate earlier 100-case care-plan bundle concerns the frozen baseline, not this new candidate.
No patient-specific treatment decision or clinical approval should be inferred from an exact quotation.
The clinical source registry remains pending review. Do not enter names, identifiers or real cases into this pack.

Source links: NICE NG195 https://www.nice.org.uk/guidance/ng195 ; AAP https://doi.org/10.1542/peds.2018-2894 ;
WHO https://www.who.int/publications/i/item/9789240102903 . PDF-page numbers refer to the supplied extracts,
and their mapping to complete publisher documents also requires checking.


## Latest addendum: source-context development

Open source_context_cases.html first for the latest candidate. Complete the 300 blank rows in source_context_panel_ratings.csv. The three evidence panels are shuffled separately for each of the 100 unchanged synthetic cases; no method key is included. Some panels are identical, reflecting a genuine null ablation.

Review source_context_edge_review.csv and source_context_exclusion_review.csv for clinically misleading relationships or excluded useful conditional evidence. Graph edges are engineering links, not clinically approved causal relations. Publisher definitions are explicitly labelled as supplemental context outside the top-four recommendation slots. High engineering recall does not approve the relevance labels or patient applicability.

The real-data PIC longitudinal comparison is not ready for clinical prediction: 543 infants but only seven independent documented-pathogen outcomes under the strict pre-culture cohort. No real PIC patient rows, model weights, individual predictions or inferred maternal histories are included. A linked obstetric-neonatal cohort and outcome adjudication are required before combined clinical prediction.


## Wording robustness and explanation safety addendum

1. Complete wording_equivalence_review.csv (200 variants of the same 100 base cases). Confirm equivalent clinical intent, numbers, units, negation, missingness and appropriate gold sections; identify changes that invalidate a paraphrase comparison. These are not 200 independent patient cases.
2. Open explanation_safety_review.html and complete explanation_claim_ratings.csv. These three unapproved model drafts include errors. Model verdicts are hidden for initial independent review. Afterward consult explanation_priority_after_blind_review.csv; do not treat its engineering concerns as clinician adjudication.
3. Open lossless_evidence_views.html and complete the 100 blank rows in lossless_evidence_ratings.csv. This source-only fallback removes generative clinical conclusions; whether it is useful or complete is still an open clinical-review question.

The final evaluation and candidate application integration remain on hold. High original-query recall does not demonstrate generalisation: fresh plain-wording NICE Recall@4 is 0.7667 versus 0.9167 originally. The terminology repair is post-hoc and not an independent test. No real PIC rows or model weights are in this bundle. The paper-inspired Bayesian comparison retains all seeds and does not produce a deployable clinical risk model.
