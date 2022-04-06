import numpy as np
import pytest

from tankoh2.design.metal.fatigue import getCyclesToFailure, stressLifeMinerRule, \
    getFatigueLifeAircraftTanks, correctSnParameters
from tankoh2.design.metal.material import alu6061T6
from tankoh2.service.exception import Tankoh2Error


def test_getCyclesToFailure():
    # comparison with excel chart scenario #2 first row
    A1, A2, A3, A4 = alu6061T6['SN_parameters']
    A1, A4 = correctSnParameters(A1, A2, A4, alu6061T6['Kt_curve'], 1.2, 1)
    nf = getCyclesToFailure(187.05, 0., A1, A2, A3, A4)
    assert np.allclose(nf, 6.250796E+5, rtol=1e-3)


def test_getCyclesToFailure_Fail1():
    # comparison with excel chart scenario #2 first row
    A1, A2, A3, A4 = alu6061T6['SN_parameters']
    A1, A4 = correctSnParameters(A1, A2, A4, alu6061T6['Kt_curve'], 1.2, 1)
    with pytest.raises(Tankoh2Error):
        getCyclesToFailure(100., 187.05, A1, A2, A3, A4)


def test_getCyclesToFailure_Fail2():
    # comparison with excel chart scenario #2 first row
    A1, A2, A3, A4 = alu6061T6['SN_parameters']
    A1, A4 = correctSnParameters(A1, A2, A4, alu6061T6['Kt_curve'], 1.2, 1)
    with pytest.raises(Tankoh2Error):
        getCyclesToFailure(0., 187.05, A1, A2, A3, A4)


def test_stressLifeMinerRule():
    # comparison with excel chart scenario #2
    A1, A2, A3, A4 = alu6061T6['SN_parameters']
    A1, A4 = correctSnParameters(A1, A2, A4, alu6061T6['Kt_curve'], 1.2, 1)
    nf = getCyclesToFailure([187.05, 187.05], [0., 115.49], A1, A2, A3, A4)
    occurences = np.array([5000, 50000])
    damage = stressLifeMinerRule(occurences, nf)
    assert np.allclose(damage, 8.2061E-3, rtol=1e-3)


def test_getFatigueLifeAircraftTanks():
    # use scenario 2 of excel sheet
    scatter = 10
    ref = 8.206100E-03 * scatter
    fatigueLife = getFatigueLifeAircraftTanks(alu6061T6, 187.05, 115.49, 50000 * scatter, 5000 * scatter, 1.2)
    assert np.allclose(fatigueLife, ref, rtol=1e-3)
