# Local Ollama deployment candidates

These files prepare explicit context settings; they have not been activated in
the application or evaluated for clinical answer quality.

Ollama's OpenAI-compatible endpoint requires a model configured with an
appropriate context size; the OpenAI request itself does not set that size.
See the [official context-size instructions](https://docs.ollama.com/api/openai-compatibility#setting-the-local-context-size).

After the selected pipeline's evaluation and deployment review:

```powershell
ollama create neoguard-qwen3-16k -f deploy/ollama/Modelfile.qwen3
ollama create neoguard-mistral-16k -f deploy/ollama/Modelfile.mistral
```

Choose the evaluated alias in the local-model settings. Preserve a digest of
the resulting model and test the full evidence packet, output contract, runtime
memory and latency on the target machine. A 16k context setting alone does not
prove that every possible packet fits; input and completion budgets must be
checked together. Never silently truncate conditions or switch to a cloud model.

`backend/scripts/probe_local_transport_development.py` performs tiny JSON
transport checks on the installed base models, with cloud fallback disabled.
Those checks do not establish care-plan validity or long-context performance.
