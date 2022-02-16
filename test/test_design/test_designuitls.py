

from tankoh2.design.designutils import getRequiredVolume


def test_getRequiredVolume():
    #from brewer ch 4.4.1
    m = 30815  # lb
    p = 21  # psi
    v = getRequiredVolume(m, p, roh=4.326)
    vRef = 7636 # lb/ft3
    assert abs(1-v/vRef) < 2e-5



