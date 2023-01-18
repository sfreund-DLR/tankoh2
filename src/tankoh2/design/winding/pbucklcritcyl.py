'''
Created on 15.12.2022

@author: lefe_je
'''
from math import pi as Pi
from tankoh2.service.exception import Tankoh2Error

def getMaterialDefinition(orthotropMatProp):
    """doc"""
    from tankoh2.design.winding.material_delis_standallone import MaterialDefinition

    stiffnessMatrix = None
    name = "muWindMaterialType"
    rho = 1.58e-9

    # elastic (engineering) properties (describing plane stress condition)
    e1 = orthotropMatProp[0]
    e2 = orthotropMatProp[1]
    g12 = orthotropMatProp[5]
    nu12 = orthotropMatProp[8]
    nu23 = orthotropMatProp[6]

    materialDefinition = MaterialDefinition(
        id = name,
        name = name,
        rho = rho,
    )
#    materialDefinition.specificHeats = [specificHeat] * 2
#    materialDefinition.specificHeatTemperatures = [temperature] * 2
    if stiffnessMatrix is None:
        materialDefinition.setStiffnessMatrix(e1, g12, e2, nu12, nu23)

    return materialDefinition

def getComposite(orientations=None, thickness=None, number=1, offset=0.0, materialDefinition=None):
    """
    if there is only one orientation an isotrop material is assumed

    :param thickness: thickness of one layer. defualts to [0.000125]
    :param number: todo
    :param offset: todo
    :param materialDefinition: todo
                      If thickness is a float or a list with one enty whereas there are several
                      orientations, the thickness value is used for each layer
    :param orientations: orientation of one layer in degree. defaults to [0.]
    """
    if orientations is None:
        orientations = [0.0]
    if thickness is None:
        thickness = [0.125]

    if hasattr(thickness, "__len__"):
        if len(thickness) != len(orientations):
            if len(thickness) == 1:
                thickness = list(thickness)
                thickness = thickness * len(orientations)
            else:
                raise Tankoh2Error("Number of layer orientations and layer thicknesses are not equal!")
    else:
        thickness = [thickness] * len(orientations)

    from tankoh2.design.winding.material_delis_standallone import Layer, Composite

    if materialDefinition is None:
        materialDefinition = getMaterialDefinition(None) #[getMaterialDefinition(len(orientations) == 1, number)]

    if hasattr(materialDefinition, "__len__"):
        if len(materialDefinition) != len(orientations):
            if len(materialDefinition) == 1:
                materialDefinition = list(materialDefinition) * len(orientations)
            else:
                raise Tankoh2Error("Number of layer orientations and material definitions are not equal!")
    else:
        materialDefinition = [materialDefinition] * len(orientations)

    if len(orientations) == 1:
        materialDefinitionId = materialDefinition[0].id
    else:
        materialDefinitionId = "composite" + str(number)

    composite = Composite(
        name="composite" + str(number),
        id=materialDefinitionId,
        offset=offset,
        number=number,
        materialDefinitions=materialDefinition,
    )

    for i, orientation in enumerate(orientations):

        if orientation < 0:
            orientation = orientation + 180

        layer = Layer(
            id=f"layer{i}",
            name=f"layer{i}",
            phi=orientation,
            thickness=thickness[i],
            materialDefinition=materialDefinition[i],
        )

        composite.layers.append(layer)

    return composite

