"""Validate search questions against task data and the explicit EOS system scope."""
import re

def validate_questions(questions,original):
    if not isinstance(questions,list) or not 1<=len(questions)<=3:return False,'question_count'
    numbers=set(re.findall(r'\d+(?:\.\d+)?',original))
    for q in questions:
        if not isinstance(q,str) or not 8<=len(q)<=400:return False,'query_shape'
        normalized=re.sub(r'[\u2010-\u2015]','-',q)
        # The transport's system message already supplies the 0-72-hour EOS
        # population. This permits age scope, not a 72-hour treatment rule.
        normalized=re.sub(r'(?i)(?:neonates?|newborns?|infants?)\s+(?:aged\s+)?0\s*-\s*72\s*(?:hours?|h)\b','EOS population',normalized)
        normalized=re.sub(r'(?i)(early[- ]onset\s+neonatal\s+sepsis)\s*\(0\s*-\s*72\s*hours?\)',r'\1',normalized)
        normalized=re.sub(r'(?i)(?:first\s+72\s+hours?\s+of\s+life|initial\s+0\s*-\s*72\s*hour\s+period)','EOS population',normalized)
        # Some questions use 'first 72 hours' after explicitly naming newborns.
        if re.search(r'(?i)\b(?:neonate|newborn|infant)',normalized):
            normalized=re.sub(r'(?i)(?:during|within)\s+(?:the\s+)?first\s+72\s+hours?\b','during the EOS population window',normalized)
        if set(re.findall(r'\d+(?:\.\d+)?',normalized))-numbers:return False,'unsupported_numeric_detail'
        if re.search(r'\b(?:NICE-|AAP2018-|WHO2024-|1\.\d+\.\d+)\b',q):return False,'citation_identifier'
        if re.search(r'(?i)\b\d+(?:\.\d+)?\s*(?:mg|mcg|ml)\b',q):return False,'dose_detail'
    return True,None
