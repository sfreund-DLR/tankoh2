"""optimizers for various target functions

- optimize frition to achieve a target polar opening
- optimize shift for hoop layers
- optimize layup
"""

from scipy.optimize import minimize_scalar, minimize
from scipy.optimize import differential_evolution
import numpy as np
import matplotlib.pyplot as plt

from tankoh2.design.winding.winding import getPolarOpeningDiffHelical, getPolarOpeningDiffHoop, \
    getPolarOpeningDiffHelicalUsingLogFriction, getPolarOpeningXDiffHoop, \
    getPolarOpeningDiffByAngle, getNegAngleAndPolarOpeningDiffByAngle, windLayer, windHoopLayer, \
    getPolarOpeningDiffHelicalUsingNegativeLogFriction, getPolarOpeningDiffByAngleBandMid
from tankoh2.service.exception import Tankoh2Error
from tankoh2.design.winding.solver import getMaxPuckByAngle, getMaxPuckLocalPuckMassIndexByAngle, \
    getMaxPuckLocalPuckMassIndexByShift, getWeightedTargetFuncByAngle, getMaxPuckByShift
import tankoh2.settings as settings
from tankoh2 import log



def optimizeAngle(vessel, targetPolarOpening, layerNumber, angleBounds, bandWidth,
                  targetFunction=getPolarOpeningDiffByAngle):
    """optimizes the angle of the actual layer to realize the desired polar opening

    :param vessel: vessel object
    :param targetPolarOpening: polar opening radius that should be realized
    :param layerNumber: number of the actual layer
    :param angleBounds: bounds of the angles used (min angle, max angle)
    :param bandWidth: total width of the band (only used for tf getPolarOpeningDiffByAngleBandMid)
    :param targetFunction: target function to be minimized
    :return: 3-tuple (resultAngle, polar opening, number of runs)
    """
    tol = 1e-2
    if targetFunction is getPolarOpeningDiffByAngleBandMid:
        args = [vessel, layerNumber, targetPolarOpening, bandWidth]
    else:
        args = [vessel, layerNumber, targetPolarOpening]
    popt = minimize_scalar(targetFunction, method='bounded',
                           bounds=angleBounds,
                           args=args,
                           options={"maxiter": 1000, 'disp': 1, "xatol": tol})
    if not popt.success:
        raise Tankoh2Error('Could not find optimal solution')
    plotTargetFun = False
    if plotTargetFun:
        angles = np.linspace(angleBounds[0], 10, 200)
        tfValues = [targetFunction(angle, args) for angle in angles]
        fig, ax = plt.subplots()
        ax.plot(angles, tfValues, linewidth=2.0)
        plt.show()
    angle, funVal, iterations = popt.x, popt.fun, popt.nfev
    if popt.fun > 1 and targetFunction is getPolarOpeningDiffByAngle:
        # desired polar opening not met. This happens, when polar opening is near fitting.
        # There is a discontinuity at this point. Switch target function to search from the fitting side.
        angle, funVal, iterations = optimizeAngle(vessel, targetPolarOpening, layerNumber, angleBounds,
                                                  getNegAngleAndPolarOpeningDiffByAngle)
    else:
        windLayer(vessel, layerNumber, angle)
    log.debug(f'Min angle {angle} at funcVal {funVal}')
    return angle, funVal, iterations


