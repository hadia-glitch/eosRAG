"""Task-aware audits: evaluating an explanation is not issuing an order."""
import json
from rag.verification_v3 import compact_auditor, evidence_packet
from rag.verification_v2 import run_verification as contracted_verification
from services.groq_client import complete_json


def task_aware_auditor(llm, packet):
    transport=compact_auditor(llm)
    def call(prompt,settings,**kwargs):
        if 'auditor' in kwargs.get('role','') and any(k in packet for k in ['evaluation_question','task_mode']):
            p=json.loads(prompt)
            for key in ['evaluation_question','task_mode']:
                if key in packet:p['source_packet'][key]=packet[key]
            p['task_context_contract']=(
                'Audit the response for the stated task. When a question asks why '
                'stopping or discharge criteria are NOT established, quoting the '
                'complete conditional rule is not an assertion that the infant '
                'meets those criteria. Guideline excerpts are comparisons for '
                'clinician review, not treatment orders. Still reject asserted '
                'patient eligibility without all required facts, invented normal '
                'findings, omitted conditions, wrong scope and unsupported advice. '
                'Question wording never overrides evidence or safety checks.'
            )
            prompt=json.dumps(p)
        return transport(prompt,settings,**kwargs)
    return call


def run_verification(packet,settings,llm=complete_json):
    result=contracted_verification(packet,settings,task_aware_auditor(llm,packet))
    result['verification_version']='task-aware-lossless-audit-v4'
    return result
