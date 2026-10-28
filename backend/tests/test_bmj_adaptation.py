import numpy as np
import pytest
from ml.evaluate_bmj_adaptation import balanced_weights,threshold_90,measure


def test_mixed_labels_do_not_require_inventing_a_patient_outcome():
    y=np.array([0,1,0,0,1]);g=np.array(['a','a','b','c','d'])
    original=y.copy();w=balanced_weights(y,g)
    assert w[y==0].sum()==pytest.approx(w[y==1].sum())
    np.testing.assert_array_equal(y,original)


def test_high_sensitivity_threshold_uses_supplied_threshold_cohort():
    y=np.array([1,1,1,1,0,0]);p=np.array([.1,.2,.3,.4,.05,.6]);w=np.ones(len(y))
    cut=threshold_90(y,p,w)
    assert cut==.1
    m=measure(y,p,p>=cut,w)
    assert m['sensitivity']==1 and m['specificity']==.5


def test_constant_scores_expose_trivial_all_positive_solution():
    y=np.array([1,0,0,0]);p=np.full(4,.25);w=np.ones(4)
    cut=threshold_90(y,p,w);m=measure(y,p,p>=cut,w)
    assert m['sensitivity']==1 and m['specificity']==0 and m['precision']==.25
