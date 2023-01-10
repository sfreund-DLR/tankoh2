# Copyright (C) 2013 Deutsches Zentrum fuer Luft- und Raumfahrt(DLR, German Aerospace Center) <www.dlr.de>
"""
documentation
"""
import numpy as np
import numpy.linalg as nplin
import math
from scipy.linalg import block_diag
#from scipy import interpolate
from collections import OrderedDict
from functools import reduce

#from delis.service.globals import MYGLOBAL
from fa_pyutils.service.logger import log
#from delis.service.tivalibs import CpacsError
from fa_pyutils.service.exceptions import ImproperParameterError
from fa_pyutils.service.exceptions import InternalError
#from delis.model.commonstructure import StructureElement
from fa_pyutils.service.exceptions import CustomException

class CpacsError(CustomException):
    """classdocs"""

class MyGlobals:
    """This class holds global variables

        """
    epsilon = 1e-8
    maximalNumberOfMaterialDefinitions = 100

MYGLOBAL = MyGlobals()

def abdOffset(abdMatrix, offset=0.0):
    """Calculates the given ABD matrix offset by offset
    
    :param abdMatrix: 6x6 np array 
    :param offset: scalar
    """
    a = abdMatrix[:3, :3]
    b = -offset * a + abdMatrix[:3, 3:6]
    d = offset ** 2 * a - 2 * offset * abdMatrix[:3, 3:6] + abdMatrix[3:6, 3:6]

    newAbdMatrix = np.zeros_like(abdMatrix)
    newAbdMatrix[:3, :3] = a
    newAbdMatrix[3:6, :3] = newAbdMatrix[:3, 3:6] = b
    newAbdMatrix[3:6, 3:6] = d

    return newAbdMatrix


def abdByPlyShares(q, r0, r90, r_pm45, laminateThickness):
    """Returns the abd-matrix of a laminate with given thickness and ply shares. 
    The laminate is expected to be homogenized by all angles. Thus, the reducedStiffness of each 
    angle orientation is reduced by the ply share for calculation of the abd matrix.
    The reference surface is midPlane.
    
    :param q: reduced stiffness matrix [3,3] in material coordinate system (0-deg)
    :param r0: relative 0-deg share
    :param r90: relative 90-deg share
    :param r_pm45: relative plus minus 45-deg share
    :param laminateThickness: thickness of the laminate
    """
    plyShares = [r0, r90, r_pm45 / 2.0, r_pm45 / 2.0]
    if not (np.sum(plyShares) - 1) < MYGLOBAL.epsilon:
        raise ImproperParameterError(f"The ply shares sum has to be 1 but got: {plyShares}")

    abd = np.zeros((6, 6))
    angles = np.radians(np.array([0, 90, 45, -45]))
    for phi, plyShare in zip(angles, plyShares):
        qTrans = MaterialDefinition.rotateReducedStiffnessMatrix(q, phi)
        abd[:3, :3] += qTrans * plyShare * laminateThickness
        abd[3:, 3:] += qTrans * plyShare * laminateThickness ** 3 / 12  # no excentricity, e=0

    return abd


def abdByLaminationParameters(laminationParameters, stiffnessInvariants, thickness):
    """calculate 6x6 ABD matrix based on laminaiton parameters and stiffness invariants
    
    see [1]C. G. Diaconu und H. Sekine,
    „Layup Optimization for Buckling of Laminated Composite Shells with Restricted Layer Angles“,
    AIAA Journal, Bd. 42, Nr. 10, S. 2153–2163, Okt. 2004.
    """

    abdComponents = []
    lamParm2D = laminationParameters.reshape((3, 4))
    for lamParmComponent, factor, isBMatrix in zip(
        lamParm2D, [thickness, thickness ** 2 / 4.0, thickness ** 3 / 12.0], [False, True, False]
    ):
        xsiMatrix = _getXsiMatrix(lamParmComponent, isBMatrix)
        abdComponentVec = np.dot(xsiMatrix, stiffnessInvariants)
        abdComponent = np.zeros((3, 3))
        abdComponent[0, 0] = abdComponentVec[0]
        abdComponent[1, 1] = abdComponentVec[1]
        abdComponent[0, 1] = abdComponentVec[2]
        abdComponent[2, 2] = abdComponentVec[3]
        abdComponent[0, 2] = abdComponentVec[4]
        abdComponent[1, 2] = abdComponentVec[5]
        # symm
        abdComponent[1, 0] = abdComponentVec[2]
        abdComponent[2, 0] = abdComponentVec[4]
        abdComponent[2, 1] = abdComponentVec[5]

        abdComponent *= factor
        abdComponents.append(abdComponent)

    abdMatrix = np.zeros((6, 6))
    abdMatrix[:3, :3] += abdComponents[0]
    abdMatrix[:3, 3:] += abdComponents[1]
    abdMatrix[3:, :3] += abdComponents[1]
    abdMatrix[3:, 3:] += abdComponents[2]

    return abdMatrix


def _getXsiMatrix(xsi, isBMatrix):
    """calculates the xsi matrix based on xsi(lamination parameters either A,B,D)
    
    :return: 6x5 matrix"""
    factor = 0.0 if isBMatrix else 1.0
    xsiMatrix = np.array(
        [
            [factor, xsi[0], xsi[1], 0.0, 0.0],
            [factor, -xsi[0], xsi[1], 0.0, 0.0],
            [0.0, 0.0, -xsi[1], factor, 0.0],
            [0.0, 0.0, -xsi[1], 0.0, factor],
            [0.0, xsi[2] / 2.0, xsi[3], 0.0, 0.0],
            [0.0, xsi[2] / 2.0, -xsi[3], 0.0, 0.0],
        ]
    )
    return xsiMatrix


