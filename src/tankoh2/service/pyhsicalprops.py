import numpy as np
import pandas as pd
from scipy import interpolate



# properties at equilibrium pressure
lh2Properties = pd.DataFrame(
    np.array([[13.96,        14,     16,     18,     20,    22,    24,    26,    28, 30, 32, 33.19],
              [0.00770, 0.00789, 0.0215, 0.0481, 0.0932, 0.163, 0.264, 0.403, 0.585, 0.850, 1.12, 1.33],
              [76.91,     76.87,  75.12,  73.22,  71.11, 68.73, 66.00, 62.80, 58.92, 53.84, 45.64, 30.12]]).T,
    columns=['T', 'p', 'roh'])  # 'T [K]', 'p [Mpa]', 'roh [kg/m^3]'
gh2Properties = pd.DataFrame(
    np.array([[13.96, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 33.19],
              [0.0077, 0.00789, 0.0215, 0.0481, 0.0932, 0.163, 0.264, 0.403, 0.585, 0.85, 1.12, 1.33],
              [0.1362, 0.1391, 0.338, 0.688, 1.243, 2.067, 3.244, 4.9, 7.258, 10.81, 17.5, 30.12]]).T,
    columns=['T', 'p', 'roh'])  # 'T [K]', 'p [Mpa]', 'roh [kg/m^3]'

# properties not at equilibrium pressure
# source https://h2tools.org/hyarc/hydrogen-data/hydrogen-density-different-temperatures-and-pressures
pressures = [0.1, 1, 5, 10, 30, 50, 100] # MPa
temperatures = np.array([-255, -250, -225, -200, -175, -150, -125,
                         -100, -75, -50,  -25, 0, 25, 50, 75, 100, 125]) + 273.15 #
rohs = np.array([
    [73.284, 74.252, -1  ,   -1  ,   -1  ,   -1  ,   -1    ],
    [1.1212, 68.747, 73.672, -1  ,   -1  ,   -1  ,   -1    ],
    [0.5081, 5.5430, 36.621, 54.812, 75.287, -1  ,   -1    ],
    [0.3321, 3.3817, 17.662, 33.380, 62.118, 74.261, -1    ],
    [0.2471, 2.4760, 12.298, 23.483, 51.204, 65.036, -1    ],
    [0.1968, 1.9617, 9.5952, 18.355, 43.079, 57.343, -1    ],
    [0.1636, 1.6271, 7.9181, 15.179, 37.109, 51.090, 71.606],
    [0.1399, 1.3911, 6.7608, 12.992, 32.614, 46.013, 66.660],
    [0.1223, 1.2154, 5.9085, 11.382, 29.124, 41.848, 62.322],
    [0.1086, 1.0793, 5.2521, 10.141, 26.336, 38.384, 58.503],
    [0.0976, 0.9708, 4.7297, 9.1526, 24.055, 35.464, 55.123],
    [0.0887, 0.8822, 4.3036, 8.3447, 22.151, 32.968, 52.115],
    [0.0813, 0.8085, 3.9490, 7.6711, 20.537, 30.811, 49.424],
    [0.0750, 0.7461, 3.6490, 7.1003, 19.149, 28.928, 47.001],
    [0.0696, 0.6928, 3.3918, 6.6100, 17.943, 27.268, 44.810],
    [0.0649, 0.6465, 3.1688, 6.1840, 16.883, 25.793, 42.819],
    [0.0609, 0.6061, 2.9736, 5.8104, 15.944, 24.474, 41.001],])


rhoLh2 = interpolate.interp1d(lh2Properties['T'], lh2Properties['roh'])
rhoGh2 = interpolate.interp1d(gh2Properties['T'], gh2Properties['roh'])
rhoLh2ByP = interpolate.interp1d(lh2Properties['p'], lh2Properties['roh'])
rhoGh2ByP = interpolate.interp1d(gh2Properties['p'], gh2Properties['roh'])
pressureLh2 = interpolate.interp1d(lh2Properties['T'], lh2Properties['p'])
pressureGh2 = interpolate.interp1d(gh2Properties['T'], gh2Properties['p'])
g = 9.81  # m/s**2

rhoGh2NonCryo = interpolate.interp2d(pressures, temperatures, rohs, kind='linear',
                                     fill_value=-1, bounds_error=True)


