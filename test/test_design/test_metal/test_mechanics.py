
import numpy as np

from tankoh2.design.designmetal.mechanics import getWallThickness

def test_getWallThickness():
    thkRef = 0.0029086678
    thk = getWallThickness('defaultMetalMaterial', 1, 1)
    assert np.allclose(thk, thkRef)



