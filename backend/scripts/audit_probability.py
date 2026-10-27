"""Post-hoc audit of suspicious supplied-label scores; no clinical validation."""
import hashlib,io,json,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from pydantic import ValidationError
from sklearn.metrics import roc_auc_score,accuracy_score,brier_score_loss,log_loss
from sklearn.tree import DecisionTreeClassifier
from ml.research_cohort import partitions,portable_probability,save
from scripts.audit_model_leakage import design
from ml.supplied_model import SuppliedModel,SuppliedPredictionRequest

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/research/probability_audit'

def ece(y,p):
    bins=[]
    for lo in np.linspace(0,.9,10):
        ix=(p>=lo)&((p<lo+.1) if lo<.9 else (p<=1))
        if ix.any():bins.append({'lower':float(lo),'n':int(ix.sum()),'predicted':float(p[ix].mean()),'observed':float(y[ix].mean())})
    return {'ece_10_equal_width':float(sum(b['n']*abs(b['predicted']-b['observed']) for b in bins)/len(y)),'bins':bins}

def metrics(y,p):
    return {'n':len(y),'auroc':float(roc_auc_score(y,p)),'accuracy_at_0_5':float(accuracy_score(y,p>=.5)),
        'brier':float(brier_score_loss(y,p)),'log_loss':float(log_loss(y,p)),**ece(y,p)}

