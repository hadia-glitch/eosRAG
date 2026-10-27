import numpy as np

from ml.research_cohort import partitions, portable_probability


def test_tree_float32_boundary_matches_sklearn():
    from sklearn.tree import DecisionTreeClassifier
    from ml.train import export_estimator
    from types import SimpleNamespace
    x=np.array([[0.1],[0.2],[0.3],[0.4]])
    tree=DecisionTreeClassifier(max_depth=1,random_state=31).fit(x,[0,0,1,1])
    # float64 value on the other side of the threshold rounds to float32.
    boundary=tree.tree_.threshold[0]
    test=np.array([[boundary+1e-10],[boundary-1e-10],[0.1],[0.4]])
    a={'kind':'forest','calibration':{'slope':1.,'intercept':0.},**export_estimator(SimpleNamespace(estimators_=[tree]),'forest')}
    expected=np.clip(tree.predict_proba(test)[:,1],1e-9,1-1e-9)
    np.testing.assert_allclose(portable_probability(a,test),expected,atol=1e-9)


def test_research_partitions_never_overlap():
    import pandas as pd
    d=pd.DataFrame({'Patient_ID':[f'P{i}' for i in range(100)]*3})
    groups=partitions(d)
    assert [len(x) for x in groups]==[55,15,15,15]
    assert len(set.union(*groups))==100


def test_quote_ids_materialize_only_immutable_source_text():
    import pytest
    from rag.verification_graph import index_quotes, materialize_draft, validate_support
    packet={'evidence':[{'id':'E1','text':'Review the maternal history. Missing measurements remain unknown.'}]}
    indexed,quotes=index_quotes(packet)
    assert 'text' not in indexed['evidence'][0]
    response={'claims':[{'id':'C1','section':'recommended_actions','text':'Review the recorded maternal history.','support':[{'quote_id':'E1Q1'}]}]}
    draft=materialize_draft(response,quotes)
    assert draft.claims[0].support[0].quote=='Review the maternal history.'
    assert validate_support(draft,packet)==[]
    response['claims'][0]['support'][0]['quote_id']='E99Q1'
    with pytest.raises(ValueError,match='Unknown immutable quote ID'):
        materialize_draft(response,quotes)


def test_retry_does_not_reuse_auditors_that_never_reviewed_a_draft():
    from scripts.evaluate_generation import replay_response
    role='You are an independent source-entailment auditor.'
    previous={'result':{'draft':{},'evidence_verdict':{'supported':False,'checked_claim_ids':[],'reasons':['Draft failed structural/source checks']}}}
    assert replay_response(previous,role) is None
    previous['result']['draft']={'claims':[{'id':'C1'}]}
    assert replay_response(previous,role) is None
    previous['result']['evidence_verdict']={'supported':False,'checked_claim_ids':['C1'],'rejected_claim_ids':['C1'],'reasons':['Unsupported claim']}
    assert replay_response(previous,role)['supported'] is False
