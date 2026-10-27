"""Keep provider availability out of model-quality scores.

Completed but malformed, truncated, unsupported or rejected model answers remain
quality outcomes. Rate limits, connection failures and service errors are logged
separately and cannot count as either semantic failures or successful safeguards.
"""

def provider_failure(code):
    if not code:return False
    return code not in {'JSONDecodeError','finish_reason_length',
                        'finish_reason_content_filter','finish_reason_tool_calls',
                        'incomplete_generation'}


def quality_eligible(record):
    # Legacy attempts did not capture the exception class. Their incomplete
    # execution cannot be assigned a model-quality outcome retrospectively.
    if any(c.get('ok') is False and not c.get('error_code') and not c.get('retried')
           for c in record.get('calls',[])):return False
    result=record.get('result',{})
    codes=[result.get('generation_error_code'),
           result.get('resolution_error_code'),
           result.get('evidence_verdict',{}).get('error_code'),
           result.get('safety_verdict',{}).get('error_code')]
    codes += [c.get('error_code') for c in record.get('calls',[]) if not c.get('retried')]
    return not any(provider_failure(code) for code in codes)


def cached_role_response(record,role,prompt_sha256=None):
    # Preserve completed model errors/dissent too: replacing these with a more
    # favorable answer would change the quality experiment, not fix transport.
    for call in reversed(record.get('calls',[])):
        if call.get('role')!=role or 'response' not in call:continue
        if prompt_sha256 is not None:
            recorded=call.get('prompt_sha256')
            if recorded and recorded!=prompt_sha256:continue
            if not recorded and record.get('result',{}).get('resolution_trace'):continue
        if call.get('role')==role and 'response' in call:
            return call['response']
    return None