class MaterialDefinition:
    """classdocs"""

    def __init__(self, **kwargs):
        """doc"""
        #StructureElement.__init__(self)
        self.id = None
        self.name = None
        self.description = None
        self.rho = None

        self.isShell = False
        """Flag if shell properties are given. Required for cpacs writing"""

        self.stiffnessMatrix = np.zeros((6, 6))
        """stiffnesses of material definition"""

        self.strength = {}
        """Max strength"""
        self.strengthValues = ["sigma11t", "sigma11c", "sigma22t", "sigma22c", "tau"]

        self.strain = {}
        """Max strain"""
        self.strainValues = ["eps11t", "eps11c", "eps22t", "eps22c", "gamma"]

        self._savedModuli = {}

        self._kPlaneStressCondition = None
        """3x3 matrix containing the plane stress stiffnesses.
        calculated according to altenberg page 53. The z-direction is the out of
        plane direction with sigma_z = 0 and so on."""

        self.number = None
        """id within fe systems"""

        self.usedAngles = set()
        """Angles as integer in degrees which represent the orientations that 
        are used with this materialDefinition. 
        It is set within Layer.materialDefinition and is needed to create rotated
        materialDefinitions for complex cross sections"""

        self.thermalConductivity = np.zeros((6,))
        """Thermal conductivity KXX KXY KXZ KYY KYZ KZZ"""

        self.thermalExpansionCoeff = np.zeros((6,))
        """Thermal expansion coefficient in the 3 directions XX XY XZ YY YZ ZZ"""

        self.thermalExpansionCoeffTemp = 20 + 273.15
        """Reference temperature for thermalExpansionCoeff"""

        self.specificHeats = None
        """Specific heat capacity sample points of the material in [J/(kg*K)].
        Vector with at least len=2"""

        self.specificHeatTemperatures = None
        """Temperatures to the specific heat capacities
        Vector with at least len=2"""

        self.specificHeatDefaultTemp = 20 + 273.15
        """Default temperature for specificHeat"""

        self.setStrength(kwargs.pop("strength", {s: 0.0 for s in self.strengthValues}))

        for key in kwargs:
            if not hasattr(self, key):
                log.warning(f'Setting unknown key "{key}" in class {self.__class__} with name "{str(self)}"')
            setattr(self, key, kwargs[key])

    def copy(self):
        """doc"""
        return MaterialDefinition(
            id = self.id,
            name = self.name,
            description = self.description,
            rho = self.rho,
            stiffnessMatrix = self.stiffnessMatrix,
            strength = self.strength,
            number = self.number,
        )

    def specificHeatFunction(self, temperature):
        """returns specific heat to the given temperature
        :param temperature: scalar or vector with temperatures [K]
        :return: scalar or vector with specific heats
        """
        return np.interp(temperature, self.specificHeatTemperatures, self.specificHeats)

    def setStiffnessMatrix(
        self,
        # isotrop
        e1,
        g12,
        # transversal isotrop
        e2=None,
        nu12=None,
        nu23=None,
        # orthotrop
        e3=None,
        g23=None,
        g13=None,
        nu31=None,
    ):
        """This method assumes a transverse isotropic material.

        Altenbach, Holm, Johannes Altenbach, und Rolands Rikards.
            Einführung in die Mechanik der Laminat- und Sandwichtragwerke:
            Modellierung und Berechnung von Balken und Platten aus Verbundwerkstoffen.
            1. Aufl. Stuttgart: Wiley-VCH, 1996.

            page 45 (Transversale Isotropie)

        Accepted parameter combinations:

        - isotrop
            - e1, g12
            - e1, nu12
        - transversal isotrop
            - e1, g12, e2, nu12
            - e1, g12, e2, nu12, nu23
            - e1, g12, e2, nu12, nu23, g23, g13
        - orthotrop
            - e1, g12, e2, nu12, nu23, e3, g23, g13, nu31
        """

        if g12 is None:
            # isotrop switch if e and nu are given
            g12 = e1 / (2 * (1 + nu12))

        if not all(np.array([e2, nu12]) != None):
            log.debug(f"Isotrop behavior material assumed for material with id {self.id}")
            e2 = e3 = e1
            nu12 = e1 / 2 / g12 - 1
            nu31 = nu23 = nu12
            g13 = g23 = g12
        elif not all(np.array([e3, g23, g13, nu31]) != None):
            log.debug(f"Transversal isotrop material behavior assumed for material with id {self.id}")
            e3 = e2
            nu31 = nu12
            g13 = g12 if g13 is None else g13
            nu23 = nu12 if nu23 is None else nu23
            g23 = e2 / (2.0 * (1 + nu23)) if g23 is None else g23
        else:
            log.debug(f"Orthotrop material behavior assumed for material with id {self.id}")

        self._savedModuli = {}

        matUpperLeft = np.array(
            [
                [1.0 / e1, -nu12 / e1, -nu31 / e1],
                [-nu12 / e1, 1.0 / e2, -nu23 / e2],
                [-nu31 / e1, -nu23 / e2, 1.0 / e3,],
            ]
        )

        matLowerRight = np.diag([1.0 / g23, 1.0 / g13, 1.0 / g12])

        compliance = block_diag(matUpperLeft, matLowerRight)
        self.stiffnessMatrix = np.linalg.inv(compliance)

    def setStrength(self, strength):
        """This method is intended to set the strength of the material."""
        self.strength.update(strength)

    @staticmethod
    def rotateReducedStiffnessMatrix(redStiff, phi):
        """transforms the given reduced stiffnessmatrix according to angle phi
        see eq 2.85 [1]R. M. Jones, Mechanics Of Composite Materials, 2 New edition. Philadelphia, PA: Taylor & Francis Inc, 1998.
        
        :param redStif: 3x3 matrix
        :param phi: angle [rad]
        """
        redStiffVec = np.array([[redStiff[0, 0]], [redStiff[0, 1]], [redStiff[1, 1]], [redStiff[2, 2]]])

        c = np.cos(phi)
        s = np.sin(phi)

        transM = np.array(
            [
                [c ** 4, 2 * c ** 2 * s ** 2, s ** 4, 4 * c ** 2 * s ** 2],
                [c ** 2 * s ** 2, c ** 4 + s ** 4, c ** 2 * s ** 2, -4 * c ** 2 * s ** 2],
                [c ** 3 * s, c * s * (c ** 2 - s ** 2), -c * s ** 3, -2 * c * s * (c ** 2 - s ** 2)],
                [s ** 4, 2 * c ** 2 * s ** 2, c ** 4, 4 * c ** 2 * s ** 2],
                [c * s ** 3, c * s * (c ** 2 - s ** 2), -(c ** 3) * s, 2 * c * s * (c ** 2 - s ** 2)],
                [c ** 2 * s ** 2, -2 * c ** 2 * s ** 2, c ** 2 * s ** 2, (c ** 2 - s ** 2) ** 2],
            ]
        )

        redStiffVecGlo = np.mat(transM) * np.mat(redStiffVec)
        redStiffMatGlo = np.array(
            [
                [redStiffVecGlo[0, 0], redStiffVecGlo[1, 0], redStiffVecGlo[2, 0]],
                [redStiffVecGlo[1, 0], redStiffVecGlo[3, 0], redStiffVecGlo[4, 0]],
                [redStiffVecGlo[2, 0], redStiffVecGlo[4, 0], redStiffVecGlo[5, 0]],
            ]
        )
        return redStiffMatGlo

    def getSpecificHeat(self, T=None):
        if T is None:
            T = self.specificHeatDefaultTemp
        return self.specificHeatFunction(T)

    def _getModuli(self):
        """
        calculates moduli

        :return: dict with these keys: e11, e22, e33, g12, g23, g13, nu12, nu21, nu31, nu31, nu23
        """
        if self._savedModuli != {}:
            return self._savedModuli
        stiffnessM = self.stiffnessMatrix
        try:
            complianceM = np.linalg.inv(stiffnessM)
        except np.linalg.LinAlgError:
            raise CpacsError(
                "Please check your material definition! "
                + "Could not calculate compliance matrix of material element at xPath "
                #+ self.xPath
            )

        e11 = complianceM[0, 0] ** -1
        e22 = complianceM[1, 1] ** -1
        e33 = complianceM[2, 2] ** -1

        g23 = complianceM[3, 3] ** -1
        g13 = complianceM[4, 4] ** -1
        g12 = complianceM[5, 5] ** -1

        nu12 = -complianceM[1, 0] * e11
        nu21 = -complianceM[0, 1] * e22
        nu13 = -complianceM[0, 2] * e11

        nu31 = -complianceM[2, 0] * e33
        nu23 = -complianceM[2, 1] * e22
        nu32 = -complianceM[1, 2] * e33

        if any(value < 0 for value in [e11, e22, e33, g12, g23, g13]):
            if not hasattr(self, "xPath"):
                self.xPath = ""
            raise CpacsError(
                "Please check your material definition! "
                + "Got negative youngs- or shear modulus at material element at xPath "
                #+ self.xPath
            )

        self._savedModuli = OrderedDict(
            [
                ("e11", e11),
                ("e22", e22),
                ("e33", e33),
                ("g12", g12),
                ("g23", g23),
                ("g13", g13),
                ("nu12", nu12),
                ("nu21", nu21),
                ("nu13", nu13),
                ("nu31", nu31),
                ("nu23", nu23),
                ("nu32", nu32),
            ]
        )

        return self._savedModuli

    def getRotatedMaterialDefinition(self, orientationAngle):
        r""" This function assume that not more than MYGLOBAL.maximalNumberOfMaterialDefinitions-1
        materials are defined. If there are more defined, 
        the materialDefinition.numbering has to be changed.
        The materialDefinitions of this layer with 'orientationAngle' will be calculated.
        
        Angle definition:
        
        \2   |y   /1
         \   |   /     
          \  |  /<--\
           \ | / phi \   
            \|/_______\_______x
        'phi' is defined as the positive angle from the global coordinate system (x,y) to the 
        local coordinate system (1,2), which is fiberorientated.    
        
        validated with eLamX from TU Dresden
        
        Reference: VDI 2014 Part 3, 2006, 'Development of fibre-reinforced plastics components'
        """
        newMaterialDefinition = self.copy()
        # reset attributes
        newMaterialDefinition._savedModuli = {}
        newMaterialDefinition._kPlaneStressCondition = None

        stiff = np.mat(newMaterialDefinition.stiffnessMatrix)

        c = np.cos(np.radians(orientationAngle))
        s = np.sin(np.radians(orientationAngle))
        trafoMinv = np.mat(
            np.array(
                [
                    [c ** 2.0, s ** 2.0, 0.0, 0.0, 0.0, -2 * s * c],
                    [s ** 2.0, c ** 2.0, 0, 0.0, 0.0, 2 * s * c],
                    [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, c, s, 0.0],
                    [0.0, 0.0, 0.0, -s, c, 0.0],
                    [s * c, -s * c, 0.0, 0.0, 0.0, c ** 2 - s ** 2],
                ]
            )
        )

        rotStiff = trafoMinv * stiff * trafoMinv.T

        newMaterialDefinition.stiffnessMatrix = rotStiff
        newMaterialDefinition.id = f"{self.id}_{orientationAngle}"

        newMaterialDefinition.number += MYGLOBAL.maximalNumberOfMaterialDefinitions * int(orientationAngle)

        newMaterialDefinition.description = f"{self.id}rotated {orientationAngle}deg"
        newMaterialDefinition.name = f"{self.name}rotated {orientationAngle}deg"

        return newMaterialDefinition

    def getReducedStiffnessMatrix(self):
        """doc"""
        return self.getReducedStiffnessMatrixStatic(self.stiffnessMatrix)

    @staticmethod
    def getReducedStiffnessMatrixStatic(stiffnessMatrix):
        """calculates the reduced stiffness matrix
        see eq 2.63 [1]R. M. Jones, Mechanics Of Composite Materials, 2 New edition. Philadelphia, PA: Taylor & Francis Inc, 1998.
        
        :param stiffnessMatrix:
        """
        k = stiffnessMatrix

        redCom = np.zeros((3, 3))
        if k[2, 2] == 0 or k[3, 3] == 0 or k[4, 4] == 0:
            com = nplin.inv(k[:2, :2])
            redCom[:2, :2] = com[:2, :2]
            redCom[2, 2] = k[5, 5] ** -1
        else:
            com = nplin.inv(k)
            redCom[:2, :2] = com[:2, :2]
            redCom[2, 2] = com[5, 5]

        return nplin.inv(redCom)

    def _getkPlaneStressCondition(self):
        """doc"""
        if self._kPlaneStressCondition is not None:
            return self._kPlaneStressCondition

        self._kPlaneStressCondition = np.zeros((3, 3))

        denom = 1 - self.moduli["nu12"] * self.moduli["nu21"]
        # k11
        self._kPlaneStressCondition[0, 0] = self.moduli["e11"] / denom
        # k22
        self._kPlaneStressCondition[1, 1] = self.moduli["e22"] / denom
        # k66
        self._kPlaneStressCondition[2, 2] = self.moduli["g12"]
        # k12
        self._kPlaneStressCondition[0, 1] = self.moduli["nu12"] * self.moduli["e22"] / denom
        # k21
        self._kPlaneStressCondition[1, 0] = self._kPlaneStressCondition[0, 1]

        return self._kPlaneStressCondition

    def _getIsIsotrop(self):
        """:return: True if MaterialDefinition is isotrop. This is calculated by means of the stiffness matrix."""
        return abs((self.stiffnessMatrix[0, 1] / self.stiffnessMatrix[1, 2]) - 1) < MYGLOBAL.epsilon

    def _getIsOrthotrop(self):
        """:return: True if MaterialDefinition is orthotrop. This is calculated by means of the stiffness matrix."""
        return not np.any(self.stiffnessMatrix[3:, :3])

    def _getStiffnessInvariants(self):
        """doc"""

        reducedStiffness = np.array(
            [
                self.kPlaneStressCondition[0, 0],
                self.kPlaneStressCondition[1, 1],
                self.kPlaneStressCondition[0, 1],
                self.kPlaneStressCondition[2, 2],
            ]
        )

        coefficientMatrix = np.array(
            [
                [3.0 / 8.0, 3.0 / 8.0, 1.0 / 4.0, 1.0 / 2.0],
                [1.0 / 2.0, -1.0 / 2.0, 0.0, 0.0],
                [1.0 / 8.0, 1.0 / 8.0, -1.0 / 4.0, -1.0 / 2.0],
                [1.0 / 8.0, 1.0 / 8.0, 3.0 / 4.0, -1.0 / 2.0],
                [1.0 / 8.0, 1.0 / 8.0, -1.0 / 4.0, 1.0 / 2.0],
            ]
        )

        return np.dot(coefficientMatrix, reducedStiffness)

    stiffnessInvariants = property(fget=_getStiffnessInvariants)

    moduli = property(fget=_getModuli)

    kPlaneStressCondition = property(fget=_getkPlaneStressCondition)
    """see MaterialDefinition._kPlaneStressCondition"""

    isIsotrop = property(fget=_getIsIsotrop)
    isOrthotrop = property(fget=_getIsOrthotrop)

    specificHeat = property(fget=getSpecificHeat)


