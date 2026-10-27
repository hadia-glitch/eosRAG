# RAG improvement study

Post-hoc development results on the previously examined 100 synthetic cases; not an independent clinical test.

|Source|Embedding|Variant|N|Recall@4|Precision@4 (ceiling)|MRR@4|nDCG@4|
|---|---|---|---:|---:|---:|---:|---:|
|AAP|historical_MiniLM|dense|30|0.4167|0.2083 (0.5000)|0.4389|0.3682|
|AAP|historical_MiniLM|hybrid|30|0.5500|0.2750 (0.5000)|0.6722|0.5281|
|AAP|historical_MiniLM|hybrid_concepts|30|0.3833|0.1917 (0.5000)|0.3750|0.3162|
|AAP|historical_MiniLM|lexical|30|0.6167|0.3083 (0.5000)|0.7306|0.5846|
|AAP|sentence-transformers/all-MiniLM-L6-v2|decomposed_rrf_ce_mmr|30|0.4167|0.2083 (0.5000)|0.4167|0.3569|
|AAP|sentence-transformers/all-MiniLM-L6-v2|expanded_rrf_ce|30|0.5000|0.2500 (0.5000)|0.4583|0.4284|
|AAP|sentence-transformers/all-MiniLM-L6-v2|expanded_rrf_ce_mmr|30|0.4167|0.2083 (0.5000)|0.4167|0.3569|
|AAP|sentence-transformers/all-MiniLM-L6-v2|focused_hybrid|30|0.5833|0.2917 (0.5000)|0.5417|0.4929|
|NICE|historical_MiniLM|dense|40|0.2792|0.1812 (0.6687)|0.4000|0.2634|
|NICE|historical_MiniLM|hybrid|40|0.3792|0.2375 (0.6687)|0.4938|0.3555|
|NICE|historical_MiniLM|hybrid_concepts|40|0.3750|0.2437 (0.6687)|0.4604|0.3398|
|NICE|historical_MiniLM|lexical|40|0.2583|0.1750 (0.6687)|0.5000|0.2852|
|NICE|sentence-transformers/all-MiniLM-L6-v2|decomposed_rrf_ce_mmr|40|0.2167|0.1437 (0.6687)|0.5000|0.2714|
|NICE|sentence-transformers/all-MiniLM-L6-v2|expanded_rrf_ce|40|0.3667|0.2437 (0.6687)|0.6333|0.3816|
|NICE|sentence-transformers/all-MiniLM-L6-v2|expanded_rrf_ce_mmr|40|0.2167|0.1437 (0.6687)|0.5000|0.2714|
|NICE|sentence-transformers/all-MiniLM-L6-v2|focused_hybrid|40|0.5125|0.3250 (0.6687)|0.8250|0.5438|
|WHO|historical_MiniLM|dense|30|0.2333|0.1167 (0.5000)|0.2500|0.1898|
|WHO|historical_MiniLM|hybrid|30|0.3333|0.1667 (0.5000)|0.2694|0.2484|
|WHO|historical_MiniLM|hybrid_concepts|30|0.1667|0.0833 (0.5000)|0.1667|0.1505|
|WHO|historical_MiniLM|lexical|30|0.1667|0.0833 (0.5000)|0.2167|0.1505|
|WHO|sentence-transformers/all-MiniLM-L6-v2|decomposed_rrf_ce_mmr|30|0.1667|0.0833 (0.5000)|0.2222|0.1533|
|WHO|sentence-transformers/all-MiniLM-L6-v2|expanded_rrf_ce|30|0.2500|0.1250 (0.5000)|0.2222|0.2044|
|WHO|sentence-transformers/all-MiniLM-L6-v2|expanded_rrf_ce_mmr|30|0.1667|0.0833 (0.5000)|0.2222|0.1533|
|WHO|sentence-transformers/all-MiniLM-L6-v2|focused_hybrid|30|0.4167|0.2083 (0.5000)|0.3194|0.3129|

Gold relevance is not exhaustively clinician adjudicated. Additional valid passages may be counted as false positives. Precision ceiling = min(number of labelled relevant passages, 4)/4; recall ceiling = min(number of labelled relevant passages, 4)/number of labelled relevant passages. MRR and normalized DCG have ceiling 1 when a relevant first result exists and ideal ordering is attainable. BLEU/METEOR/ROUGE/BERTScore have no justified 0.8 clinical target: wording overlap is not clinical correctness. Fault rejection must remain high; reducing the number of detected injected faults would be a regression.

All variants, including negative comparisons, are retained. Case bootstrap intervals use 2,000 resamples, seed 31.
