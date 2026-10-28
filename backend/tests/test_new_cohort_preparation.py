import pytest
from ml.evaluate_new_cohorts import gestation


def test_gestational_days_are_not_decimal_weeks():
    assert gestation('30+6')==pytest.approx(30+6/7)
    assert gestation('36')==36
    assert gestation(' 32+0 ')==32


@pytest.mark.parametrize('value',['30+7','30+-1','unknown','30+2+1'])
def test_invalid_gestational_age_is_not_silently_imputed(value):
    with pytest.raises(ValueError):gestation(value)
