"""create DOEs and execute design workflow

Caution:
This module requires fa_pytuils and delismm!
Please contatct the developers for these additional packages.
"""

import os
from collections import OrderedDict
import datetime
import numpy as np
import matplotlib.pyplot as plt

from delismm.model.doe import LatinizedCentroidalVoronoiTesselation, DOEfromFile
from delismm.model.samplecalculator import getY
from delismm.model.customsystemfunction import BoundsHandler, AbstractTargetFunction

from tankoh2.control.control_winding import createDesign
from tankoh2 import programDir, log, pychain
from tankoh2.service.utilities import indent, getRunDir


dome = 'circle'  # isotensoid  circle
safetyFactor = 1  # 2.25
lb = OrderedDict([('r', 500.), ('lcylByR', 0.01), ('dp', 0.13 * safetyFactor)])  # [mm, - , MPa]
ub = OrderedDict([('r', 1600.), ('lcylByR', 12.), ('dp', 0.5 * safetyFactor)])
useFibreFailure = False

numberOfSamples = 201

class TankWinder(AbstractTargetFunction):
    """"""
    name = 'tank winder'

    def __init__(self, lb, ub, runDir):
        """"""
        resultNames = ['frpMass', 'volume', 'area', 'lcylinder', 'numberOfLayers', 'angles', 'hoopLayerShifts']
        AbstractTargetFunction.__init__(self, lb, ub, resultNames=resultNames)
        self.doParallelization = []
        self.runDir = runDir
        self.allowFailedSample = True

    def _call(self, parameters):
        """call function for the model"""
        runDir = getRunDir(basePath=os.path.join(self.runDir), useMilliSeconds=True)
        r, lcyl, burstPressure = parameters

        result = createDesign(dcyl=r * 2, lcylByR=lcyl, burstPressure=burstPressure,
                              polarOpeningRadius=r / 10, runDir=runDir,
                              domeType=pychain.winding.DOME_TYPES.ISOTENSOID if dome == 'isotensoid' else pychain.winding.DOME_TYPES.CIRCLE,
                              useFibreFailure = useFibreFailure)
        return result

volumeFunc = lambda r, lcylByR: (4 / 3 * np.pi * r ** 3 + r * lcylByR * np.pi * r ** 2)
"""[m**3]"""

def plotGeometryRange(radii, lcylByRs, plotDir='', show=False, samples=None):
    """

    :param radii: tuple with min and max radius [mm]
    :param lcylByRs: tuple with min and max lcylByR [-]
    :return: None
    """
    radii = np.array(radii) / 1e3  # convert to m
    if samples is not None:
        samplesR, sampleslcylByR = samples[:2, :]
        samplesR = samplesR / 1e3

    fig = plt.figure(figsize=(15,6))
    axes = [fig.add_subplot(1, 2, 1), fig.add_subplot(1, 2, 2)]
    axes[1].set_yscale("log")
    for ax in axes:
        ax.set_title("Parameter bounds")
        ax.set_xlabel('Radius [m]')
        ax.set_ylabel('Volume [m^3]')
        color = 'tab:blue'
        for lcylByR in lcylByRs:
            x = np.linspace(*radii,11)
            volumes = [volumeFunc(r, lcylByR) for r in x]
            ax.plot(x, volumes, color=color, label=f'lcylByR={lcylByR}')
            color = 'tab:orange'
        ax.legend()
        if samples is not None:
            volumes = volumeFunc(samplesR, sampleslcylByR)
            ax.scatter(samplesR, volumes, label=f'samples')

    if plotDir:
        plt.savefig(plotDir+'/geometryRange.png')
    if show:
        plt.show()



def main():
    sampleFile = ''   + 'C:/PycharmProjects/tankoh2/tmp/doe_circle_20210520_135237_cvt/sampleX.txt'

    startTime = datetime.datetime.now()
    names = list(lb.keys())
    runDir = getRunDir(f'doe_{dome}_{"puckff" if useFibreFailure else "puckiff"}',
                       basePath=os.path.join(programDir, 'tmp'))

    winder = TankWinder(lb, ub, runDir)
    if sampleFile:
        lcvt = DOEfromFile(sampleFile)
    else:
        lcvt = LatinizedCentroidalVoronoiTesselation(numberOfSamples, len(names))

    sampleX = BoundsHandler.scaleToBoundsStatic(lcvt.sampleXNormalized, list(lb.values()), list(ub.values()))
    plotGeometryRange([lb['r'], ub['r']],[lb['lcylByR'], ub['lcylByR']], plotDir=runDir, samples=sampleX)
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

    duration = datetime.datetime.now() - startTime
    log.info(f'runtime {duration.seconds} seconds')


if __name__ == '__main__':
    if 1:
        main()
    else:
        plotGeometryRange([lb['r'], ub['r']],[lb['lcylByR'], ub['lcylByR']], show=True)