class Composite:
    """classdocs"""

    def __init__(self, **kwargs):
        """doc"""
        #StructureElement.__init__(self)
        self.id = None
        self.name = None
        self.description = None
        self.offset = None
        self.number = None
        self.xPath = None
        self.layers = []
        self._savedModuli = {}
        self.materialDefinitions = []
        self._laminationParameters = None
        """vector of length 12 (eq.7a-c from diaconu 2004)
        defines the lamination parameters for the whole composite"""
        self._stiffnessInvariants = None
        """vector of length 5 (eq.5 from diaconu 2004)
        stiffness invariants for the material of the whole composite. Only one material can be used for all layers"""

        for key in kwargs:
            if not hasattr(self, key):
                log.warning('Setting unknown key "%s" in class %s with name "%s"' % (key, self.__class__, str(self)))
            setattr(self, key, kwargs[key])

    def copy(self):
        """doc"""
        return self.__class__(
            id = self.id,
            name = self.name,
            description = self.description,
            offset = self.offset,
            layers = [layer.copy() for layer in self.layers],
            _savedModuli = self._savedModuli,
            materialDefinitions = self.materialDefinitions,
        )

    def getOffsetForSubLaminate(self, layers):
        """Calculates the actual z-coordinate of the specified layer (which belongs to the current laminate) wrt.
        the mid-plane of the laminate.

        :param layers: list, containing continuous instances of type Layer() or
            VariableStiffnessLayer() representing the sub-laminate
        
        :return: float, specifying the offset of the layer from the mid-plane of the laminate
        """
        layerStartIndex = self.layers.index(layers[0])
        layerEndIndex = self.layers.index(layers[-1])

        lowerZ = -self.thickness / 2.0
        distanceToLowerBorder = sum(self.layerThicknesses[:layerStartIndex])
        subLaminateThickness = sum(self.layerThicknesses[layerStartIndex : layerEndIndex + 1])
        return lowerZ + distanceToLowerBorder + subLaminateThickness / 2.0

    def _getThickness(self):
        """doc"""
        thickness = sum((layer.thickness for layer in self.layers), 0.0)

        if thickness < MYGLOBAL.epsilon:
            log.warning(f'thickness of composite with id "{self.id}" is zero. Resetting it to {MYGLOBAL.epsilon}')
            thickness = MYGLOBAL.epsilon
        return thickness

    def _getLayerOrientations(self):
        """doc"""
        return [layer.phi for layer in self.layers]

    def _getLayerThicknesses(self):
        """return layer thicknesses as list"""
        return np.array([layer.thickness for layer in self.layers])

    def _getRho(self):
        """doc"""
        rho = sum((layer.materialDefinition.rho * layer.thickness for layer in self.layers), 0.0)
        return rho / self.thickness

    def getABD(self, scaling=None, offset=None):
        """calculates ABD-matrix - see a composite book for explanation

        :param scaling: optional parameter to use a custom scaling of the thickness of the composites layers
        :param offset: optional parameter can set another offset. The reference plane
            is the composites middle plane. If offset is not given, the class property
            offset is used instead. If none of these are given, offset=0 which means the mid-thickness
            surface is the reference surface.
        """
        if self.layers:
            return self.getAbdByLayers(scaling, offset)

        if self.laminationParameters is not None:
            return self.getAbdByLaminationParameters()

        raise InternalError("There are no layers or lamination parameters defined")

    def getAbdByLayers(self, scaling=None, offset=None):
        """calculates ABD-matrix - see a composite book for explanation

        :param scaling: optional parameter to use a custom scaling of the thickness of the composites layers
        :param offset: optional parameter can set another offset. The reference plane
            is the composites middle plane. If offset is not given, the class property
            offset is used instead. If none of these are given, offset=0 which means the mid-thickness
            surface is the reference surface.

            abd             = ABD matrix
            zk              = offset of layer from the middle of the laminate
                              0 -> of previous layer, 1-> of present layer
            com             = compliance matrix
            redCom          = reduced compliance matrix
            redStiff        = reduced stiffness matrix
            redStiffVec     = reduced stiffness matrix in vector form
            transM          = transformation matrix
            redStiffVecGlo  = reduced stiffness vector in the global coordinate system
        """

        if scaling is None:
            scaling = 1.0
        if offset is None:
            offset = 0.0 if self.offset is None else self.offset

        abd = np.zeros((6, 6))
        zk1 = -(self.thickness * scaling) / 2 - offset
        for layer in self.layers:
            redStiff = MaterialDefinition.getReducedStiffnessMatrixStatic(layer.materialDefinition.stiffnessMatrix)
            redStiffMatGlo = MaterialDefinition.rotateReducedStiffnessMatrix(redStiff, np.radians(layer.phi))

            zk0 = zk1
            zk1 = zk0 + layer.thickness * scaling

            zkA = np.zeros((3, 3))
            zkA[:, :] = zk1 - zk0

            zkB = np.zeros((3, 3))
            zkB[:, :] = zk1 ** 2 - zk0 ** 2

            zkD = np.zeros((3, 3))
            zkD[:, :] = zk1 ** 3 - zk0 ** 3

            abd[:3, :3] += redStiffMatGlo * zkA
            abd[3:, :3] += redStiffMatGlo * zkB
            abd[:3, 3:] += redStiffMatGlo * zkB
            abd[3:, 3:] += redStiffMatGlo * zkD

        abd[3:, :3] = abd[3:, :3] * 1 / 2
        abd[:3, 3:] = abd[:3, 3:] * 1 / 2
        abd[3:, 3:] = abd[3:, 3:] * 1 / 3
        # ABD-matrix now fully calculated

        return abd

    def setLaminationParametersOfLayers(self, scaling=None, offset=None):
        """This method sets for each layer the lamination parameters according to the actual stacking sequence."""
        if scaling is None:
            scaling = 1.0
        if offset is None:
            offset = 0.0 if self.offset is None else self.offset

        actualZ = -(self.thickness * scaling) / 2 + offset
        for layer in self.layers:
            xsiAList = np.zeros(4)
            xsiBList = np.zeros(4)
            xsiDList = np.zeros(4)
            actualAngle = layer.phi * np.pi / 180.0
            actualThickness = layer.thickness

            previousZ = actualZ
            actualZ = previousZ + actualThickness

            cos2 = np.cos(2.0 * actualAngle)
            cos4 = np.cos(4.0 * actualAngle)
            sin2 = np.sin(2.0 * actualAngle)
            sin4 = np.sin(4.0 * actualAngle)

            xsiAList[0] += 1.0 / 2.0 * cos2 * (actualZ - previousZ)
            xsiAList[1] += 1.0 / 2.0 * cos4 * (actualZ - previousZ)
            xsiAList[2] += 1.0 / 2.0 * sin2 * (actualZ - previousZ)
            xsiAList[3] += 1.0 / 2.0 * sin4 * (actualZ - previousZ)

            xsiBList[0] += cos2 * (actualZ ** 2 - previousZ ** 2)
            xsiBList[1] += cos4 * (actualZ ** 2 - previousZ ** 2)
            xsiBList[2] += sin2 * (actualZ ** 2 - previousZ ** 2)
            xsiBList[3] += sin4 * (actualZ ** 2 - previousZ ** 2)

            xsiDList[0] += 3.0 / 2.0 * cos2 * (actualZ ** 3 - previousZ ** 3)
            xsiDList[1] += 3.0 / 2.0 * cos4 * (actualZ ** 3 - previousZ ** 3)
            xsiDList[2] += 3.0 / 2.0 * sin2 * (actualZ ** 3 - previousZ ** 3)
            xsiDList[3] += 3.0 / 2.0 * sin4 * (actualZ ** 3 - previousZ ** 3)

            layer.laminationParameters = [xsiAList, xsiBList, xsiDList]

    def getAbdByLaminationParameters(self):
        """doc"""
        if self._laminationParameters:
            # there are lamination parameters defined for the whole composite
            if self._stiffnessInvariants is None:
                raise Exception()
            return abdByLaminationParameters(self._laminationParameters, self._stiffnessInvariants, self.thickness)

        else:
            # calculate layerwise
            abdMatrix = np.zeros((6, 6))
            for layerIndex, layer in enumerate(self.layers):
                stiffnessInvariants = layer.stiffnessInvariants
                laminationParameters = np.array(self._getLamParmsCoeffMatOfLayer(layerIndex + 1)).flatten()
                abd = abdByLaminationParameters(laminationParameters, stiffnessInvariants, layer.thickness)
                abdMatrix += abd
            return abdMatrix

    def _getLamParmsCoeffMatOfLayer(self, layerNumber):
        """This method returns the lamination parameters of the specifed ply.

        :param layerNumber: int, the number of the layer within the actual stacking sequence (starting with 1)

        :return: list, containing three arrays (lamination parameter matrixes for a-Matrix, b-Matrix and d-Matrix)
        """
        laminationParameters = self.layers[layerNumber - 1].laminationParameters
        plyThickness = self.layers[layerNumber - 1].thickness
        ratio = plyThickness / self.thickness

        xsiAList = laminationParameters[0]
        xsiAMatrix = np.array(
            [
                [1.0 * ratio, xsiAList[0], xsiAList[1], 0.0, 0.0],
                [1.0 * ratio, -xsiAList[0], xsiAList[1], 0.0, 0.0],
                [0.0, 0.0, -xsiAList[1], 1.0 * ratio, 0.0],
                [0.0, 0.0, -xsiAList[1], 0.0, 1.0 * ratio],
                [0.0, xsiAList[2] / 2.0, xsiAList[3], 0.0, 0.0],
                [0.0, xsiAList[2] / 2.0, -xsiAList[3], 0.0, 0.0],
            ]
        )

        xsiBList = laminationParameters[1]
        xsiBMatrix = np.array(
            [
                [0.0, xsiBList[0], xsiBList[1], 0.0, 0.0],
                [0.0, -xsiBList[0], xsiBList[1], 0.0, 0.0],
                [0.0, 0.0, -xsiBList[1], 0.0, 0.0],
                [0.0, 0.0, -xsiBList[1], 0.0, 0.0],
                [0.0, xsiBList[2] / 2.0, xsiBList[3], 0.0, 0.0],
                [0.0, xsiBList[2] / 2.0, -xsiBList[3], 0.0, 0.0],
            ]
        )

        xsiDList = laminationParameters[2]
        xsiDMatrix = np.array(
            [
                [1.0 * ratio, xsiDList[0], xsiDList[1], 0.0, 0.0],
                [1.0 * ratio, -xsiDList[0], xsiDList[1], 0.0, 0.0],
                [0.0, 0.0, -xsiDList[1], 1.0 * ratio, 0.0],
                [0.0, 0.0, -xsiDList[1], 0.0, 1.0 * ratio],
                [0.0, xsiDList[2] / 2.0, xsiDList[3], 0.0, 0.0],
                [0.0, xsiDList[2] / 2.0, -xsiDList[3], 0.0, 0.0],
            ]
        )

        return [xsiAMatrix, xsiBMatrix, xsiDMatrix]

    @staticmethod
    def getLaminationParameter(thickness, orientation):
        """ Calculates and returns  the "Lamination Parameter"
        Source: Shutian Liu , Yupin Hou , Xiannian Sun , Yongcun Zhang: A two-step optimization scheme for
        maximum stiffness design of laminated
        plates based on lamination parameters, 2012

        p. 3531ff.
        """

        # Determine the normalized coordinate of thickness z
        # (origin: plane of symmetrie , direction: from plane of symmetrie to rim]

        thicknessList = orientation
        for i in range(0, len(thicknessList)):
            thicknessList[i] = thickness

        # t = [0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001] # test-thicknesses
        h = reduce(lambda x, y: x + y, thicknessList)

        ori = orientation  # list with plyorientations

        z = []  # list with normalized thickness-coordinates zi
        if len(thicknessList) % 2 == 0:
            for i in range(0, len(thicknessList) // 2):
                p = reduce(lambda k, l: k + l, thicknessList[i : len(thicknessList) / 2], 0)
                z.append(p)

            # reflect list at the plane of symmetry
            # z.extend(z[::1])
            z.append(0)
            zRezi = [-x for x in z]
            z.extend(zRezi[::-1])
            z.remove(0)
            zges = [x / h for x in z]

        else:

            try:
                i = 0
                while i < len(thicknessList) / 2:
                    p = (len(thicknessList) / 2 - i) * thickness

                    z.append(p)
                    i += 1

                z.append(0.5 * thickness)
                zRezi = [-x for x in z]
                z.extend(zRezi[::-1])
                zges = [x / h for x in z]
            except:
                z.append(0.5 * thickness)
                zRezi = [-x for x in z]
                z.extend(zRezi[::-1])
                zges = [x / h for x in z]

        # Calculation of the Lamination Parameter:

        lpA1 = []  # list of the components of lpA1 calculating to the Lamination Parameter lpA1ges
        lpA2 = []  # list of the components of lpA2 calculating to the Lamination Parameter lpA2ges
        lpA3 = []  # list of the components of lpA3 calculating to the Lamination Parameter lpA3ges
        lpA4 = []  # list of the components of lpA4 calculating to the Lamination Parameter lpA4ges
        lpB1 = []  # list of the components of lpB1 calculating to the Lamination Parameter lpB1ges
        lpB2 = []  # list of the components of lpB2 calculating to the Lamination Parameter lpB2ges
        lpB3 = []  # list of the components of lpB3 calculating to the Lamination Parameter lpB3ges
        lpB4 = []  # list of the components of lpB4 calculating to the Lamination Parameter lpB4ges
        lpD1 = []  # list of the components of lpD1 calculating to the Lamination Parameter lpD1ges
        lpD2 = []  # list of the components of lpD2 calculating to the Lamination Parameter lpD2ges
        lpD3 = []  # list of the components of lpD3 calculating to the Lamination Parameter lpD3ges
        lpD4 = []  # list of the components of lpD4 calculating to the Lamination Parameter lpD4ges
        lenThickness = len(thicknessList)  # number of plies of a stack
        # print 'lenThickness:', lenThickness
        for n in range(0, lenThickness - 1):
            # Lamination Parameter for matrix A

            lpA1n = (zges[n + 1] - zges[n]) * (math.cos(2 * ori[n] * math.pi / 180))
            lpA1.append(lpA1n)

            lpA2n = (zges[n + 1] - zges[n]) * (math.sin(2 * ori[n] * math.pi / 180))
            lpA2.append(lpA2n)

            lpA3n = (zges[n + 1] - zges[n]) * (math.cos(4 * ori[n] * math.pi / 180))
            lpA3.append(lpA3n)

            lpA4n = (zges[n + 1] - zges[n]) * (math.sin(4 * ori[n] * math.pi / 180))
            lpA4.append(lpA4n)

            # Lamination Parameter for matrix B

            lpB1n = (zges[n + 1] ** 2 - zges[n] ** 2) * (math.cos(2 * ori[n] * math.pi / 180))
            lpB1.append(lpB1n)

            lpB2n = (zges[n + 1] ** 2 - zges[n] ** 2) * (math.sin(2 * ori[n] * math.pi / 180))
            lpB2.append(lpB2n)

            lpB3n = (zges[n + 1] ** 2 - zges[n] ** 2) * (math.cos(4 * ori[n] * math.pi / 180))
            lpB3.append(lpB3n)

            lpB4n = (zges[n + 1] ** 2 - zges[n] ** 2) * (math.sin(4 * ori[n] * math.pi / 180))
            lpB4.append(lpB4n)

            # Lamination Parameter for matrix D

            lpD1n = (zges[n + 1] ** 3 - zges[n] ** 3) * (math.cos(2 * ori[n] * math.pi / 180))
            lpD1.append(lpD1n)

            lpD2n = (zges[n + 1] ** 3 - zges[n] ** 3) * (math.sin(2 * ori[n] * math.pi / 180))
            lpD2.append(lpD2n)

            lpD3n = (zges[n + 1] ** 3 - zges[n] ** 3) * (math.cos(4 * ori[n] * math.pi / 180))
            lpD3.append(lpD3n)

            lpD4n = (zges[n + 1] ** 3 - zges[n] ** 3) * (math.sin(4 * ori[n] * math.pi / 180))
            lpD4.append(lpD4n)

        truncToZero = lambda x: 0 if x < MYGLOBAL.epsilon else x

        # Lamination Parameter for A:
        lpA = []
        for lp_a in [lpA1, lpA2, lpA3, lpA4]:
            res = truncToZero(reduce(lambda i, j: i + j, lp_a, 0))
            lpA.append(res)

        # Lamination Parameter for B:
        lpB = []
        for lp_b in [lpB1, lpB2, lpB3, lpB4]:
            res = truncToZero(reduce(lambda i, j: i + 2 * j, lp_b, 0))
            lpB.append(res)

            # Lamination Parameter for D:
        lpD = []
        for lp_d in [lpD1, lpD2, lpD3, lpD4]:
            res = truncToZero(reduce(lambda i, j: i + 4 * j, lp_d, 0))
            lpD.append(res)

    # =========================================================

    def getPolarParameter(self, Q11, Q12, Q22, Q16, Q26, Q66):
        """ Calculates and returns  the "Polar Parameter" -> calculation according to: Optimal Orthotropy for Minimum Elastic Energy
            by the Polar Method by A. Vincenti , B. Desmorat"""

        # stiffnesses of the A- matrix were needed

        T0 = (Q11 + Q22 - 2 * Q12 + 4 * Q66) / 8
        T1 = (Q11 + Q22 + 2 * Q12) / 8
        R0 = (
            math.sqrt(
                (Q11 + Q22 - 2 * Q12 - 4 * Q66) * (Q11 + Q22 - 2 * Q12 - 4 * Q66)
                + (4 * (Q16 - Q26)) * (4 * (Q16 - Q26))
            )
        ) / 8
        R1 = (math.sqrt((Q11 - Q22) * (Q11 - Q22) + (2 * (Q16 + Q26)) * (2 * (Q16 + Q26)))) / 8

        if (Q16 - Q26) == 0:
            phi0 = 0
        else:
            try:
                phi0 = math.atan(4 * (Q16 - Q26) / (Q11 + Q22 - 2 * Q12 - 4 * Q66)) / 4
            except:
                phi0 = math.pi / 8

        if (Q16 + Q26) == 0:
            phi1 = 0
        else:
            try:
                phi1 = math.atan(2 * (Q16 + Q26) / (Q11 - Q22)) / 2
            except:
                phi1 = math.pi / 4

        return {"T0": T0, "T1": T1, "R0": R0, "R1": R1, "phi0": phi0, "phi1": phi1}

    def _getModuli(self):
        """
        abdCompliance   = inverse of (ABD matrix divided by the laminate thickness) 
        """
        if self._savedModuli != {}:
            return self._savedModuli
        abd = self.getABD()
        self._savedModuli = self.getModuliStatic(abd, self.thickness)
        return self._savedModuli

    @staticmethod
    def getModuliStatic(abd, thickness):
        """doc"""
        abdCompliance = nplin.inv(abd[:, :] / thickness)
        e11 = abdCompliance[0, 0] ** -1
        e22 = abdCompliance[1, 1] ** -1
        g12 = abdCompliance[2, 2] ** -1
        nu12 = -abdCompliance[1, 0] * e11
        nu21 = -abdCompliance[0, 1] * e22

        return {"e11": e11, "e22": e22, "g12": g12, "nu12": nu12, "nu21": nu21}

    def _isComposite(self):
        """doc"""
        return self.numberOfLayers != 1 or not self.layers[0].materialDefinition.isIsotrop

    def getInfoString(self):
        """doc"""
        retStr = "Composite with materialname, orientation, thickness\n"
        retStr += "\n".join(layer.getInfoString() for layer in self.layers)
        return retStr

    def _getNumberOfLayers(self):
        """doc"""
        return len(self.layers)

    def _getLaminationParameters(self):
        """doc"""
        laminationParameters = []
        xsiA = np.zeros(4)
        xsiB = np.zeros(4)
        xsiD = np.zeros(4)

        for layer in self.layers:
            # in case that not for all layers lamination parameters are set (e.g. when a layer was changed)
            if layer.laminationParameters is None:
                return None

            xsiA += layer.laminationParameters[0]
            xsiB += layer.laminationParameters[1]
            xsiD += layer.laminationParameters[2]

        laminationParameters += [xsiA, xsiB, xsiD]
        return laminationParameters

    rho = property(fget=_getRho)
    """homogenized density"""

    thickness = property(fget=_getThickness)

    layerorientation = property(fget=_getLayerOrientations)

    layerThicknesses = property(fget=_getLayerThicknesses)

    moduli = property(fget=_getModuli)

    isComposite = property(fget=_isComposite)

    abd = property(fget=getABD)

    numberOfLayers = property(fget=_getNumberOfLayers)

    laminationParameters = property(fget=_getLaminationParameters)


class Layer:
    """This class describes one layer of a composite"""

    def __init__(self, **kwargs):
        """doc"""
        #StructureElement.__init__(self)
        self.id = None
        self.name = None
        self.description = None
        self.phi = None
        """region between [0,180] degrees"""
        self.xPath = None
        self.laminationParameters = None
        self.thickness = None
        self._materialDefinition = None
        self.materialDefinitions = []

        for key in kwargs:
            if not hasattr(self, key):
                log.warning(f'Setting unknown key "{key}" in class {self.__class__} with name "{str(self)}"')
            setattr(self, key, kwargs[key])

    def copy(self):
        """Returns a copy of self"""
        return Layer(
            id = self.id,
            name = self.name,
            description = self.description,
            phi = self.phi,
            thickness = self.thickness,
            _materialDefinition = self._materialDefinition,
            materialDefinitions = self.materialDefinitions,
        )

    def _findMaterialDefinition(self, materialID):
        """doc"""
        if not self.materialDefinitions:
            raise InternalError(f"List of materialDefinitions in object {self} is empty!")
        for materialDefinition in self.materialDefinitions:
            if materialID == materialDefinition.id:
                return materialDefinition
        raise CpacsError(
            f'Could not find materialDefinition with id "{materialID}" at layer with xPath "{self.xPath}"'
        )

    def _setMaterialDefinition(self, materialDefinition):
        """doc"""
        if self.phi:
            materialDefinition.usedAngles.add(int(self.phi))
        self._materialDefinition = materialDefinition

    def _getMaterialDefinition(self):
        """doc"""
        return self._materialDefinition

    def getInfoString(self):
        """doc"""
        return f"{self.materialDefinition.name},\t{self.phi},\t{self.thickness}"

    materialDefinition = property(fset=_setMaterialDefinition, fget=_getMaterialDefinition)
