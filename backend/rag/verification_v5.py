"""Patient-specific explanation research adapter; strict two-auditor release."""
import json
from rag.verification_core_v5 import run_verification as core
from rag.verification_graph import Verdict
from rag.verification_v4 import task_aware_auditor
from rag.output_contracts import constrained_schema
from services.groq_client import complete_json


def run_verification(packet,settings,llm=complete_json):
    configured=settings.model_copy(update={'llm_schema_enforcement':True})
    audited=task_aware_auditor(llm,packet)
    def contracted(prompt,settings,**kwargs):
        payload=json.loads(prompt);role=kwargs.get('role','')
        if 'auditor' in role:
            ids=[c['id'] for c in payload['claims']]
            payload['output_schema']=Verdict.model_json_schema()
            payload['required_checked_claim_ids']=ids
            payload['response_contract']=(
                'Audit every claim ID exactly once. supported is a boolean; reasons '
                'is an array of strings explaining failures only. When supported=true, '
                'rejected_claim_ids and reasons must both be empty. Do not invent '
                'normal results or turn a conditional rule into established eligibility.'
            )
            kwargs['response_schema']=constrained_schema(Verdict,claim_ids=set(ids))
            kwargs['completion_tokens']=2400
        elif role=='You are the evidence synthesis agent.' and packet.get('task_mode')=='clinical_explanation':
            payload['task']=(
                'Answer evaluation_question for THIS recorded infant in three to five '
                'atomic, source-supported discussion claims, or fewer if evidence is '
                'insufficient. Connect recorded findings, genuine serial changes or '
                'explicit unknowns to the applicable source conditions and limitations. '
                'A generic quotation alone may fail to explain the case. Every factual '
                'patient statement must be supported by patient/history, and every '
                'guideline component by immutable quote IDs. Do not invent diagnosis, '
                'normal observations, treatment exposure or satisfied stopping criteria. '
                'Keep medication and discharge options conditional; no treatment orders '
                'or numeric doses. Do not invent laboratory units or diagnostic cutoffs; '
                'observed measurements are rendered separately. Return the required '
                'claim schema; do not generate a full unrelated care plan.'
            )
        elif role=='You are the source-grounded resolution agent.':
            payload['task']+=' Preserve the original case-specific question and explicit unknowns. Never add a risk category or claim clinical validation.'
        return audited(json.dumps(payload),settings,**kwargs)
    result=core(packet,configured,contracted)
    result['verification_version']='patient-specific-specimen-aware-v5-research'
    return result
