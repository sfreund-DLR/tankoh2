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
from tankoh2 import programDir, log, pychain
from tankoh2.service import indent

dome = 'circle'  # isotensoid  circle

class TankWinder(AbstractTargetFunction):
    """"""
    name = 'tank winder'

    def __init__(self, lb, ub, runDir):
        """"""
        resultNames = ['frpMass', 'volume', 'area', 'lzylinder', 'numberOfLayers', 'angles']
        AbstractTargetFunction.__init__(self, lb, ub, resultNames=resultNames)
        self.doParallelization = []
        self.runDir = runDir
        self.allowFailedSample = False

    def _call(self, parameters):
        """call function for the model"""
        runDir = getRunDir(basePath=os.path.join(self.runDir),useMilliSeconds=True)
        r, lzyl, burstPressure = parameters

        result = createWindingDesign(dzyl=r*2, lzylByR=lzyl, burstPressure=burstPressure,
                                     minPolarOpening = r/10, runDir=runDir,
                                     domeType = pychain.winding.DOME_TYPES.ISOTENSOID if dome=='isotensoid' else pychain.winding.DOME_TYPES.CIRCLE)
        return result


def main():
    sampleFile = '' + 'C:/PycharmProjects/tankoh2/tmp/doe_isotensoid_20201028_210108/sampleX.txt'
    numberOfSamples = 41

    startTime = datetime.datetime.now()
    safetyFactor = 2.25
    lb = OrderedDict([('r',200.),('lzylByR',.5),('dp',0.05*safetyFactor)])  # [mm, - , MPa]
    ub = OrderedDict([('r',2000.),('lzylByR',7.),('dp',1.*safetyFactor)])
    names = list(lb.keys())
    runDir = getRunDir(f'doe_{dome}', basePath=os.path.join(programDir,'tmp'))

    winder = TankWinder(lb,ub, runDir)
    if sampleFile:
        lcvt = DOEfromFile(sampleFile)
    else:
        lcvt = LatinizedCentroidalVoronoiTesselation(numberOfSamples, len(names))

    sampleX = BoundsHandler.scaleToBoundsStatic(lcvt.sampleXNormalized, list(lb.values()), list(ub.values()))
    print(sampleX.shape)
    lcvt.xToFile(os.path.join(runDir, 'sampleX.txt'))
    lcvt.xToFileStatic(os.path.join(runDir, 'sampleX_bounds.txt'), sampleX)
    sampleY = getY(sampleX, winder, verbose=True, runDir=runDir)

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
