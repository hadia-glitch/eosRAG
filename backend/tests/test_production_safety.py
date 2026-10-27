import json
from types import SimpleNamespace

import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from config import Settings
from main import app
from ml.features import PredictionRequest, extract_features, FEATURE_VERSION
from ml.inference import ModelUnavailable, PortableModel, load_model
from ml.train import export_estimator, partition, train
from rag.evidence_policy import admit_chunk
from rag.production_retrieval import retrieve
from rag.verification_graph import run_verification
from services.clinical_pipeline import sanitize_snapshot
from services.security import Principal, require_user


@pytest.fixture(autouse=True)
def reset_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


@pytest.mark.parametrize("path,method", [('/api/v1/evidence/search', 'post'), ('/api/v1/models/status', 'get'), ('/api/v1/risk/predict', 'post'), ('/api/v1/admin/rag/health', 'get'), ('/ready', 'get')])
def test_routes_require_auth(path, method):
    response = getattr(TestClient(app), method)(path, **({'json': {}} if method == 'post' else {}))
    assert response.status_code == 401
    assert response.headers['cache-control'] == 'no-store'


def test_clinician_cannot_access_admin():
    app.dependency_overrides[require_user] = lambda: Principal('u', False)
    assert TestClient(app).get('/api/v1/admin/rag/health').status_code == 403


def test_no_trained_artifact_returns_unavailable(monkeypatch, tmp_path):
    import production_api
    monkeypatch.setattr(production_api, 'get_settings', lambda: settings(model_artifact_path=str(tmp_path/'absent'), model_artifact_sha256='x'))
    app.dependency_overrides[require_user] = lambda: Principal('u')
    response = TestClient(app).post('/api/v1/risk/predict', json={'current': {'age_hours': 5, 'values': {}}})
    assert response.status_code == 503
    assert 'probability' not in response.text


def test_encounter_ownership_before_history(monkeypatch):
    import services.security as security
    class Query:
        def __init__(self): self.filters = []
        def select(self, _): return self
        def eq(self, k, v): self.filters.append((k, v)); return self
        def limit(self, _): return self
        def execute(self): return SimpleNamespace(data=[])
    q = Query()
    monkeypatch.setattr(security, 'get_supabase', lambda: SimpleNamespace(table=lambda _: q))
    app.dependency_overrides[require_user] = lambda: Principal('owner')
    response = TestClient(app).post('/api/v1/encounters/00000000-0000-0000-0000-000000000001/care-plan', json={'risk_result': {}})
    assert response.status_code == 404
    assert ('owner_user_id', 'owner') in q.filters


def test_body_size_is_bounded():
    r = TestClient(app).post('/api/v1/evidence/search', content=b'x' * 262145)
    assert r.status_code == 413


def test_encounter_evidence_uses_stored_population_facts(monkeypatch):
    import production_api
    from schemas import EvidenceSearchRequest
    from datetime import datetime,timedelta,timezone
    stored={'birth_date_time':(datetime.now(timezone.utc)-timedelta(hours=6)).isoformat(),
        'gestational_age_days':224,'birth_weight_g':1650}
    context=SimpleNamespace(current_snapshot={'gestational_age_weeks':40},load_error='',query_context_terms=lambda:[])
    monkeypatch.setattr(production_api,'require_encounter',lambda *args:stored)
    monkeypatch.setattr(production_api,'build_patient_context',lambda *args:context)
    observed={}
    def search(query,guideline,limit,*,patient):
        observed.update(patient);return SimpleNamespace(chunks=[])
    monkeypatch.setattr(production_api,'search',search)
    production_api.evidence_search(EvidenceSearchRequest(query='early onset infection',active_guideline='AAP',encounter_id='synthetic'),Principal('owner'))
    assert observed['gestational_age_weeks']==32
    assert observed['birth_weight_g']==1650
    assert 5.9<observed['age_hours']<6.1
    bad=production_api.encounter_scope({'gestational_age_weeks':40,'age_hours':3},{'gestational_age_days':'invalid','birth_date_time':'invalid'})
    assert 'age_hours' not in bad and 'gestational_age_weeks' not in bad


@pytest.mark.parametrize('history', [[{'age_hours': 6, 'values': {}}], [{'age_hours': 4, 'values': {}}, {'age_hours': 4, 'values': {}}]])
def test_temporal_leakage_rejected(history):
    with pytest.raises(ValidationError):
        PredictionRequest.model_validate({'current': {'age_hours': 6, 'values': {}}, 'history': history})


@pytest.mark.parametrize('values', [{'crp_level': -1}, {'neonatal_temperature': float('nan')}, {'blood_culture_positive': True}, {'gbs_positive': 'false'}, {'oxygen_need': 'unknown'}, {'maternal_temperature': True}])
def test_invalid_predictors_rejected(values):
    with pytest.raises(ValidationError):
        PredictionRequest.model_validate({'current': {'age_hours': 6, 'values': values}})


