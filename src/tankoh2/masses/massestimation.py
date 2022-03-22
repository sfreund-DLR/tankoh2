"""very rough estimations of liner and insulation mass"""

from tankoh2.masses.massdata import insulationDens, linerDens, fairingDens


def getLinerMass(liner, linerMatName = None, linerThickness = 0.5):
    """
    :param liner: object of type tankoh2.geometry.liner.Liner
    :param linerMatName: name of liner material in linerDens
    :param linerThickness: thickness of the liner [mm]
    """
    if linerMatName in linerDens:
        rho = linerDens[linerMatName]  # [kg/m**3]
    else:
        rho = next(iter(linerDens.values()))

    volume = liner.getWallVolume(-1*linerThickness) /1000/1000/1000
    return abs(rho * volume)


def getInsulationMass(liner, insulationMatName = None,
                      insulationThickness = 127  # source Brewer fig 3-6
                      ):
    """
    :param liner: object of type tankoh2.geometry.liner.Liner
    :param insulationMatName: name of insulation material in linerDens
    :param insulationThickness: thickness of the insulation [mm]
    """
    if insulationMatName in linerDens:
        rho = insulationDens[insulationMatName]  # [kg/m**3]
    else:
        rho = next(iter(insulationDens.values()))

    volume = liner.getWallVolume(insulationThickness) /1000/1000/1000
    return rho * volume


def getFairingMass(liner, fairingMatName = None, fairingThickness = 0.5, insulationCfrpThickness = 127):
    """
    :param liner: object of type tankoh2.geometry.liner.Liner
    :param fairingMatName: name of fairing material in linerDens
    :param fairingThickness: thickness of the fairing [mm]
    :param insulationCfrpThickness: thickness of the cfrp or metal structure and insulation [mm]
    """
    if fairingMatName in linerDens:
        rho = fairingDens[fairingMatName]  # [kg/m**3]
    else:
        rho = next(iter(fairingDens.values()))

    liner = liner.getLinerResizedByThickness(insulationCfrpThickness)
    volume = liner.getWallVolume(fairingThickness) /1000/1000/1000
    return rho * volume



