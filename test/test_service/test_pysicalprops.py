

import numpy as np

from tankoh2.service.pyhsicalprops import rhoGh2NonCryo

def test_rhoGh2NonCryo():
    assert np.allclose(-1., rhoGh2NonCryo(50,22))
    assert np.allclose(0.0609, rhoGh2NonCryo(0.1,125+273.15))
