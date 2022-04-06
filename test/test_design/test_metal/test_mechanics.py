
import numpy as np

from tankoh2.design.metal.material import defaultMetalMaterial
from tankoh2.design.metal.mechanics import getWallThickness, getStress


def test_getWallThickness():
    thkRef = 0.00119189
    thk = getWallThickness(defaultMetalMaterial, 1, 1)
    assert np.allclose(thk, thkRef)


def test_getStress():
    sigRef = 300.125
    sig = getStress(0.25, 1.2*2, 0.001)
    assert np.allclose(sig, sigRef)

