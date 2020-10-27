"""create DOEs and execute design workflow

Caution:
This module requires fa_pytuils and delismm!
Please contatct the developers for these additional packages.
"""

import os
from collections import OrderedDict
import datetime

from delismm.model.doe import LatinizedCentroidalVoronoiTesselation, DOEfromFile
from delismm.model.samplecalculator import getY
from delismm.model.customsystemfunction import BoundsHandler, AbstractTargetFunction
from fa_pyutils.service.systemutils import getRunDir

from tankoh2.control_sf import createWindingDesign
from tankoh2 import programDir, log
from tankoh2.service import indent

class TankWinder(AbstractTargetFunction):
    """"""
    name = 'tank winder'

    def __init__(self, lb, ub, runDir):
        """"""
        resultNames = ['frpMass', 'volume', 'area', 'lzylinder', 'numberOfLayers']
        AbstractTargetFunction.__init__(self, lb, ub, resultNames=resultNames)
        self.doParallelization = []
        self.runDir = runDir
        self.allowFailedSample = False

    def _call(self, parameters):
        """call function for the model"""
        runDir = getRunDir(basePath=os.path.join(self.runDir),useMilliSeconds=True)
        r, lzyl, burstPressure = parameters
        result = createWindingDesign(dzyl=r*2, lzyl=lzyl, burstPressure=burstPressure,
                                     minPolarOpening = r/10, runDir=runDir)
        return result


def main():
    sampleFile = 'C:/PycharmProjects/tankoh2/tmp/doe_20201027_181202_isotensoid/sampleX.txt'
    numberOfSamples = 101

    startTime = datetime.datetime.now()
    safetyFactor = 2.25
    lb = OrderedDict([('r',200.),('lzyl',800.),('dp',0.05*safetyFactor)])  # [mm, - , MPa]
    ub = OrderedDict([('r',3000.),('lzyl',12000.),('dp',1.*safetyFactor)])
    names = list(lb.keys())
    runDir = getRunDir('doe_circle', basePath=os.path.join(programDir,'tmp'))

    winder = TankWinder(lb,ub, runDir)
    if sampleFile:
        lcvt = DOEfromFile(sampleFile)
    else:
        lcvt = LatinizedCentroidalVoronoiTesselation(numberOfSamples, len(names))

    sampleX = BoundsHandler.scaleToBoundsStatic(lcvt.sampleXNormalized, list(lb.values()), list(ub.values()))
    lcvt.xToFile(os.path.join(runDir, 'sampleX.txt'))
    lcvt.xToFileStatic(os.path.join(runDir, 'sampleX_bounds.txt'), sampleX)
    sampleY = getY(sampleX, winder, verbose=True)

    # store samples
    lcvt.yToFile(os.path.join(runDir, 'sampleY.txt'), winder, sampleY)
    #lcvt.xyToFile(os.path.join(runDir, 'full_doe2.txt'), winder, sampleY, True)

    allSamples = [names + winder.resultNames]
    for inputSample, outputSample in zip(sampleX.T, sampleY):
        if hasattr(outputSample, '__iter__'):
            allSamples.append(list(inputSample) + list(outputSample))
        else:
            allSamples.append(list(inputSample) + list([outputSample]))
    with open(os.path.join(runDir, 'full_doe.txt'), 'w') as f:
        f.write(indent(allSamples, hasHeader=True))

    duration = datetime.datetime.now() - startTime
    log.info(f'runtime {duration.seconds} seconds')

if __name__ == '__main__':
    main()
