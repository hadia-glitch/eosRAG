import json
from pathlib import Path
import numpy as np
from config import Settings
from ml.supplied_model import load_supplied_model,SuppliedPredictionRequest
from ml.explanations import matrix_probability,explain


def test_shap_explains_the_served_calibrated_probability():
    fixture=json.loads((Path(__file__).resolve().parents[2]/'test/fixtures/research_prediction_case.json').read_text())
    request=SuppliedPredictionRequest.model_validate(fixture['request'])
    model=load_supplied_model(Settings(_env_file=None).supplied_model_dir)
    result=explain(model,request)
    assert 'SHAP KernelExplainer' in result['contribution_method']
    assert result['probability']==fixture['response']['probability']
    assert result['shap']['additivity_error']<1e-5
    assert len(result['contributions'])==18
    assert abs(result['shap']['baseline_probability']+sum(c['contribution'] for c in result['contributions'])-result['probability'])<1e-5
