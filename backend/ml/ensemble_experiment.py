"""Four-model supplied-label research experiment and actual ensemble SHAP.

Fixed patient-ID partitions and fitting-only preprocessing; no target numerical
performance is imposed. The previously reported test is reused for a post-hoc
comparison and is NOT a new independent validation cohort.
"""
import io,json,hashlib,zipfile,importlib.metadata
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier,RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from xgboost import XGBClassifier

from ml.research_cohort import partitions,save,metrics,bootstrap
from ml.train import export_estimator
from scripts.audit_model_leakage import design

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/research/ensemble'


def tree_values(tree,x,key='value'):
    nodes=np.zeros(len(x),dtype=int)
    left,right=np.array(tree['left']),np.array(tree['right'])
    feature,threshold=np.array(tree['feature']),np.array(tree['threshold'])
    while (left[nodes]!=-1).any():
        active=np.flatnonzero(left[nodes]!=-1);n=nodes[active]
        nodes[active]=np.where(x[active,feature[n]]<=threshold[n],left[n],right[n])
    return np.array(tree[key])[nodes]


def portable_margin(component,x):
    kind=component['kind']
    if kind=='svm':return x@np.array(component['coefficients'])+component['intercept']
    x=x.astype(np.float32)
    if kind=='forest':
        p=np.mean([tree_values(t,x,'probability') for t in component['trees']],axis=0)
        p=np.clip(p,1e-9,1-1e-9);return np.log(p/(1-p))
    if kind=='gradient_boosting':
        return component['base_margin']+component['learning_rate']*np.sum([tree_values(t,x) for t in component['trees']],axis=0)
    margins=np.full(len(x),component['base_margin'],dtype=float)
    for tree in component['trees']:
        def visit(node,indices):
            if not len(indices):return
            if 'leaf' in node:
                margins[indices]+=node['leaf'];return
            feature=int(str(node['split']).removeprefix('f'))
            lower=x[indices,feature]<node['split_condition']
            children={n['nodeid']:n for n in node['children']}
            visit(children[node['yes']],indices[lower]);visit(children[node['no']],indices[~lower])
        visit(tree,np.arange(len(x)))
    return margins


def portable_ensemble(artifact,x):
    probabilities=[]
    for component in artifact['components']:
        score=portable_margin(component,x)
        z=component['calibration']['slope']*score+component['calibration']['intercept']
        probabilities.append(1/(1+np.exp(-np.clip(z,-700,700))))
    return np.mean(probabilities,axis=0)


def export(model,kind):
    if kind=='forest':return {'kind':kind,**export_estimator(model,'forest')}
    if kind=='svm':return {'kind':kind,'coefficients':model.coef_[0].tolist(),'intercept':float(model.intercept_[0])}
    if kind=='gradient_boosting':
        trees=[]
        for estimator in model.estimators_[:,0]:
            t=estimator.tree_
            trees.append({'left':t.children_left.tolist(),'right':t.children_right.tolist(),
                          'feature':t.feature.tolist(),'threshold':t.threshold.tolist(),'value':t.value[:,0,0].tolist()})
        p=float(model.init_.class_prior_[1])
        return {'kind':kind,'base_margin':float(np.log(p/(1-p))),'learning_rate':model.learning_rate,'trees':trees}
    config=json.loads(model.get_booster().save_config())
    score=config['learner']['learner_model_param']['base_score']
    score=json.loads(score) if isinstance(score,str) else score
    p=float(score[0] if isinstance(score,list) else score)
    return {'kind':kind,'base_margin':float(np.log(p/(1-p))),
            'trees':[json.loads(t) for t in model.get_booster().get_dump(dump_format='json')]}


def raw_margin(model,kind,x):
    if kind in {'svm','gradient_boosting'}:return model.decision_function(x)
    if kind=='xgboost':return model.predict(x,output_margin=True)
    p=np.clip(model.predict_proba(x)[:,1],1e-9,1-1e-9)
    return np.log(p/(1-p))


