# add path to the API module
import sys
import random

sys.path.append("M:/Software/MyCrOChain/versions/0_89b/x64/python38")
import mycropychain as pychain
import numpy as np

xDome = np.array([ 0.0, 5.702898, 11.387232, 17.034502, 22.626326, 28.144502, 33.571069, 38.888363, 44.079078, 49.126318, 54.013653, 58.725177, 63.245553, 67.560068, 71.654678, 75.516055, 79.131632, 82.489638, 85.579145, 88.390095, 90.91334, 93.140667, 95.064824, 96.679551, 97.97959])
rDome = np.array([ 100.0, 99.837252, 99.349539, 98.538448, 97.406619, 95.957736, 94.196515, 92.128688, 89.760987, 87.101119, 84.15774, 80.940432, 77.459667, 73.726774, 69.753904, 65.553988, 61.140697, 56.528396, 51.732098, 46.767415, 41.650505, 36.398025, 31.027071, 25.555126, 20.0])

# write relative coordinates
fid = open("TestDome.dcon", "w")
fid.write("# Test Dome\n")
for i in range(len(xDome)):
     fid.write("%5.2f   %5.2f\n"%(xDome[i], rDome[i]))
fid.close()

# fitting boss contour
xBoss = np.array([247.97959, 248.147653, 248.369116, 248.642204, 248.964723, 249.334084, 249.747324, 250.201126, 250.691846, 251.215547, 251.768024, 252.344844, 252.941377, 253.552834, 254.174308, 254.80081, 259.592473, 264.141682, 279.592473])
rBoss = np.array([20.0, 19.395807, 18.80908, 18.244529, 17.706685, 17.199865, 16.728137, 16.295288, 15.904791, 15.55978, 15.263026, 15.016909, 14.823406, 14.68407, 14.600018, 14.571925, 14.571925, 18.0, 18.0])

cylinderLength = 300.0

# write relative coordinates
fid = open("TestBoss.bcon", "w")
fid.write("# Test Boss\n")
for i in range(len(xBoss)-1):
     fid.write("%5.2f   %5.2f\n"%(xBoss[i+1]-xBoss[i], rBoss[i+1]-rBoss[i]))
fid.close()

import matplotlib.pylab as plt

fig = plt.figure()
ax = fig.gca()
ax.axis('equal')
ax.plot([0,0.5*cylinderLength], [rDome[0], rDome[0]])
ax.plot(xDome + 0.5*cylinderLength, rDome)
ax.plot(xBoss, rBoss)
plt.show()

dome = pychain.winding.Dome()
# build dome from X-R arrays
dome.setPoints(xDome, rDome)

liner = pychain.winding.Liner()
# build liner with dome
liner.buildFromDome(dome, 300, 1.0)

# get fitting reference of the liner and change it
fitting = liner.getFitting(True)
fitting.setFittingTypeCustom()
fitting.loadCustomBossPointsFromFile("TestBoss.bcon")
fitting.buildFittingFromDiscRadius(50.0)
fitting.dx1 = 0.0
fitting.rebuildFitting()

# save liner for loading in µChain
liner.saveToFile("vessel_3_testliner.liner")






