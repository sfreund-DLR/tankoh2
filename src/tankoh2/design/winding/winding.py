"""performs the winding of one layer and provides target functions for optimizers"""

import numpy as np

from tankoh2.geometry.geoutils import getRadiusByShiftOnContour
from tankoh2 import log


def getPolarOpeningDiffByAngleBandMid(angle, args):
    """calculates the difference of a target polar opening (PO) compared to the actual PO based on given angle

    The method uses the band middle PO and adds half a band width

    :param angle: angle of the helical layer
    :param args: tuple: vessel, layerNumber (zero-based), targetPolarOpening
    :return: diff of polar openings
    """
    vessel, layerNumber, targetPolarOpening, bandWidth = args
    log.debug(f'angle {angle}')
    bandMidPo = windLayer(vessel, layerNumber, angle, useBandMid=True)
    outerMandrel = vessel.getVesselLayer(layerNumber).getOuterMandrel1()
    actualPolarOpening = getRadiusByShiftOnContour(outerMandrel.getRArray(), outerMandrel.getLArray(),
                                                   bandMidPo, bandWidth / 2)
    log.debug(f'angle {angle}, band mid PO {bandMidPo}, actualPolarOpening {actualPolarOpening}, targetPolarOpening {targetPolarOpening}')
    return abs(targetPolarOpening - actualPolarOpening)


def getPolarOpeningDiffByAngle(angle, args):
    """calculates the difference of a target polar opening (PO) compared to the actual PO based on given angle

    :param angle: angle of the helical layer
    :param args: tuple: vessel, layerNumber (zero-based), targetPolarOpening
    :return: diff of polar openings
    """
    vessel, layerNumber, targetPolarOpening = args
    log.debug(f'angle {angle}')
    actualPolarOpening = windLayer(vessel, layerNumber, angle)
    log.debug(f'angle {angle}, actualPolarOpening {actualPolarOpening}, targetPolarOpening {targetPolarOpening}')
    return abs(targetPolarOpening - actualPolarOpening)


def getNegAngleAndPolarOpeningDiffByAngle(angle, args):
    vessel, layerNumber, targetPolarOpening = args
    log.debug(f'angle {angle}')
    actualPolarOpening = windLayer(vessel, layerNumber, angle)
    funVal = -1*angle + abs(targetPolarOpening - actualPolarOpening)
    log.debug(f'angle {angle}, target function val {funVal}, actualPolarOpening {actualPolarOpening}, targetPolarOpening {targetPolarOpening}')
    return funVal


def getAngleAndPolarOpeningDiffByAngle(angle, args):
    vessel, layerNumber, targetPolarOpening = args
    log.debug(f'angle {angle}')
    actualPolarOpening = windLayer(vessel, layerNumber, angle)
    funVal = angle + abs(targetPolarOpening - actualPolarOpening)
    log.debug(f'angle {angle}, target function val {funVal}, actualPolarOpening {actualPolarOpening}, targetPolarOpening {targetPolarOpening}')
    return funVal


def windHoopLayer(vessel, layerNumber, shift = 0):
    """wind up to the given layer(0-based count) and return polar opening angle"""
    vessel.setLayerAngle(layerNumber, 90)
    if shift:
        vessel.setHoopLayerShift(layerNumber, shift, True)
    vessel.runWindingSimulation(layerNumber + 1)


def windLayer(vessel, layerNumber, angle=None, useBandMid=False):
    """wind up to the given layer and return polar opening angle

    :param vessel: µWind vessel instance
    :param layerNumber: number of the layer to wind (0-based indexed)
    :param angle: angle of the layer to wind [°]. If no angle is given, the angle should be given in the
        actual µWind design.
    :param useBandMid: flag if the band middle polar opening should be used or the bottom PO
    :return: polar opening radius of the new layer [mm] (outer band - not mid)
    """

    if angle:
        vessel.setLayerAngle(layerNumber, angle)
    try:
        vessel.runWindingSimulation(layerNumber + 1)
    except (RuntimeError, IndexError) as e:
        if 'bandmiddle path crossed polar opening!' in str(e):
            log.debug(f'Got an error at angle {angle}: {e}')
            return np.inf
        if isinstance(e, IndexError):
            log.debug(f'Got an error at angle {angle}. '
                      f'Maybe due to too small polar opening relative to cylindrical radius. '
                      f'Error message: {e}')
            return np.inf
        if 'Polar Opening too small - Thickness Error!' in str(e):
            log.warning(f'Got this error during winding: {e}')
            return np.inf
        else:
            raise

    if useBandMid:
        return vessel.getPolarOpeningRadiusBandMiddle(layerNumber, True)
    else:
        return vessel.getPolarOpeningR(layerNumber, True)

