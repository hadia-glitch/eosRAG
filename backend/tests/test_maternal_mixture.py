import numpy as np
import pandas as pd
import pytest
from scripts.evaluate_maternal_mixture import (MATERNAL,CLINICAL,SHARED,FORBIDDEN,
    logistic,clinical,export,portable,prepare)

def test_mixture_contract_excludes_labels_scores_cultures_and_later_outcomes():
    assert not set(MATERNAL+CLINICAL+SHARED)&FORBIDDEN
    assert 'maternal_infection' in MATERNAL
    assert 'sepsis_probability_score' in FORBIDDEN

@pytest.mark.parametrize('factory',[logistic,clinical])
def test_exported_mixture_branch_preserves_predictions(factory):
    rng=np.random.default_rng(31);x=rng.normal(size=(160,3));y=(x[:,0]+x[:,1]>.1).astype(int)
    model=factory().fit(x,y);artifact=export(model,['one','two','three'])
    np.testing.assert_allclose(portable(artifact,x),model.predict_proba(x)[:,1],atol=1e-7)

def test_synthetic_onset_filter_does_not_turn_late_onset_into_negative_controls():
    base={k:'False' for k in ['prom','maternal_infection','resuscitation_needed',*CLINICAL]}
    rows=[{**base,'delivery_mode':'Vaginal','sepsis_status':status,'sepsis_onset':onset}
          for status,onset in [('Positive','Early-onset'),('Positive','Late-onset'),('Negative','')]]
    result=prepare(pd.DataFrame(rows))
    assert len(result)==2 and result.target.tolist()==[1,0]
