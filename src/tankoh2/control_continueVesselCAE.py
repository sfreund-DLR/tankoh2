# Continue vessel model implementation 
# -*- coding: utf-8 -*-

#Created on Wed July 14 12:30 2021
#Author: Carloline Lueders


###############################################################################
import sys

sys.path.append('C://DATA//Projekte//NGT_lokal//09_Projektdaten//03_Simulationsmodelle//01_Tankmodellierung_MikroWind//Projekt_MikroWind//tankoh2//src//tankoh2')
import os
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
    #modelname = 'NGT-BIT-2020-09-16_Solid3D'
    #modelname = 'NGT-BIT-2020-09-16_AxSolid'
    modelname = 'CcH2_Subscale_Axis'
    domefile = "C://DATA//Projekte//NGT_lokal//09_Projektdaten//03_Simulationsmodelle//01_Tankmodellierung_MikroWind//Projekt_MikroWind//Current_vessel//SetSimulationOptions//Dome_contour_NGT-BIT-2020-09-16_48mm.txt"
    layerPartPrefix = 'Layer'
    rzylinder = 200. # radius of cylindrical part
    lzylinder = 500. # length of cylindrical part
    nMandrels = 1 # number of mandrels
    reveloveAngle = 1.
    
# ------- Liner        
    linerthickness = 4.0
    createLiner = False

# ------- Material
    #layerMaterialPrefix = 'Layer'
    layerMaterialPrefix = 'WCM_Tank1_Mat1_Bin'
    materialPath = "C://DATA//Projekte//NGT_lokal//09_Projektdaten//03_Simulationsmodelle//01_Tankmodellierung_MikroWind//Projekt_MikroWind//tankoh2//data//CFRP_T700SC_LY556.json"
    materialName = "CFRP_T700SC_LY556"
    UMATprefix = "MCD_SHOKRIEH"    
    nDepvar = 312 # number of solution dependen variables
    degr_fac = 0.01 # degradation factor for material properties after failure initiation
    createUMAT = True    

# ------- Mesh    # remeshes with given number of elements per liner thickness (elementsPerLayerThickness) and wedge elements in very narrow regions (minAngle)
# set to reduced integration
# to do: distorted elements at fitting in widning and fitting
# --> hex-dominated in fitting, smaller global element size
# --> virtual topology /ignore edges --> modifiy Orientations as surfaces and edges for ori definition may be deleted
    elementsPerLayerThickness = 1       
    minAngle = 10.
    remesh = False

# ------- Boundary Conditions
    exceptionSets = ("Fitting1.contactFacesWinding", "Mandrel1_Layer_2.FittingContact")
    createPeriodicBCs = False
    


    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")  
    print("---------------------- START SCRIPT at "+current_time+" ---------------------------------")
    
    getModel(modelname)
    
    if remesh == True:
        cvc.reMeshVessel(elementsPerLayerThickness, layerPartPrefix, minAngle)

    if createLiner == True:
        cvc.loadDomeContourToSketch(domefile, rzylinder, lzylinder, linerthickness)
    
    if createUMAT == True:
        cvc.createUMATmaterials(model, layerMaterialPrefix, UMATprefix, materialPath, materialName, nDepvar, degr_fac)

    if createPeriodicBCs:
        cvc.applyPeropdicBCs(layerPartPrefix, reveloveAngle, exceptionSets)

    # step definition
    # generate output


    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")    
    print("---------------------- SCRIPT FINISHED at "+current_time+" ---------------------------------")

if __name__ == '__main__':
    main()