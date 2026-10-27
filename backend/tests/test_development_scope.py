"""Known clinical scope and final-evaluation gate regressions."""
import copy
import json
import math
import pytest
from rag.clinical_scope import applicable
from rag.verification_v4 import task_aware_auditor
from scripts.check_development_readiness import check


def test_outpatient_and_hospital_recommendations_are_not_interchangeable():
    scope={'care_setting':['non_hospital'],'postnatal_age_hours':[0,1439]}
    assert applicable(scope,{'care_setting':'primary_health_clinic','age_hours':12})
    assert not applicable(scope,{'care_setting':'neonatal_unit','age_hours':12})


def test_known_minimum_gestation_and_age_band_are_enforced():
    scope={'care_setting':['hospital_birth'],'gestational_age_weeks':[35,None],'postnatal_age_hours':[0,72]}
    assert applicable(scope,{'care_setting':'postnatal_ward','gestational_age_weeks':38,'age_hours':12})
    assert not applicable(scope,{'care_setting':'hospital','gestational_age_weeks':34,'age_hours':12})
    assert not applicable(scope,{'care_setting':'hospital','age_hours':12})
    assert not applicable({'postnatal_age_hours':[168,1439]},{'age_hours':12})


def test_question_and_task_reach_the_auditors_without_changing_facts():
    patient={'age_hours':36,'culture_status':'unknown'}
    packet={'evaluation_question':'Why are stopping conditions NOT established?','task_mode':'care_plan'}
    source={'patient':patient,'history':[],'evidence':[{'id':'E1','text':'Stop only if all required conditions are met.'}]}
    p={'source_packet':source,'claims':[{'id':'C1','text':'Missing data means culture is normal.','support':[{'evidence_id':'E1'}]}]}
    def llm(prompt,settings,**kw):
        data=json.loads(prompt)
        assert data['source_packet']['patient']==patient
        assert data['source_packet']['evaluation_question']==packet['evaluation_question']
        assert data['source_packet']['task_mode']=='care_plan'
        assert data['claims'][0]['text']=='Missing data means culture is normal.'
        assert 'Still reject' in data['task_context_contract']
        return {}
    task_aware_auditor(llm,packet)(json.dumps(p),None,role='safety auditor')


def valid_report():
    return {'retrieval':{g:{'recall_at_4':.8,'mrr_at_4':.8,'complete':True} for g in ['NICE','AAP','WHO']},
            'generation':{g:{'valid_fraction':.9,'usable_reviewed_coverage':.8,'families_covered':6} for g in ['NICE','AAP','WHO']},
            'safety':{'fault_cases_completed':36,'unsafe_fault_releases':0},'complete_audits':True,
            'scope_regressions_passed':True,'backend_regressions_passed':True,'config_pinned':True}


def test_good_nice_scores_cannot_mask_bad_who_or_unsafe_fault():
    r=valid_report();r['retrieval']['WHO']['recall_at_4']=.3
    assert not check(r)['final_evaluation_allowed']
    r=valid_report();r['safety']['unsafe_fault_releases']=1
    assert not check(r)['final_evaluation_allowed']


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),True,None,1.1])
def test_missing_or_invalid_metrics_cannot_open_final_gate(bad):
    r=valid_report();r['retrieval']['AAP']['mrr_at_4']=bad
    assert not check(r)['final_evaluation_allowed']


def test_query_facets_describe_observed_changes_without_a_risk_rule():
    from rag.history_queries import observed_queries
    q=observed_queries({'respiratory_rate':72,'spo2':91,'crp_level':4},
        [{'measurements':{'respiratory_rate':48,'spo2':98,'crp_level':12}}])
    assert any('respiratory rate increasing' in s for s in q)
    assert any('oxygen saturation decreasing' in s for s in q)
    assert any('C-reactive protein decreasing' in s for s in q)
    assert not any('diagnosed' in s or 'high risk' in s for s in q)
    assert observed_queries({'respiratory_rate':72},[])==[]


def test_plan_search_does_not_inject_another_guidelines_drug_or_stopping_rule():
    from rag.production_retrieval import PLAN_QUERIES
    text=' '.join(PLAN_QUERIES).lower()
    assert 'benzylpenicillin' not in text and '36 hours' not in text


def test_rag_setting_is_allowlisted_and_does_not_enter_the_ml_feature_contract():
    from services.clinical_pipeline import sanitize_snapshot
    from ml.features import FEATURE_NAMES
    assert sanitize_snapshot({'care_setting':'primary_health_clinic'})=={'care_setting':'primary_health_clinic'}
    assert sanitize_snapshot({'care_setting':'unstructured personal notes'})=={}
    assert sanitize_snapshot({'care_setting':{'notes':'unstructured'}})=={}
    assert 'care_setting' not in FEATURE_NAMES


def test_reviewed_hospital_source_cannot_be_applied_to_a_clinic_patient(tmp_path):
    from config import Settings
    from rag.evidence_policy import admit_chunk
    doc={'file_name':'fixture.pdf','approved_for_generation':True,'reviewed_by':'unit-test fixture',
         'reviewed_at':'2026-10-27','status':'current','sha256':'fixture-hash','url':'https://example.invalid',
         'version':'fixture','source':'WHO','min_ga':22,'max_ga':44,'min_age_hours':0,'max_age_hours':72,
         'care_setting':'hospital'}
    path=tmp_path/'manifest.json';path.write_text(json.dumps({'documents':[doc]}))
    settings=Settings(_env_file=None,evidence_manifest_path=str(path))
    row={'version':'fixture','metadata':{'file_name':'fixture.pdf','document_sha256':'fixture-hash'}}
    patient={'age_hours':12,'gestational_age_weeks':38,'care_setting':'primary_health_clinic'}
    assert not admit_chunk(row,settings,'WHO',patient)
    doc['care_setting']='non_hospital';path.write_text(json.dumps({'documents':[doc]}))
    assert admit_chunk(row,settings,'WHO',patient)
    doc['mixed_population']=True;path.write_text(json.dumps({'documents':[doc]}))
    assert not admit_chunk(row,settings,'WHO')


