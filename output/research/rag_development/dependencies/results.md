# Patient-conditioned retrieval development

Study: dependencies. Saved cases: 18/18. Balanced pilot: 18/18. Final evaluation remains on hold.

|Population|Source|Method|N|Recall@4|MRR@4|Recall@8|
|---|---|---|---:|---:|---:|---:|
|balanced_pilot|NICE|patient_selected|6|0.694444|0.791667|0.750000|
|balanced_pilot|NICE|patient_consensus|6|0.694444|0.833333|0.833333|
|balanced_pilot|NICE|question_consensus|6|0.694444|0.833333|0.833333|
|balanced_pilot|NICE|prior_patient_consensus|6|0.694444|0.833333|0.888889|
|balanced_pilot|AAP|patient_selected|6|0.750000|0.708333|1.000000|
|balanced_pilot|AAP|patient_consensus|6|0.833333|0.763889|1.000000|
|balanced_pilot|AAP|question_consensus|6|0.750000|0.708333|0.833333|
|balanced_pilot|AAP|prior_patient_consensus|6|0.833333|0.791667|0.916667|
|balanced_pilot|WHO|patient_selected|6|0.666667|0.666667|0.666667|
|balanced_pilot|WHO|patient_consensus|6|0.833333|0.791667|1.000000|
|balanced_pilot|WHO|question_consensus|6|0.750000|0.750000|1.000000|
|balanced_pilot|WHO|prior_patient_consensus|6|0.833333|0.791667|1.000000|

Intervals and paired differences retain 2,000 case and whole-family bootstrap resamples (seed 31). The six-case source pilot has one example per family; its intervals cannot establish broad generalization. Gold IDs and patient data remain unchanged.