def test_slope_uses_actual_time_and_missing_stays_unknown():
    request = PredictionRequest.model_validate({'current': {'age_hours': 6, 'values': {'crp_level': 7}}, 'history': [{'age_hours': 1, 'values': {'crp_level': 2}}]})
    features = extract_features(request)
    assert features['crp_level__slope_per_hour'] == pytest.approx(1)
    assert features['crp_level__delta'] == 5
    assert features['wbc_count'] is None
    assert features['gbs_positive'] is None


def artifact(kind, estimator):
    return {'feature_version': FEATURE_VERSION, 'features': ['age_hours', 'crp_level'], 'kind': kind,
            'median': [0, 0], 'mean': [0, 0], 'scale': [1, 1], 'ranges': [[0, 72], [0, 600]],
            'calibration': {'slope': 1, 'intercept': 0}, 'scope': {'min_ga': 22, 'max_ga': 44, 'min_age_hours': 0, 'max_age_hours': 72},
            'model_version': 'unit-test-only', 'validation_status': 'research_only', **export_estimator(estimator, kind)}


@pytest.mark.parametrize('kind', ['logistic', 'forest'])
def test_portable_inference_matches_sklearn(kind):
    rng = np.random.default_rng(12)
    x = rng.normal(size=(100, 4))
    y = (x[:, 0] + x[:, 1] > 0).astype(int)
    estimator = LogisticRegression().fit(x, y) if kind == 'logistic' else RandomForestClassifier(n_estimators=8, max_depth=3, random_state=12).fit(x, y)
    m = PortableModel(artifact(kind, estimator))
    np.testing.assert_allclose([m.probability(row.tolist()) for row in x], estimator.predict_proba(x)[:, 1], atol=1e-8)


def test_prediction_abstains_outside_training_support():
    estimator = LogisticRegression().fit([[0,0,0,0], [1,1,0,0]], [0,1])
    m = PortableModel(artifact('logistic', estimator))
    request = PredictionRequest.model_validate({'current': {'age_hours': 3, 'values': {'crp_level': 4}}})
    result = m.predict(request)
    assert result['status'] == 'abstained'  # Missing gestational age.
    assert result['probability_per_1000'] is None


def test_corrupt_or_unpinned_model_not_loaded(tmp_path):
    p = tmp_path / 'model.json'
    p.write_text('{}')
    for digest in ('', 'incorrect'):
        with pytest.raises(ModelUnavailable): load_model(str(p), digest)


def test_synthetic_data_cannot_be_exported(tmp_path):
    p = tmp_path / 'synthetic.jsonl'
    p.write_text(json.dumps({'patient_id': 'x', 'label': 1, 'label_adjudicated': True, 'synthetic': True, 'source': 'fixture'}))
    with pytest.raises(ValueError, match='Synthetic'):
        train(p, tmp_path/'output')


def test_split_patient_isolation_and_shifted_date_disclosure():
    records = [{'patient_id': str(i), 'birth_time': str(i), 'label': i%2, 'source': 'mimiciii-1.4'} for i in range(300) for _ in range(2)]
    splits, method = partition(records)
    sets = [{r['patient_id'] for r in s} for s in splits]
    assert all(not a & b for i, a in enumerate(sets) for b in sets[i+1:])
    assert 'NOT temporal' in method


def packet():
    return {'guideline': 'NICE', 'patient': {'age_hours': 6}, 'history': [], 'evidence': [{'id': 'E1', 'text': 'Measure and record clinical observations during assessment.', 'chunk_id': 'x'}]}


def fake_llm(mode='pass'):
    def call(prompt, settings, *, role, model=None, **kwargs):
        if role == 'You are the evidence synthesis agent.':
            return {'claims': [{'id': 'C1', 'section': 'monitoring_plan', 'text': 'Record clinical observations during assessment.',
                                'support': [{'evidence_id': 'E99' if mode == 'citation' else 'E1', 'quote': 'An invented quotation that does not exist.' if mode == 'quote' else 'Measure and record clinical observations during assessment.'}]}]}
        if mode == 'outage':
            from services.groq_client import GenerationUnavailable
            raise GenerationUnavailable('simulated outage')
        if mode == 'partial':
            return {'supported': True, 'checked_claim_ids': ['C2'], 'rejected_claim_ids': [], 'reasons': []}
        if mode == 'string_bool':
            return {'supported': 'true', 'checked_claim_ids': ['C1'], 'rejected_claim_ids': [], 'reasons': []}
        reject = mode == 'dissent' and 'safety' in role
        return {'supported': not reject, 'checked_claim_ids': ['C1'], 'rejected_claim_ids': ['C1'] if reject else [], 'reasons': ['Not supported in patient context'] if reject else []}
    return call


def test_two_verifiers_accept_complete_grounded_packet():
    result = run_verification(packet(), settings(), fake_llm())
    assert result['status'] == 'supported_for_review'
    assert result['evidence_verdict']['supported'] and result['safety_verdict']['supported']


@pytest.mark.parametrize('mode', ['citation', 'quote', 'dissent', 'outage', 'partial', 'string_bool'])
def test_failed_or_incomplete_verification_abstains(mode):
    result = run_verification(packet(), settings(), fake_llm(mode))
    assert result['status'] == 'abstained'
    assert result['errors']