def pBucklCritCyl(dcyl, lcylinder, orthotropMatProp, resultThicknesses, resultAngles, safetyFactor):
    '''
    This method is supposed to evaluate the critical (outer) pressure of a hoop stiffened cylinder following the
    AD2000 Regelwerk,
    AD 2000-Merkblatt N 1:2014-06 Druckbehälter aus nichtmetallischen Werkstoffen - Druckbehälter aus
    textilglasverstärkten duroplastischen Kunststoffen (GFK),
    4. Berechnung,
    4.7 Nachweise gegenüber äußerem Überdruck,
    4.7.2 Berechnung gegen Instabilität

    note from 1 Geltungsbereich:
    "Bei Verwendung von anderen Faserverstärkungen darf dieses AD 2000-Merkblatt sinngemäß angewendet werden."

    :param dcyl: outer diameter of cylinder [mm]
    :param lcylinder: total length of cylinder (un-stiffened case) [mm]
    :param orthotropMatProp: elastic properties of orthotropic material as a list [N/mm**2, or - ]
    :param resultThicknesses: list of layer thicknesses [mm]
    :param resultAngles: list of layer angles [°]
    '''

    # totalized composite thickness of cylinder
    thicknessWallCyl = sum(resultThicknesses)
    #
    materialDefinitionCyl = getMaterialDefinition(orthotropMatProp)
    compositeCyl = getComposite(orientations=resultAngles, thickness=resultThicknesses, materialDefinition=materialDefinitionCyl)
    #
    #ABD-matrix of composite lay-up
    abdCyl = compositeCyl.abd
    #
    moduliFromDMatrix = compositeCyl.moduliBending
    #
    #Young's modulus (bending) in axial direction
    modulELBending = moduliFromDMatrix['e11']
    #
    #Young's modulus (bending) in tangential/circumferential direction
    modulEUBending = moduliFromDMatrix['e22']
    #
    #Poisson's ratio axial times Poisson's ratio tangential/circumferential
    #value taken from AD2000 standard
    nuLnuU = 0.1
    #
    #effective Young's modulus (bending) of shell
    modulES = (modulEUBending ** 3 * modulELBending) ** (1. / 4.)
    #
    #material reduction factor
    factorA = 2.
    #
    #safety factor
    if safetyFactor is None:
        safetyFactor = 2.
    #
    # parameter for hoop stiffened vessels
    ######################################
    hoopStiffened = False
    #Young's modulus (bending) of hoop in tangential/circumferential direction
    modulER = 70000.
    #distance between stiffening hoops
    lengthR = 150.
    #width of hoop
    bHoop = 20.
    #height of hoop
    hHoop = 10.
    #effective second moment of area of hoop's cross section [mm**4]
    inertMomentHoop = bHoop * (hHoop ** 3) / 12.
    #buckling mode order in tangential/circumferential direction
    mBuckl = 1.

    if hoopStiffened:

        #supporting shell length at hoop position
        lengthBM = 1.1 * (dcyl * thicknessWallCyl) ** (1. / 2.)
        if (lengthBM) >= 20. * thicknessWallCyl:
            lengthBM = 20. * thicknessWallCyl
        lengthBM += bHoop

        inertMomentHoop += lengthBM * (thicknessWallCyl **3 ) / 12.

        lambdaBuckl = (Pi * dcyl) / 2. / lengthR

        pComp = 1.E+09
        pCrit = 1.E+08

        while pCrit < pComp:

            pComp = pCrit
            mBuckl += 1.

            pCrit = 0.1 * (20. * modulES * thicknessWallCyl / dcyl * lambdaBuckl ** 4 / (mBuckl ** 2 -1. + 0.5 * lambdaBuckl **2) / (mBuckl ** 2 + lambdaBuckl ** 2) ** 2 + (mBuckl ** 2 - 1.) * 80. * modulER * inertMomentHoop / dcyl ** 3 / lengthR)

        pAllowedBuckl = pComp / factorA / safetyFactor

    else:
        #un-stiffened cylinder
        ######################
         if lcylinder <= 6. * dcyl:
             pCrit = 0.1 * 23.5 * modulES * dcyl / lcylinder * (thicknessWallCyl / dcyl) ** (5. / 2.)
         else:
             pCrit = 0.1 * 20. * modulEUBending / (1. - nuLnuU) * dcyl / lcylinder * (thicknessWallCyl / dcyl) ** (5. / 2.)

         pAllowedBuckl = pCrit / factorA / safetyFactor

    #pAllowedBuckl is evaluated in N/mm**2
    #if pressure is needed in bar
    #pAllowedBucklBar = 10. * pAllowedBuckl
    #remark: standard atmosphere pressure is 1.01325 bar = 0.101325 N/mm**2

    return(pAllowedBuckl)