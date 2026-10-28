"""Task routing for source topics, distinct from medical eligibility/approval.

Background remains searchable explicitly. These rules do not infer a diagnosis,
treatment exposure or test result, and do not establish semantic correctness.
"""
import re


def current_case_topic(chunk, query, patient):
    text=chunk['raw_text'];q=query.lower()
    if re.search(r'\b(?:future pregnancies|become pregnant again|subsequent pregnanc)',text,re.I):
        if not re.search(r'\b(?:future pregnanc|pregnant again|subsequent pregnanc)',q):
            return False,'future_pregnancy_counselling_not_requested'
    if re.search(r'\b(?:antibiotics during labour|intrapartum antibiotic prophylaxis|managing prelabour rupture)\b',text,re.I):
        if not re.search(r'\b(?:intrapartum|during labo[ur]+|prophylaxis|prelabour|before birth)\b',q):
            return False,'maternal_intrapartum_management_not_requested'
    if re.search(r'^For (?:women|pregnant)',text,re.I) and re.search(r'\bin labour\b',text,re.I):
        if not re.search(r'\b(?:intrapartum|during labo[ur]+|before birth|maternal assessment)\b',q):
            return False,'maternal_labour_assessment_not_requested'
    if re.search(r'^Interpret\b.{0,35}\b(?:CSF|cerebrospinal fluid)\b',text,re.I):
        recorded=any(patient.get(k) is not None for k in ['csf_results','csf_wbc','csf_glucose','csf_protein'])
        if not recorded and not re.search(r'\b(?:csf|cerebrospinal|lumbar puncture|meningitis)\b',q):
            return False,'csf_interpretation_without_requested_or_recorded_csf_context'
    return True,'topic_not_excluded'
