"""Transport smoke test with synthetic content only. Prints no secrets/prompts."""
from config import get_settings
from services.groq_client import complete_json, GenerationUnavailable

if __name__ == '__main__':
    s = get_settings()
    try:
        result = complete_json('Synthetic connectivity test; no patient data. Return {"ok": true}.', s, role='You are testing the JSON transport only.')
        print({'transport_ok': result.get('ok') is True, 'model': s.groq_model})
    except GenerationUnavailable as exc:
        cause = exc.__cause__
        print({'transport_ok': False, 'reason': 'Provider unavailable or unconfigured',
               'error_type': type(cause).__name__ if cause else 'configuration',
               'http_status': getattr(getattr(cause, 'response', None), 'status_code', None)})
        raise SystemExit(1)