def test_neonatal_culture_and_treatment_clocks_cannot_be_replaced_by_age():
    from schemas import PatientSnapshot
    from pydantic import ValidationError
    from services.clinical_pipeline import sanitize_snapshot
    from ml.features import FEATURE_NAMES,Observation
    r=PatientSnapshot(age_hours=36,culture_status='negative',culture_incubation_hours=24,antibiotic_exposure_hours=20)
    facts=sanitize_snapshot(r.model_dump())
    assert facts['culture_incubation_hours']==24 and facts['antibiotic_exposure_hours']==20
    assert 'culture_incubation_hours' not in FEATURE_NAMES and 'antibiotic_exposure_hours' not in FEATURE_NAMES
    with pytest.raises(ValidationError):PatientSnapshot(age_hours=12,culture_incubation_hours=36)
    with pytest.raises(ValidationError):Observation(age_hours=12,values={'culture_incubation_hours':6})
    with pytest.raises(ValidationError):PatientSnapshot(culture_status='positive',blood_culture_positive=False)
    assert sanitize_snapshot({'blood_culture_positive':False})['culture_status']=='unknown'
    assert sanitize_snapshot({'blood_culture_positive':True})['culture_status']=='positive'
    assert sanitize_snapshot({'blood_culture_positive':False,'culture_status':'negative',
                              'care_setting':'hospital'})=={
        'blood_culture_positive':False,'culture_status':'negative','care_setting':'hospital'}


@pytest.mark.parametrize('value',[True,'36',float('nan'),float('inf')])
def test_patient_measurements_reject_coercion_and_nonfinite_values(value):
    from schemas import PatientSnapshot
    from pydantic import ValidationError
    with pytest.raises(ValidationError):PatientSnapshot(age_hours=value)


def test_patient_setting_cannot_bypass_hospital_only_plan_scope(monkeypatch):
    from services import clinical_pipeline as cp
    from rag.production_retrieval import Retrieval
    from config import Settings
    monkeypatch.setattr(cp,'retrieve_plan',lambda *a,**k: (_ for _ in ()).throw(AssertionError('No outpatient retrieval')))
    monkeypatch.setattr(cp,'run_verification',lambda *a,**k: (_ for _ in ()).throw(AssertionError('No outpatient generation')))
    plan=cp.produce({'patient':{'age_hours':12,'gestational_age_weeks':38,'care_setting':'non_hospital'}},
                    'WHO',Settings(_env_file=None,allow_clinical_cloud_processing=True))
    assert plan.verification_status=='abstained'


def test_passage_scope_cannot_be_replaced_by_broad_document_approval(tmp_path):
    from config import Settings
    from rag.evidence_policy import admit_chunk
    doc={'file_name':'fixture.pdf','approved_for_generation':True,'reviewed_by':'test fixture',
         'reviewed_at':'2026-10-28','status':'current','sha256':'fixture-hash','url':'https://example.invalid',
         'version':'fixture','source':'WHO','min_ga':22,'max_ga':44,'min_age_hours':0,'max_age_hours':1439,
         'care_setting':'non_hospital','mixed_population':True}
    path=tmp_path/'manifest.json';path.write_text(json.dumps({'documents':[doc]}))
    settings=Settings(_env_file=None,evidence_manifest_path=str(path))
    row={'version':'fixture','metadata':{'file_name':'fixture.pdf','document_sha256':'fixture-hash',
          'population':'neonatal_all_onset','scope_reviewed_by':'test fixture','scope_reviewed_at':'2026-10-28'}}
    patient={'age_hours':12,'gestational_age_weeks':38,'care_setting':'non_hospital'}
    assert not admit_chunk(row,settings,'WHO',patient)
    row['metadata']['scope']={'gestational_age_weeks':[None,None],'postnatal_age_hours':[168,1439],
                             'care_setting':['non_hospital']}
    assert not admit_chunk(row,settings,'WHO',patient)
    assert not admit_chunk(row,settings,'WHO')
    row['metadata']['scope']['postnatal_age_hours']=[0,143]
    assert admit_chunk(row,settings,'WHO',patient)
    row['metadata']['scope']['gestational_age_weeks']=[39,None]
    assert not admit_chunk(row,settings,'WHO',patient)
    row['metadata']['scope']['care_setting']=[{'unexpected':'object'}]
    assert not admit_chunk(row,settings,'WHO',patient)


def test_cloud_processing_guard_precedes_retrieval(monkeypatch):
    from services import clinical_pipeline as cp
    from config import Settings
    monkeypatch.setattr(cp,'retrieve_plan',lambda *a,**k: (_ for _ in ()).throw(AssertionError('No unauthorized retrieval')))
    plan=cp.produce({'patient':{'age_hours':12,'gestational_age_weeks':38,'care_setting':'hospital'}},
                    'NICE',Settings(_env_file=None,allow_clinical_cloud_processing=False))
    assert plan.verification_status=='abstained'
