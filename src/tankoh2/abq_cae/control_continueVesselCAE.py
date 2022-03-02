# Continue vessel model implementation 
# -*- coding: utf-8 -*-

#Created on Wed July 14 12:30 2021
#Author: Carloline Lueders


###############################################################################
import sys, os

sys.path.append('C://DATA//Projekte//NGT_lokal//09_Projektdaten//03_Simulationsmodelle//01_Tankmodellierung_MikroWind//Projekt_MikroWind//tankoh2//src//tankoh2//abq_cae')

import numpy as np 
import json
import mesh
from datetime import datetime

import importlib
import continueVesselCAE as cvc

cvc = reload(cvc)

def getModel(projectname):  

    #sourcepath=os.getcwd()
    #projectname=getInput('Geben Sie den Projektnamen ein:',default='test')
    #projectpath=sourcepath+'////'+projectname
    #os.chdir(projectpath)
    #filename=os.listdir(projectpath) 

    modelname=projectname
    global model
    model = mdb.models[modelname]    
    global parts
    parts = model.parts
    global assembly
    assembly = model.rootAssembly

#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% MAIN PROGRAMM %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

def main():

#    %%%%%%%%%%%%% DEFINE PARAMETER %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

# ------- general    
    #modelname = 'NGT-BIT-2020-09-16_10_Solid3D' 
    #modelname = 'NGT-BIT-2020-10-15_AxSolid'
    #modelname = 'CcH2_Subscale_Axis'
    #modelname = "NGT-BIT-OPT-2021-11-05_AxSolid"
    modelname = 'NGT-BIT-2022-02-18_Shell_3DShell'
    domefile = "C://DATA//Projekte//NGT_lokal//09_Projektdaten//03_Simulationsmodelle//01_Tankmodellierung_MikroWind//Projekt_MikroWind//Current_vessel//SetSimulationOptions//Dome_contour_NGT-BIT-2020-09-16_48mm.txt"    
    rzylinder = 200. # radius of cylindrical part
    lcylinder = 290. # length of cylindrical part
    nMandrels = 1 # number of mandrels
    layerPartPrefix = 'Layer'    
    reveloveAngle = 180.
    CoordAxisWhichIsRotAxis = "y" # coordinate main axis which acts as vessels's rotation axis
    windingPartName = "Mandrel1"
    
# ------- Liner        
    linerthickness = 4.0
    createLiner = False

# ------- Material
    layerMaterialPrefix = 'Layer'
    layerMaterialPrefix = 'M1_Section'
    #layerMaterialPrefix = 'WCM_Tank1_Mat1_Bin'
    #materialName = "CFRP_HyMod"
    materialName = "CFRP_T700SC_LY556"
    materialPath = "C://DATA//Projekte//NGT_lokal//09_Projektdaten//03_Simulationsmodelle//01_Tankmodellierung_MikroWind//Projekt_MikroWind//tankoh2//data//"+materialName+".json"
    UMATprefix = "MCD_SHOKRIEH"    
    AbqMATinAcuteTriangles = False # if true, ABQ-Material is set for very acute triangle elements yielding warnings in mesh verification
    #nDepvar = 312 # number of solution dependen variables
    nDepvar = 156 # number of solution dependen variables
    #degr_fac = 0.40 # last value for berst pressure analysis
    degr_fac = 0.1 # degradation factor for material properties after failure initiation
    udLayers = True
    compositeLayup = True
    userDefinedField = False
    createUMAT = True
    removeUMAT = False

# ------------------- rename Material
    oldChars = '_ABQMAT'
    newChars = ''
    renameMaterials = False

# ------- Mesh    # remeshes with given number of elements per liner thickness (elementsPerLayerThickness) and wedge elements in very narrow regions (minAngle)
# set to reduced integration
# to do: distorted elements at fitting in widning and fitting
# --> hex-dominated in fitting, smaller global element size
# --> virtual topology /ignore edges --> modifiy Orientations as surfaces and edges for ori definition may be deleted
    elementsPerLayerThickness = 1       
    minAngle = 10.
    remesh = False

# ------- Periodic Boundary Conditions
    exceptionSets = (("Fitting1","contactFacesWinding"), ("Layer_1", "FittingContact")) # (partname, setname)
    createPeriodicBCs = False

# -------- Step-Definition

    steptime = [1.0, ]
    minInk = [1.0E-6, ]
    startInk = [0.001, ]
    maxInk = [0.05, ]
    stab = [4.0E-6, ]
    maxNumInk = [5000, ]
    NLGEOM = [ON, ]
    
    createStepDefinition = True

# ------ Output definition

    dt = 0.05 # time interval for output request; set 0 if no reuqest per time interval
    dnInk = 10 # interval of increment number for output request; set 0 if no reuqest per increment number
    fieldVariables = ('S','SDV', 'LE', 'P', 'U')
    historyVariables = () # leave empty if no history output
    createOutputDefinition = True

# ---------- Load Definition

    pressure = 1400 # bar
    valveForce = 0.
    createLoadDefinition = False

# ----------- Layer connection

    useContact = False # True -- use contact, False -- use Tie
    checkLayerConnection = False


############# START

    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")  
    print("---------------------- START SCRIPT at "+current_time+" ---------------------------------")
    
    getModel(modelname)
    
    if remesh == True:
        cvc.reMeshVessel(elementsPerLayerThickness, layerPartPrefix, minAngle, parts)

    if createLiner == True:
        cvc.loadDomeContourToSketch(domefile, rzylinder, lcylinder, linerthickness)
    
    if createUMAT == True:
        cvc.createUMATmaterials(model, layerMaterialPrefix, UMATprefix, materialPath, materialName, nDepvar, degr_fac, AbqMATinAcuteTriangles, udLayers, compositeLayup, windingPartName, userDefinedField)

    if removeUMAT == True:
        cvc.removeUMAT(model)

    if renameMaterials:
        cvc.renameMaterials(model, oldChars, newChars)
    
    if createStepDefinition:
        cvc.createStepDefinition(steptime, minInk, maxInk, startInk, maxNumInk, stab, NLGEOM, model)

    if createOutputDefinition:
        
        if maxInk > dt:
            print ('WARNING: maximal increment size is larger then output frequency. Output frequency is increased to fit maximum increment size')
            dt = max(maxInk) 
        cvc.createOutputDefinition(model, dt, dnInk, fieldVariables, historyVariables)

    if createLoadDefinition:
        cvc.createLoads(model, valveForce, pressure)

    if checkLayerConnection:
        cvc.adaptLayerConnection(model, parts, assembly, layerPartPrefix, useContact)        

    if createPeriodicBCs:
        cvc.applyPeropdicBCs(layerPartPrefix, reveloveAngle, exceptionSets, assembly, parts, model, useContact, CoordAxisWhichIsRotAxis) # 



    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")    
    print("---------------------- SCRIPT FINISHED at "+current_time+" ---------------------------------")

if __name__ == '__main__':
    main()