'''
Created on 22.11.2013

@author: iyya_ab
'''
import pytest
import numpy as np

from material_standallone01 import MYGLOBAL
from material_standallone01 import CpacsError
#from delis.service.custominput import getComposite, getMaterialDefinition
from material_standallone01 import MaterialDefinition, abdOffset, abdByPlyShares, abdByLaminationParameters
#from delis.buckling.bucklingpanel import BuckPanel
from fa_pyutils.service.exceptions import ImproperParameterError
from fa_pyutils.service.logger import log


def getMaterialDefinition(isotrop=True, number=1, cfkMaterialType="femmas"):
    """doc"""
    from material_standallone01 import MaterialDefinition

    stiffnessMatrix = None
    e1, e2, g12, nu12, nu23 = [None] * 5
    if isotrop:  # aluminium 2024
        name = "aluminium 2024"
        rho = 2.8e3

        # stiffness data from data from http://asm.matweb.com/search/SpecificMaterial.asp?bassnum=MA2024T4
        e1 = 73.1e9
        g12 = 28e9

        strength = {key: 3.26800000e08 for key in ["sigma11t", "sigma11c", "sigma22t", "sigma22c"]}
        strength["tau"] = 242e6

        thermalConductivity = np.array([190.0, 0, 0, 190, 0, 190])
        thermalExpansionCoeff = np.array([0.0000228, 0, 0, 0.0000228, 0, 0.0000228])
        temperature, specificHeat = 293.15, 897

    else:  # CFK

        validNames = ["Tenax_5631_RTM6", "femmas", "posicoss", "diss", "DLRT1", "geier_dipl"]
        if cfkMaterialType not in validNames:
            raise ImproperParameterError("wrong material name! Current valid names: [%s]" % ", ".join(validNames))

        name = "CFK_" + cfkMaterialType
        rho = 1.58e3

        strength = {
            "sigma11t": 2.20790000e09,
            "sigma11c": 1.09500000e09,
            "sigma22t": 4.26000000e07,
            "sigma22c": 1.89000000e08,
            "tau": 71.8e6,
        }

        # the thermal values are from HexTow_AS4C
        thermalConductivity = np.array([11.0, 0, 0, 0.6, 0, 0.6])
        thermalExpansionCoeff = np.array([-0.0000015, 0, 0, 0.000001, 0, 0.000001])
        temperature, specificHeat = 293.15, 711

        if cfkMaterialType == "Tenax_5631_RTM6":
            # from Diss Hartung FVF=63,4; Tenax 5631 RTM6
            stiffnessMatrix = np.diag(
                [137112195918.0, 9152552846.9, 9152552846.9, 3457258064.52, 4538000000.0, 4538000000.0]
            )
            lowerIx = np.tril_indices(3, -1)
            upperIx = np.triu_indices(3, 1)
            stiffnessMatrix[upperIx] = [2733741495.54, 2733741495.54, 2238036717.86]
            stiffnessMatrix[lowerIx] = stiffnessMatrix[upperIx]

        elif cfkMaterialType == "femmas":
            nu12 = 0.35  # femmas material properties
            e1 = 157e9
            e2 = 8.5e9
            g12 = 4.2e9

        elif cfkMaterialType == "posicoss":
            nu12 = 0.34
            e1 = 146.635e09
            e2 = 9.72e9
            g12 = 6.054e9
            # posicoss material properties
            stiffnessMatrix = np.diag(
                [150120889734.0, 11165554542.6, 11165554542.6, 3626865671.64, 6054000000.0, 6054000000.0]
            )
            lowerIx = np.tril_indices(3, -1)
            upperIx = np.triu_indices(3, 1)
            stiffnessMatrix[upperIx] = [5126308432.22, 5126308432.22, 3911823199.27]
            stiffnessMatrix[lowerIx] = stiffnessMatrix[upperIx]

        elif cfkMaterialType == "diss":
            # diss material properties
            nu12 = 0.33
            e1 = 147e09  # EtL is 170e9 but using EcL here
            e2 = (8.3e9 + 8.7e9) / 2
            g12 = 5.11e9

        elif cfkMaterialType == "DLRT1":
            # diss material properties
            nu12 = 0.33
            nu23 = 0.4
            e1 = 154e09  # EtL is 170e9 but using EcL here
            e2 = 8.7e9
            g12 = 5.11e9
            rho = 1.8e3
        elif cfkMaterialType == "geier_dipl":
            # diss material properties
            nu12 = 0.35
            e1 = 145e9
            e2 = 8.5e9
            g12 = 4.2e9

    materialDefinition = MaterialDefinition(
        id = name,
        name = name,
        rho = rho,
        stiffnessMatrix = stiffnessMatrix,
        strength = strength,
        number = number,
        thermalConductivity = thermalConductivity,
        thermalExpansionCoeff = thermalExpansionCoeff,
    )
    materialDefinition.specificHeats = [specificHeat] * 2
    materialDefinition.specificHeatTemperatures = [temperature] * 2
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
        thickness = [0.000125]

    if hasattr(thickness, "__len__"):
        if len(thickness) != len(orientations):
            if len(thickness) == 1:
                thickness = list(thickness)
                thickness = thickness * len(orientations)
            else:
                raise ImproperParameterError("Number of layer orientations and layer thicknesses are not equal!")
    else:
        thickness = [thickness] * len(orientations)

    from material_standallone01 import Layer, Composite

    if materialDefinition is None:
        materialDefinition = [getMaterialDefinition(len(orientations) == 1, number)]

    if hasattr(materialDefinition, "__len__"):
        if len(materialDefinition) != len(orientations):
            if len(materialDefinition) == 1:
                materialDefinition = list(materialDefinition) * len(orientations)
            else:
                raise ImproperParameterError("Number of layer orientations and material definitions are not equal!")
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
        if orientation not in [0, 45, 90, 135]:
            log.warning(
                "The given orientation in none of the angles [0,45,90,135]. The Ado panel generator won't work with this orientation."
            )

        layer = Layer(
            id=f"layer{i}",
            name=f"layer{i}",
            phi=orientation,
            thickness=thickness[i],
            materialDefinition=materialDefinition[i],
        )

        composite.layers.append(layer)

    return composite

