from scripts.evaluation_transport import quality_eligible,cached_role_response


def test_provider_errors_are_not_model_quality_outcomes():
    for code in ['http_429','http_401','http_503','ReadTimeout','ConnectError','unavailable']:
        assert not quality_eligible({'calls':[{'error_code':code}]})
    for code in ['JSONDecodeError','ValueError','model_json_contract_failure','finish_reason_length','incomplete_generation']:
        assert quality_eligible({'calls':[{'error_code':code}]})
    assert quality_eligible({'calls':[{'response':{'supported':False}}]})
    assert not quality_eligible({'calls':[{'ok':False}]})
    assert not quality_eligible({'calls':[], 'result':{'evidence_verdict':{'error_code':'http_429'}}})


def test_transport_retry_preserves_completed_invalid_answers_and_dissent():
    malformed={'claims':'wrong schema'}
    dissent={'supported':False,'reasons':['Unsupported inference']}
    previous={'calls':[{'role':'generator','response':malformed},
                       {'role':'judge','response':dissent},
                       {'role':'other judge','error_code':'http_429'}]}
    assert cached_role_response(previous,'generator') is malformed
    assert cached_role_response(previous,'judge') is dissent
    assert cached_role_response(previous,'other judge') is None


def test_changed_revision_prompt_never_reuses_a_review_of_other_claims():
    previous={'calls':[{'role':'judge','prompt_sha256':'old','response':{'supported':True}}]}
    assert cached_role_response(previous,'judge','new') is None
    assert cached_role_response(previous,'judge','old')=={'supported':True}
