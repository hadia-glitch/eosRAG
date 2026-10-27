"""Actual bounded model-agnostic SHAP, computed locally on the served model.

The reference is an aggregate fit-median vector. Contributions are statistical
attributions of the supplied-label probability, not causes or treatment advice.
"""
import threading
import numpy as np
from ml.supplied_model import NUMERIC,CATEGORIES

_lock=threading.Lock()


def matrix_probability(model,raw):
    a=model.a;raw=np.asarray(raw,dtype=float)
    numeric=raw[:,:len(NUMERIC)]
    encoded=[numeric]
    for j,(key,categories) in enumerate(CATEGORIES.items()):
        code=raw[:,len(NUMERIC)+j]
        encoded.extend([(code==i).astype(float) for i,_ in enumerate(categories)])
    values=np.column_stack(encoded);missing=np.isnan(values)
    x=np.column_stack(((np.where(missing,a['median'],values)-a['mean'])/a['scale'],missing.astype(float)))
    if a['kind']=='logistic':
        z=x@np.array(a['coefficients'])+a['intercept']
        p=1/(1+np.exp(-np.clip(z,-700,700)))
    else:
        x=x.astype(np.float32);predictions=[]
        for tree in a['trees']:
            left,right=np.array(tree['left']),np.array(tree['right'])
            feature,threshold=np.array(tree['feature']),np.array(tree['threshold'])
            nodes=np.zeros(len(x),dtype=int)
            while (left[nodes]!=-1).any():
                active=np.flatnonzero(left[nodes]!=-1);n=nodes[active]
                nodes[active]=np.where(x[active,feature[n]]<=threshold[n],left[n],right[n])
            predictions.append(np.array(tree['probability'])[nodes])
        p=np.mean(predictions,axis=0)
    p=np.clip(p,1e-9,1-1e-9)
    z=a['calibration']['slope']*np.log(p/(1-p))+a['calibration']['intercept']
    return 1/(1+np.exp(-np.clip(z,-700,700)))


def explain(model,request):
    result=model.predict(request)
    if result['status']!='predicted':return result
    import shap
    fields=NUMERIC+list(CATEGORIES)
    reference=[model.a['median'][model.names.index(k)] for k in NUMERIC]
    case=[float('nan') if request.values[k] is None else request.values[k] for k in NUMERIC]
    for key,categories in CATEGORIES.items():
        shares=[model.a['mean'][model.names.index(f'{key}={value}')] for value in categories]
        reference.append(int(np.argmax(shares)))
        case.append(categories.index(request.values[key]))
    background=np.array([reference]);current=np.array([case])
    # KernelExplainer uses numpy's global RNG. Serialize and restore its state
    # so independent requests do not change one another's sampling sequence.
    if not _lock.acquire(timeout=1):raise RuntimeError('Explanation service busy')
    try:
        state=np.random.get_state();np.random.seed(31)
        try:
            explainer=shap.KernelExplainer(lambda x:matrix_probability(model,x),background)
            values=np.asarray(explainer.shap_values(current,nsamples=256,l1_reg=0,silent=True))[0]
        finally:np.random.set_state(state)
    finally:_lock.release()
    p=float(matrix_probability(model,current)[0]);baseline=float(explainer.expected_value)
    error=abs(baseline+float(values.sum())-p)
    if error>1e-5 or abs(p-result['probability'])>1e-7:raise ValueError('SHAP additivity or served-model parity failed')
    return {**result,'contribution_method':'SHAP KernelExplainer of supplied-label probability; fit-median reference; not causal',
            'contributions':sorted([{'feature':key,'value':request.values[key],'contribution':float(value)} for key,value in zip(fields,values)],key=lambda c:abs(c['contribution']),reverse=True),
            'shap':{'baseline_probability':baseline,'additivity_error':error,'nsamples':256,'seed':31,'version':shap.__version__,
                    'reference':'aggregate fit medians and modal categories; reference choice affects attributions'}}
