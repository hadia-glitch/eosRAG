"""Explicit research-only selector. It never enables clinical inference."""
import hashlib,json,math
from pathlib import Path
import numpy as np
from ml.supplied_model import supplied_status
from ml.inference import ModelUnavailable
from ml.dynamic_features import features,GROUPS
from ml.longitudinal_inputs import contract,preview


def load_pic(settings):
    root=Path(settings.pic_model_dir)
    try:
        raw=(root/'dynamic_model.json').read_bytes();manifest=json.loads((root/'dynamic_manifest.json').read_text())
        if hashlib.sha256(raw).hexdigest()!=manifest['artifact_sha256']:raise ValueError('digest mismatch')
        a=json.loads(raw);prep=a['preprocessing'];n=len(prep['indices'])
        if a.get('calibration',{}).get('slope')!=1. or a['calibration'].get('intercept')!=0.:raise ValueError('Unexpected PIC calibration contract')
        if a['kind']!='logistic' or a['feature_version']!='pic-longitudinal-v1' or a['clinical_eos_eligible'] is not False:raise ValueError('unsupported research model')
        if a['validation_status']!='research_only' or len(a['coefficients'])!=2*n:raise ValueError('invalid model dimensions')
        cols=GROUPS[a['group']]
        if [cols[i] for i in prep['indices']]!=prep['features']:raise ValueError('feature contract mismatch')
        for key in ['median','mean','scale']:
            if len(prep[key])!=n or not all(math.isfinite(v) for v in prep[key]):raise ValueError('invalid preprocessing')
        if any(v<=0 for v in prep['scale']) or not all(math.isfinite(v) for v in [a['intercept'],*a['coefficients']]):raise ValueError('invalid parameters')
        return a
    except (OSError,KeyError,ValueError,TypeError,IndexError) as e:
        raise ModelUnavailable('PIC research artifact unavailable or invalid; configure PIC_MODEL_DIR with the locally trained, hash-pinned artifact') from e


def status(settings):
    if settings.research_ml_model=='kaggle':
        return {**supplied_status(settings),'selected_model':'kaggle','input_mode':'single_assessment','display_name':'Kaggle research model'}
    try:
        a=load_pic(settings)
        return {'available':True,'selected_model':'pic','input_mode':'longitudinal','display_name':'PIC longitudinal research model',
            'version':a['model_version'],'clinical_ready':False,'validation_status':'research_only',
            'input_contract_version':'pic-longitudinal-v1','notice':'Uncalibrated research score; not a clinical EOS probability.',
            'input_contract':contract(),'age_scope_hours':[0,72]}
    except ModelUnavailable as e:return {'available':False,'selected_model':'pic','clinical_ready':False,'reason':str(e)}


def longitudinal_contract(settings):
    c=contract()
    if settings.research_ml_model=='pic':
        c.update(prediction_status='research_score_available',reason='PIC is explicitly selected for research. Clinical risk and treatment decisions remain disabled.',
            selected_model='pic',prediction_endpoint='/api/v1/research/longitudinal/predict')
    return c


def predict_pic(request,settings):
    if settings.research_ml_model!='pic':raise ModelUnavailable('PIC is not selected; set RESEARCH_ML_MODEL=pic and restart the backend')
    a=load_pic(settings);seq=request.sequence
    observed=[e.model_dump() for e in seq.observations]
    recent={e['field'] for e in observed if e['age_hours']>=seq.age_hours-6 and e['field'] in {'neonatal_temperature','heart_rate','respiratory_rate','spo2','pulse_rate'}}
    if len(recent)<2:raise ModelUnavailable('Record at least two distinct recent vital signs within six hours, matching the PIC development scope')
    f=features(seq.age_hours,seq.sex,observed);prep=a['preprocessing'];values=np.array([f[k] for k in prep['features']],dtype=float)
    missing=np.isnan(values);filled=np.where(missing,prep['median'],values)
    x=np.r_[(filled-prep['mean'])/prep['scale'],missing.astype(float)]
    co=np.array(a['coefficients']);z=float(a['intercept']+co@x);p=1/(1+math.exp(-max(-700,min(700,z))))
    base=np.r_[(np.array(prep['median'])-prep['mean'])/prep['scale'],np.zeros(len(values))]
    parts=co*(x-base);n=len(values)
    contributions=sorted([{'feature':k,'value':f[k],'contribution':float(parts[i]+parts[n+i])} for i,k in enumerate(prep['features'])],key=lambda c:abs(c['contribution']),reverse=True)
    result=preview(request)
    return {**result,'status':'research_score_available','prediction_status':'research_only','research_score':p,
        'model_version':a['model_version'],'selected_model':'pic','clinical_ready':False,'clinical_probability_available':False,
        'contributions':contributions,'contribution_method':'Linear contributions relative to fit medians, in model log-odds; not clinical causes',
        'missing_features':[k for k,m in zip(prep['features'],missing) if m],
        'validation_limitations':['Inadequate development discrimination','Only seven independent positive infants','No independent clinical calibration or external validation'],
        'notice':'Research model score, not a clinical EOS probability. It does not confirm or exclude sepsis and must not determine treatment. Maternal context is recorded but does not contribute to this score.'}
