"""Lightweight units and causal availability rules shared by train and serve."""
import math

VERSION='pic-longitudinal-v1'
BOUNDS={'neonatal_temperature':(30.,43.),'heart_rate':(30.,300.),
        'respiratory_rate':(0.,150.),'spo2':(20.,100.),'pulse_rate':(30.,300.),
        'diastolic_pressure':(5.,150.),'systolic_pressure':(10.,200.),'measured_weight_kg':(.2,6.5)}


def available_events(events,index_age,lookback=24.):
    selected=[]
    for event in events:
        t,known=event['age_hours'],event['available_age_hours']
        if not (math.isfinite(t) and math.isfinite(known)) or known<t:
            raise ValueError('Invalid measurement/availability chronology')
        if 0<=t<=index_age and known<=index_age and t>=index_age-lookback:selected.append(event)
    return selected
