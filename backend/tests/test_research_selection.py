import hashlib,json,math
from types import SimpleNamespace
import pytest
from config import Settings
from ml.research_selection import status,predict_pic
from ml.inference import ModelUnavailable
from ml.longitudinal_inputs import LongitudinalInputs,CONTEXT


def setup(tmp_path):
    a={'kind':'logistic','feature_version':'pic-longitudinal-v1','clinical_eos_eligible':False,'validation_status':'research_only',
       'group':'snapshot','model_version':'test-pic','calibration':{'slope':1.,'intercept':0.},
       'preprocessing':{'indices':[0,3],'features':['age_hours','heart_rate__last'],'median':[10.,150.],'mean':[10.,150.],'scale':[10.,10.]},
       'coefficients':[.2,.3,.1,.1],'intercept':-3.}
    raw=json.dumps(a).encode();(tmp_path/'dynamic_model.json').write_bytes(raw)
    (tmp_path/'dynamic_manifest.json').write_text(json.dumps({'artifact_sha256':hashlib.sha256(raw).hexdigest()}))
    return SimpleNamespace(research_ml_model='pic',pic_model_dir=str(tmp_path))


def request():
    return LongitudinalInputs.model_validate({'sequence':{'input_contract_version':'pic-longitudinal-v1','purpose':'research','age_hours':10.,'observations':[
        {'age_hours':10.,'available_age_hours':10.,'field':'heart_rate','value':160.},
        {'age_hours':10.,'available_age_hours':10.,'field':'respiratory_rate','value':60.}]},'context':{k:None for k in CONTEXT}})


def test_explicit_pic_choice_serves_real_parameters_without_clinical_probability(tmp_path):
    s=setup(tmp_path);r=predict_pic(request(),s)
    assert status(s)['input_mode']=='longitudinal'
    assert r['research_score']==pytest.approx(1/(1+math.exp(2.7)))
    assert r['clinical_probability_available'] is False and r['clinical_ready'] is False
    assert all(not v['used_in_real_pic_model'] for v in r['context_usage'].values())


def test_other_model_choice_and_corrupt_artifact_fail_closed(tmp_path):
    s=setup(tmp_path);s.research_ml_model='kaggle'
    with pytest.raises(ModelUnavailable,match='not selected'):predict_pic(request(),s)
    s.research_ml_model='pic';(tmp_path/'dynamic_model.json').write_text('{}')
    assert status(s)['available'] is False


def test_selector_rejects_unknown_model_and_requires_recent_vitals(tmp_path):
    with pytest.raises(ValueError):Settings(_env_file=None,research_ml_model='unknown')
    s=setup(tmp_path);r=request();r.sequence.observations=r.sequence.observations[:1]
    with pytest.raises(ModelUnavailable,match='two distinct'):predict_pic(r,s)


def test_selected_pic_api_requires_auth_and_rejects_kaggle_payload(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    import production_api as api
    from services.security import require_user
    setup(tmp_path)
    settings=Settings(_env_file=None,research_ml_model='pic',pic_model_dir=str(tmp_path))
    monkeypatch.setattr(api,'get_settings',lambda:settings)
    monkeypatch.setattr(api,'record_decision',lambda *args:None)
    client=TestClient(api.app)
    assert client.get('/api/v1/research/model/status').status_code==401
    previous=api.app.dependency_overrides.copy()
    api.app.dependency_overrides[require_user]=lambda:SimpleNamespace(user_id='research-test')
    try:
        assert client.get('/api/v1/research/model/status').json()['selected_model']=='pic'
        c=client.get('/api/v1/research/longitudinal/contract').json()
        assert c['prediction_endpoint']=='/api/v1/research/longitudinal/predict'
        result=client.post(c['prediction_endpoint'],json=request().model_dump())
        assert result.status_code==200 and result.json()['clinical_probability_available'] is False
        case={'research_request':json.loads((__import__('pathlib').Path(__file__).parents[2]/'data/synthetic_eos_v2/probability_audit_input.json').read_text())}
        assert client.post('/api/v1/research/model/predict',json=case['research_request']).status_code==409
        wrong=request().model_dump();wrong['sequence']['purpose']='clinical'
        assert client.post(c['prediction_endpoint'],json=wrong).status_code==422
    finally:
        api.app.dependency_overrides.clear();api.app.dependency_overrides.update(previous)
