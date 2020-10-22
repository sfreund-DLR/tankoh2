"""optimizers for various target functions

- optimize frition to achieve a target polar opening
- optimize shift for hoop layers
- optimize layup
"""

from scipy.optimize import minimize_scalar, LinearConstraint
from scipy.optimize import minimize
from scipy.optimize import differential_evolution
import numpy as np

from tankoh2 import log
from tankoh2.winding import getPolarOpeningDiffHelical, getPolarOpeningDiffHoop, \
    getPolarOpeningDiffHelicalUsingLogFriction, getPolarOpeningXDiffHoop, \
    getPolarOpeningDiffByAngle, getNegAngleAndPolarOpeningDiffByAngle, windLayer, getPolarOpeningDiffHelicalUsingNegativeLogFriction
from tankoh2.exception import Tankoh2Error


def optimizeAngle(vessel, targetPolarOpening, layerNumber, verbose=False,
                  targetFunction = getPolarOpeningDiffByAngle):
    """optimizes the angle of the actual layer to realize the desired polar opening

    :param vessel: vessel object
    :param targetPolarOpening: polar opening radius that should be realized
    :param layerNumber: number of the actual layer
    :param verbose: flag if more output should be given
    :return: 3-tuple (resultAngle, polar opening, number of runs)
    """
    tol = 1e-2
    popt = minimize_scalar(targetFunction, method='bounded',
                           bounds=[.1, 75],  # bounds of the angle
                           args=[vessel, layerNumber, targetPolarOpening, verbose],
                           options={"maxiter": 1000, 'disp': 1, "xatol": tol})
    if not popt.success:
        raise Tankoh2Error('Could not finde optimal solution')
    angle, funVal, iterations = popt.x, popt.fun, popt.nfev
    if popt.fun > 1 and targetFunction is getPolarOpeningDiffByAngle:
        # desired polar opening not met. This happens, when polar opening is near fitting.
        # There is a discontinuity at this point. Switch target function to search from the fitting side.
        angle, funVal, iterations = optimizeAngle(vessel, targetPolarOpening, layerNumber, verbose,
                                                        getAngleAndPolarOpeningDiffByAngle)
    else:
        windLayer(vessel, layerNumber, angle)
    #angle2 = vessel.estimateCylinderAngle(layerNumber, targetPolarOpening)
    #r = angle / angle2
    return angle, funVal, iterations

def optimizeFriction(vessel, wendekreisradius, layerindex, verbose=False):
    # popt, pcov = curve_fit(getPolarOpeningDiff, layerindex, wk_goal, bounds=([0.], [1.]))
    #
    # popt  = minimize(getPolarOpeningDiff, x0 = (1.), method = 'BFGS', args=[vessel, wendekreisradius],
    #                   options={'gtol': 1e-6, 'disp': True})
    tol = 1e-7
    popt = minimize_scalar(getPolarOpeningDiffHelical, method='bounded',
                           bounds=[0., 1e-5],
                           args=[vessel, wendekreisradius, layerindex, verbose],
                           options={"maxiter": 1000, 'disp': 1, "xatol": tol})
    friction = popt.x
    return friction, popt.fun, popt.nfev


def optimizeHoopShift(vessel, krempenradius, layerindex, verbose=False):
    popt = minimize_scalar(getPolarOpeningDiffHoop, method='brent',
                           options={'xtol': 1e-2},
                           args=[vessel, krempenradius, layerindex, verbose])
    shift = popt.x
    return shift, popt.fun, popt.nit


def optimizeHoopShiftForPolarOpeningX(vessel, polarOpeningX, layerindex, verbose=False):
    popt = minimize_scalar(getPolarOpeningXDiffHoop, method='brent',
                           options={'xtol': 1e-2},
                           args=[vessel, polarOpeningX, layerindex, verbose])
    shift = popt.x
    return shift, popt.fun, popt.nit


# write new optimasation with scipy.optimize.differential_evolution

def optimizeFrictionGlobal_differential_evolution(vessel, wendekreisradius, layerindex, verbose=False):
    """
    optimize friction value for given polarOpening
    using global optimizer scipy.optimize.differential_evolution
    """
    tol = 1e-15
    args = (vessel, wendekreisradius, layerindex, verbose)
    popt = differential_evolution(getPolarOpeningDiffHelicalUsingLogFriction,
                                  bounds=[(-10, -4)],
                                  args=[args],
                                  strategy='best1bin',
                                  mutation=1.9,
                                  recombination=0.9,
                                  seed=200,
                                  tol=tol,
                                  atol=tol)
    friction = popt.x
    return 10 ** friction, popt.fun, popt.nfev