def getPolarOpeningDiffHelical(friction, args):
    vessel, targetPolarOpeningR, layerindex = args
    vessel.setLayerFriction(layerindex, friction[0], True)
    try:
        vessel.runWindingSimulation(layerindex + 1)
        polarOpeningR = vessel.getPolarOpeningR(layerindex, True)
    except (IOError, ValueError, IOError, ZeroDivisionError):
        raise

    log.debug(f"layer {layerindex}, friction {friction}, po actual {polarOpeningR}, po target {targetPolarOpeningR}, po diff {polarOpeningR-targetPolarOpeningR}")
    # log.info('this helical layer shoud end at', wendekreisradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', wendekreisradius[layerindex]-wk, 'mm') if abs(wendekreisradius[layerindex]-wk) < 2.:
    # arr_fric.append(abs(friction)) arr_wk.append(wk)

    return abs(polarOpeningR - targetPolarOpeningR)


def getPolarOpeningDiffHelicalUsingLogFriction(friction, args):
    vessel, wendekreisradius, layerindex = args
    vessel.setLayerFriction(layerindex, 10.**friction[0], True)
    try:
        vessel.runWindingSimulation(layerindex + 1)
        wk = vessel.getPolarOpeningR(layerindex, True)
    except (IOError, ValueError, IOError, ZeroDivisionError, RuntimeError):
        raise

    log.debug(f"layer {layerindex}, friction {10.**friction}, po actual {wk}, po target {wendekreisradius}, po diff {wk-wendekreisradius}")
    # log.info('this helical layer shoud end at', wendekreisradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', wendekreisradius[layerindex]-wk, 'mm') if abs(wendekreisradius[layerindex]-wk) < 2.:
    # arr_fric.append(abs(friction)) arr_wk.append(wk)

    return abs(wk - wendekreisradius)

def getPolarOpeningDiffHelicalUsingNegativeLogFriction(friction, args):
        
    vessel, wendekreisradius, layerindex = args
    vessel.setLayerFriction(layerindex, -1.0*abs(10.**friction[0]), True)
    try:
        vessel.runWindingSimulation(layerindex + 1)
        wk = vessel.getPolarOpeningR(layerindex, True)
    except (IOError, ValueError, IOError, ZeroDivisionError, RuntimeError):
        log.info('I have to pass')
        wk = 0.
        pass

    log.debug(f"layer {layerindex}, friction {10.**friction}, po actual {wk}, po target {wendekreisradius}, po diff {wk-wendekreisradius}")
    # log.info('this helical layer shoud end at', wendekreisradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', wendekreisradius[layerindex]-wk, 'mm') if abs(wendekreisradius[layerindex]-wk) < 2.:
    # arr_fric.append(abs(friction)) arr_wk.append(wk)

    return abs(wk - wendekreisradius)

def getPolarOpeningDiffHoop(shift, args):
    vessel, krempenradius, layerindex = args
    vessel.setHoopLayerShift(layerindex, shift, True)
    try:
        vessel.runWindingSimulation(layerindex + 1)
        wk = vessel.getPolarOpeningR(layerindex, True)
    except (IOError, ValueError, IOError, ZeroDivisionError, RuntimeError):
        raise

    log.debug(f"layer {layerindex}, shift {shift}, po actual {wk}, po target {krempenradius}, po diff {wk - krempenradius}")

    # log.info('this hoop layer shoud end at', krempenradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', krempenradius[layerindex]-wk, 'mm')

    return abs(wk - krempenradius)

def getPolarOpeningXDiffHoop(shift, args):
    vessel, polarOpeningX, layerindex = args
    vessel.setHoopLayerShift(layerindex, shift, True)
    try:
        vessel.runWindingSimulation(layerindex + 1)
        wk = vessel.getPolarOpeningX(layerindex, True)
    except (IOError, ValueError, IOError, ZeroDivisionError, RuntimeError):
        raise

    log.debug(f"layer {layerindex}, shift {shift}, po actual {wk}, po target {polarOpeningX}, po diff {wk - polarOpeningX}")

    # log.info('this hoop layer shoud end at', krempenradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', krempenradius[layerindex]-wk, 'mm')

    return abs(wk - polarOpeningX)