def minimizeUtilization(bounds, targetFunction, optArgs, localOptimization = False):
    """Minimizes puck (inter) fibre failure criterion in defined bounds (angles or hoop shifts)

    This method calls the optimization routines. There is a disctinction between local and global
    optimization.

    :param bounds: iterable with 2 items: lower and upper bound
    :param targetFunction: function to be used as target function
    :param optArgs: list with these items: 
        - vessel: µWind vessel instance
        - layerNumber: actual layer (zero based counting)
        - puckProperties: µWind puckProperties instance
        - burstPressure: burst pressure in MPa
        - useIndices: list of element indicies that will be used for stress and puck evaluation
        - useFibreFailure: flag if fibrefailure or interfibrefailure is used
        - verbosePlot: flag if additional plot output values should be created
        - symmetricContour: flag if the conour is symmetric or unsymmetric
        - critIndex: index of the most critical element before adding the actual layer
        - targetFuncScaling: scaling of the target function constituents for the weighted sum
    :param localOptimization: can be (True, False, 'both'). Performs a local or global optimization. If 'both'
        is selected, both optimizations are performed and the result with the lowest function value is used.
    :return: 4-tuple
        - x optimization result
        - funVal: target function value at x
        - iterations: number of iterations used
        - tfPlotVals: plot values of the target function if verbosePlot==True else None

    """
    helicalTargetFunctions = [getWeightedTargetFuncByAngle, getMaxPuckByAngle]

    verbosePlot = optArgs[6]
    if verbosePlot:
        tfX = np.linspace(*bounds, 200)
        targetFunctionPlot = getMaxPuckLocalPuckMassIndexByAngle if targetFunction in helicalTargetFunctions else \
            getMaxPuckLocalPuckMassIndexByShift
        tfPlotVals = np.array([targetFunctionPlot(angleParam, optArgs) for angleParam in tfX]).T
        if targetFunction in [getMaxPuckByAngle, getMaxPuckByShift]:
            tfPlotVals = np.append(tfPlotVals[:1], tfPlotVals[-1:], axis=0)
        tfPlotVals = np.append([tfX], tfPlotVals, axis=0)
    else:
        tfPlotVals = None

    if localOptimization not in [True, False, 'both']:
        raise Tankoh2Error('no proper value for localOptimization')
    tol = 1e-2
    if localOptimization is True or localOptimization=='both':
        popt_loc = minimize(targetFunction, bounds[:1],
                            bounds=[bounds],  # bounds of the angle or hoop shift
                            args=optArgs,
                            tol=tol,
                            )
        if localOptimization is True:
            popt = popt_loc
    if localOptimization is False or localOptimization=='both':
        popt_glob = differential_evolution(targetFunction,
                                           bounds=(bounds,),
                                           args=[optArgs],
                                           atol=tol*10,
                                           seed=settings.optimizerSeed)

        if localOptimization is False:
            popt = popt_glob
    if localOptimization == 'both':
        popt = popt_loc if popt_loc.fun < popt_glob.fun else popt_glob
    if not popt.success:
        from tankoh2.service.plot.muwind import plotTargetFunc
        errMsg = 'Could not find optimal solution'
        log.error(errMsg)
        plotTargetFunc(None, tfPlotVals, [(popt.x,0)], 'label Name', optArgs[9], None, None, True)
        raise Tankoh2Error(errMsg)
    x, funVal, iterations = popt.x, popt.fun, popt.nfev
    if hasattr(x, '__iter__'):
        x = x[0]
    vessel, layerNumber = optArgs[:2]
    if targetFunction in helicalTargetFunctions:
        windLayer(vessel, layerNumber, x)
    else:
        windHoopLayer(vessel, layerNumber, x)

    return x, funVal, iterations, tfPlotVals


def optimizeFriction(vessel, wendekreisradius, layerindex):
    # popt, pcov = curve_fit(getPolarOpeningDiff, layerindex, wk_goal, bounds=([0.], [1.]))
    #
    # popt  = minimize(getPolarOpeningDiff, x0 = (1.), method = 'BFGS', args=[vessel, wendekreisradius],
    #                   options={'gtol': 1e-6, 'disp': True})
    tol = 1e-7
    popt = minimize_scalar(getPolarOpeningDiffHelical, method='bounded',
                           bounds=[0., 1e-5],
                           args=[vessel, wendekreisradius, layerindex],
                           options={"maxiter": 1000, 'disp': 1, "xatol": tol})
    friction = popt.x
    return friction, popt.fun, popt.nfev


def optimizeHoopShift(vessel, krempenradius, layerindex):
    popt = minimize_scalar(getPolarOpeningDiffHoop, method='brent',
                           options={'xtol': 1e-2},
                           args=[vessel, krempenradius, layerindex])
    shift = popt.x
    return shift, popt.fun, popt.nit


def optimizeHoopShiftForPolarOpeningX(vessel, polarOpeningX, layerindex):
    popt = minimize_scalar(getPolarOpeningXDiffHoop, method='brent',
                           options={'xtol': 1e-2},
                           args=[vessel, polarOpeningX, layerindex])
    shift = popt.x
    return shift, popt.fun, popt.nit


# write new optimasation with scipy.optimize.differential_evolution

def optimizeFrictionGlobal_differential_evolution(vessel, wendekreisradius, layerindex):
    """
    optimize friction value for given polarOpening
    using global optimizer scipy.optimize.differential_evolution
    """
    tol = 1e-15
    args = (vessel, wendekreisradius, layerindex)
    popt = differential_evolution(getPolarOpeningDiffHelicalUsingLogFriction,
                                  bounds=[(-10, -4)],
                                  args=[args],
                                  strategy='best1bin',
                                  mutation=1.9,
                                  recombination=0.9,
                                  seed=settings.optimizerSeed,
                                  tol=tol,
                                  atol=tol,)
    friction = popt.x
    return 10 ** friction, popt.fun, popt.nfev

def optimizeNegativeFrictionGlobal_differential_evolution(vessel, wendekreisradius, layerindex):
    """
    optimize friction value for given polarOpening
    using global optimizer scipy.optimize.differential_evolution
    """
    tol = 1e-15
    args = (vessel, wendekreisradius, layerindex)
    popt = differential_evolution(getPolarOpeningDiffHelicalUsingNegativeLogFriction,
                                  bounds=[(-10, -3.6)],
                                  args=[args],
                                  strategy='best1bin',
                                  mutation=1.9,
                                  recombination=0.9,
                                  seed=settings.optimizerSeed,
                                  tol=tol,
                                  atol=tol)
    friction = popt.x
    return -1.*abs(10 ** friction), popt.fun, popt.nfev
