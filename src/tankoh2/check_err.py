
import os
from tankoh2 import pychain

runDir = r'C:\PycharmProjects\tankoh2\tmp\tank_20230111_230343_atheat_He'
vessel = pychain.winding.Vessel()
vessel.loadFromFile(os.path.join(runDir, 'before_error.vessel'))
vessel.finishWinding()
a = vessel.getVesselLayer(0).getVesselLayerElement(0, True).clairaultAngle

composite = pychain.material.Composite()
composite.loadFromFile(os.path.join(runDir, 'atheat_He.design'))
vessel.setComposite(composite)
vessel.finishWinding()
a = vessel.getVesselLayer(0).getVesselLayerElement(0, True).clairaultAngle