def test_AbdOffset():
    composite = getComposite([90,0])
    abd = composite.abd
    offset = 0.001
    abdOff1 = composite.getABD(offset = offset)
    abdOff2 = abdOffset(abd, offset)
    assert np.allclose(abdOff1, abdOff2)

def test_rotateReducedStiffnessMatrix():
    m = getMaterialDefinition(False)
    q = m.getReducedStiffnessMatrix()
    assert np.allclose(q, m.rotateReducedStiffnessMatrix(q, np.pi), atol = 1, rtol = 1)
    q90 = m.rotateReducedStiffnessMatrix(q, np.pi/2)
    assert np.allclose([q[0,0],q[1,1]], [q90[1,1],q90[0,0]], atol = 1, rtol = 1)
    
def test_abdPlyShare():
    m = getMaterialDefinition(False)
    t = 0.001
    c = getComposite([90], t, materialDefinition = m)
    assert np.allclose(c.abd, abdByPlyShares(m.getReducedStiffnessMatrix(), 0, 1, 0, t))
    
    multiplyer = 10
    c = getComposite([0,90,90,0]*multiplyer, t/multiplyer/4, materialDefinition = m)
    assert np.allclose(c.abd, abdByPlyShares(m.getReducedStiffnessMatrix(), 0.5, 0.5, 0, t), rtol = 1e-2)

def test_reducedStiffnesses():
    m = getMaterialDefinition(False)
    assert np.allclose(m.kPlaneStressCondition, m.getReducedStiffnessMatrix())

def test_StiffnessMatrixIsotrop1():
    m=MaterialDefinition()
    m.setStiffnessMatrix(1.,1.)
    assert abs(m.moduli['g12'] - 1.0) < MYGLOBAL.epsilon
    assert abs(m.moduli['e11'] - 1.0) < MYGLOBAL.epsilon

def test_StiffnessMatrixIsotrop2():
    m=MaterialDefinition()
    m.setStiffnessMatrix(1.,None, nu12=1.)
    assert abs(m.moduli['nu12'] - 1.0) < MYGLOBAL.epsilon
    assert abs(m.moduli['e11'] - 1.0) < MYGLOBAL.epsilon

def test_StiffnessMatrixIsotrop3():
    m=MaterialDefinition()
    m.setStiffnessMatrix(67698795861.,27120300751.)
    assert abs(m.moduli['g12'] / 27120300751.0 - 1) < MYGLOBAL.epsilon
    assert abs(m.moduli['e11'] / 67698795861.0 - 1) < MYGLOBAL.epsilon

