
import numpy as np
from tankoh2.design.designutils import getRequiredVolume, getLengthRadiusFromVolume


def test_getRequiredVolume():
    #from brewer ch 4.4.1
    m = 30815  # lb
    p = 21  # psi
    v = getRequiredVolume(m, p, roh=4.326, maxFill=1/1.072)
    vRef = 7636 # lb/ft3
    assert abs(1-v/vRef) < 2e-5

def test_getLengthRadiusFromVolume():
    r1,l1 = getLengthRadiusFromVolume(100 * 1e6, # l → mm**3
                                      mode='quick', domeType='ellipse')
    r2,l2 = getLengthRadiusFromVolume(100 * 1e6, domeType='ellipse')
    assert np.allclose([r1,l1], [r2,l2])

