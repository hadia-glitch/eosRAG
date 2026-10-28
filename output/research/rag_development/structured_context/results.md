# Source-context retrieval development

Study: structured_context. Completed 100/100 previously examined synthetic cases. No final evaluation or clinical validation.

|Source|Method|Depth|Complete / N|Recall|Precision|MRR|nDCG|
|---|---|---:|---:|---:|---:|---:|---:|
|NICE|publisher_hierarchy|4|40/40|0.716667|0.468750|0.912500|0.727811|
|NICE|publisher_hierarchy|8|40/40|0.841667|0.275000|0.912500|0.785774|
|NICE|qualifier_graph|4|40/40|0.891667|0.600000|0.912500|0.839610|
|NICE|qualifier_graph|8|40/40|0.991667|0.331250|0.912500|0.885841|
|NICE|longitudinal_context_graph|4|40/40|0.916667|0.618750|0.912500|0.854768|
|NICE|longitudinal_context_graph|8|40/40|0.991667|0.331250|0.912500|0.888463|
|AAP|publisher_hierarchy|4|30/30|1.000000|0.500000|1.000000|0.939396|
|AAP|publisher_hierarchy|8|30/30|1.000000|0.250000|1.000000|0.939396|
|AAP|qualifier_graph|4|30/30|1.000000|0.500000|1.000000|0.939396|
|AAP|qualifier_graph|8|30/30|1.000000|0.250000|1.000000|0.939396|
|AAP|longitudinal_context_graph|4|30/30|1.000000|0.500000|1.000000|0.939396|
|AAP|longitudinal_context_graph|8|30/30|1.000000|0.250000|1.000000|0.939396|
|WHO|publisher_hierarchy|4|30/30|1.000000|0.500000|0.866667|0.858587|
|WHO|publisher_hierarchy|8|30/30|1.000000|0.250000|0.866667|0.858587|
|WHO|qualifier_graph|4|30/30|1.000000|0.500000|0.866667|0.858587|
|WHO|qualifier_graph|8|30/30|1.000000|0.250000|0.866667|0.858587|
|WHO|longitudinal_context_graph|4|30/30|1.000000|0.500000|0.866667|0.858587|
|WHO|longitudinal_context_graph|8|30/30|1.000000|0.250000|0.866667|0.858587|

All case-level and scenario-family bootstrap intervals use 2,000 resamples, seed 31. Cases, golds and RRF offset 60 are unchanged. Negative outcomes are retained. Definition context word/node budgets are in the CSVs. Clinical source/genre review remains pending.
