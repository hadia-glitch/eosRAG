# Expanded evaluation: 100 synthetic cases

NICE 40; AAP 30; WHO 30. The original 18 cases remain unchanged. Results are engineering measurements; clinician adjudication is pending.

All intervals use 2,000 bootstrap resamples, seed 31. Case intervals resample cases; family intervals resample all members of a scenario family together. Six authored families are too few for broad population inference.

|Guideline|Method|Recall@4 (case 95% CI)|MRR@4 (case 95% CI)|
|---|---|---|---|
|NICE|lexical|0.258333 [0.179167, 0.341667]|0.500000 [0.358333, 0.637500]|
|NICE|dense|0.279167 [0.191667, 0.370833]|0.400000 [0.287500, 0.525000]|
|NICE|hybrid|0.379167 [0.275000, 0.483333]|0.493750 [0.362448, 0.622969]|
|NICE|hybrid_concepts|0.375000 [0.287500, 0.466667]|0.460417 [0.337500, 0.583333]|
|AAP|lexical|0.616667 [0.500000, 0.733333]|0.730556 [0.602708, 0.850000]|
|AAP|dense|0.416667 [0.300000, 0.550000]|0.438889 [0.294444, 0.588889]|
|AAP|hybrid|0.550000 [0.433333, 0.666667]|0.672222 [0.527778, 0.811111]|
|AAP|hybrid_concepts|0.383333 [0.266667, 0.516667]|0.375000 [0.250000, 0.508333]|
|WHO|lexical|0.166667 [0.083333, 0.250000]|0.216667 [0.097222, 0.358403]|
|WHO|dense|0.233333 [0.133333, 0.333333]|0.250000 [0.130556, 0.383333]|
|WHO|hybrid|0.333333 [0.216667, 0.466667]|0.269444 [0.155556, 0.405556]|
|WHO|hybrid_concepts|0.166667 [0.033333, 0.300000]|0.166667 [0.033333, 0.300000]|

Full precision, family intervals and paired contrasts are in the CSV tables. Negative differences are retained.

Stage status: primary metrics complete; fault tests 36/36; judge executions 100/100; paired backbone/resolution executions 200/200.

The full declared study is complete.

The identical initial draft forms both primary arms. Verification changes release/withholding, not the wording of released drafts. Released-only alignment must be read beside release coverage.

WHO has a broader age/resource-setting scope. Its 0-72-hour subset is evaluated separately; absence of a WHO recommendation is not filled using NICE or AAP guidance. The technical graph is fixed concept expansion, not proof of causal reasoning or live Neo4j performance.

The 114-case retrieval-only prototype and the WHO duplicate-index amendment remain archived. No RRF, k, encoder, concept mapping or generation prompt was tuned using the expanded results. Historical/current verifier source drift is logged in protocol.json.

## Primary paired release experiment

|Guideline|Arm|Emitted / quality N|Corpus BLEU-4|METEOR|ROUGE-L|DistilBERT F1|RoBERTa F1|
|---|---|---:|---:|---:|---:|---:|---:|
|NICE|without_verification|34/40|0.028713|0.233601|0.152407|0.677498|0.723052|
|NICE|verified_all_cases|5/40|2.366e-06|0.028005|0.028669|0.100375|0.107799|
|NICE|released_only|5/40|0.021696|0.224037|0.229350|0.802997|0.862394|
|NICE|generated_only|34/40|0.028713|0.274824|0.179303|0.797057|0.850650|
|AAP|without_verification|30/30|0.013815|0.273767|0.157379|0.800679|0.846394|
|AAP|verified_all_cases|1/30|1.565e-09|0.010837|0.008235|0.028084|0.029339|
|AAP|released_only|1/30|0.042849|0.325124|0.247059|0.842517|0.880169|
|AAP|generated_only|30/30|0.013815|0.273767|0.157379|0.800679|0.846394|
|WHO|without_verification|30/30|0.010893|0.240703|0.133626|0.783506|0.838893|
|WHO|verified_all_cases|2/30|7.308e-12|0.013593|0.012971|0.055487|0.058033|
|WHO|released_only|2/30|0.043451|0.203901|0.194561|0.832300|0.870494|
|WHO|generated_only|30/30|0.010893|0.240703|0.133626|0.783506|0.838893|

All-case empty outputs affect corpus BLEU brevity as well as overlap. Conditional alignment does not establish clinical correctness or a rewriting benefit.

|Guideline|Paired N|Released / N|DistilBERT F1 difference|Case 95% CI|Family 95% CI|
|---|---:|---:|---:|---|---|
|NICE|40|5/40|-0.577124|[-0.678648, -0.474184]|[-0.718519, -0.445538]|
|AAP|30|1/30|-0.772595|[-0.803602, -0.715657]|[-0.803246, -0.722321]|
|WHO|30|2/30|-0.728020|[-0.781884, -0.648929]|[-0.780342, -0.628458]|

## Blinded model-judge proxies

|Guideline|Arm|Judged / quality N|Grounding|Patient fidelity|Actionability|Observed unsafe claims|
|---|---|---:|---:|---:|---:|---:|
|NICE|without_verification|34/40|3.852941|3.911765|3.823529|15|
|NICE|with_verification|5/40|4.800000|3.800000|3.400000|0|
|AAP|without_verification|30/30|4.333333|4.233333|4.533333|5|
|AAP|with_verification|1/30|5.000000|5.000000|5.000000|0|
|WHO|without_verification|30/30|4.500000|4.500000|4.333333|3|
|WHO|with_verification|2/30|5.000000|5.000000|3.500000|0|

The judge shares the generator/auditor model. Released-only means are selection comparisons, not evidence that verification improved the same text. Ratings are not measured clinician usability.

## Fault challenge

|Guideline|Completed / planned|Structural reject|Semantic reject|Invalid review|Verified emitted|
|---|---:|---:|---:|---:|---:|
|NICE|12/12|3|9|0|0|
|AAP|12/12|3|8|1|0|
|WHO|12/12|3|9|0|0|

## Additional backbones and bounded resolution

Completed counts.

|Model|Guideline|Paired / planned|Baseline releases|One-repair releases|Attempts|Release-fraction difference|
|---|---|---:|---:|---:|---:|---:|
|openai/gpt-oss-20b|NICE|40/40|1|2|2|0.025000|
|openai/gpt-oss-20b|AAP|30/30|0|0|2|0.000000|
|openai/gpt-oss-20b|WHO|30/30|0|0|5|0.000000|
|qwen/qwen3.8-27b|NICE|40/40|23|24|1|0.025000|
|qwen/qwen3.8-27b|AAP|30/30|26|26|0|0.000000|
|qwen/qwen3.8-27b|WHO|30/30|27|27|0|0.000000|

Full case/family intervals, original-18 controls and quoted historical values are in the CSV tables. The clinician bundle contains unfilled adjudication fields; no clinician acceptance is inferred.
