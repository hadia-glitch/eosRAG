# Additional cross-encoder development ablation

Same exposed 100 synthetic cases and frozen candidate pools. All declared variants are retained. No new Groq calls or final evaluation.

|Source|Method|Depth|Completed/total|Recall|MRR|Precision|nDCG|
|---|---|---:|---:|---:|---:|---:|---:|
|NICE|bge_only|4|40/40|0.5875|0.7375|0.3688|0.5548|
|NICE|bge_only|8|40/40|0.6583|0.7375|0.2062|0.5874|
|NICE|bge_upstream_rrf_mmr|4|40/40|0.6250|0.7375|0.3875|0.5804|
|NICE|bge_upstream_rrf_mmr|8|40/40|0.6917|0.7375|0.2188|0.6153|
|NICE|bge_consensus_rrf_mmr|4|40/40|0.6583|0.7875|0.4125|0.6248|
|NICE|bge_consensus_rrf_mmr|8|40/40|0.8333|0.8000|0.2719|0.7094|
|NICE|previous_consensus|4|40/40|0.6792|0.7875|0.4375|0.6437|
|NICE|previous_consensus|8|40/40|0.8333|0.8075|0.2719|0.7225|
|AAP|bge_only|4|30/30|0.4167|0.4167|0.2083|0.3773|
|AAP|bge_only|8|30/30|0.5000|0.4375|0.1250|0.4096|
|AAP|bge_upstream_rrf_mmr|4|30/30|0.5000|0.5833|0.2500|0.4591|
|AAP|bge_upstream_rrf_mmr|8|30/30|0.6667|0.6071|0.1667|0.5327|
|AAP|bge_consensus_rrf_mmr|4|30/30|0.5000|0.5833|0.2500|0.4795|
|AAP|bge_consensus_rrf_mmr|8|30/30|0.8333|0.6405|0.2083|0.6249|
|AAP|previous_consensus|4|30/30|0.7500|0.7083|0.3750|0.6973|
|AAP|previous_consensus|8|30/30|0.8333|0.7292|0.2083|0.7295|
|WHO|bge_only|4|30/30|0.8333|0.7556|0.4167|0.7251|
|WHO|bge_only|8|30/30|1.0000|0.7556|0.2500|0.7987|
|WHO|bge_upstream_rrf_mmr|4|30/30|0.7500|0.7833|0.3750|0.6874|
|WHO|bge_upstream_rrf_mmr|8|30/30|1.0000|0.7833|0.2500|0.8029|
|WHO|bge_consensus_rrf_mmr|4|30/30|0.8000|0.7667|0.4000|0.7280|
|WHO|bge_consensus_rrf_mmr|8|30/30|1.0000|0.7800|0.2500|0.8197|
|WHO|previous_consensus|4|30/30|0.8000|0.8500|0.4000|0.7586|
|WHO|previous_consensus|8|30/30|1.0000|0.8633|0.2500|0.8482|

Case and whole-family bootstrap intervals use 2,000 resamples, seed 31. Candidate recall ceilings, source-word budgets and negative paired effects remain in CSVs.
These are relevance-ranking outcomes, not clinical answer-usability, safety, or effectiveness results. Model weights remain outside the repository.
