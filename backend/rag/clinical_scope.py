"""Deterministic applicability checks using explicit passage scope metadata.

This never infers patient facts, selects a treatment or grants source approval.
Unknown required patient values fail applicability; source review is separate.
"""
import math

HOSPITAL={'hospital','hospital_birth','postnatal_ward','neonatal_unit','nicu','transitional_care'}
OUTPATIENT={'non_hospital','primary_health_clinic','community_clinic','outpatient','health_centre','community'}


def setting_class(value):
    if value in HOSPITAL:return 'hospital'
    if value in OUTPATIENT:return 'non_hospital'
    return None


def applicable(scope,patient):
    if not isinstance(scope,dict):return False
    for field,bounds_name in [('age_hours','postnatal_age_hours'),('gestational_age_weeks','gestational_age_weeks')]:
        bounds=scope.get(bounds_name)
        if bounds is None:continue
        if len(bounds)!=2:return False
        lo,hi=bounds
        if lo is None and hi is None:continue
        value=patient.get(field)
        if type(value) not in (int,float) or not math.isfinite(value):return False
        if lo is not None and value<lo:return False
        if hi is not None and value>hi:return False
    settings=scope.get('care_setting',[])
    if settings:
        allowed={setting_class(s) for s in settings}-{None}
        actual=setting_class(patient.get('care_setting'))
        if not actual or actual not in allowed:return False
    return True
