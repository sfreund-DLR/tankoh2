"""Utility functions for design"""


from tankoh2.service.pyhsicalprops import rhoLh2ByP


def getRequiredVolume(lh2Mass, operationalPressure, volumetricAllowance = 0.072, roh=None):
    """Calculate volume according to mass and operational pressure according to Brewer ch. 4.4.1
    :param lh2Mass: mass of lh2 [kg]
    :param operationalPressure: operational pressure [MPa]
    """
    if roh is None:
        roh = rhoLh2ByP(operationalPressure) # roh at 22K
    v = lh2Mass * (1/(roh/(1+volumetricAllowance)))
    return v


