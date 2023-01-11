"""create DOEs and execute design workflow

Caution:
This module requires fa_pytuils and delismm!
Please contatct the developers for these additional packages.
"""

import os
from collections import OrderedDict
from datetime import datetime
from multiprocessing import cpu_count
import numpy as np

from delismm.model.doe import LatinizedCentroidalVoronoiTesselation, DOEfromFile
from delismm.model.samplecalculator import getY
from delismm.model.customsystemfunction import BoundsHandler, AbstractTargetFunction
from delismm.control.tank import getKrigings

from fa_pyutils.service.systemutils import getRunDir

import tankoh2
from tankoh2.control.control_winding import createDesign
from tankoh2 import programDir, log
from tankoh2.service.plot.doeplot import plotGeometryRange
from tankoh2.service.utilities import indent
from tankoh2.control.genericcontrol import resultNamesFrp
from tankoh2.design.existingdesigns import dLightBase, vphDesign1_isotensoid
from tankoh2.service.exception import Tankoh2Error


class TankWinder(AbstractTargetFunction):
    """"""
    name = 'tank winder'

    def __init__(self, lb, ub, runDir, designKwargs):
        """"""
        AbstractTargetFunction.__init__(self, lb, ub, resultNames=resultNamesFrp)
        self.doParallelization = []
        self.runDir = runDir
        self.allowFailedSample = True
        self.designKwargs = designKwargs
        """keyword arguments defining constants for the tank design"""
        self.asyncMaxProcesses = int(np.ceil(cpu_count()*2/3))

    def _call(self, parameters):
        """call function for the model"""
        runDir = getRunDir(basePath=os.path.join(self.runDir), useMilliSeconds=True)
        paramDict = OrderedDict(zip(self.parameterNames, parameters))
        inputDict = OrderedDict()
        inputDict.update(self.designKwargs)
        inputDict.update(paramDict)
        inputDict['runDir'] = runDir

        result = createDesign(**inputDict)
        return result

    def getNumberOfNewJobs(self):
        return self.asyncMaxProcesses

def getDesignAndBounds(name):
    """returns base design properties (like in existingdesigns) of a tank and upper/lower bounds for the doe

    :param name: name of the design and bounds to return. Not case sensitive!
    :return: designKwargs, lowerBoundDict, upperBoundDict, numberOfSamples
    """
    allowedNames = {'dlight', 'exact_cyl_isotensoid'}
    if name not in allowedNames:
        raise Tankoh2Error(f'Parameter name={name} unknown. Allowed names: {allowedNames}')
    name = name.lower()
    numberOfSamples = 101
    if name == 'dlight':
        lb = OrderedDict([('dcyl', 300.), ('lcyl', 800), ('pressure', 30)])  # [mm, mm , MPa]
        ub = OrderedDict([('dcyl', 1000.), ('lcyl', 3000), ('pressure', 95)])
        designKwargs = dLightBase
    elif name == 'exact_cyl_isotensoid':
        lb = OrderedDict([('dcyl[mm]', 1000.), ('lcyl[mm]', 150), ('pressure[MPa]', 0.1)])  # [mm, mm , MPa]
        ub = OrderedDict([('dcyl[mm]', 4000.), ('lcyl[mm]', 3000), ('pressure[MPa]', 1)])
        designKwargs = vphDesign1_isotensoid.copy()
        designKwargs['targetFuncWeights'] = [1.,.2,0.,.0, 0, 0]
        designKwargs['verbosePlot'] = True
        designKwargs['numberOfRovings'] = 12
        designKwargs.pop('lcyl')
        designKwargs.pop('safetyFactor')
        if 0:  # for testing
            numberOfSamples = 3
            designKwargs['maxLayers'] = 3
    return designKwargs, lb, ub, numberOfSamples


def mainControl(name, sampleXFile):
    """

    :param name: name of the design and bounds to return. Not case sensitive!
    :param sampleXFile: path and filename to a list with sampleX vaules
    """
    startTime = datetime.now()

    designKwargs, lb, ub, numberOfSamples = getDesignAndBounds(name)

    names = list(lb.keys())
    runDir = getRunDir(f'doe_{name}', basePath=os.path.join(programDir, 'tmp'))

    winder = TankWinder(lb, ub, runDir, designKwargs)
    if sampleXFile:
        lcvt = DOEfromFile(sampleXFile)
    else:
        lcvt = LatinizedCentroidalVoronoiTesselation(numberOfSamples, len(names))

    sampleX = BoundsHandler.scaleToBoundsStatic(lcvt.sampleXNormalized, list(lb.values()), list(ub.values()))
    plotGeometryRange(lb, ub, plotDir=runDir, samples=sampleX)
    lcvt.xToFile(os.path.join(runDir, 'sampleX.txt'))
    lcvt.xToFileStatic(os.path.join(runDir, 'sampleX_bounds.txt'), sampleX)
    sampleY = getY(sampleX, winder, verbose=True, runDir=runDir)

    # store samples
    lcvt.yToFile(os.path.join(runDir, 'sampleY.txt'), winder, sampleY)
    # lcvt.xyToFile(os.path.join(runDir, 'full_doe2.txt'), winder, sampleY, True)

    allSamples = [names + winder.resultNames]
    for inputSample, outputSample in zip(sampleX.T, sampleY):
        if hasattr(outputSample, '__iter__'):
            allSamples.append(list(inputSample) + list(outputSample))
        else:
            allSamples.append(list(inputSample) + list([outputSample]))
    with open(os.path.join(runDir, 'full_doe.txt'), 'w') as f:
        f.write(indent(allSamples, hasHeader=True))

    duration = datetime.now() - startTime
    log.info(f'runtime {duration.seconds} seconds')


def main():
    createDoe = False
    plotDoe = False
    createSurrogate = True
    if 1:
        designName = 'exact_cyl_isotensoid'
        sampleXFile = '' + r'C:\PycharmProjects\tankoh2\tmp\doe_exact_cyl_isotensoid_20230106_230150/sampleX.txt'
        mmRunDir = getRunDir('tank_surrogates', basePath=os.path.join(tankoh2.programDir, 'tmp'))
        resultNamesIndexesLog10 = [
            ('totalMass[kg]',        4, True),
            ('volume[dm^3]',         5, True),
            ('area[m^2]',            6, False),
            ('lengthAxial[mm]',      7, False),
            ('gravimetricIndex[-]', 10, False),
        ]
        surrogateDir = '' + r'C:\PycharmProjects\tankoh2\tmp\tank_surrogates_20230109_180336'
    else:
        designName = 'dlight'
    if createDoe:
        mainControl(designName, sampleXFile)
    if plotDoe:
        samples = DOEfromFile(sampleXFile) if sampleXFile else None
        _, lb, ub, _ = getDesignAndBounds(designName)
        plotGeometryRange(lb, ub, show=True, samples= samples)
    if createSurrogate:
        designKwargs, lb, ub, numberOfSamples = getDesignAndBounds(designName)
        parameterNames = list(lb.keys())
        krigings = getKrigings(surrogateDir, mmRunDir, parameterNames, resultNamesIndexesLog10)


if __name__ == '__main__':
    main()