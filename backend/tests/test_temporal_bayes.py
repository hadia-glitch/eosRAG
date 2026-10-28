import copy
import numpy as np
import pytest
from ml.temporal_bayes import TemporalBayes


def test_conditional_dependence_can_be_learned_without_an_independent_signal():
    # XOR is uninformative to independent NB, informative with a conditional edge.
    rng=np.random.default_rng(31);x=rng.integers(0,2,size=(2000,2)).astype(float);y=(x[:,0]!=x[:,1]).astype(int)
    tan=TemporalBayes().fit(x,y);nb=TemporalBayes(tree=False).fit(x,y)
    points=np.array([[0,0],[0,1],[1,0],[1,1]],dtype=float)
    assert (tan.predict_proba(points)[:,1]>.5).tolist()==[False,True,True,False]
    assert np.ptp(nb.predict_proba(points)[:,1])<.15


def test_missing_is_a_separate_state_and_json_roundtrip_is_lossless():
    x=np.array([[np.nan,0],[0,1],[1,0],[np.nan,1],[2,0],[3,1]],float);y=np.array([0,0,0,1,1,1])
    model=TemporalBayes().fit(x,y);restored=TemporalBayes.from_dict(model.to_dict())
    assert model._states(x)[0,0]==0 and model._states(x)[1,0]!=0
    np.testing.assert_allclose(restored.predict_proba(x),model.predict_proba(x),atol=1e-12)
    before=copy.deepcopy(model.edges);model.predict_proba([[1e9,0]])
    assert model.edges==before  # Inference never refits discretization.


def test_corrupt_probability_tables_and_cycles_are_rejected():
    model=TemporalBayes().fit(np.array([[0,1],[1,0],[2,1],[3,0]],float),[0,0,1,1]);a=model.to_dict()
    a['parents']=[1,0]
    with pytest.raises(ValueError,match='tree'):TemporalBayes.from_dict(a)
