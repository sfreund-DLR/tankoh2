import numpy as np

from CoolProp.CoolProp import PropsSI

fluid = 'Hydrogen'
psiToMPaFac = 6.89476
MPaToPsiFac = 1 / psiToMPaFac
g = 9.81  # m/s**2

arrayOrScalar = lambda x: np.array(x) if hasattr(x, '__len__') else x

rhoLh2Saturation = lambda T: PropsSI('D', 'T', arrayOrScalar(T), 'Q', 0, fluid)
rhoGh2Saturation = lambda T: PropsSI('D', 'T', arrayOrScalar(T), 'Q', 1, fluid)
rhoLh2ByPSaturation = lambda p: PropsSI('D', 'P', arrayOrScalar(p) * 1e6, 'Q', 0, fluid)
rhoGh2ByPSaturation = lambda p: PropsSI('D', 'P', arrayOrScalar(p) * 1e6, 'Q', 1, fluid)

pressureLh2Saturation = lambda T: PropsSI('P', 'T', arrayOrScalar(T), 'Q', 0, fluid)
pressureGh2Saturation = lambda T: PropsSI('P', 'T', arrayOrScalar(T), 'Q', 1, fluid)

rhoGh2 = lambda p, T: PropsSI('D', 'T', arrayOrScalar(T), 'P', arrayOrScalar(p) * 1e6, fluid)

if __name__ == '__main__':
    rhoLh2Saturation(21)
    rhoLh2Saturation([21])
    print(rhoLh2ByPSaturation(0.2), rhoLh2ByPSaturation(0.25))
