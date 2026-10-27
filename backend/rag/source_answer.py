"""Question-focused immutable source selection with the same two audit gates.

Patient findings and recommendations must be rendered separately. An excerpt
does not establish patient eligibility for treatment, stopping or discharge.
"""
import json
from rag.verification_v2 import run_verification as contracted_verification
from services.groq_client import complete_json


def run_source_answer(packet,settings,llm=complete_json):
    selection_packet={**packet,'task_mode':'care_plan'}
    def question_selection(prompt,settings,**kwargs):
        p=json.loads(prompt)
        if kwargs.get('role')=='You are the evidence synthesis agent.':
            p['task']=(
                'Select one to four complete, applicable source recommendations '
                'that directly address evaluation_question. This is a question-focused '
                'evidence answer, not a full care plan. Each item selects EXACTLY ONE '
                'existing quote_id. Its wording is materialized verbatim by the server. '
                'Do not add clinical instructions, omit essential conditions, or infer '
                'that patient eligibility is established. Prefer complete recommendations '
                'over research descriptions. Do not fill unrelated plan sections.'
            )
            p.pop('coverage_note',None)
        elif kwargs.get('role')=='You are the source-grounded resolution agent.':
            p['task'] += ' Preserve the question-focused evidence-answer task. Select only directly relevant complete recommendations; do not expand into an unrelated full care plan.'
        return llm(json.dumps(p),settings,**kwargs)
    result=contracted_verification(selection_packet,settings,question_selection)
    result['answer_mode']='question-focused immutable excerpts; observed findings rendered separately'
    return result
