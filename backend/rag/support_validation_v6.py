"""Versioned dose guard: measured concentrations are not drug doses."""
import re
from rag.support_validation_v5 import validate_support as previous

DOSE=re.compile(r'\b(?:administer|give|infuse|inject|bolus|dose|dosage|transfuse)\b|\b(?:ampicillin|amoxicillin|gentamicin|benzylpenicillin|penicillin)\b',re.I)
CONCENTRATION=re.compile(r'\b\d+(?:\.\d+)?\s*(?:mg|mcg|micrograms?)\s*/\s*(?:L|dL|mL)\b',re.I)
QUANTITY=re.compile(r'\b\d+(?:\.\d+)?\s*(?:mg|mcg|micrograms?|mL|units?)\b',re.I)


def validate_support(draft,packet):
    errors=previous(draft,packet)
    for c in draft.claims:
        # Only a laboratory concentration discussion qualifies. A dose/infusion
        # verb or drug name keeps the therapeutic-quantity guard in force.
        if not re.search(r'\b(?:CRP|C.reactive protein|creatinine|procalcitonin|lactate)\b',c.text,re.I) or DOSE.search(c.text):continue
        stripped=CONCENTRATION.sub('',c.text)
        if CONCENTRATION.search(c.text) and not QUANTITY.search(stripped):
            errors=[e for e in errors if e!=f'{c.id}: numerical medication/fluid dosing is not supported']
    return errors