def test_StiffnessMatrixTransversalIsotrop1():
    m=MaterialDefinition()
    m.setStiffnessMatrix(133068810100.,6274228870.,9238974380., 0.318)
    assert abs(m.moduli['g12'] / 6274228870.0 - 1) < MYGLOBAL.epsilon
    assert abs(m.moduli['e11'] / 133068810100.0 - 1) < MYGLOBAL.epsilon

def test_StiffnessMatrixTransversalIsotrop2():
    m=MaterialDefinition()
    m.setStiffnessMatrix(133068810100.,6274228870.,9238974380., 0.318, 0.318)
    assert abs(m.moduli['g12'] / 6274228870.0 - 1) < MYGLOBAL.epsilon
    assert abs(m.moduli['e11'] / 133068810100.0 - 1) < MYGLOBAL.epsilon
    assert abs(m.moduli['nu23'] / 0.318 - 1) < MYGLOBAL.epsilon

def test_StiffnessMatrixTransversalIsotrop3():
    m=MaterialDefinition()
    m.setStiffnessMatrix(133068810100.,6274228870.,9238974380., 0.318, 0.318, g13=6274228870.0, g23=3504921995.5)
    assert abs(m.moduli['g12'] / 6274228870.0 - 1) < MYGLOBAL.epsilon
    assert abs(m.moduli['e11'] / 133068810100.0 - 1) < MYGLOBAL.epsilon
    assert abs(m.moduli['nu23'] / 0.318 - 1) < MYGLOBAL.epsilon
    assert abs(m.moduli['g23'] / 3504921995.5 - 1) < MYGLOBAL.epsilon

def test_StiffnessMatrixOrthotrop2():
    m=MaterialDefinition()
    m.setStiffnessMatrix(133068810100.,6274228870.,9238974380., 0.318, 0.318,
                         9238974380., 3504921995, 6274228870, 0.318)
    assert abs(m.moduli['g12'] / 6274228870.0 - 1) < MYGLOBAL.epsilon
    assert abs(m.moduli['e11'] / 133068810100.0 - 1) < MYGLOBAL.epsilon
    assert abs(m.moduli['nu23'] / 0.318 - 1) < MYGLOBAL.epsilon

def test_StiffnessMatrixCpacsErrorException():
    m=MaterialDefinition()
    m.setStiffnessMatrix(-1.,1.,1.,1.)
    with pytest.raises(CpacsError):
        m.moduli()
    
    
#===============================================================================
# lamination parameters 
#===============================================================================
def getLamParamMaterialDefinition():
    """doc"""
    #===========================================================================
    # Falks input
    # #e11, e22, nu12, g12, e33, g13, g23, nu31, nu23
    # #r11t, r11c, r22t, r22c, r12, r33t, r33c, r13, r23            
    # #AS4/8552 - Properties mainly from Falco
    # udMaterial = customInput.getMaterialDefinition(engineeringConstants = [138000., 8600., 0.35, 4900., 8600., 4900., 2800., 0.35, 0.487], 
    #                                                strengths = [2042., 1495., 66.1, 257., 105.2, 66.1, 257., 66.1, 66.1], materialScaling = 1.)
    #===========================================================================
    m = MaterialDefinition()
    m.setStiffnessMatrix(138000., 4900., 8600., 0.35, 0.35) # units in mm
    return m

def test_stiffnessInvariants():
    m = getLamParamMaterialDefinition()
    stiffnessInvariants = m.stiffnessInvariants
    
    resultStiffnessInvariants = [5.860619968382e+04,  6.519772319848e+04,  1.525768146685e+04,  1.829083675012e+04]
    resultStiffnessInvariants += [(resultStiffnessInvariants[0]-resultStiffnessInvariants[3])/2]
    assert np.allclose(stiffnessInvariants, resultStiffnessInvariants)

def test_abdToLamParam():
    """todo: extension by calculating own Q and lamination parameters for a composite"""
    m = getLamParamMaterialDefinition()
    angleList = [-45., 0., 45., 90., 35., 70., 0., -60.]
#    c = getComposite(angleList, 0.25, materialDefinition = m)
    stiffnessInvariants = m.stiffnessInvariants
    layerThk = 0.25
    thickness = layerThk * len(angleList)
