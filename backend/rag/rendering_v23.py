"""Preserve source/audit decisions while correcting observational rendering."""
from rag.verification_v7 import finalize as previous
from rag.offline_repairs_v23 import repair_rendering

def finalize(result,packet):
    return repair_rendering(previous(result,packet),packet)
