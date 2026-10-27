"""Contract-hardened verification adapter; historical experiment stays frozen.

Audits still fail closed on missing IDs, contradictory verdicts or unsupported
claims. This changes future prompts/decoding, never repairs saved verdicts.
"""
import json

from rag.verification_graph import (
    Verdict, evidence_packet, run_verification as frozen_verification,
)
from rag.output_contracts import constrained_schema
from services.groq_client import complete_json


def run_verification(packet, settings, llm=complete_json):
    configured = settings.model_copy(update={'llm_schema_enforcement': True})

    def contracted(prompt, settings, **kwargs):
        payload = json.loads(prompt)
        role = kwargs.get('role', '')
        if 'auditor' in role:
            ids = [c['id'] for c in payload['claims']]
            payload['output_schema'] = Verdict.model_json_schema()
            payload['required_checked_claim_ids'] = ids
            payload['response_contract'] = (
                'Return supported as a JSON boolean, checked_claim_ids as an array '
                'containing every reviewed ID exactly once, rejected_claim_ids as an '
                'array of failed IDs, and reasons as an ARRAY OF STRINGS, never an '
                'object keyed by claim. Do not assume an unreviewed claim passes. '
                'Reasons must explain failures only. A conditional statement does '
                'not establish that its patient eligibility criteria have been met.'
            )
            kwargs['response_schema'] = constrained_schema(Verdict, claim_ids=set(ids))
            # Reasoning tokens share the completion budget. The previous 1,000
            # token budget and absent explicit prompt schema caused malformed
            # audits. Keep the limit bounded, but leave room for all claim IDs.
            kwargs['completion_tokens'] = 2400
        elif role == 'You are the evidence synthesis agent.' and packet.get('task_mode') != 'care_plan':
            payload['task'] += (
                ' Answer only the evaluation question in three to five atomic claims '
                'when evidence permits; fewer are allowed. Do not pad to six claims '
                'or fill unrelated monitoring, treatment or escalation headings. '
                'Do not turn study descriptions into clinical recommendations. '
                'If evidence cannot answer a subquestion, state the evidence gap '
                'outside the claims rather than inventing clinical instructions.'
            )
        return llm(json.dumps(payload), settings, **kwargs)

    result = frozen_verification(packet, configured, llm=contracted)
    result['verification_version'] = 'explicit-audit-contract-v2'
    return result
