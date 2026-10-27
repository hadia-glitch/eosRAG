# Frozen expanded benchmark

114 synthetic cases: 18 unchanged originals, 72 new NICE cases, 24 new AAP cases. Seed 31. No real patient records.

|Family|NICE|AAP|Total|
|---|---:|---:|---:|
|deterioration|15|4|19|
|crp_alone|15|4|19|
|incomplete_stop|15|4|19|
|initial_investigation|15|4|19|
|single_risk|15|4|19|
|missing_results|15|4|19|

Index: 132 frozen NICE passages; 43 AAP paragraphs/recommendations. All gold IDs and source hashes validated.

Clinical review remains pending. The production reviewed-source registry is unchanged. AAP >=35-week scope must not be extended to more premature infants.

Priority review: all stopping/critical-illness cases, missing-result cases and NICE preterm cases (see clinician_review_queue.json). Original NICE box extraction and recommendation-boundary contamination also require source review. No uncertainty was resolved by changing original cases.

AAP differs from NICE: no imported NICE 12-hour monitoring requirement, baseline CRP mandate or four-condition stopping rule. Term critical-illness exceptions are retained.

AAP candidate passages include narrative paragraphs, which differ from numbered NICE recommendations; source-stratified results must disclose this asymmetry. AAP references remain source-derived and do not constitute independent clinical validation.
