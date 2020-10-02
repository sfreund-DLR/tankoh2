# add path to the API module
import sys
import random

sys.path.append("M:/Software/MyCrOChain/versions/0_89b/x64/python38")

# import API - MyCrOChain GUI with activiated TCP-Connector needed
import mycropychain as pychain
import matplotlib.pylab as plt
import matplotlib.lines as mlines
import numpy as np 

# set general path information
settings = pychain.utility.MyCrOSettings()
settings.abaqusPythonLibPath = "M:/Software/MyCrOChain/MyCrOChainAbaqus"

# build isotensoid dome with r= 100.0 mm and polar opening 20 mm
dome = pychain.winding.Dome()
dome.buildDome(250., 25., pychain.winding.DOME_TYPES.ISOTENSOID)

# create a symmetric liner with dome information and cylinder length 500 mm 
liner = pychain.winding.Liner()
liner.buildFromDome(dome, 500, 1.0)

# save liner for visualization with µChainWind
#liner.saveToFile("vessel_1.liner")

# create default material
t700 = pychain.material.OrthotropMaterial()
t700.setDefaultCFRP()

# create composite
composite = pychain.material.Composite()
composite.appendLayer(90, 1.88, t700, pychain.material.LAYER_TYPES.BAP)
composite.appendLayer(90, 1.88, t700, pychain.material.LAYER_TYPES.BAP)
composite.appendLayer(90, 1.88, t700, pychain.material.LAYER_TYPES.BAP)

# recalculate thickness from winding parameters
composite.updateThicknessFromWindingProperties()

#print composite
composite.info()

# create vessel and set liner and composite
vessel = pychain.winding.Vessel()
vessel.setLiner(liner)
vessel.setComposite(composite)

# check simulation status
vessel.printSimulationStatus()

vessel.runWindingSimulation(1) # to estimate the angle of layer 1 the mandrel must be known
angle = vessel.estimateCylinderAngle(0, 25.0)
vessel.setLayerAngle(0, angle) # resets layer (will be recomputed with next runWindingSimulation)
vessel.runWindingSimulation(2) # to estimate the angle the mandrel must be known
angle = vessel.estimateCylinderAngle(1, 60.0)
vessel.setLayerAngle(1, angle)
vessel.setHoopLayerShift(2, 5.0, True)
vessel.finishWinding()

print("Polar opening layer 1: ", vessel.getPolarOpeningR(0, True))
print("Polar opening layer 2: ", vessel.getPolarOpeningR(1, True))

vessel.printSimulationStatus()

# reset winding simulation
vessel.resetWindingSimulation()
vessel.printSimulationStatus()

vessel.saveToFile("Test.vessel")