#     lamParam = [ [ 9.496962525836e-03,  8.955685333600e-02, -1.154953318151e-02,  6.550065755735e-02],  
#                  [-1.392535370635e-01,  2.518367572983e-02,  1.642156278088e-01,  1.172044430357e-01],
#                  [ 1.053102268867e-01, -4.422166722768e-01, -1.800820874957e-01,  2.015005724893e-01],
#                 ]
    lamParam = np.array([[ 9.496962525836e-03, -1.154953318151e-02,  8.955685333600e-02,  6.550065755735e-02],  
                         [-1.392535370635e-01,  1.642156278088e-01,  2.518367572983e-02,  1.172044430357e-01],
                         [ 1.053102268867e-01, -1.800820874957e-01, -4.422166722768e-01,  2.015005724893e-01],
                        ])
    abd = abdByLaminationParameters(lamParam.flatten(), stiffnessInvariants, thickness)
    
    resultAbd = [[  1.180983218389e+05,  3.693411169698e+04,  7.837679272086e+03, -6.573463822888e+03, -2.505549740986e+03,  2.609227218014e+03 ],
                 [  3.693411169698e+04,  1.156216005029e+05,  3.840126596569e+03, -2.505549740986e+03,  1.158456330486e+04, -9.673088986609e+02 ],
                 [  7.837679272086e+03,  3.840126596569e+03,  4.066780113045e+04,  2.609227218014e+03, -9.673088986609e+02, -2.505549740986e+03 ],
                 [ -6.573463822888e+03, -2.505549740986e+03,  2.609227218014e+03,  4.181636771830e+04,  1.402564791934e+04, -7.560885697332e+03 ],
                 [ -2.505549740986e+03,  1.158456330486e+04, -9.673088986609e+02,  1.402564791934e+04,  3.266171835493e+04, -1.166012776457e+04 ],
                 [  2.609227218014e+03, -9.673088986609e+02, -2.505549740986e+03, -7.560885697332e+03, -1.166012776457e+04,  1.527021106383e+04 ],
                ]
#     from delis.service.utilities import indent
#     print()
#     print(indent(abd))
#     print(indent(resultAbd))
# #    print(indent(c.getABD()))
#     print(indent(abd-resultAbd))
    assert np.allclose(abd, resultAbd)






class Test_Composite():
    """classdoc"""
    
    def test_compositeABD(self):
        orientations = [45,135,0,90]
        composite = getComposite(orientations+orientations[::-1])
        refAbd = [
                [65325572.4671     , 20971765.7714     , 3.72529029846e-09, -4.54747350886e-13, 0.0               , 0.0           ],
                [20971765.7714     , 65325572.4671     , 1.86264514923e-09, 0.0               , -4.54747350886e-13, 0.0           ],
                [3.72529029846e-09 , 1.86264514923e-09 , 22176903.3478    , 0.0               , 0.0               , 0.0           ],
                [-4.54747350886e-13, 0.0               , 0.0              , 4.90419223099     , 2.87120360686     , 0.875926476953],
                [0.0               , -4.54747350886e-13, 0.0              , 2.87120360686     , 3.73629026171     , 0.875926476953],
                [0.0               , 0.0               , 0.0              , 0.875926476953    , 0.875926476953    , 2.97163173823 ],]
        assert np.allclose(composite.abd, refAbd) 

#    def test_compositeAbdFemmas(self):
#        """introduced, since these abd values slightly differ between local pc and jenkins pc"""
#        composite = getComposite(BuckPanel.getFemmasTParameters()['refLamina'])
#        refAbd = [
#                [164105698.622     , 22843554.7861     , 3.72529029846e-09 , -4.0017766878e-11 , -7.27595761418e-12, 9.09494701773e-13 ],
#                [22843554.7861     , 70673541.0806     , 1.86264514923e-09 , -7.27595761418e-12, -1.81898940355e-11, 9.09494701773e-13 ],
#                [3.72529029846e-09 , 1.86264514923e-09 , 24801903.3478     , 9.09494701773e-13 , 9.09494701773e-13 , -5.45696821064e-12],
#                [-4.0017766878e-11 , -7.27595761418e-12, 9.09494701773e-13 , 28.6534745985     , 8.39744119915     , 2.91975492318     ],
#                [-7.27595761418e-12, -1.81898940355e-11, 9.09494701773e-13 , 8.39744119915     , 16.2688474661     , 2.91975492318     ],
#                [9.09494701773e-13 , 9.09494701773e-13 , -5.45696821064e-12, 2.91975492318     , 2.91975492318     , 8.82837988004     ],]
#        assert np.allclose(composite.abd, refAbd)












if __name__ == '__main__':
    test_abdToLamParam()






