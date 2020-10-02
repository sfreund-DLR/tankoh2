# add path to the API module
import sys
sys.path.append("M:/MyCrOChain_Version_0_88c_x64_BETA/pythonAPI/python38_x64")

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
dome.buildDome(100., 20., pychain.winding.DOME_TYPES.ISOTENSOID)

# create a symmetric liner with dome information and cylinder length 500 mm 
liner = pychain.winding.Liner()
liner.buildFromDome(dome, 500, 1.0)

# save liner for visualization with µChainWind
liner.saveLiner("vessel_1.liner")

# create default material
t700 = pychain.material.OrthotropMaterial()
t700.setDefaultCFRP()

# create composite with 3 layers
composite = pychain.material.Composite()
composite.appendLayer(15, 0.88, t700, pychain.material.LAYER_TYPES.BAP)
composite.appendLayer(88, 0.88, t700, pychain.material.LAYER_TYPES.BAP)
composite.appendLayer(45, 0.88, t700, pychain.material.LAYER_TYPES.BAP)


# create vessel and set liner and composite
vessel = pychain.winding.Vessel()
vessel.setLiner(liner)
vessel.setComposite(composite)
# run winding simulation
vessel.finishWinding()
vessel.saveToFile("vessel_1.vessel") # save vessel

# save winding results
windingResults = pychain.winding.VesselWindingResults()
windingResults.buildFromVessel(vessel)
windingResults.saveToFile("vessel_1.wresults")

# build shell model for internal calculation
converter = pychain.mycrofem.VesselConverter()
shellModel = converter.buildAxShellModell(vessel, 10)

# run linear solver
linerSolver = pychain.mycrofem.LinearSolver(shellModel)
linerSolver.run(True)

# get stresses in the fiber COS
S11, S22, S12 = shellModel.calculateLayerStressesBottom()
# get  x coordinates (element middle)
xCoords = shellModel.getElementCoordsX()

# create model options for abaqus calculation
modelOptions = pychain.mycrofem.VesselFEMModelOptions()
modelOptions.modelName = "TestVessel"
modelOptions.jobName = "TestVesselJob"
modelOptions.windingResultsFileName = "vessel_1"
modelOptions.useMaterialPhi = False
modelOptions.fittingContactWinding = pychain.mycrofem.CONTACT_TYPE.PENALTY
modelOptions.globalMeshSize = 0.25
modelOptions.pressureInBar = 300.0

# write abaqus scripts
scriptGenerator = pychain.abaqus.AbaqusVesselScriptGenerator()
scriptGenerator.writeVesselAxSolidBuildScript("vessel_1_Build.py", settings, modelOptions)
scriptGenerator.writeVesselAxSolidBuildScript("vessel_1_Eval.py", settings, modelOptions)


import matplotlib.pylab as plt

fig = plt.figure()
ax = fig.gca()
ax.plot(S11[:,0])
ax.plot(S11[:,1])
ax.plot(S11[:,2])
plt.show()