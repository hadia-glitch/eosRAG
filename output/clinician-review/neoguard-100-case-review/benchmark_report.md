# 100-case three-guideline benchmark

40 NICE, 30 AAP and 30 WHO synthetic cases; 18 unchanged originals and 82 additions. Seed 31.

|Family|NICE|AAP|WHO|Total|
|---|---:|---:|---:|---:|
|deterioration|7|5|5|17|
|crp_alone|7|5|5|17|
|incomplete_stop|7|5|5|17|
|initial_investigation|7|5|5|17|
|single_risk|6|5|5|16|
|missing_results|6|5|5|16|

Corpus: NICE 132, AAP 43, WHO 141 passages. Every gold ID and source hash is checked; references are engineering-authored and await clinician review.

The former 114-case retrieval-only prototype remains in expanded/. Selection for this user-requested size change used predetermined family quotas and case order, not retrieval scores. The original 18 JSON objects and file are unchanged.

WHO cases remain below 72 hours. WHO guidance covers a broader 0-59-day population and different resource settings. Its non-hospital recommendations retain referral conditions. No NICE stopping criteria, AAP risk tool or gestation-specific subgroup claim is attributed to WHO.

Priority clinician review: all WHO cases, especially hospital diagnostic evidence-gap and stopping-duration cases; all AAP critical-illness exceptions; original NICE extraction boundaries. These are synthetic engineering tests, not independently validated clinical gold standards.

Exact-text WHO PDF duplicates were removed in a logged pre-generation index amendment. Canonical gold identifiers and all 100 cases remain unchanged.

Additional preserved-case review priorities: single_risk-1/2 (prematurity may add risk), incomplete_stop-1/2/3 (age is not culture-incubation duration), missing_results-1/2/3 (current versus unavailable later observations). These original cases are flagged rather than altered.
