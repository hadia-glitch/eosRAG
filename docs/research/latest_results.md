# Latest saved RAG results (28 October 2026)

Status: exposed synthetic development benchmark; final evaluation not completed. This publication is a code/research snapshot, not a clinical release or promotion of the experimental candidate.

The 100 base cases comprise NICE 40, AAP 30 and WHO 30, spanning six scenario families and only 24 unique focused question templates. The 200 wording slots reuse those cases; 152 change wording and 48 are unchanged controls. Clinical equivalence and gold relevance remain unadjudicated.

| Guideline | Latest plain-wording canonical selector R@4 | MRR@4 | R@8 | P@8 | nDCG@8 | Retrieval coverage |
| --- | --- | --- | --- | --- | --- | --- |
| NICE | 0.7667 | 0.8000 | 0.9375 | 0.3156 | 0.7791 | 40/40 |
| AAP | 1.0000 | 0.9167 | 1.0000 | 0.2500 | 0.9017 | 30/30 |
| WHO | 1.0000 | 0.8667 | 1.0000 | 0.2500 | 0.8515 | 30/30 |

These are retrieval completion counts, not useful/released-answer coverage. P@8 annotation ceilings are 0.3344, 0.2500 and 0.2500; raw precision is not normalized. NICE original-wording R@4 was 0.9167, so the wording stress exposes a material weakness. WHO plain-wording slots include unchanged controls. Canonical normalization was developed after examining failures.

Exact values, case and family bootstrap 95% intervals (2,000 resamples, seed 31), negative comparisons and all declared variants: [CSV](../../output/research/rag_development/robustness_audit/all_retrieval_metrics.csv). See [robustness audit](rag_robustness_audit.md) and [final gate](final_evaluation_gate.md).

The explanation safety smoke attempted 3/18 planned cases: 2/3 structurally valid, complete audits for 2/3, 1/3 released (1/18 of the planned cohort). AAP audit approval still missed an exception; NICE contained unsafe reasoning withheld for a separate structural issue; WHO auditors disagreed. These engineering findings do not establish a clinical error rate. Balanced usable-answer coverage, fresh semantic fault checks and independent clinical validation remain outstanding.

Send the [development review ZIP](../../output/clinician-review/neoguard-development-clinician-review.zip) with its README to a clinician. Reviewers should complete blinded forms before opening engineering priority files. The [100-case bundle](../../output/clinician-review/neoguard-100-case-clinician-review.zip) supplies the base casebook. Both contain synthetic data and blank ratings, not completed clinical verification.

Historical reports retain the prior publication hold wording. The current user-authorized GitHub upload publishes development evidence and code only; final evaluation, clinical deployment and experimental-candidate promotion remain gated.
