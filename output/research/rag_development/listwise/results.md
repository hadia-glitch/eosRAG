# Bounded listwise reranking: development results

All 100 previously exposed synthetic cases are retained. This is development, not final evaluation or clinical validation.
Gold identifiers and engineering reference answers enter this scoring script only; they never enter ranking prompts.

|Source|Method|Depth|Completed/total|Recall|MRR|Precision (ceiling)|nDCG|Mean source words|
|---|---|---:|---:|---:|---:|---:|---:|---:|
|NICE|upstream_fusion|4|40/40|0.6208|0.7208|0.3937 (0.6687)|0.5686|364.6|
|NICE|upstream_fusion|8|40/40|0.7417|0.7208|0.2375 (0.3344)|0.6266|640.6|
|NICE|listwise|4|40/40|0.6792|0.7562|0.4375 (0.6687)|0.6341|344.7|
|NICE|listwise|8|40/40|0.7958|0.7762|0.2625 (0.3344)|0.6943|515.6|
|AAP|upstream_fusion|4|30/30|0.6667|0.6528|0.3333 (0.5000)|0.5613|467.8|
|AAP|upstream_fusion|8|30/30|0.7500|0.6528|0.1875 (0.2500)|0.6008|989.3|
|AAP|listwise|4|30/30|0.7500|0.7222|0.3750 (0.5000)|0.7044|474.7|
|AAP|listwise|8|30/30|0.7500|0.7222|0.1875 (0.2500)|0.7044|659.5|
|WHO|upstream_fusion|4|30/30|0.7167|0.8222|0.3583 (0.5000)|0.6941|423.5|
|WHO|upstream_fusion|8|30/30|1.0000|0.8356|0.2500 (0.2500)|0.8192|655.0|
|WHO|listwise|4|30/30|0.6333|0.6833|0.3167 (0.5000)|0.5919|248.8|
|WHO|listwise|8|30/30|0.7167|0.6967|0.1792 (0.2500)|0.6315|275.5|

Both case-level and whole-scenario-family bootstrap intervals (2,000 resamples, seed 31) and all paired changes are in CSVs.
The selection-validity counts are in coverage.csv. No provider-blocked case is imputed as an answer failure. Completed malformed model outputs remain failures.
The candidate-recall ceiling is the fraction of annotated gold passages present in the fixed upstream pool, not a theoretical ceiling for all retrieval.
WHO has a small guidance pool. The language model also adds latency and shares a backbone with existing answer experiments; independent clinical assessment remains necessary.
No answer generation, fault regression or usability result is inferred from these retrieval scores. The final evaluation stays on hold.