def main():
    with zipfile.ZipFile(Path.home()/'Downloads/archive (1).zip') as z:raw=z.read('Neonatal_Sepsis.csv')
    d=pd.read_csv(io.BytesIO(raw));groups=partitions(d);d=d.loc[d.Postnatal_Age.between(0,2)].copy()
    fit=d.loc[d.Patient_ID.isin(groups[0])];test=d.loc[d.Patient_ID.isin(groups[3])]
    folder=ROOT/'backend/ml/deployed/supplied_neonatal'
    a=json.loads((folder/'model.json').read_text());scope=json.loads((folder/'scope.json').read_text())
    model=SuppliedModel(a,scope);xtest=design(test,a);y=test.Sepsis_Label.to_numpy(int)
    uncal={**a,'calibration':{'slope':1.,'intercept':0.}}
    uncalibrated=portable_probability(uncal,xtest);calibrated=portable_probability(a,xtest)
    demo=json.loads((ROOT/'backend/demo/case.json').read_text())['research_request']
    values=demo['values'];dx=design(pd.DataFrame([values]),a)
    raw_score=float(portable_probability(uncal,dx)[0]);score=float(portable_probability(a,dx)[0])
    trees=[];z=model.transform(values);z=np.asarray(z,dtype=np.float32)
    for tree in a['trees']:
        node=0
        while tree['left'][node]!=-1:node=tree['left'][node] if z[tree['feature'][node]]<=tree['threshold'][node] else tree['right'][node]
        trees.append(tree['probability'][node])
    distributions={}
    for c in a['numeric_columns']:
        v=values[c]
        distributions[c]={'case_value':v,'fit_percentile_all':float((fit[c].dropna()<=v).mean()),
            'fit_label_quantiles':{str(label):np.quantile(fit.loc[fit.Sepsis_Label==label,c].dropna(),[.05,.25,.5,.75,.95]).tolist() for label in [0,1]}}
    single={}
    for c in a['numeric_columns']:
        f=fit[c].fillna(fit[c].median()).to_numpy();t=test[c].fillna(fit[c].median()).to_numpy()
        orientation=1 if roc_auc_score(fit.Sepsis_Label,f)>=.5 else -1
        stump=DecisionTreeClassifier(max_depth=1,min_samples_leaf=30,random_state=31).fit(f[:,None],fit.Sepsis_Label)
        sp=stump.predict_proba(t[:,None])[:,1]
        single[c]={'test_auroc_oriented_on_fit':float(roc_auc_score(y,orientation*t)),
            'orientation':orientation,'fit_only_stump_threshold':float(stump.tree_.threshold[0]),'stump_test':metrics(y,sp)}
    rng=np.random.default_rng(20261025);perturbed=[]
    for _ in range(250):
        row=dict(values)
        for c in ['HR','Resp','Temp','SpO2','BP','Oxygen','WBC','CRP','PCT','Platelets','Lactate','Hemoglobin']:
            # Engineering sensitivity only; temperature uses a 0.1-C SD.
            sd=.1 if c=='Temp' else abs(row[c])*.05
            row[c]=float(row[c]+rng.normal(0,sd))
        try:
            req=SuppliedPredictionRequest(**{**demo,'values':row})
            result=model.predict(req)
        except ValidationError:
            result={'status':'invalid_input_rejected','probability':None}
        perturbed.append({'status':result['status'],'probability':result['probability']})
    accepted=[r['probability'] for r in perturbed if r['status']=='predicted']
    counterfactuals=[]
    for changes in [{},{'CRP':5,'PCT':.3,'Lactate':1.5},
        {'HR':150,'Resp':48,'Temp':36.8,'SpO2':97,'Oxygen':21},
        {'HR':150,'Resp':48,'Temp':36.8,'SpO2':97,'Oxygen':21,'CRP':5,'PCT':.3,'Lactate':1.5},
        {'CRP':None,'PCT':None,'Lactate':None}]:
        r=model.predict(SuppliedPredictionRequest(**{**demo,'values':{**values,**changes}}))
        counterfactuals.append({'changes':changes,'status':r['status'],'supplied_label_probability':r['probability'],
            'not_a_causal_effect':True,'no_clinical_outcome_assumed':True})
    report={'analysis':'post-hoc development audit; previously examined test partition',
        'source_csv_sha256':hashlib.sha256(raw).hexdigest(),'model_sha256':hashlib.sha256((folder/'model.json').read_bytes()).hexdigest(),
        'target':a['target'],'clinical_eos_eligible':False,'csv_synthetic_status':'unverified; user confirmed only the RAG benchmark is synthetic',
        'calibration':a['calibration'],'forest_trees':len(a['trees']),
        'model_test_raw':metrics(y,uncalibrated),'model_test_calibrated':metrics(y,calibrated),
        'fit_prevalence':float(fit.Sepsis_Label.mean()),'test_prevalence':float(y.mean()),
        'demo':{'raw_forest_probability':raw_score,'calibrated_supplied_label_probability':score,
            'calibration_equation':'sigmoid(slope * logit(raw forest mean) + intercept)',
            'tree_leaf_probability_quantiles':np.quantile(trees,[0,.25,.5,.75,1]).tolist(),
            'individual_feature_context':distributions,'counterfactuals':counterfactuals,
            'measurement_perturbation':{'n':len(perturbed),'accepted':len(accepted),'abstained':sum(r['status']=='abstained' for r in perturbed),
                'invalid_input_rejected':sum(r['status']=='invalid_input_rejected' for r in perturbed),
                'accepted_probability_quantiles':np.quantile(accepted,[0,.05,.5,.95,1]).tolist() if accepted else [],
                'interpretation':'Local engineering sensitivity, not probability correctness or clinical robustness'}},
        'single_feature_diagnostics':single,
        'conclusions':['The supplied label has strong concurrent laboratory and vital-sign separation; identity and timing problems prevent clinical interpretation.',
            'Platt calibration is fitted to the same supplied-label population; it can sharpen already high raw scores.',
            'A high internal AUC and a small train-test gap do not establish culture-confirmed EOS prediction, calibrated clinical risk, or transportability.',
            'Changing synthetic cases or clipping the probability would not repair invalid outcome provenance.',
            'Raw data, fixed patient-disjoint partitions, gold evidence and original model parameters were not altered by this audit.']}
    save(OUT/'audit.json',report)
    print(json.dumps({'demo_raw':raw_score,'demo_calibrated':score,'calibration':a['calibration'],
        'raw_brier':report['model_test_raw']['brier'],'calibrated_brier':report['model_test_calibrated']['brier'],
        'single_feature_auroc':{c:r['test_auroc_oriented_on_fit'] for c,r in single.items()},
        'saved':str(OUT/'audit.json')}),flush=True)

if __name__=='__main__':main()
