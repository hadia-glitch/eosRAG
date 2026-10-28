# Faceted guidance retrieval: development results

Final evaluation remains on hold. Cases and gold IDs are unchanged. Results reuse a previously examined synthetic benchmark.

|Source|Method|Depth|N|Recall|Precision (ceiling)|MRR|nDCG|Mean source words|
|---|---|---:|---:|---:|---:|---:|---:|---:|
|AAP|generic_faceted|4|30|0.6667|0.3333 (0.5000)|0.8056|0.6399|551.5|
|AAP|generic_faceted|8|30|0.7500|0.1875 (0.2500)|0.6944|0.6229|1048.7|
|AAP|generic_single|4|30|0.4167|0.2083 (0.5000)|0.4722|0.3844|494.5|
|AAP|generic_single|8|30|0.6667|0.1667 (0.2500)|0.4960|0.4976|981.5|
|AAP|medical_faceted|4|30|0.6667|0.3333 (0.5000)|0.7500|0.6085|514.2|
|AAP|medical_faceted|8|30|0.8333|0.2083 (0.2500)|0.7500|0.6960|914.0|
|AAP|medical_faceted_graph|4|30|0.5833|0.2917 (0.5000)|0.7222|0.5377|511.5|
|AAP|medical_faceted_graph|8|30|0.8333|0.2083 (0.2500)|0.7222|0.6647|966.5|
|AAP|medical_single|4|30|0.6667|0.3333 (0.5000)|0.6667|0.5746|438.0|
|AAP|medical_single|8|30|0.9167|0.2292 (0.2500)|0.6667|0.6828|841.2|
|NICE|generic_faceted|4|40|0.6083|0.3875 (0.6687)|0.6333|0.5310|308.5|
|NICE|generic_faceted|8|40|0.7167|0.2281 (0.3344)|0.6083|0.5714|525.2|
|NICE|generic_single|4|40|0.5125|0.3250 (0.6687)|0.7500|0.5303|283.9|
|NICE|generic_single|8|40|0.6250|0.1938 (0.3344)|0.7500|0.5829|515.9|
|NICE|medical_faceted|4|40|0.6292|0.4125 (0.6687)|0.7958|0.6300|271.9|
|NICE|medical_faceted|8|40|0.7417|0.2375 (0.3344)|0.7958|0.6818|515.5|
|NICE|medical_faceted_graph|4|40|0.5958|0.3875 (0.6687)|0.7958|0.6073|279.1|
|NICE|medical_faceted_graph|8|40|0.7417|0.2375 (0.3344)|0.7958|0.6716|509.3|
|NICE|medical_single|4|40|0.5000|0.3250 (0.6687)|0.7188|0.5086|265.6|
|NICE|medical_single|8|40|0.7667|0.2469 (0.3344)|0.7188|0.6324|512.5|
|WHO|generic_faceted|4|30|0.7167|0.3583 (0.5000)|0.8000|0.6849|419.7|
|WHO|generic_faceted|8|30|1.0000|0.2500 (0.2500)|0.8133|0.8076|663.3|
|WHO|generic_single|4|30|0.7167|0.3583 (0.5000)|0.7389|0.6430|423.5|
|WHO|generic_single|8|30|1.0000|0.2500 (0.2500)|0.7522|0.7699|655.3|
|WHO|medical_faceted|4|30|0.7167|0.3583 (0.5000)|0.8000|0.6849|423.5|
|WHO|medical_faceted|8|30|1.0000|0.2500 (0.2500)|0.8133|0.8076|653.8|
|WHO|medical_faceted_graph|4|30|0.6333|0.3167 (0.5000)|0.8000|0.6275|385.2|
|WHO|medical_faceted_graph|8|30|1.0000|0.2500 (0.2500)|0.8133|0.7879|658.3|
|WHO|medical_single|4|30|0.6333|0.3167 (0.5000)|0.6972|0.5786|416.8|
|WHO|medical_single|8|30|1.0000|0.2500 (0.2500)|0.7106|0.7513|650.3|

All five methods and all six depths are retained in the CSVs. Case and whole-family intervals use 2,000 resamples and seed 31. Repeated query templates limit independence.

Larger evidence budgets trade precision and context size for recall. A small WHO recommendation pool makes high-depth recall easier; these results are not directly comparable to a large mixed background index without disclosing that change.

Source roles come from publisher structure, not gold labels. Background evidence remains indexed separately. Technical scope extraction and engineering references still require clinician adjudication. No clinical usability or safety claim follows from retrieval overlap alone.

This selector comparison recomputes all 100 passage orders using exact cached cross-encoder scores and the corrected corpus. Facet anchors must belong to both the original-question and fused top-2k relevance heads. No new Groq or cross-encoder calls are used; query embeddings are recomputed locally. This is exposed development, not independent validation.
