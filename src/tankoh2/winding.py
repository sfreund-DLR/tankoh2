"""performs the winding of one layer and provides target functions for optimizers"""


from tankoh2 import log

def getPolarOpeningDiffByAngle(angle, args):
    vessel, layerNumber, targetPolarOpening, verbose = args
    if verbose:
        log.info(f'angle {angle}')
    actualPolarOpening = windLayer(vessel, layerNumber, angle, verbose)
    if verbose:
        log.info(f'angle {angle}, actualPolarOpening {actualPolarOpening}, targetPolarOpening {targetPolarOpening}')
    return abs(targetPolarOpening - actualPolarOpening)

def getAngleAndPolarOpeningDiffByAngle(angle, args):
    vessel, layerNumber, targetPolarOpening, verbose = args
    if verbose:
        log.info(f'angle {angle}')
    actualPolarOpening = windLayer(vessel, layerNumber, angle, verbose)
    funVal = -1*angle + abs(targetPolarOpening - actualPolarOpening)
    if verbose:
        log.info(f'angle {angle}, target function val {funVal}, actualPolarOpening {actualPolarOpening}, targetPolarOpening {targetPolarOpening}')
    return funVal

def windLayer(vessel, layerNumber, angle=None, verbose = False):
    """wind up to the given layer(0-based count) and return polar opening angle"""
    if angle:
        vessel.setLayerAngle(layerNumber, angle)
    try:
        vessel.runWindingSimulation(layerNumber + 1)
    except RuntimeError as e:
        if 'bandmiddle path crossed polar opening!' in str(e):
            if verbose:
                log.warning(f'Got an error at angle {angle}: {e}')
            return 1e10
        else:
            raise

    return vessel.getPolarOpeningR(layerNumber, True)

def getPolarOpeningDiffHelical(friction, args):
    vessel, wendekreisradius, layerindex, verbose = args
    vessel.setLayerFriction(layerindex, friction[0], True)
    try:
        vessel.runWindingSimulation(layerindex + 1)
        wk = vessel.getPolarOpeningR(layerindex, True)
    except (IOError, ValueError, IOError, ZeroDivisionError):
        raise
        log.info('I have to pass')

    if verbose:
        log.info(f"layer {layerindex}, friction {friction}, po actual {wk}, po target {wendekreisradius}, po diff {wk-wendekreisradius}")
    # log.info('this helical layer shoud end at', wendekreisradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', wendekreisradius[layerindex]-wk, 'mm') if abs(wendekreisradius[layerindex]-wk) < 2.:
    # arr_fric.append(abs(friction)) arr_wk.append(wk)

    return abs(wk - wendekreisradius)

def getPolarOpeningDiffHelicalUsingLogFriction(friction, args):
        
    vessel, wendekreisradius, layerindex, verbose = args
    vessel.setLayerFriction(layerindex, 10.**friction[0], True)
    try:
        vessel.runWindingSimulation(layerindex + 1)
        wk = vessel.getPolarOpeningR(layerindex, True)
    except (IOError, ValueError, IOError, ZeroDivisionError, RuntimeError):
        raise
        log.info('I have to pass')
    
        
    if verbose:
        log.info(f"layer {layerindex}, friction {10.**friction}, po actual {wk}, po target {wendekreisradius}, po diff {wk-wendekreisradius}")
    # log.info('this helical layer shoud end at', wendekreisradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', wendekreisradius[layerindex]-wk, 'mm') if abs(wendekreisradius[layerindex]-wk) < 2.:
    # arr_fric.append(abs(friction)) arr_wk.append(wk)

    return abs(wk - wendekreisradius)

def getPolarOpeningDiffHelicalUsingNegativeLogFriction(friction, args):
        
    vessel, wendekreisradius, layerindex, verbose = args
    vessel.setLayerFriction(layerindex, -1.0*abs(10.**friction[0]), True)
    try:
        vessel.runWindingSimulation(layerindex + 1)
        wk = vessel.getPolarOpeningR(layerindex, True)
    except (IOError, ValueError, IOError, ZeroDivisionError, RuntimeError):
        log.info('I have to pass')
        wk = 0.
        pass
        
    
        
    if verbose:
        log.info(f"layer {layerindex}, friction {10.**friction}, po actual {wk}, po target {wendekreisradius}, po diff {wk-wendekreisradius}")
    # log.info('this helical layer shoud end at', wendekreisradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', wendekreisradius[layerindex]-wk, 'mm') if abs(wendekreisradius[layerindex]-wk) < 2.:
    # arr_fric.append(abs(friction)) arr_wk.append(wk)

    return abs(wk - wendekreisradius)

def getPolarOpeningDiffHoop(shift, args):
    vessel, krempenradius, layerindex, verbose = args
    vessel.setHoopLayerShift(layerindex, shift, True)
    try:
        vessel.runWindingSimulation(layerindex + 1)
        wk = vessel.getPolarOpeningR(layerindex, True)
    except (IOError, ValueError, IOError, ZeroDivisionError, RuntimeError):
        raise
        log.info('I have to pass')


    if verbose:
        log.info(f"layer {layerindex}, shift {shift}, po actual {wk}, po target {krempenradius}, po diff {wk - krempenradius}")

    # log.info('this hoop layer shoud end at', krempenradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', krempenradius[layerindex]-wk, 'mm')

    return abs(wk - krempenradius)

def getPolarOpeningXDiffHoop(shift, args):
    vessel, polarOpeningX, layerindex, verbose = args
    vessel.setHoopLayerShift(layerindex, shift, True)
    try:
        vessel.runWindingSimulation(layerindex + 1)
        wk = vessel.getPolarOpeningX(layerindex, True)
    except (IOError, ValueError, IOError, ZeroDivisionError, RuntimeError):
        raise
        log.info('I have to pass')


    if verbose:
        log.info(f"layer {layerindex}, shift {shift}, po actual {wk}, po target {polarOpeningX}, po diff {wk - polarOpeningX}")

    # log.info('this hoop layer shoud end at', krempenradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', krempenradius[layerindex]-wk, 'mm')

    return abs(wk - polarOpeningX)


