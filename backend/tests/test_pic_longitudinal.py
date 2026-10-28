import pytest
from pydantic import ValidationError
from ml.dynamic_features import DynamicRequest,features
from ml.pic_dataset import outcome,available_events
from ml.longitudinal_inputs import LongitudinalInputs,CONTEXT,contract,preview


def e(time,value,known=None,field='heart_rate'):
    return {'age_hours':float(time),'available_age_hours':float(time if known is None else known),'field':field,'value':float(value)}


def test_future_measurements_and_late_entries_cannot_enter_a_landmark():
    events=[e(1,120),e(2,130),e(3,200),e(1.5,180,known=4)]
    f=features(2.,None,events)
    assert f['heart_rate__last']==130 and f['heart_rate__count']==2
    assert f['heart_rate__delta']==10 and f['heart_rate__slope_per_hour']==10
    with pytest.raises(ValidationError,match='Future'):
        DynamicRequest(input_contract_version='pic-longitudinal-v1',purpose='research',age_hours=2.,observations=events)


def test_actual_elapsed_time_and_order_define_trends_not_row_order():
    f=features(7.,None,[e(7,150),e(1,120),e(3,130)])
    assert f['heart_rate__slope_per_hour']==pytest.approx(5.)
    assert f['heart_rate__delta']==30
    assert f['respiratory_rate__last'] is None
    assert f['respiratory_rate__count']==0


def test_missing_organism_fungus_and_preliminary_results_are_not_controls():
    assert outcome([None]) is None
    assert outcome(['No fungus cultured']) is None
    assert outcome(['Gram positive cocci (G+C)']) is None
    assert outcome(['Staphylococcus epidermidis']) is None
    assert outcome(['Cultured for 5 days without bacteria, fungus growth'])==0
    assert outcome(['Escherichia coli','No fungus cultured'])==1


def test_late_or_duplicate_observation_is_not_silently_treated_as_current():
    with pytest.raises(ValidationError,match='Duplicate'):
        DynamicRequest(input_contract_version='pic-longitudinal-v1',purpose='research',age_hours=4.,observations=[e(1,120),e(1,130)])
    f=features(10.,None,[e(1,120)])
    assert f['heart_rate__last'] is None and f['heart_rate__recency_hours']==9


def test_unknown_maternal_inputs_remain_unknown_and_poor_model_is_withheld():
    request=LongitudinalInputs(sequence={'input_contract_version':'pic-longitudinal-v1','purpose':'research',
        'age_hours':4.,'observations':[e(1,120),e(4,135)]},context={k:None for k in CONTEXT})
    result=preview(request)
    assert result['research_score'] is None and result['prediction_status']=='withheld_quality_gate'
    assert result['context_usage']['gbs_positive']['recorded'] is False
    assert all(not r['used_in_real_pic_model'] for r in result['context_usage'].values())
    fields={f['key'] for f in contract()['sequence_fields']}
    assert 'measured_weight_kg' in fields and 'birth_weight_kg' not in fields
    assert {'heart_rate','pulse_rate'}<=fields


def test_identifiers_numeric_booleans_and_extra_context_are_rejected():
    base={'sequence':{'input_contract_version':'pic-longitudinal-v1','purpose':'research','age_hours':4.,'observations':[e(1,120)]},'context':{k:None for k in CONTEXT}}
    with pytest.raises(ValidationError):LongitudinalInputs.model_validate({**base,'patient_name':'Identifier'})
    with pytest.raises(ValidationError):LongitudinalInputs.model_validate({**base,'context':{**base['context'],'gbs_positive':0.}})
    with pytest.raises(ValidationError):LongitudinalInputs.model_validate({**base,'context':{**base['context'],'mrn':123.}})


def test_authenticated_preview_endpoint_withholds_new_risk_and_rejects_phi(monkeypatch):
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from production_api import app
    from services.security import require_user
    client=TestClient(app)
    url='/api/v1/research/longitudinal/contract'
    assert client.get(url).status_code==401
    previous=app.dependency_overrides.copy()
    app.dependency_overrides[require_user]=lambda:SimpleNamespace(user_id='research-test')
    try:
        assert client.get(url).json()['prediction_status']=='withheld_quality_gate'
        body={'sequence':{'input_contract_version':'pic-longitudinal-v1','purpose':'research','age_hours':4.,
                          'observations':[e(1,120),e(4,140)]},'context':{k:None for k in CONTEXT}}
        result=client.post('/api/v1/research/longitudinal/preview',json=body)
        assert result.status_code==200 and result.json()['research_score'] is None
        assert result.json()['trends']['heart_rate']['delta']==20
        bad=client.post('/api/v1/research/longitudinal/preview',json={**body,'patient_name':'identifier'})
        assert bad.status_code==422
    finally:
        app.dependency_overrides.clear();app.dependency_overrides.update(previous)
