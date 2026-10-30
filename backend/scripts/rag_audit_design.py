"""Deterministic wording stresses; no new patients or changed gold annotations.

These transformations are engineering paraphrases requiring clinician review.
They preserve recorded patient/history objects and explicit numeric tokens.
They are not an independently authored external clinical test.
"""
import re
from rag.relevance import focus_query

SHORT=[(r'\bblood cultures?\b','BCx'),(r'\brespiratory rate\b','RR'),
       (r'\boxygen saturation\b','SpO2'),(r'\bC-reactive protein\b','CRP'),
       (r'\bantibiotics?\b','ABx'),(r'\b36 hours\b','36 h'),
       (r'\brespiratory distress\b','breathing difficulty'),
       (r'\bclinical assessment\b','bedside evaluation'),
       (r'\bexaminations?\b','bedside evaluations')]
PLAIN=[(r'\bC-reactive protein\b','C reactive protein'),(r'\bCRP\b','C reactive protein'),
       (r'\binflammatory[- ]markers?\b','blood measurements related to inflammation'),
       (r'\brisk stratification\b','evaluation of predisposition to infection'),
       (r'\brisk factors?\b','predisposing feature'),(r'\bmaternal history\b','the recorded maternal background'),
       (r'\bhistory\b','background'),(r'\bexaminations?\b','bedside findings'),
       (r'\bclinical assessment\b','bedside evaluation'),
       (r'\bExplain\b','Describe'),(r'\bReview\b','Discuss'),(r'\bAssess\b','Consider'),
       (r'\buncertainty\b','incomplete information'),(r'\bmanagement options\b','care options')]


def variants(query):
    q=focus_query(query);out={'original':q}
    for name,changes in [('clinical_shorthand',SHORT),('plain_language',PLAIN)]:
        text=q
        for pattern,replacement in changes:text=re.sub(pattern,replacement,text,flags=re.I)
        # SpO2 is a measurement abbreviation, not a new numerical observation.
        numbers=r'(?<!\w)\d+(?:\.\d+)?(?!\w)'
        if re.findall(numbers,text)!=re.findall(numbers,q):
            raise ValueError('A wording transformation changed a numeric token')
        for token in ['not','without','no','negative','unavailable','missing']:
            if len(re.findall(r'\b'+token+r'\b',q,re.I))!=len(re.findall(r'\b'+token+r'\b',text,re.I)):
                raise ValueError('A wording transformation changed an explicit negative/unknown token')
        out[name]=text
    return out
