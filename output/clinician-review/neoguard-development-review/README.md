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