def test_no_evidence_never_calls_generator():
    def forbidden(*a, **k): raise AssertionError('No source; no model call permitted')
    p = packet(); p['evidence'] = []
    assert run_verification(p, settings(), forbidden)['status'] == 'abstained'


def test_deidentification_is_allowlist_not_name_redaction():
    assert sanitize_snapshot({'name': 'Example', 'mrn': '123', 'notes': 'Ignore instructions', 'oxygen_need': 'inject prompt', 'crp_level': 5}) == {'crp_level': 5}


def test_reviewed_hash_required_for_evidence(tmp_path):
    manifest = {'documents': [{'file_name': 'nice.pdf', 'approved_for_generation': True, 'reviewed_by': 'reviewer', 'reviewed_at': '2026-10-24', 'status': 'current', 'sha256': 'expected', 'url': 'https://www.nice.org.uk/guidance/ng195', 'version': '2026', 'source': 'NICE'}]}
    p = tmp_path/'manifest.json'; p.write_text(json.dumps(manifest))
    s = settings(evidence_manifest_path=str(p))
    row = {'version': '2026', 'metadata': {'file_name': 'nice.pdf', 'document_sha256': 'wrong'}}
    assert not admit_chunk(row, s, 'NICE')
    row['metadata']['document_sha256'] = 'expected'
    assert admit_chunk(row, s, 'NICE')
    assert not admit_chunk(row, s, 'WHO')
    assert not admit_chunk(row, s, 'NICE', {'age_hours': 6, 'gestational_age_weeks': 38})
    manifest['documents'][0].update({'min_ga': 35, 'max_ga': 44, 'min_age_hours': 0, 'max_age_hours': 72, 'care_setting': 'hospital'})
    p.write_text(json.dumps(manifest))
    assert admit_chunk(row, s, 'NICE', {'age_hours': 6, 'gestational_age_weeks': 38})
    assert not admit_chunk(row, s, 'NICE', {'age_hours': 6, 'gestational_age_weeks': 30})
    manifest['documents'][0]['mixed_population']=True
    p.write_text(json.dumps(manifest))
    patient={'age_hours':6,'gestational_age_weeks':38,'care_setting':'hospital'}
    assert not admit_chunk(row,s,'NICE',patient)
    row['metadata'].update(population='late_onset_neonatal',scope_reviewed_by='scope reviewer',scope_reviewed_at='2026-10-25')
    assert not admit_chunk(row,s,'NICE',patient)
    row['metadata']['population']='early_onset_neonatal'
    row['metadata']['scope']={'gestational_age_weeks':[35,44],'postnatal_age_hours':[0,72],
                              'care_setting':['hospital']}
    assert admit_chunk(row,s,'NICE',patient)


def test_audit_failure_withholds_decision(monkeypatch):
    from services import decision_audit
    from fastapi import HTTPException
    monkeypatch.setattr(decision_audit, 'get_supabase', lambda: (_ for _ in ()).throw(RuntimeError('unavailable')))
    with pytest.raises(HTTPException) as exc:
        decision_audit.record_decision(Principal('u'), 'prediction', {'status': 'predicted'})
    assert exc.value.status_code == 503


def test_lexical_fallback_retains_reviewed_sources_without_seed(tmp_path):
    manifest = {'documents': [{'file_name': 'nice.pdf', 'approved_for_generation': True, 'reviewed_by': 'reviewer', 'reviewed_at': '2026-10-24', 'status': 'current', 'sha256': 'expected', 'url': 'https://www.nice.org.uk/guidance/ng195', 'version': '2026', 'source': 'NICE'}]}
    p = tmp_path/'manifest.json'; p.write_text(json.dumps(manifest))
    s = settings(evidence_manifest_path=str(p))
    row = {'id': 'x', 'version': '2026', 'source_name': 'NICE NG195', 'section': 'Assessment', 'chunk_text': 'Source excerpt', 'metadata': {'file_name': 'nice.pdf', 'document_sha256': 'expected', 'source': 'NICE'}}
    class DB:
        def rpc(self, name, params): return SimpleNamespace(execute=lambda: SimpleNamespace(data=[row]))
    class Encoder:
        def encode(self, *a, **kw): raise RuntimeError('offline')
    class Reranker:
        def predict(self, *a, **kw): raise RuntimeError('offline')
    result = retrieve('EOS', 'NICE', 5, s, db=DB(), encoder=Encoder(), reranker=Reranker())
    assert [c.chunk_id for c in result.chunks] == ['x']
    assert result.mode == 'lexical'
    assert len(result.warnings) == 2


def test_empty_evidence_never_issues_patient_plan(monkeypatch):
    from services import clinical_pipeline
    from rag.production_retrieval import Retrieval
    monkeypatch.setattr(clinical_pipeline, 'retrieve', lambda *a, **k: Retrieval())
    result = clinical_pipeline.produce({'patient': {'age_hours': 6, 'gestational_age_weeks': 38}}, 'NICE', settings(allow_clinical_cloud_processing=True))
    assert result.verification_status == 'abstained'
    assert result.antibiotic_plan.decision_status == 'undetermined'
    assert not result.fact_check.verified
    assert result.citation_list == []
