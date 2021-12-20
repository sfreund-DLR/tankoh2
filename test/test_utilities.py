

from tankoh2.utilities import getHydrostaticPressure
import numpy as np


def test_getHydrostaticPressure():
    locLengthHeightBaffles = [
        ('fuselage', 1, 1, None),
        ('fuselage', 3, 1, 1),
        ('fuselage', 0.5, 1.5, None),
        ('wing_no_engine', 2, 1, None),
        ('wing_no_engine', 1, 1.5, None),
        ('wing_no_engine', 3, 1, 2),
        ('wing_at_engine', 1, 1, None),
        ('wing_at_engine', 0.5, 1.5, None),
    ]
    r = []
    for loc, length, height, baffle in locLengthHeightBaffles:
        r.append(getHydrostaticPressure(loc, length, height, baffle))
    r = np.array(r)
    assert np.all(np.abs(r-r[0] < 1e-8)) # check if all equal



