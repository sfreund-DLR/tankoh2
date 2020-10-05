"""optimizers for various target functions

- optimize frition to achieve a target polar opening
- optimize shift for hoop layers
- optimize layup
"""


from scipy.optimize import minimize_scalar
from scipy.optimize import minimize
from scipy.optimize import differential_evolution

from tankoh2 import log
from tankoh2.winding import getPolarOpeningDiffHelical, getPolarOpeningDiffHoop, getPolarOpeningDiffHelicalUsingLogFriction

def optimizeFriction(vessel, wendekreisradius, layerindex, verbose=False):
    # popt, pcov = curve_fit(getPolarOpeningDiff, layerindex, wk_goal, bounds=([0.], [1.]))
    #
    # popt  = minimize(getPolarOpeningDiff, x0 = (1.), method = 'BFGS', args=[vessel, wendekreisradius],
    #                   options={'gtol': 1e-6, 'disp': True})
    tol = 1e-7
    popt = minimize_scalar(getPolarOpeningDiffHelical, method='bounded',
                           bounds = [0., 1e-5],
                           args=[vessel, wendekreisradius, layerindex, verbose],
                           options={"maxiter": 1000, 'disp':1, "xatol":tol})
    friction = popt.x
    return friction, popt.fun, popt.nfev



def optimizeHoopShift(vessel, krempenradius, layerindex, verbose=False):
    popt = minimize_scalar(getPolarOpeningDiffHoop, method='brent',
                           options={'xtol':1e-2},
                           args=[vessel, krempenradius, layerindex, verbose])
    shift = popt.x
    return shift, popt.fun, popt.nit


# write new optimasation with scipy.optimize.differential_evolution

def optimizeFrictionGlobal_differential_evolution(vessel, wendekreisradius, layerindex, verbose=False):
    """
    optimize friction value for given polarOpening
    using global optimizer scipy.optimize.differential_evolution
    """
    tol = 1e-15
    args=(vessel, wendekreisradius, layerindex, verbose)
    popt = differential_evolution(getPolarOpeningDiffHelicalUsingLogFriction, 
                           bounds = [(-10, -4)],
                           args=[args],
                           strategy='best1bin',
                           mutation = 1.9,
                           recombination = 0.9,  
                           seed = 200, 
                           tol = tol, 
                           atol = tol)
    friction = popt.x
    return 10**friction, popt.fun, popt.nfev