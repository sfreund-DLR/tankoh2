

import numpy as np

from tankoh2.mechanics.fatigue import getCyclesToFailure


def test_getCyclesToFailure():
    refCycles = 1398723709
    cycles = getCyclesToFailure(187, 115, 20.68, -9.84, 0.63, 0)
    assert np.allclose(refCycles, cycles)



