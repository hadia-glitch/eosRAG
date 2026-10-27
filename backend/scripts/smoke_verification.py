"""Live Groq/LangGraph integration test using a fictional, non-treatment
protocol fixture. Never adds fixture evidence to a production registry.
"""
from config import get_settings
from rag.verification_graph import run_verification

if __name__ == '__main__':
    packet = {'guideline': 'SYNTHETIC INTEGRATION FIXTURE', 'patient': {'age_hours': 6}, 'history': [],
              'evaluation_question':'State only the recordkeeping details explicitly requested in this fictional protocol. One short discussion point is sufficient.',
              'evidence': [{'id': 'E1', 'chunk_id': 'synthetic-fixture-not-clinical-evidence',
                            'source': 'Synthetic test protocol', 'version': 'test-only', 'section': 'Documentation',
                            'text': 'During a research simulation of early-onset neonatal sepsis assessment for an infant aged six hours, record the assessment time and observed measurements for clinician review. This fictional documentation protocol contains no treatment recommendations.'}]}
    s = get_settings()
    result = run_verification(packet, s)
    print({'status': result['status'], 'generator_model': s.groq_model, 'verifier_model': s.verifier_model,
           'claims': len(result.get('draft', {}).get('claims', [])), 'errors': result.get('errors', []),
           'error_codes': [result.get(k, {}).get('error_code') for k in ('evidence_verdict','safety_verdict')], 'synthetic': True})
    raise SystemExit(0 if result['status'] == 'supported_for_review' else 1)
