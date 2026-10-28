import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from main import app
from ml.supplied_model import (CONTRACT_VERSION,NUMERIC,CATEGORIES,KEYS,
    SuppliedPredictionRequest,load_supplied_model,supplied_status)
from ml.research_cohort import portable_probability
from config import Settings
from services.security import Principal,require_user


def payload():
    return {'input_contract_version':CONTRACT_VERSION,'purpose':'research','age_hours':12.,'reviewed_inputs':True,
            'values':{'Gestational_Age':36.,'Birth_Weight':3.2,'Sex':'Male','Postnatal_Age':0.,'Delivery_Mode':'Vaginal',
                      'Apgar':8.,'HR':150.,'Resp':50.,'Temp':36.8,'SpO2':97.,'BP':45.,'Oxygen':21.,
                      'WBC':12.,'CRP':5.,'PCT':.7,'Platelets':220.,'Lactate':1.5,'Hemoglobin':14.5}}


def test_installed_model_uses_fitted_preprocessing_and_exact_export():
    settings=Settings(_env_file=None)
    model=load_supplied_model(settings.supplied_model_dir)
    request=SuppliedPredictionRequest.model_validate(payload())
    x=np.array([model.transform(request.values)])
    expected=portable_probability(model.a,x)[0]
    result=model.predict(request)
    assert result['status']=='predicted'
    assert result['clinical_use'] is False
    assert result['probability']==pytest.approx(expected,abs=1e-8)
    assert result['missing_features']==[]
    details=result['probability_details']
    assert details['raw_model_score']==model.raw_probability(request.values)
    assert details['calibrated_dataset_score']==result['probability']
    assert details['clinical_probability_available'] is False
    metadata=supplied_status(settings)
    assert {f['name'] for f in metadata['input_contract']}==KEYS
    assert metadata['clinical_ready'] is False
    fixture=Path(__file__).resolve().parents[2]/'test/fixtures/research_model_contract.json'
    assert json.loads(fixture.read_text())['input_contract']==metadata['input_contract']


def test_extreme_demo_score_exposes_sharpening_without_clipping_or_clinical_claim():
    root=Path(__file__).resolve().parents[2]
    demo={'research_request':json.loads((root/'data/synthetic_eos_v2/probability_audit_input.json').read_text())}
    model=load_supplied_model(Settings(_env_file=None).supplied_model_dir)
    result=model.predict(SuppliedPredictionRequest.model_validate(demo['research_request']))
    details=result['probability_details']
    assert .99<details['raw_model_score']<.999
    assert result['probability']>.999999
    assert details['extreme_score'] is True
    assert details['calibration_slope']>1
    assert any('saturation' in w for w in result['warnings'])
    assert result['clinical_use'] is False


@pytest.mark.parametrize('change',[
    lambda p:p.update(name='synthetic'),
    lambda p:p.update(purpose='clinical'),
    lambda p:p.update(age_hours=72.),
    lambda p:p.update(reviewed_inputs=False),
    lambda p:p['values'].update(MRN='synthetic'),
    lambda p:p['values'].update(HR=True),
    lambda p:p['values'].update(HR='150'),
    lambda p:p['values'].update(PCT=float('nan')),
    lambda p:p['values'].update(Postnatal_Age=2),
    lambda p:p['values'].update(WBC=12000),
    lambda p:p['values'].update(Sex=None),
])
def test_invalid_or_identifying_inputs_are_rejected(change):
    p=payload();change(p)
    with pytest.raises(ValidationError):SuppliedPredictionRequest.model_validate(p)


def test_missing_and_outside_support_are_visible():
    model=load_supplied_model(Settings(_env_file=None).supplied_model_dir)
    p=payload();p['values']['WBC']=None
    result=model.predict(SuppliedPredictionRequest.model_validate(p))
    assert result['status']=='predicted' and 'WBC' in result['imputed_features']
    p['values']['HR']=300
    result=model.predict(SuppliedPredictionRequest.model_validate(p))
    assert result['status']=='abstained' and result['probability'] is None
    p=payload()
    for field in ['WBC','CRP','PCT','Platelets','Lactate','Hemoglobin']:p['values'][field]=None
    result=model.predict(SuppliedPredictionRequest.model_validate(p))
    assert result['status']=='abstained' and 'development-matched limit' in ' '.join(result['warnings'])


def test_research_endpoint_auth_and_optional_research_audit(monkeypatch):
    import production_api
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        assert client.post('/api/v1/research/model/predict',json=payload()).status_code==401
        app.dependency_overrides[require_user]=lambda:Principal('synthetic-test')
        monkeypatch.setattr(production_api,'record_decision',lambda *a,**kw:(_ for _ in ()).throw(HTTPException(503,'Unavailable')))
        monkeypatch.setattr(production_api,'get_settings',lambda:Settings(_env_file=None,research_prediction_requires_audit=False))
        r=client.post('/api/v1/research/model/predict',json=payload())
        assert r.status_code==200 and r.json()['status']=='predicted'
        assert r.json()['audit_status']=='unavailable' and r.json()['clinical_use'] is False
        monkeypatch.setattr(production_api,'get_settings',lambda:Settings(_env_file=None,research_prediction_requires_audit=True))
        assert client.post('/api/v1/research/model/predict',json=payload()).status_code==503
    app.dependency_overrides.clear()


def test_clinical_snapshot_rejects_identifiers_before_context_loading():
    from schemas import RiskPayload
    for patient in [{'name':'synthetic'},{'mrn':'synthetic'},{'notes':'synthetic'},
                    {'respiratory_distress':'free text identifying a person'}]:
        with pytest.raises(ValidationError):RiskPayload.model_validate({'patient':patient})
    from production_api import EvidenceAiRequest
    from schemas import CarePlanRequest
    with pytest.raises(ValidationError):
        EvidenceAiRequest.model_validate({'query':'EOS','patient_context':{'mrn':'synthetic'}})
    with pytest.raises(ValidationError):
        CarePlanRequest.model_validate({'risk_result':{'patient':{'age_hours':6}},'previous_assessments':[{'notes':'private fixture'}]})


def test_flutter_fixture_has_real_server_prediction():
    root=Path(__file__).resolve().parents[2]
    fixture=json.loads((root/'test/fixtures/research_prediction_case.json').read_text())
    model=load_supplied_model(Settings(_env_file=None).supplied_model_dir)
    result=model.predict(SuppliedPredictionRequest.model_validate(fixture['request']))
    assert result['probability']==pytest.approx(fixture['response']['probability'],abs=1e-12)
