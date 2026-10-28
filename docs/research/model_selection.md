# Choosing the application's research predictor

Set **backend/.env**, then restart the FastAPI process:

```dotenv
RESEARCH_ML_MODEL=kaggle
```

Supported choices are `kaggle` and `pic`. The default is `kaggle`. This is a server setting; Flutter reads the selected model and input mode from the model-status API. Restart the backend and reopen the assessment after changing the setting. The selected research model takes precedence in the assessment card; a missing selected artifact does not silently select another model.

- `kaggle`: the installed single-assessment supplied-label forest. The app requests its 18 documented inputs and exposes the existing SHAP waterfall.
- `pic`: the locally trained longitudinal logistic research artifact. The model card opens the timed-observation form. Supply measurement and availability age, with at least two distinct recent vital signs. The server applies the actual trained preprocessing and coefficients and returns an **uncalibrated research score**, observed trends and linear log-odds contributions. Maternal context is retained but has no learned PIC effect. These contributions are not labelled probability-scale SHAP.

PIC reads `dynamic_model.json` and `dynamic_manifest.json` from `PIC_MODEL_DIR`. Its default is the workspace's ignored `data/picdb_private` directory. For a server elsewhere, configure that directory explicitly and provision the artifacts under the source agreement. Missing or mismatched artifacts fail closed; there is no silent Kaggle fallback. Restricted real-data weights are not bundled or pushed to GitHub.

Neither choice is clinically validated. This switch does not enable `CLINICAL_USE_ENABLED`, the clinical prediction endpoint, treatment eligibility, or a blended maternal/neonatal probability. Research outputs must not confirm/exclude sepsis or determine care. The existing timing/input preview remains available without calculating a score.

The separate synthetic recording entry point is deliberately pinned to Kaggle regardless of this selection. It contains no PIC selector or PIC prediction screen in its recording. Its visible recording controls are disabled unless explicitly built with `DEMO_SHOW_CONTROLS=true`.
