# Complete-source semantic retrieval development

Completed 100/100 previously examined synthetic cases. No final evaluation or clinical validation.

|Source|Method|Depth|Complete / N|Recall|Precision|MRR|nDCG|
|---|---|---:|---:|---:|---:|---:|---:|
|NICE|ce_full_pool|4|40/40|0.716667|0.468750|0.962500|0.744812|
|NICE|ce_full_pool|8|40/40|0.850000|0.278125|0.962500|0.807638|
|NICE|ce_guidance_genre|4|40/40|0.716667|0.468750|0.912500|0.718323|
|NICE|ce_guidance_genre|8|40/40|0.841667|0.275000|0.806667|0.731970|
|NICE|ce_definition_graph|4|40/40|0.716667|0.468750|0.912500|0.718323|
|NICE|ce_definition_graph|8|40/40|0.841667|0.275000|0.806667|0.731970|
|AAP|ce_full_pool|4|30/30|0.583333|0.291667|0.625000|0.523547|
|AAP|ce_full_pool|8|30/30|0.666667|0.166667|0.625000|0.555785|
|AAP|ce_guidance_genre|4|30/30|0.583333|0.291667|0.513889|0.479536|
|AAP|ce_guidance_genre|8|30/30|0.833333|0.208333|0.708333|0.665060|
|AAP|ce_definition_graph|4|30/30|0.583333|0.291667|0.513889|0.479536|
|AAP|ce_definition_graph|8|30/30|0.833333|0.208333|0.708333|0.665060|
|WHO|ce_full_pool|4|30/30|0.716667|0.358333|0.850000|0.707517|
|WHO|ce_full_pool|8|30/30|1.000000|0.250000|0.863333|0.838798|
|WHO|ce_guidance_genre|4|30/30|0.716667|0.358333|0.800000|0.684888|
|WHO|ce_guidance_genre|8|30/30|1.000000|0.250000|0.813333|0.816168|
|WHO|ce_definition_graph|4|30/30|0.833333|0.416667|0.866667|0.763480|
|WHO|ce_definition_graph|8|30/30|0.916667|0.229167|0.866667|0.803013|

All case-level and scenario-family bootstrap intervals use 2,000 resamples, seed 31. Cases, golds and RRF offset 60 are unchanged. Negative outcomes are retained. Definition context word/node budgets are in the CSVs. Clinical source/genre review remains pending.
