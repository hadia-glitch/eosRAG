# Faceted guidance retrieval: development results

Final evaluation remains on hold. Cases and gold IDs are unchanged. Results reuse a previously examined synthetic benchmark.

|Source|Method|Depth|N|Recall|Precision (ceiling)|MRR|nDCG|Mean source words|
|---|---|---:|---:|---:|---:|---:|---:|---:|
|AAP|generic_faceted|4|30|0.6667|0.3333 (0.5000)|0.6944|0.5888|553.2|
|AAP|generic_faceted|8|30|0.7500|0.1875 (0.2500)|0.6944|0.6229|1048.7|
|AAP|generic_single|4|30|0.4167|0.2083 (0.5000)|0.4722|0.3844|494.5|
|AAP|generic_single|8|30|0.6667|0.1667 (0.2500)|0.4960|0.4976|981.5|
|AAP|medical_faceted|4|30|0.7500|0.3750 (0.5000)|0.7222|0.6462|497.3|
|AAP|medical_faceted|8|30|0.8333|0.2083 (0.2500)|0.7222|0.6826|935.2|
|AAP|medical_faceted_graph|4|30|0.6667|0.3333 (0.5000)|0.7083|0.5817|494.7|
|AAP|medical_faceted_graph|8|30|0.8333|0.2083 (0.2500)|0.7083|0.6577|966.5|
|AAP|medical_single|4|30|0.6667|0.3333 (0.5000)|0.6667|0.5746|438.0|
|AAP|medical_single|8|30|0.9167|0.2292 (0.2500)|0.6667|0.6828|841.2|
|NICE|generic_faceted|4|40|0.5250|0.3250 (0.6687)|0.4521|0.4038|306.0|
|NICE|generic_faceted|8|40|0.7167|0.2281 (0.3344)|0.4521|0.4967|528.4|
|NICE|generic_single|4|40|0.5125|0.3250 (0.6687)|0.7500|0.5303|283.9|
|NICE|generic_single|8|40|0.6250|0.1938 (0.3344)|0.7500|0.5829|515.9|
|NICE|medical_faceted|4|40|0.5958|0.3875 (0.6687)|0.7458|0.5878|266.6|
|NICE|medical_faceted|8|40|0.7417|0.2375 (0.3344)|0.7458|0.6578|510.7|
|NICE|medical_faceted_graph|4|40|0.5958|0.3875 (0.6687)|0.7458|0.5854|278.3|
|NICE|medical_faceted_graph|8|40|0.7417|0.2375 (0.3344)|0.7458|0.6543|509.3|
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

This source-boundary amendment recomputes NICE retrieval. AAP and WHO are exact unchanged-source replays from the preceding development experiment, not independent replication. Cases and proposed gold IDs are unchanged. No Groq calls are used.