def fit(name,cohort,groups):
    a=json.loads((ROOT/'output/research'/name/'model.json').read_text())
    splits=[cohort.loc[cohort.Patient_ID.isin(g)] for g in groups]
    xs=[design(s,a) for s in splits];ys=[s.Sepsis_Label.to_numpy(int) for s in splits]
    weights=[1/s.groupby('Patient_ID').Patient_ID.transform('size').to_numpy() for s in splits]
    estimators={
        'gradient_boosting':GradientBoostingClassifier(n_estimators=150,learning_rate=.05,max_depth=3,min_samples_leaf=15,random_state=31),
        'xgboost':XGBClassifier(n_estimators=200,max_depth=4,learning_rate=.05,subsample=.9,colsample_bytree=.9,reg_lambda=5,tree_method='hist',n_jobs=2,random_state=31,eval_metric='logloss'),
        'svm':LinearSVC(C=.5,dual='auto',max_iter=5000,random_state=31),
        'forest':RandomForestClassifier(n_estimators=150,max_depth=10,min_samples_leaf=15,n_jobs=2,random_state=31),
    }
    fitted=[];components=[];candidates={};vps=[];tps=[]
    for kind,estimator in estimators.items():
        estimator.fit(xs[0],ys[0],sample_weight=weights[0])
        calibrator=LogisticRegression(C=1e6,max_iter=2000).fit(raw_margin(estimator,kind,xs[1]).reshape(-1,1),ys[1],sample_weight=weights[1])
        def probability(x):return calibrator.predict_proba(raw_margin(estimator,kind,x).reshape(-1,1))[:,1]
        vp,tp=probability(xs[2]),probability(xs[3]);vps.append(vp);tps.append(tp)
        threshold=float(np.quantile(vp[ys[2]==1],.05))
        component=export(estimator,kind)
        component['calibration']={'slope':float(calibrator.coef_[0,0]),'intercept':float(calibrator.intercept_[0])}
        portable=1/(1+np.exp(-np.clip(component['calibration']['slope']*portable_margin(component,xs[3])+component['calibration']['intercept'],-700,700)))
        np.testing.assert_allclose(portable,tp,atol=1e-5,rtol=1e-5)
        components.append(component);fitted.append((estimator,kind,calibrator))
        candidates[kind]={'validation':metrics(ys[2],vp,threshold),'test':metrics(ys[3],tp,threshold)}
        print(name,kind,'test_auroc',round(candidates[kind]['test']['auroc'],6),flush=True)
    vp,tp=np.mean(vps,axis=0),np.mean(tps,axis=0)
    threshold=float(np.quantile(vp[ys[2]==1],.05))
    candidates['equal_probability_ensemble']={'validation':metrics(ys[2],vp,threshold),'test':metrics(ys[3],tp,threshold)}
    artifact={'feature_version':'supplied-neonatal-ensemble-research-v1','model_version':name+'-GB-XGB-linearSVM-RF-equal-vote-v1',
              'clinical_eos_eligible':False,'validation_status':'research_only','target':'supplied observation-associated Sepsis_Label',
              'features':a['features'],'numeric_columns':a['numeric_columns'],'categories':a['categories'],
              'median':a['median'],'mean':a['mean'],'scale':a['scale'],'components':components}
    np.testing.assert_allclose(portable_ensemble(artifact,xs[3]),tp,atol=1e-5,rtol=1e-5)
    selected=min(candidates,key=lambda k:candidates[k]['validation']['brier'])
    selected_p=tp if selected=='equal_probability_ensemble' else tps[list(estimators).index(selected)]
    selected_threshold=candidates[selected]['test']['threshold']
    report={'cohort':name,'target':artifact['target'],'clinical_eos_eligible':False,
            'split':'Same previously reported patient-ID-disjoint fit/calibration/validation/test; post-hoc model comparison',
            'estimators':['GradientBoostingClassifier','XGBClassifier','LinearSVC','RandomForestClassifier'],
            'svm_kernel':'linear; this is not an RBF SVM','ensemble':'fixed equal mean of separately Platt-calibrated component probabilities',
            'candidates':candidates,'selected_by_validation_brier':selected,
            'selected_test_cluster_bootstrap_95ci':bootstrap(ys[3],selected_p,splits[3].Patient_ID.to_numpy(),selected_threshold),
            'portable_probability_parity_atol':1e-5,'application_model_changed':False,
            'application_note':'Existing pinned forest remains deployed pending separate artifact/input contract review'}
    OUT.mkdir(parents=True,exist_ok=True);folder=OUT/name;folder.mkdir(exist_ok=True)
    save(folder/'model.json',artifact);save(folder/'evaluation.json',report)
    (folder/'model.sha256').write_text(hashlib.sha256((folder/'model.json').read_bytes()).hexdigest()+'\n')
    # Actual model-agnostic SHAP of the calibrated ensemble, not a relabeled
    # feature-importance heuristic. One fit-median reference, fixed budget.
    import shap
    background=np.median(xs[0],axis=0,keepdims=True)
    rng=np.random.default_rng(31);indices=rng.choice(len(xs[3]),min(8,len(xs[3])),replace=False)
    np.random.seed(31)
    explainer=shap.KernelExplainer(lambda x:portable_ensemble(artifact,x),background)
    shap_values=np.asarray(explainer.shap_values(xs[3][indices],nsamples=256,l1_reg=0,silent=True))
    p=portable_ensemble(artifact,xs[3][indices]);residual=np.max(np.abs(explainer.expected_value+shap_values.sum(axis=1)-p))
    if residual>1e-5:raise ValueError('SHAP local additivity check failed')
    fields=list(dict.fromkeys(n.split('=')[0] for n in a['features']))
    grouped=np.zeros((len(indices),len(fields)))
    for j,n in enumerate(a['features']):
        grouped[:,fields.index(n.split('=')[0])]+=shap_values[:,j]+shap_values[:,j+len(a['features'])]
    explanation={'method':'SHAP KernelExplainer of calibrated four-model ensemble probability',
                 'shap_version':shap.__version__,'samples':len(indices),'nsamples_per_case':256,
                 'background':'one fit-partition median design vector; reference choice affects attributions',
                 'baseline_probability':float(explainer.expected_value),'maximum_additivity_error':float(residual),
                 'features':fields,'mean_absolute_shap':np.abs(grouped).mean(axis=0).tolist(),
                 'sample_probability':p.tolist(),'sample_shap_values':grouped.tolist(),
                 'not_causal':True,'clinical_eos_eligible':False}
    save(folder/'shap.json',explanation)
    return report


if __name__=='__main__':
    with zipfile.ZipFile(r'C:\Users\hadia\Downloads\archive (1).zip') as z:raw=z.read('Neonatal_Sepsis.csv')
    d=pd.read_csv(io.BytesIO(raw));groups=partitions(d)
    reports=[fit('all_neonatal_ages',d,groups),fit('postnatal_days_0_2',d.loc[d.Postnatal_Age.between(0,2)],groups)]
    save(OUT/'summary.json',{'seed':31,'csv_sha256':hashlib.sha256(raw).hexdigest(),'experiments':reports,
                           'versions':{k:importlib.metadata.version(k) for k in ['scikit-learn','xgboost','shap','numpy']}})
