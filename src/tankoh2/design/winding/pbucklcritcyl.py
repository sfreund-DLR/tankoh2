'''
Created on 15.12.2022

@author: lefe_je
'''
import numpy as np
from math import pi as Pi

def pBucklCritCyl():
    '''
    This method is supposed to evaluate the critical (outer) pressure of a hoop stiffened cylinder following the AD2000
    :param outDiameter: outer diameter of cylinder
    :param lengthCyl: total length of cylinder (un-stiffened case)
    :param thicknessWallCyl: wall thickness of cylinder
    :param modulEUB: Young's modulus (bending) in tangential/circumferential direction
    :param modulELB: Young's modulus (bending) in axial direction
    :param modulES: effective Young's modulus (bending) of shell
    :param lengthR: distance between stiffening hoops
    :param inertMomentHoop: effective second moment of area of hoop's cross section
    :param modulER: Young's modulus (bending) of hoop in tangential/circumferential direction
    :param nuLnuU: Poisson's ratio axial times Poisson's ratio tangential/circumferential
    :param bHoop: width of hoop
    :param hHoop: height of hoop
    :param lengthBM: supporting shell length at hoop position
    :param mBuckl: buckling mode order in tangential/circumferential direction
    :param matrixABD: ABD-matrix of composite lay-up
    :param factorA: material reduction factor
    :param factorS: safety factor
    '''
    outDiameter = 600.
    lengthCyl = 1200.
    thicknessWallCyl = 3.
    modulEUB = 70000.
    modulELB = 70000.
    modulER = 70000.
    nuLnuU = 0.1
    lengthR = 150.
    bHoop = 20.
    hHoop = 10.
    inertMomentHoop = bHoop * (hHoop ** 3) / 12.
    factorA = 2.
    factorS = 2.
    hoopStiffened = True
    mBuckl = 1.

    lengthBM = 1.1 * (outDiameter * thicknessWallCyl) ** (1. / 2.)
    if (lengthBM) >= 20. * thicknessWallCyl:
        lengthBM = 20. * thicknessWallCyl
    lengthBM += bHoop

    inertMomentHoop += lengthBM * (thicknessWallCyl **3 ) / 12.

    lambdaBuckl = (Pi * outDiameter) / 2. / lengthR
    modulES = (modulEUB ** 3 * modulELB) ** (1. / 4.)

    pComp = 1.E+09
    pCrit = 1.E+08

    while pCrit < pComp:

        pComp = pCrit
        mBuckl += 1.

        if hoopStiffened:
            pCrit = 0.1 * (20. * modulES * thicknessWallCyl / outDiameter * lambdaBuckl ** 4 / (mBuckl ** 2 -1. + 0.5 * lambdaBuckl **2) / (mBuckl ** 2 + lambdaBuckl ** 2) ** 2 + (mBuckl ** 2 - 1.) * 80. * modulER * inertMomentHoop / outDiameter ** 3 / lengthR)
        else:
            if lengthCyl <= 6. * outDiameter:
                pCrit = 0.1 * 23.5 * modulES * outDiameter / lengthCyl * (thicknessWallCyl / outDiameter) ** (5. / 2.)
            else:
                pCrit = 0.1 * 20. * modulEUB / (1. - nuLnuU) * outDiameter / lengthCyl * (thicknessWallCyl / outDiameter) ** (5. / 2.)

    pAllowed = pComp / factorA / factorS

    return (pAllowed)
