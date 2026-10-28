import numpy as np
from ml.improve_pic_models import FoldModel,CANDIDATES,folds


def test_patient_landmarks_never_cross_folds():
    rows=[{'patient_id':str(i),'label':int(i<6)} for i in range(18) for _ in range(i%3+1)]
    for a,b in folds(rows,31):
        assert not {rows[i]['patient_id'] for i in a}&{rows[i]['patient_id'] for i in b}
        assert {rows[i]['label'] for i in b}=={0,1}


def test_knn_heldout_queries_cannot_change_fitted_donors_or_scaling():
    x=np.array([[i,float(i*i)] for i in range(10)],dtype=float);x[2,1]=np.nan
    y=np.array([0]*5+[1]*5);g=np.arange(10)
    model=FoldModel(CANDIDATES['compact_lr_knn_C01'],31).fit(x,y,g,np.ones(10))
    before=model.imputer._fit_X.copy();mean=model.mean.copy();scale=model.scale.copy()
    p=model.predict(np.array([[100000.,np.nan],[np.nan,1.]]))
    assert np.isfinite(p).all()
    np.testing.assert_allclose(model.imputer._fit_X,before,equal_nan=True)
    np.testing.assert_array_equal(model.mean,mean);np.testing.assert_array_equal(model.scale,scale)


def test_feature_observation_floor_counts_independent_infants():
    x=np.array([[i,float(i) if i<6 else np.nan] for i in range(12)])
    groups=np.array([0]*6+list(range(1,7)));y=np.array([0]*6+[1]*6)
    model=FoldModel(CANDIDATES['compact_lr_median_C001'],31).fit(x,y,groups,np.ones(12))
    assert model.keep==[0]  # second feature has six rows, but only one donor infant
