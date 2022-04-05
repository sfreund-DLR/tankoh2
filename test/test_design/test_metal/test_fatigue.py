
import numpy as np
import pytest

from tankoh2.design.metal.material import alu6061T6
from tankoh2.service.exception import Tankoh2Error
from tankoh2.design.metal.fatigue import getCyclesToFailure, stressLifeMinerRule, getFatigueLifeAircraftTanks


def test_getCyclesToFailure():
    # comparison with excel chart scenario #2 first row
    nf = getCyclesToFailure(187.05, 0., *(alu6061T6['SN_parameters']), 1.2)
    assert np.allclose(nf, 6.250796E+5, rtol=1e-3)

def test_getCyclesToFailure_Fail1():
    # comparison with excel chart scenario #2 first row
    with pytest.raises(Tankoh2Error):
        getCyclesToFailure(100., 187.05, *(alu6061T6['SN_parameters']), 1.2)

def test_getCyclesToFailure_Fail2():
    # comparison with excel chart scenario #2 first row
    with pytest.raises(Tankoh2Error):
        getCyclesToFailure(0., 187.05, *(alu6061T6['SN_parameters']), 1.2)


def test_stressLifeMinerRule():
    # comparison with excel chart scenario #2
    nf = getCyclesToFailure([187.05, 187.05], [0., 115.49], *(alu6061T6['SN_parameters']), 1.2)
    occurences = np.array([5000, 50000])
    damage = stressLifeMinerRule(occurences, nf)
    assert np.allclose(damage, 8.2061E-3, rtol=1e-3)


def test_getFatigueLifeAircraftTanks():
    # use scenario 2 of excel sheet
    scatter = 10
    ref = 8.206100E-03 * scatter
    fatigueLife = getFatigueLifeAircraftTanks(alu6061T6, 187.05, 115.49, 50000 * scatter, 5000*scatter, 1.2)
    assert np.allclose(fatigueLife, ref, rtol=1e-3)
