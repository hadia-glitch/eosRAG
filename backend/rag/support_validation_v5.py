"""Development validator distinguishing verbatim specimen text from dosing.

The historical validator is retained. This narrow exception does not authorize
sampling, change source approval or replace semantic and patient-safety audits.
"""
import re
from rag.verification_graph import validate_support as historical_validate_support

QUANTITY = re.compile(r'\b(\d+(?:\.\d+)?)\s*(mg|mcg|microgram|ml|units?)(?:\b|/)', re.I)


def is_verbatim_specimen_claim(claim):
    if claim.section != 'investigations':
        return False
    text = ' '.join(claim.text.split())
    if not any(text in ' '.join(s.quote.split()) for s in claim.support):
        return False
    matches = list(QUANTITY.finditer(text))
    if not matches:
        return False
    for match in matches:
        if match.group(2).lower() != 'ml':
            return False
        before = text[max(0, match.start() - 100):match.start()]
        after = text[match.end():match.end() + 70]
        # A culture inoculum described in a verbatim source sentence is not a
        # medication/fluid dose. Other mL uses continue to fail closed.
        if not re.search(r'\bblood\s+(?:sample|specimen|volume)\b[^.!?;]{0,60}$', before, re.I):
            return False
        if not re.search(r'^[^.!?;]{0,50}\b(?:inoculat\w*|cultur\w*)\b', after, re.I):
            return False
        if re.search(r'\b(?:administer\w*|infus\w*|transfus\w*|bolus|flush\w*)\b', before + after, re.I):
            return False
    return True


def validate_support(draft, packet):
    errors = historical_validate_support(draft, packet)
    exceptions = {f'{claim.id}: numerical medication/fluid dosing is not supported'
                  for claim in draft.claims if is_verbatim_specimen_claim(claim)}
    # Unknown labels, altered source quotes, duplicate claims and every other
    # historical error survive this exception unchanged.
    return [error for error in errors if error not in exceptions]
