"""performs the winding of one layer and provides target functions for optimizers"""


from tankoh2 import log


def getPolarOpeningDiffHelical(friction, args):
    vessel, wendekreisradius, layerindex, verbose = args
    vessel.setLayerFriction(layerindex, abs(friction), True)
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
    except (IOError, ValueError, IOError, ZeroDivisionError):
        raise
        log.info('I have to pass')
    
        
    if verbose:
        log.info(f"layer {layerindex}, friction {10.**friction}, po actual {wk}, po target {wendekreisradius}, po diff {wk-wendekreisradius}")
    # log.info('this helical layer shoud end at', wendekreisradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', wendekreisradius[layerindex]-wk, 'mm') if abs(wendekreisradius[layerindex]-wk) < 2.:
    # arr_fric.append(abs(friction)) arr_wk.append(wk)

    return abs(wk - wendekreisradius)

def getPolarOpeningDiffHoop(shift, args):
    vessel, krempenradius, layerindex, verbose = args
    vessel.setHoopLayerShift(layerindex, shift, True)
    vessel.runWindingSimulation(layerindex + 1)
    wk = vessel.getPolarOpeningR(layerindex, True)

    if verbose:
        log.info(f"layer {layerindex}, shift {shift}, po actual {wk}, po target {krempenradius}, po diff {wk - krempenradius}")

    # log.info('this hoop layer shoud end at', krempenradius[layerindex], 'mm but is at', wk, 'mm so there is a
    # deviation of', krempenradius[layerindex]-wk, 'mm')

    return abs(wk - krempenradius)



