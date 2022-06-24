

import numpy as np
import pandas as pd

from tankoh2.service.physicalprops import rhoGh2, rhoLh2Saturation, rhoGh2Saturation, \
    rhoLh2ByPSaturation, rhoGh2ByPSaturation

def test_rhoGh2NonCryo():
    assert np.allclose(0.0609, rhoGh2(0.1, 125 + 273.15), rtol=0.01)


# properties at equilibrium pressure
lh2Properties = pd.DataFrame(
    np.array([[13.96,        14,     16,     18,     20,    22,    24,    26,    28, 30, 32, 33.19],
              [0.00770, 0.00789, 0.0215, 0.0481, 0.0932, 0.163, 0.264, 0.403, 0.585, 0.850, 1.12, 1.33],
              [76.91,     76.87,  75.12,  73.22,  71.11, 68.73, 66.00, 62.80, 58.92, 53.84, 45.64, 30.12]]).T,
    columns=['T', 'p', 'rho'])  # 'T [K]', 'p [Mpa]', 'rho [kg/m^3]'
gh2Properties = pd.DataFrame(
    np.array([[13.96, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 33.19],
              [0.0077, 0.00789, 0.0215, 0.0481, 0.0932, 0.163, 0.264, 0.403, 0.585, 0.85, 1.12, 1.33],
              [0.1362, 0.1391, 0.338, 0.688, 1.243, 2.067, 3.244, 4.9, 7.258, 10.81, 17.5, 30.12]]).T,
    columns=['T', 'p', 'rho'])  # 'T [K]', 'p [Mpa]', 'rho [kg/m^3]'


def test_cryoProps():
    assert np.allclose(lh2Properties['rho'][:-1], rhoLh2Saturation(lh2Properties['T'][:-1]), rtol=0.05)
    assert np.allclose(gh2Properties['rho'][:-1], rhoGh2Saturation(lh2Properties['T'][:-1]), rtol=0.1)
    assert np.allclose(lh2Properties['rho'][:-1], rhoLh2ByPSaturation(lh2Properties['p'][:-1]), rtol=0.05)
    assert np.allclose(gh2Properties['rho'][:-1], rhoGh2ByPSaturation(lh2Properties['p'][:-1]), rtol=0.05)
