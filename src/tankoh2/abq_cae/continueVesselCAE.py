# Continue vessel model implementation 
# -*- coding: utf-8 -*-

#Created on Wed July 14 12:30 2021
#Author: Carloline Lueders


###############################################################################
import sys
import os
import numpy as np 
import json
import mesh
from datetime import datetime
from symbolicConstants import *
from abaqusConstants import *
import regionToolset

global nDepvar_UserDefField
nDepvar_UserDefField = 35

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

    return model, parts, assembly

def getInnerDomeContour(ys, xs, linerthickness, rzylinder):

#   generates the inner dome conture form the given outer dome contur
#   inner dome contour created by constant distance (thickness) from 
#   outer contur
#
#   returns x and y values of inner dome/liner contour
#
#   ys              : array of y values of outer liner contur
#   xs              : array of x values of outer liner contur
#   linerthickess   : desired thickness of liner
#   rzylinder       : radius in cylindrical regime (outer side of liner = inner side of winding)

    xs_inner = list()
    ys_inner = list()

    for i in range(len(ys)):
        x0 = xs[i]
        y0 = ys[i]

        print(x0, y0)
        
        if x0 == rzylinder: # if position is on krempe/cylinder
            xs_inner.append(x0-linerthickness)
            ys_inner.append(y0)                                  
        else:

            # calculate tangent slope in (y0,x0) / dy/dx
            if i == 1: # use forward difference equations
                print('first data point')
                if (ys[i+1]-y0) == 0.:
                    tangent_slope = float('inf')
                else:   
                    tangent_slope = (xs[i+1]-x0) / (ys[i+1]-y0)
            elif i == len(ys)-1: # usee backward difference equations
                print('last data point')
                if (ys[i-1]-y0)  == 0.:
                    tangent_slope = float('inf')
                else:
                    tangent_slope = (xs[i-1]-x0) / (ys[i-1]-y0)                

            else: # use central difference equations            
                if (ys[i+1]-ys[i-1]) == 0.:
                    tangent_slope = float('inf')
                else:
                    tangent_slope = (xs[i+1]-xs[i-1]) / (ys[i+1]-ys[i-1])                 

            # get point on inner liner contour
            if tangent_slope == 0: # this is in cylidnrical regime
                xs_inner.append(x0-linerthickness)
                ys_inner.append(y0)
            elif tangent_slope == float('inf'): # this is exact at polar opening
                xs_inner.append(x0)
                ys_inner.append(y0-linerthickness)
            else: # this is in dome regime
                # get point on contour normal that is linerthickness away from current point
                # (y0, x0); there are tow points -- one outsinde, one inside the liner
                # so firts solve pq-euaqtion to obtain corresponding y-avlues
                #yinner_1 = y0 + np.sqrt(y0**2. - (y0**2. - linerthickness**2. * tangent_slope**2.0) )
                #yinner_2 = y0 - np.sqrt(y0**2. - (y0**2. - linerthickness**2. * tangent_slope**2.0) )

                # get corresponding x-values (dome radius)
                #xinner_1 = (-1./tangent_slope)*yinner_1 + x0 + y0/tangent_slope
                #xinner_2 = (-1./tangent_slope)*yinner_2 + x0 + y0/tangent_slope

                # choose point lying within the vessel
                #if xinner_1 < x0:
                #    xs_inner = list(xs_inner)+list([xinner_1])   
                #    ys_inner = list(ys_inner)+list([yinner_1])   
                #else:
                #    xs_inner = list(xs_inner)+list([xinner_2])    
                #    ys_inner = list(ys_inner)+list([yinner_2])  

                xinner =x0-linerthickness*np.sin(np.arctan(-1.0/tangent_slope))
                xs_inner.append(xinner) 
                ys_inner.append(-tangent_slope*xinner+y0+x0*tangent_slope)                    

    return xs_inner, ys_inner


def getDomeContourFromFile(domefilename, rzylinder, lcylinder, linerthickness):

#   reads and returns x,y-values of liner contour
#
#   return contour: [x-values,y-values]; x = radius-position, y = position on tank axis
#   return sheetSize: estimated sheet size for liner sketch
#
#   input domefilename  : name of txt-file including datapoints of outer liner contour
#   input rzylinder     : radius in cylindrical regime (outer side of liner = inner side of winding)
#   input lcylinder     : length of cylincrical regime of tank
#   input linerthickess   : desired thickness of liner
#
    
    filename = open(domefilename,"r") 
    print ('Read dome contour from ', domefilename)
    Data = np.loadtxt(filename)  
    filename.close()   

    ys = abs(Data[:, 0])-abs(Data[0,0])+lcylinder/2. # positiona long axis
    xs = abs(Data[:,1]) # position dome radius
    dy = abs(max(ys)-min(ys))
    dx = abs(max(xs)-min(xs))
    sheetSize = max(dy, dx)

    xs_inner, ys_inner = getInnerDomeContour(ys, xs, linerthickness, rzylinder)

    xs_inner_rev = list(xs_inner)    
    xs_inner_rev.reverse()

    ys_inner_rev = list(ys_inner)
    ys_inner_rev.reverse()  

    ys = np.array(list([0.0] + list(ys) + ys_inner_rev + list([0.0]) ))
    xs = np.array(list([rzylinder] + list(xs) + xs_inner_rev + list([rzylinder-linerthickness]) ))
    
    
    contour = tuple((x,y) for x,y in zip(xs,ys))      

    return contour, sheetSize


def loadDomeContourToSketch(domefilename, rzylinder, lcylinder, linerthickness):

#   loads dome contour from file into Abaqus-Sketch
#
#   return: none
#
#   input domefilename  : name of txt-file including datapoints of outer liner contour
#   input rzylinder     : radius in cylindrical regime (outer side of liner = inner side of winding)
#   input lcylinder     : length of cylincrical regime of tank
#   input linerthickess   : desired thickness of liner
#
    contourpoints, sheet = getDomeContourFromFile(domefilename, rzylinder, lcylinder, linerthickness)  

    s1 = model.ConstrainedSketch(name='Liner', sheetSize=sheet)  
    s1.Spline(points = contourpoints)
    s1.Line(point1 = (rzylinder-linerthickness, 0.0), point2 = (rzylinder, 0.0))

def getPropsFromJson(materialPath, materialName):

# reads material props from json file
#
#   return props : array of prop values
#
#   input materialPath  : json-file (whole file path)
#   input materialName  : name of material for wich paramaters are to be read
    
    with open(materialPath,'r') as file:
        materialJson = json.loads(file.read())   

    for materialnr in materialJson["materials"]:

        if materialJson["materials"][str(materialnr)]["name"] == materialName:
            print('found material', materialJson["materials"][str(materialnr)]["name"])

            nTemps = materialJson["materials"][str(materialnr)]["umatProperties"]["number_of_temperatures"]            
            
            props = np.empty(0)
            #print(props)
            
            for temp in range(1, nTemps+1):
                
                Temp = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["Temp"]                

                E11 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["E_1"]
                E22 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["E_2"]
                E33 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["E_3"]
                G23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["G_23"]
                G13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["G_13"]
                G12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["G_12"]
                nu23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["nu_23"]
                nu13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["nu_13"]            
                nu12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["nu_12"]     
                eta = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["eta"]     
                Xt = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatPuckProperties"]["R_1_t"]     
                Xc = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatPuckProperties"]["R_1_c"]     
                Yt = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatPuckProperties"]["R_2_t"]     
                Yc = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatPuckProperties"]["R_2_c"]     
                S12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatPuckProperties"]["R_21"]     
            
                beta_2_11t = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_11t"]    
                beta_2_11c = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_11c"]  
                beta_2_22t = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_22t"]
                beta_2_22c = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_22c"]
                beta_2_33t = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_33t"]
                beta_2_33c = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_33c"]
                beta_2_12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_12"]
                beta_2_13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_13"]
                beta_2_23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_23"]
                beta_1_11t = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_11t"]
                beta_1_11c = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_11c"]
                beta_1_22t = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_22t"]
                beta_1_22c = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_22c"]
                beta_1_33t = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_33t"]
                beta_1_33c = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_33c"]
                beta_1_12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_12"]
                beta_1_13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_13"]
                beta_1_23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_23"]
                lambda_1_11 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_1_11"]
                lambda_1_22 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_1_22"]
                lambda_1_33 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_1_33"]
                lambda_1_12 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_1_12"]
                lambda_1_13 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_1_13"]
                lambda_1_23 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_1_23"]
                lambda_2_11 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_2_11"]
                lambda_2_22 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_2_22"]
                lambda_2_33 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_2_33"]
                lambda_2_12 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_2_12"]
                lambda_2_13 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_2_13"]
                lambda_2_23 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_2_23"]
                A_11 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["A_11"]
                B_11 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["B_11"]
                A_22 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["A_22"]
                B_22 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["B_22"]
                A_33 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["A_33"]
                B_33 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["B_33"]
                A_12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["A_12"]
                B_12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["B_12"]
                A_13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["A_13"]
                B_13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["B_13"]
                A_23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["A_23"]
                B_23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["B_23"]
                u_11 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["u_11"]
                u_22 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["u_22"]
                u_33 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["u_33"]
                u_12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["u_12"]
                u_13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["u_13"]
                u_23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["u_23"]
                v_11 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["v_11"]
                v_22 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["v_22"]
                v_33 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["v_33"]
                v_12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["v_12"]
                v_13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["v_13"]
                v_23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["v_23"]


                #print('eta', eta)

                props = np.append(props, [E11, E22, E33, G12, G13, G23, nu12, nu13, nu23, Xt, Yt, Yt, Xc, Yc, Yc, S12, S12, S12, beta_2_11t, beta_2_11c, beta_2_22t, beta_2_22c, 
                beta_2_33t, beta_2_33c, beta_2_12 , beta_2_13 , beta_2_23 , beta_1_11t, beta_1_11c, beta_1_22t, beta_1_22c, beta_1_33t, beta_1_33c, beta_1_12 , beta_1_13 , beta_1_23 , 
                lambda_1_11, lambda_1_22, lambda_1_33, lambda_1_12, lambda_1_13, lambda_1_23, lambda_2_11, lambda_2_22, lambda_2_33, lambda_2_12, lambda_2_13, lambda_2_23, A_11, B_11, A_22, 
                B_22, A_33, B_33, A_12, B_12, A_13, B_13, A_23, B_23, eta, u_11, u_22, u_33, u_12, u_13, u_23, v_11, v_22, v_33, v_12, v_13, v_23, Temp])
                
                
                #props.extend([E11, E22, E33, G12, G13, G23, nu12, nu13, nu23, Xt, Yt, Yt, Xc, Yc, Yc, S12, S12, S12, beta_2_11t, beta_2_11c, beta_2_22t, beta_2_22c, 
                #beta_2_33t, beta_2_33c, beta_2_12 , beta_2_13 , beta_2_23 , beta_1_11t, beta_1_11c, beta_1_22t, beta_1_22c, beta_1_33t, beta_1_33c, beta_1_12 , beta_1_13 , beta_1_23 , 
                #lambda_1_11, lambda_1_22, lambda_1_33, lambda_1_12, lambda_1_13, lambda_1_23, lambda_2_11, lambda_2_22, lambda_2_33, lambda_2_12, lambda_2_13, lambda_2_23, A_11, B_11, A_22, 
                #B_22, A_33, B_33, A_12, B_12, A_13, B_13, A_23, B_23, eta, u_11, u_22, u_33, u_12, u_13, u_23, v_11, v_22, v_33, v_12, v_13, v_23, Temp])

    #print(props)    

    return props

def getNumberOfLayerParts(layerPartPrefix, parts):

# returns number of parts with names beginning with "layerPartPrefix"    
#
#   return nLayerParts  : numer of parts [int]
#
#   input layerPartPrefix   : name prefix of parts to be counted

    #parts = model.parts
    nParts = len(parts)
    
    nLayerParts = 0    
    for p in range(nParts):        
        try:
            layerpart = parts[layerPartPrefix+"_"+str(p)]
            nLayerParts = nLayerParts+1
        except:
            print("maximum number of parts beginnung with "+layerPartPrefix+" is found to be "+str(nLayerParts))

    return nLayerParts

def renameMaterials(model, oldChars, newChars):

#   change prefix and/or appendix in material names

#   Input 
#       string  oldPrefix       Prefix in Material name that should be replaced with a new prefix
#       string  newPrefix       new prefix in material name that sould  replace the old one
#       string  oldAppendix     Appendix in Material name that should be replaced with a new appendix
#       string  newAppendix     new appendix in material name that sould replace the old one
# Return
#   none

    print("*** RENAME MATERIALS ***") 
    print("-- cange "+oldChars+" to "+newChars)     
    
    materials = model.materials    
    sections = model.sections

    for key in materials.keys():       # ["MCD_SHOKRIEH_Layer_4_M1_233"]        
        if oldChars in key:                        
            newkey = key. replace(oldChars, newChars)
            materials.changeKey(fromName=key, toName=newkey)
            sections[key].setValues(material=newkey, thickness=None)    

def removeUMAT(model):

    print("*** REMOVE UMAT AND RE-ASSIGN ABQ-MATERIAL ***")  

    materials = model.materials    
    sections = model.sections

    for sectionkey in sections.keys():
        sections[sectionkey].setValues(material=sectionkey, thickness=None) 


def createUMAT(model, material, UMATName, MatProps, nDepvar, degr_fac, udLayers, userDefinedField):

#   for a given material a second Material with UMAT and, if demanded, user-defined-field definition, is created
#   material parameters, and description from the given material are used
#
#   INPUT
#       model               [model object]      : model to be treated
#       material            [material object]   : material for which a copy with
#       UMATName            [string]            : name of the new material with UMAT
#       MatProps            [list of floats]    : umat material properties
#       nDepvar             [int]               : number of statev variables 
#       degr_fac            [float ]            : degradation factor for property degradation due to damage; 0 ... 1
#       udLaywers           [Boolean]           : true, if UD-layers are modelled; false if balanced angle plies are modelled
#       userDefinedField    [Boolean]           : true, if also user defined field shall be defined for material; false im not
#
#   RETURN
#       None.
#   

    
    propsTemp = MatProps.copy()   
    
    if userDefinedField:
        nDepvar = nDepvar+nDepvar_UserDefField


    materialDescription= material.description
    if not udLayers:
        #get band angle from material description        
        angle = getBandAngleFromMaterialDescription(materialDescription)
    else:
        angle = 0.

    
    # append angle and degradation factor to props
    propsTemp = np.append(propsTemp, [angle])
    propsTemp = np.append(propsTemp, [degr_fac])
    
    # genereate Material with UMAT definition but also keep Abaqus-Standardmaterial definition for
    # use in triangle elements
    UmatMaterial = model.Material(name = UMATName, description = materialDescription)                                      
    UmatMaterial.UserMaterial(mechanicalConstants = propsTemp) 
    UmatMaterial.Depvar(n=nDepvar)  

    if userDefinedField:
        UmatMaterial.UserDefinedField()


def createUMATName(oldMatName, UMATprefix):

#   generates the name for a UMAT material from the old material name and a UMAT-prefix; consideres if UMAT material already exists for the given material name
#
#   INPUT

#       oldMatName          [string]      : name of the material
#       UMATprefix          [string]      : name prefix for materials with UMAT definition
#
#   RETURN
#       UMATName    [string]    : name of the UMAT material
#       sectionkey  [string]    : name of the section, the old Material is assigned to    
#   
    
    key = oldMatName
    if not key[0:len(UMATprefix)] == UMATprefix and len(UMATprefix)>0:
        newKey = UMATprefix+'_'+key                
        sectionkey = key                
    else:
        newKey = key  
        sectionkey = newKey[13:len(newKey)]
    
    UMATName = newKey

    return UMATName, sectionkey

def createUMATforHomogeneousSection(model, materials, layerMaterialPrefix, UMATprefix, materialProps, nDepvar, degr_fac, AbqMATinAcuteTriangles, udLayers, userDefinedField):

#   for a given material a material equivalent with UMAT (and user defined field) definition is created; material assignment of the section the given material is assigned to, is changed to the
#   UMAT material 
#
#   INPUT
#       model                   [model object]      : model to be treated
#       material                [material object]   : material for which a copy with
#       layerMaterialPrefix     [string]            . prefix of the material names which are materialdefinitions for frp layers of the winding
#       UMATprefix              [string]            : name prefix for materials with UMAT definition
#       materialProps           [list of floats]    : umat material properties
#       nDepvar                 [int]               : number of statev variables 
#       degr_fac                [float ]            : degradation factor for property degradation due to damage; 0 ... 1
#       AbqMATinAcuteTriangles  [boolean]           : true, if in sharp wegde elements no umat shall be used (instead abaqus material is assigned); false, if UMAT shall be used in all wedge elements, too
#       udLaywers           [Boolean]           : true, if UD-layers are modelled; false if balanced angle plies are modelled
#       userDefinedField    [Boolean]           : true, if also user defined field shall be defined for material; false im not
#
#   RETURN
#       None.
#   

    for key in materials.keys():       # ["MCD_SHOKRIEH_Layer_4_M1_233"]
        print('key', key)
        if (key[0:len(layerMaterialPrefix)] == layerMaterialPrefix) or (key[13:13+len(layerMaterialPrefix)] == layerMaterialPrefix):            
            material = materials[key]            
            propsTemp = materialProps.copy()

            newKey, sectionkey = createUMATName(key, UMATprefix)

            #print('nexKey', newKey)
            #print('sectionkey', sectionkey)

            createUMAT(model, material, newKey, propsTemp, nDepvar, degr_fac, udLayers, userDefinedField)
            
# ---------- Assign UMAT to section definition rename material to trigger UMAT    
            if len(UMATprefix) > 0:                           
                #material.changeKey(fromName=key, toName=newKey)
                sections[sectionkey].setValues(material=newKey, thickness=None)           
                                    
            if AbqMATinAcuteTriangles:   
                # check which mandrel current section belongs to; this is defined within the section name "Layer_X_M1_xyz"--> mandrel 1, "..._M2_..." --> Mandrel 2
                keyword = '_M'
                before_keyword, keyword, after_keyword = sectionkey.partition(keyword)   # 1_xyz or 2_xyz                                
                keyword = "_"                 
                before_keyword, keyword, after_keyword = after_keyword.partition(keyword)  # now before_keyword gives the Mandrel number                                                            
                setABQUMATinAcuteTriangles(model, 'Mandrel'+before_keyword, sectionkey, materialDescription)


def createUMATforCompositeLayup(model, part, materials, layerMaterialPrefix, UMATprefix, materialProps, nDepvar, degr_fac, AbqMATinAcuteTriangles, udLayers, userDefinedField):

#   for a given material a material equivalent with UMAT (and user defined field) definition is created; material assignment of the plies in all compositelayuo definitions is updated
#   to reference the UMAT material 
#
#   INPUT
#       model                   [model object]      : model to be treated
#       part                    [part object]       : part (winding) to be treated
#       material                [material object]   : material for which a copy with
#       layerMaterialPrefix     [string]            . prefix of the material names which are materialdefinitions for frp layers of the winding
#       UMATprefix              [string]            : name prefix for materials with UMAT definition
#       materialProps           [list of floats]    : umat material properties
#       nDepvar                 [int]               : number of statev variables 
#       degr_fac                [float ]            : degradation factor for property degradation due to damage; 0 ... 1
#       AbqMATinAcuteTriangles  [boolean]           : true, if in sharp wegde elements no umat shall be used (instead abaqus material is assigned); false, if UMAT shall be used in all wedge elements, too
#       udLaywers               [Boolean]           : true, if UD-layers are modelled; false if balanced angle plies are modelled
#       userDefinedField        [Boolean]           : true, if also user defined field shall be defined for material; false im not
#
#   RETURN
#       None.
#  

    propsTemp = materialProps.copy()

    for compositeLayupKey in part.compositeLayups.keys():
        print('-------------- '+compositeLayupKey+' -----------------------')       

        compositePlyList = list()

        for plyNo in range(len(part.compositeLayups[compositeLayupKey].plies)):
            ply = part.compositeLayups[compositeLayupKey].plies[plyNo]
            materialName = ply.material            
            material = model.materials[materialName]

            # extract values of composite ply and store in list
            compositePly = (ply.thickness, ply.region, ply.material, ply.plyName, ply.orientationType, ply.thicknessType, ply.orientationValue, ply.thicknessField, ply.numIntPoints, ply.axis, ply.angle, ply.additionalRotationType, ply.orientation, ply.additionalRotationField)
            compositePlyList.append(compositePly)
                      

            # create UMAT for material
            UMATName, sectionkey = createUMATName(materialName, UMATprefix)
            createUMAT(model, material, UMATName, propsTemp, nDepvar, degr_fac, udLayers, userDefinedField)

        # values of plies cannot be changed (no setValues methode) --> plies have to be deleted and defined again
        part.compositeLayups[compositeLayupKey].deletePlies()

        # re-generate plies with new material assignment
        for compositePly in compositePlyList:
            UMATName, sectionkey = createUMATName(compositePly[2], UMATprefix)                                    
            compositeLayup = part.compositeLayups[compositeLayupKey]
            compositeLayup.CompositePly(suppressed=False, plyName=compositePly[3], region=part.sets[compositePly[1][0]], material=UMATName, thicknessType=compositePly[5], thickness=compositePly[0],  orientationType=compositePly[4], orientationValue=float(compositePly[6]), additionalRotationType=compositePly[11], additionalRotationField=compositePly[13], axis=compositePly[9], angle=compositePly[10], numIntPoints=3)            

def createUMATmaterials(model, layerMaterialPrefix, UMATprefix, materialPath, materialName, nDepvar, degr_fac, AbqMATinAcuteTriangles, udLayers, compositeLayup, windingPartName, userDefinedField):

#   create material card for UMAT from material props from given json file
#
#   input layerMaterialPrefix : prefix used in material name for layer materials, e.g. "Layer_"
#   inout materialPath  : json-file (whole file path)
#   input materialName  : name of material for wich paramaters are to be read
#   input udLayers      : boolean if udLayers (true) or balance angle plies (false) are modelled
#   input compositeLayup : boolean; true if compositelayup is used as material section; false if not
#   input windingPartName : name of winding part
#   input userDefinedField : true if user defined field hall be activated in material definition

    print("*** START GENERATE UMAT MATERIAL CARDS ***")  

    materials = model.materials    
    sections = model.sections
    materialProps = getPropsFromJson(materialPath, materialName)    
    part = model.parts[windingPartName]

    print("*** GENERATE UMAT MATERIAL CARDS ***")    
        
    if not compositeLayup:
        createUMATforHomogeneousSection(model, materials, layerMaterialPrefix, UMATprefix, materialProps, nDepvar, degr_fac, AbqMATinAcuteTriangles, udLayers, userDefinedField)
    else:
        createUMATforCompositeLayup(model, part, materials, layerMaterialPrefix, UMATprefix, materialProps, nDepvar, degr_fac, AbqMATinAcuteTriangles, udLayers, userDefinedField)
            

def setABQUMATinAcuteTriangles(model, partname, sectionkey, materialDescription):         

# assigns Abaqus Standard Material to very acute triangle elements
# empty material definition is definded; Elastic material behaviour with specific
# material constants has to be added later; band angle is given in material description
#
#   return: none
#
#   input   sectionkey  :   section key of section containing elements for check and replace material [name string]
#   input   model    : model object    

    #print('serach for bad shaped triangles in material assignment '+sectionkey)
    part = model.parts[partname]
    elements = part.sets[sectionkey].elements
    i = -1
    for element in elements:        
        i = i+1
        if str(element.type) == "CAX3":
            #print ('triangle element with label', element.label)              
            edges = element.getElemEdges()            
            angle = getAngleBetweenMeshEdges(edges, part.vertices)
            #print (angle)
            if angle < 15.:                
                var1 = False
                
                if var1:
                    # change Material only for triangle element to Abq-Standard
                    part.Set(name = sectionkey+'_ABQMAT', elements = (part.sets[sectionkey].elements[i:i+1], ))                                
                    model.HomogeneousSolidSection(material=sectionkey, name=sectionkey+'_ABQMAT', thickness=None)
                    part.SectionAssignment(region=part.sets[sectionkey+'_ABQMAT'], sectionName=sectionkey+'_ABQMAT')
                else:
                    # change Material of whole section the element belongs to --> also for neighbouring elements Material is changed to Abq-Standard
                    model.sections[sectionkey].setValues(material=sectionkey, thickness=None)
            #print('----------------------')

def getElasticPropsFromMaterialDescription(materialDescription):

    keyword = 'elasticPropsUD'
    before_keyword, keyword, after_keyword = materialDescription.partition(keyword)            
    keyword = ':'
    before_keyword, keyword, after_keyword = after_keyword.partition(keyword)            
    keyword = '['
    before_keyword, keyword, after_keyword = after_keyword.partition(keyword)            
    keyword = ']'
    before_keyword, keyword, after_keyword = after_keyword.partition(keyword)                
    keyword = ','
    before_keyword, keyword, after_keyword = before_keyword.partition(keyword)            
    E1 = float(before_keyword)    
    before_keyword, keyword, after_keyword = after_keyword.partition(keyword)            
    E2 = float(before_keyword)
    before_keyword, keyword, after_keyword = after_keyword.partition(keyword)            
    G12 = float(before_keyword)
    before_keyword, keyword, after_keyword = after_keyword.partition(keyword)            
    nu12 = float(before_keyword)
    before_keyword, keyword, after_keyword = after_keyword.partition(keyword)            
    nu23 = float(before_keyword)

    return E1, E2, G12, nu12, nu23


def getBandAngleFromMaterialDescription(materialDescription):  

#   extract the band angle of the balanced anle ply the material represents by effective properties
# 
# INPUT
#   materialDescription [string]    : whole text of the material description
# 
# RETURN
#   angle [float]   : band angle
#   
    
    if 'Mean Angle' in materialDescription: # for Models generated from muWind
        keyword = 'Mean Angle: '
        before_keyword, keyword, after_keyword = materialDescription.partition(keyword)            
        keyword = 'Clairault'
        before_keyword, keyword, after_keyword = after_keyword.partition(keyword)                
        angle_str = before_keyword.replace(',', '')
        angle = float(angle_str)      
    elif 'Beta' in materialDescription: # for models generated from WoundCompositeModeller
        keyword = 'Beta = '
        before_keyword, keyword, after_keyword = materialDescription.partition(keyword)
        keyword = ' ****'
        before_keyword, keyword, after_keyword = after_keyword.partition(keyword)
        angle_str = before_keyword
        #print(angle_str)
        angle = float(angle_str)  

    return angle

def getAngleBetweenMeshEdges(edges, partVertices):

# calculates the angle between given edges in Abaqus Model
#
#   return: angle between edges in degree
#
#   input   edges           : list/array of MeshEdge objects
#   input   partVertices    : all vertices of the part the edges belongs to

    slopes = []
    alphas = []

    for edge in edges:
        EdgeNodes = edge.getNodes()                
        x0 = EdgeNodes[0].coordinates[0]
        y0 = EdgeNodes[0].coordinates[1]
        x1 = EdgeNodes[1].coordinates[0]
        y1 = EdgeNodes[1].coordinates[1]
        
        xmin = min(x0,x1)
        ymin = min(y0,y1)
        xmax = max(x0,x1)
        ymax = max(y0,y1)

        if abs((ymax - ymin)) > 0:
            slopes.append((xmax-xmin)/(ymax-ymin))
        else:
            slopes.append((ymax-ymin)/(xmax-xmin))
    
    alphas.append(np.arctan(abs((slopes[0]-slopes[1])/(1+slopes[0]*slopes[1]))))
    alphas.append(np.arctan(abs((slopes[0]-slopes[2])/(1+slopes[0]*slopes[2]))))
    alphas.append(np.arctan(abs((slopes[1]-slopes[2])/(1+slopes[1]*slopes[2]))))    

    alpha = min(alphas)

    return (alpha*180)/np.pi

def getAngleBetweenEdges(edges, partVertices):

# calculates the angle between given edges in Abaqus Model
#
#   return: angle between edges in degree
#
#   input   edges           : list/array of edge objects
#   input   partVertices    : all vertices of the part the edges belongs to

    slopes = []

    for edge in edges:
        EdgeVerticesIDs = edge.getVertices()     
        x0 = partVertices[EdgeVerticesIDs[0]].pointOn[0][0]
        y0 = partVertices[EdgeVerticesIDs[0]].pointOn[0][1]
        z0 = partVertices[EdgeVerticesIDs[0]].pointOn[0][2]
        x1 = partVertices[EdgeVerticesIDs[1]].pointOn[0][0]
        y1 = partVertices[EdgeVerticesIDs[1]].pointOn[0][1]
        z1 = partVertices[EdgeVerticesIDs[1]].pointOn[0][2]

        # consider only edges lying in xy-plane
        if (z0, z1) == (0., 0.):
            xmin = min(x0,x1)
            ymin = min(y0,y1)
            xmax = max(x0,x1)
            ymax = max(y0,y1)

            slopes.append((xmax-xmin)/(ymax-ymin))

    alpha = np.arctan(abs((slopes[0]-slopes[1])/(1+slopes[0]*slopes[1])))

    return (alpha*180)/np.pi

def seedLayerThicknessEdges(layerPartPrefix, elementsPerLayerThickness, minAngle, parts):

#   sets mesh seeds at the leyer edges which represent the layer thickness
#   sets wedge elements for regions which are limited by edges with very small angles (e.g. narrow ends of layers)
#
#   return  none
#
# input layerPartPrefix             : name prefix of layer parts
# input elementsPerLayerThickness   : numer of elements desired per layer thickness, integer
# input minAngle                    : minimum anlge for using hex elements (for regions with lower angles, wedge elements are set)



    #parts = model.parts

    # define set in layer thickness direction that can be seeded later
    for p in range(len(parts)): #      

        try:
            part = parts[layerPartPrefix+'_'+str(p)] 
            layerPart = True
            print(layerPartPrefix+'_'+str(p)) 
        
        except KeyError:
            print('This is no Layer part') 
            layerPart = False      

        if layerPart == True:
            # get geometry entities
            partEdges = part.edges
            partVertices = part.vertices
            partGeometry = part.queryGeometry(printResults = False)

            # clear 
            part.deleteMesh()
            axialBottomEdge = partEdges.getByBoundingBox(-10000., -10000., -0.01, 10000., 10000., 0.01, )  
            part.deleteSeeds(regions=(axialBottomEdge, ))
            
            # get geometric expanion of part // min and max coordinates
            boundingBoxMax = partGeometry["boundingBox"][1]
            maxVertexY = boundingBoxMax[1]

            # get vertex at dome wich is at the outer geometry position of part
            maxVertex = partVertices.getByBoundingBox(-10000., maxVertexY-0.01, -0.01, 10000., maxVertexY+0.01, 0.01)                        
            # create Set to get the vertices as vertex not as vertex array
            part.Set(name = 'MaxVertex', vertices = (maxVertex,))
            maxVertex = part.sets['MaxVertex'].vertices[0]            
            
            charpEdgeNodes = part.nodes.getByBoundingCylinder(r = rmaxVertex, z1=maxVertex_y-0.001, z2=maxVertex_y+0.001 )
            part.Set(name = 'SharpEdgeNodeSet', nodes = charpEdgeNodes)
                        
            # edges of dome are adjacent edges of vertex at dome
            # obtain angle between them to decide mesh control options
            domeEdgesIDs = maxVertex.getEdges()   
            # create sequence with all edges
            domeEdges = (partEdges[domeEdgesIDs[0]],)
            for domeEdgeID in domeEdgesIDs[1:]:
                domeEdges = domeEdges+(partEdges[domeEdgeID], )                        
            alpha = getAngleBetweenEdges(domeEdges, partVertices)
            print(alpha)

            if alpha < minAngle:
                domeCell = part.cells.findAt((maxVertex.pointOn[0]), )                   
                part.setMeshControls(regions=(domeCell, ), elemShape=mesh.WEDGE)
           
            thicknessEdge = partEdges.getByBoundingCylinder((-10000.,0.,0.),(10000.,0.,0.),0.01)                        
            part.seedEdgeByNumber(edges = thicknessEdge, number = elementsPerLayerThickness, constraint = FIXED)
            part.generateMesh()
    

def reMeshVessel(elementsPerLayerThickness, layerPartPrefix, minAngle, parts):

#   remesh the vessel with given mesh options
#
#   return   none
#
# input layerPartPrefix             : name prefix of layer parts
# input elementsPerLayerThickness   : numer of elements desired per layer thickness, integer
# input minAngle                    : minimum anlge for using hex elements (for regions with lower angles, wedge elements are set)
    
    print('*** START REMESHING PART ***')
    seedLayerThicknessEdges(layerPartPrefix, int(elementsPerLayerThickness), minAngle, parts)
    print('***  REMESHING PART FINISHED ***')

#def createCorrespondingCSYS(setName1, setName2, partname):
#
#    # create face from points/nodes from sets
#    # create normals on that faces
#
#    
#
#    return csys1, csys2

def createPeriodicEquation(setName1, setName2, partname, instancePrefix, reveloveAngle, exceptionSetNodeLables, parts, model, CoordAxisWhichIsRotAxis):

#   creates periodic boundary equations between nodes in the given node sets (name given)
#   return  :   none
#
#   input   setName1, setName2 [string]   : names of node sets; setname1 should nbe face on xy-Plane (all z=0)
#           partname [string]             : name/key of part the sets belong to  
#           reveloveAngle [float]         : revelove angle of solid model
#           exceptionSets                 : list of sets containing nodes for that equation shall not be enforced (because they are alreday used in other constraints)  
#
#   Requirements:
#   reference face is positioned on xy-plane at z=zero; at these face tank radial direction = global x, tank hoop direction = global z, tank axial direction = global y
#   revolve is done by evolve angle around y from global x in global z direction
#
    
    reveloveAngle = reveloveAngle*np.pi/180. # numpy needs angles in arc length
    part = parts[partname]
    n = -1
    
    # generate node Sets from geometric sets for diagnostic purpose
    part.Set(name=setName1+'_nodes', nodes = part.sets[setName1].nodes)
    part.Set(name=setName2+'_nodes', nodes = part.sets[setName2].nodes)

    exceptionSetlist = list()
    for node in part.sets[setName1].nodes:
        n = n+1  
            
        if node.label in exceptionSetNodeLables:
                #print('Node '+str(node.label)+' already used within another constraint. No equation will be enforced')
                exceptionSetlist.append(node.label)
        else:
            # find corresponding nodes on part level

            CorresNodeLabel = getCorrespondingNodeLabel(node.label, setName2, CoordAxisWhichIsRotAxis, part)

            #part.Set(name='ReferenceNode_'+str(n), nodes=(part.sets[setName1].nodes[n:n+1],))
            #part.Set(name='CorrespondingNode_'+str(n), nodes=(part.sets[setName2].nodes[n:n+1],))
            part.SetFromNodeLabels(name='ReferenceNode_'+str(n), nodeLabels=(node.label, ))
            part.SetFromNodeLabels(name='CorrespondingNode_'+str(n), nodeLabels=(CorresNodeLabel,))
            part.SetFromNodeLabels(name='NodePair_'+str(n), nodeLabels=(node.label, CorresNodeLabel))

            refNodeName = instancePrefix+partname+'.ReferenceNode_'+str(n)
            corresNodeName = instancePrefix+partname+'.CorrespondingNode_'+str(n)
            #------ create equation on assembly level
            # for radial displacement
            # put refNodenName first, as its DOF are used only on time and the firts dof in euqation will be eliminated
            model.Equation(name='PeriodicBC_radial_'+partname+'_'+str(n), terms=((-1.0, refNodeName, 1), (np.cos(reveloveAngle), corresNodeName, 1), (np.sin(reveloveAngle), corresNodeName, 3)))        
            # for tangential displacement
            model.Equation(name='PeriodicBC_hoop_'+partname+'_'+str(n), terms=((-1.0, refNodeName, 3), (-np.sin(reveloveAngle), corresNodeName, 1), (np.cos(reveloveAngle), corresNodeName, 3)))        
            # for tangential displacement
            #model.Equation(name='PeriodicBC_axial_'+partname+'_'+str(n), terms=((1.0, corresNodeName, 2), (-1.0, refNodeName, 2)))        
    
    #part.SetFromNodeLabels(name = 'exception_nodes', nodeLabels = exceptionSetlist)

def removeNodesFromSet(parts, partname, setname, nodeSetlist):

# input:
#       setname [string]    : name of set from which nodes shall be removed
#       nodeSetlist         : List/Sequcen of nodes, which shall be removed from node set
#

   
   #create set based on nodes
   parts[partname].Set(name = setname+'_nodes', nodes = parts[partname].sets[setname].nodes)
   
   # insert node set of contact surface at beginning of nodeSetlist, so that all following sets are substracted from that
   nodeSetlist.insert(0, parts[partname].sets[setname+'_nodes']) 

   # create set from set based on nodes without the nodes to be removed
   parts[partname].SetByBoolean(name = setname, sets = nodeSetlist, operation = DIFFERENCE)


def getNodeSetListByContainingName(parts, partname, namelist):

#
#  INPUT
#           namelist [list of strings]  : list of names of the sets whose nodes shall be stored in returned nodeSetList
# 
# 
#     

    nodeSetlist = list()

    nodeSetKeys = list()    
    strings = parts[partname].sets.keys()
    for name in namelist: 
        templist = [string for string in strings if name in string]
        for element in templist:
            nodeSetKeys.append(element)

    
    for nodeSetKey in nodeSetKeys:        
        nodeSetlist.append(parts[partname].sets[nodeSetKey])
        
    return nodeSetlist

def createPeriodicConstraints(exceptionSets, assembly, parts, model, reveloveAngle, useContact, CoordAxisWhichIsRotAxis):
    
    
    exceptionParts = list()
    exceptionSetsNames = list()

    for exceptionSet in exceptionSets:
        exceptionParts.append(exceptionSet[0])
        exceptionSetsNames.append(exceptionSet[1])

    print('exception sets in the following parts ', exceptionParts)    
    print('exceptionsets are ', exceptionSetsNames)    
    print('No periodic BC constraints are enforced on those nodes as they are already used within other constraints')    
    
    
    for key in parts.keys():        
        print("---- proceeding "+key) 

        exceptionSetNodeLables = list()

        # if contact is defined, add slave nodes to the exceptionSetNodeLables-List; the slave nodes are identicall with the node sets for adjustmant in contact called "*_adjust"
        if useContact:
            for setname in parts[key].sets.keys():
                if "_adjust" in setname:
                    contact_adjust_nodes = parts[key].sets[setname].nodes

                    for node in contact_adjust_nodes:
                        exceptionSetNodeLables.append(node.label)

        # now go along the addionally user defined exception set list and add these nodes also to the exceptionSetNodeLables-List
        if key in exceptionParts:          
            index = exceptionParts.index(key)            
            print('There are exception nodes in this part in set ', exceptionSetsNames[index])                                 
            for node in parts[key].sets[exceptionSetsNames[index]].nodes:
                exceptionSetNodeLables.append(node.label)
            
            parts[key].SetFromNodeLabels(name = 'Set_from_exceptionSetNodeLables', nodeLabels = exceptionSetNodeLables)
            print('Nodes for exception are stored in node Set Set_from_exceptionSetNodeLables of part' , key)    

        if key[0:7] == "Fitting":                        
            # list reference face at xy-plane (z=0) at first!            
            createPeriodicEquation("SymmetryFaces_1", "SymmetryFaces_2", key, "", reveloveAngle, exceptionSetNodeLables, parts, model, CoordAxisWhichIsRotAxis)
        else:
            # list reference face at xy-plane (z=0) at first!
            createPeriodicEquation(key+"_SideFaces_Zero", key+"_SideFaces_One", key, "Mandrel1_", reveloveAngle, exceptionSetNodeLables, parts, model, CoordAxisWhichIsRotAxis)   

def removePeriodicBCNodesFromContactSets(layerPartPrefix, model, parts):

    contactSets = getAllLayerContactSets(layerPartPrefix, model, parts)

    for contactSet in contactSets:

        masterpart = contactSet[0]
        masterSet = contactSet[1]
        slavepart = contactSet[2]
        slaveSet = contactSet[3]        

        # master
        nodeSetListToRemove = getNodeSetListByContainingName(parts, masterpart, ('Reference', 'Corresponding'))        
        removeNodesFromSet(parts, masterpart, masterSet, nodeSetListToRemove)
        
        # slave
        nodeSetListToRemove = getNodeSetListByContainingName(parts, slavepart, ('Reference', 'Corresponding'))
        removeNodesFromSet(parts, slavepart, slaveSet, nodeSetListToRemove)


def getNodeOutOfSetInBoundingZylinder(setname, z1, z2, r, part):

#   description
#
#   return  :   node label of found node
#   
#   input:  setname [string]    : name of node set from which node shall be extracted
#           z1                  : first coordinate of cylinder axis        
#           z2                  : second coordinate of cylinder axis
#           r                   : radius of BoundingCylinder
#           part                : part 
#       

    nodes = part.sets[setname].nodes.getByBoundingCylinder(center1 = z1, center2 = z2, radius = r+0.001)
    #print(str(len(nodes))+' nodes within outer bounding box with node labels')
    #for n in nodes:
    #    print(n.label)
    
    removeNodes = part.sets[setname].nodes.getByBoundingCylinder(center1 = z1, center2 = z2, radius = r-0.01)
    #print(str(len(removeNodes))+' nodes within inner bounding box with node labels')
    #for n in removeNodes:
    #    print(n.label)

    node = [i for i in nodes if i not in removeNodes]
    #print('found '+str(len(node))+' corresponding nodes')
    
    if len(node) == 1:        
        corresNodeLabel = node[0].label
    #    print('found exactly one corresponding node with label ', corresNodeLabel)
        return corresNodeLabel
    else:
        print('*** ERRROR: found '+str(len(node))+' corresponding nodes for node at radius '+ str(r) + 'these nodes have following labels:')
        for n in node:
            print(n.label)
        

    

def getCorrespondingNodeLabel(nodeLabel, setname, CoordAxisWhichIsRotAxis, part): 

#   corresponding node on circular segment
#
#   return  :   
#   
#   input:   nodeLabel [int]                : label of node for which corresponding node shall be find
#           CoordAxisWhichIsRotAxis [char]  : "x", "y", "z"
#           setname [string]                : set in which corresponding node should be searched for
#           part                            : partname
#
#
 
    #print('searching in set '+setname+'for corresponding node to node with label', nodeLabel)

    x_ref = part.nodes[nodeLabel-1].coordinates[0]
    y_ref = part.nodes[nodeLabel-1].coordinates[1]
    z_ref = part.nodes[nodeLabel-1].coordinates[2]

    #print('Ref points coordinates are', x_ref, y_ref, z_ref)


    if CoordAxisWhichIsRotAxis == "x":
        rotAxis = ((x_ref-0.001, 0., 0.), (x_ref+0.001, 0., 0.))
        r = np.sqrt(y_ref**2. + z_ref**2.)        
    if CoordAxisWhichIsRotAxis == "y":
        rotAxis = ((0., y_ref-0.001, 0.), (0., y_ref+0.001, 0.))
        r = np.sqrt(x_ref**2. + z_ref**2.)        
    if CoordAxisWhichIsRotAxis == "z":
        rotAxis = ((0., 0., z_ref-0.001), (0., 0., z_ref+0.001))                
        r = np.sqrt(x_ref**2. + y_ref**2.)        
    
    if not CoordAxisWhichIsRotAxis == "x" and not CoordAxisWhichIsRotAxis == "y" and not CoordAxisWhichIsRotAxis == "z":
        print("Rotation axis does not match with main axis; y-Axis is considered as rotaion axis")
        rotAxis = ((0., y_ref-0.001, 0.), (0., y_ref+0.001, 0.))
        r = np.sqrt(x_ref**2. + z_ref**2.)        

    correspondingNodeLabel = getNodeOutOfSetInBoundingZylinder(setname, rotAxis[0], rotAxis[1], r, part)

    return correspondingNodeLabel


def applyPeropdicBCs(layerPartPrefix, reveloveAngle, exceptionSets, assembly, parts, model, useContact, CoordAxisWhichIsRotAxis): #

#   applies perdiodic boubdary conditions to revolve tank section (equal displacements on both sides)
#
#   return  :   nonde
#   
#   input
#       
#
    print("*** APPLY PERIODIC BOUNDARY CONDITIONS BY EQUATIONS ***") 
    
    createPeriodicConstraints(exceptionSets, assembly, parts, model, reveloveAngle, useContact, CoordAxisWhichIsRotAxis)
    
    removePeriodicBCNodesFromContactSets(layerPartPrefix, model, parts)              
    

def createStepDefinition(steptime, minInk, maxInk, startInk, maxNumInk, stab, NLGEOM, model):

#   creates step definitian for a general all static steps which are already available in the model
#   return  :   none
#
#   input   steptime [float]            : timePeriod of step
#           minInk [float]              : minimum increment size allowed
#           maxInk [float]              : maximal increment size allowed
#           startInk [float]            : size of initial increment
#           maxNumInk [float]           : maximum number of increments allowed
#           stab [float]                : stabilizationMagnitude for dissipative damping stabilization (only Method DISSIPATED_ENERGY_FRACTION without adaptive damping is implemented)           
#           NLGEOM [symbolicConstant]   : ON -- use geometric non-linearity // OFF -- use geometric linear equations
#           model [model objec]         : model to be modified
#
#   Requirements:
#   Analysis steps are available within the model
#   Initial step is named "Initial"
#    

    nstep = -2 # start with -2 vor dont counting inital step
    for step in model.steps.keys():
    
        nstep = nstep +1 
        
        if not step == 'Initial':
            print('Set values for Step '+step)
            model.steps[step].setValues(timePeriod=steptime[nstep], stabilizationMagnitude=stab[nstep], stabilizationMethod=DISSIPATED_ENERGY_FRACTION, continueDampingFactors=False, 
            adaptiveDampingRatio=None, initialInc=startInk[nstep], minInc=minInk[nstep], maxInc=maxInk[nstep], nlgeom = NLGEOM[nstep], maxNumInc=maxNumInk[nstep])

def createOutputDefinition(model, dt, dnInk, fieldVariables, historyVariables):

#   deletes all present output definitions within the model and creates new output definitions based on given parameters
#   return  :   none
#
#   input   
#           model [model objec]         : model to be modified
#           dt [float]                  : time interval for output request; if zero no request per time interval is defined
#           dnInk [float]               : increment frequency for output request; if zero no request per increment frequency is defined
#           fieldVariables [squence]    : sequence of field Variables for output
#           historyVariables [squence]  : sequence of history Variables for output
#
#   Requirements:
#   same output frequence per interval and/or increment is defined for field and history output
#   

    print('*** CREATE OUTPUT DEFINITION ***')
    count_field_output = 1
    count_history_output = 1

    # delete already defined output to overwrite
    for output in (model.fieldOutputRequests.keys()):
        print('delete', output)
        del model.fieldOutputRequests[str(output)]
    for output in (model.historyOutputRequests.keys()):
        print('delete', output)
        del model.fieldOutputRequests[str(output)]

    # create new output for all steps
    for step in model.steps.keys():

        if not step == 'Initial':
            if len(fieldVariables) > 0:
                if dnInk > 0:

                    model.FieldOutputRequest(name='F-Output-'+str(count_field_output), createStepName=step, variables=fieldVariables, frequency=dnInk)
                    count_field_output = count_field_output+1
                if dt > 0:                    
                    model.FieldOutputRequest(name = 'F-Output-'+str(count_field_output), createStepName=step, variables=fieldVariables, timeInterval=dt)
                    count_field_output = count_field_output+1


            if len(historyVariables) > 0:
                if dnInk > 0:
                    model.HistoryOutputRequests(name = 'F-Output-'+str(count_history_output), createStepName=step, variables=historyVariables, frequency=dnInk)
                    count_history_output = count_history_output+1
                if dt > 0:
                    model.HistoryOutputRequests(name = 'F-Output-'+str(count_history_output), createStepName=step, variables=historyVariables, timeInterval=dt)
                    count_history_output = count_history_output+1
    
    print('*** OUTPUT DEFINITION FINISHED ***')

def createLoads(model, valveForce, pressure):

#   redefines the load definitions for internal pressure and axialValveForce in the model based on the given parameters
#   axialValveForce is deleted, if valveForce is set to zero
#   return  :   none
#
#   input   
#           model [model objec]         : model to be modified
#           valveForce [float]          : magnitude of axial valve force [N]
#           pressure [float]            : magnitude of internal pressure in [bar] (is transferred into MPa within function)
#
#   Requirements:
#   axialValveForce and internal pressure loads are already defined within the model
#       

    print('*** CREATE LOAD DEFINITION ***')
    
    if 'Fitting_1_axialValveForce' in model.loads.keys() and valveForce == 0.:
        del model.loads['Fitting_1_axialValveForce']
    
    for load in model.loads.keys():
        if 'Pressure' in load:
            model.loads[load].setValues(magnitude=pressure/10.)
    
    print('*** LOAD DEFINITION CREATED ***')


def getAssemblyRegionFromPartAndSurface(partname, surfname, assembly):

#   generates a Region Object for a given surface of a given part
#   return  :   region object
#
#   input   
#           partname [string]           : name of part that contains the surface 
#           surfname [string]           : name of the surface for which region object shall be generated
#           assembly [assembly object]  : assembly
#
#       

    print('Part', partname)
    strings = assembly.instances.keys()
    instanceKey = [string for string in strings if partname in string]
    print('Instance', instanceKey)
    Region = assembly.instances[instanceKey[0]].surfaces[surfname]

    return Region

def getAssemblyRegionFromPartAndSet(partname, setname, assembly, parts):


#   generates a Region Object for a given set of a given part
#   return  :   region object
#
#   input   
#           partname [string]           : name of part that contains the surface 
#           setname [string]            : name of the set for which region object shall be generated
#           assembly [assembly object]  : assembly
#
#    

    print('Part', partname)
    strings = assembly.instances.keys()
    instanceKey = [string for string in strings if partname in string]
    print('Instance', instanceKey)
    Region = assembly.instances[instanceKey[0]].sets[setname]

    return Region  

def createNodeSetFromPartSurface(part, surfacename, nodeSetName):

    nodes = part.surfaces[surfacename].nodes
    part.Set(name = nodeSetName, nodes = nodes)
  
def copyNodeSet(part, originalNodeSetName, copyNodeSetName):

#   copys an existing node set 
#
# INPUT
#       part [partobject]               : partobject at which a nodeset shall be copied
#       originalNodeSetName [string]    : name of node set that shall be copied    
#       copyNodeSetName [string]        : name of the node set copy
#
#   RETURN
#           None
#   
    
    nodes = part.sets[originalNodeSetName].nodes
    part.Set(name = copyNodeSetName, nodes = (nodes, ))


def getLayerContacts(model, layer):

#   gives a list of the keys of all interactions which defines a contact for the given layer of the winding
#
#   return  :   list of keys [strings]
#
#   input   
#           model [model object]      : model
#           layer [string]            : partname of the layer
#    

    strings = model.interactions.keys()
    contactKeys = [string for string in strings if 'Layer_'+str(layer+1) in string]
    
    return contactKeys


def getContactPartners(model, contact):

#   gives information about slave and matster of the given contact. 
#
#   return  :   
#               masterPart [string] : name of the part containing the master surface
#               masterSet [string]  : name of the surface/set which is used as  master surface
#               slavePart [string] : name of the part containing the slave surface
#               slaveSet [string]  : name of the surface/set which is used as  slave surface
#
#   input   
#           model [model object]      : model
#           contact [string]          : key of the contact interaction for which contact parts shall be obtained
#   


    slave = model.interactions[contact].slave
    master = model.interactions[contact].master  

    slavePart = slave[1]
    slaveSet = slave[0]
    masterPart = master[1]
    masterSet =  master[0]

    return masterPart, masterSet, slavePart, slaveSet

def getAllLayerContactSets(layerPartPrefix, model, parts):

#   gives information about slave and matster for all contact definitions involving layers of the winding 
#
#   return  :   
#               contactSets [list of strings]   : list of the contact information for all contacts with vorm (contact1, contact2, ..., contactn)
#                                                   each contact<i> is a list of the following strings 
#                                                           masterPart [string] : name of the part containing the master surface
#                                                           masterSet [string]  : name of the surface/set which is used as  master surface
#                                                           slavePart [string] : name of the part containing the slave surface
#                                                           slaveSet [string]  : name of the surface/set which is used as  slave surface
#
#   input   
#           layerPartPrefix [string]  : name prefix of layer parts
#           model [model object]      : model
#           parts [part objects]      : all parts of the model
#   

    contactSets = list()
    for layer in range(getNumberOfLayerParts(layerPartPrefix, parts)):              
        
        contactKeys = getLayerContacts(model, layer)

        for contact in contactKeys:
            masterPart, masterSurf, slavePart, slaveSurf = getContactPartners(model, contact)
            contactSets.append((masterPart, masterSurf, slavePart, slaveSurf))

    return contactSets

def getElementtypesInPart(part):

# returns a list with all elemennt types in the given part
#
# INPUT
#   part [partObject]   : part for which element types shall be returned
# 
# OUTPUT
#   elementTypeList [list of strings]   : list of element types existing in given part
# 

    elementTypeList = list()
    
    for element in part.elements:
        if not element.type in elementTypeList:
            elementTypeList.append(element.type)
    
    return elementTypeList



def adaptLayerConnection(model, parts, assembly, layerPartPrefix, useContact):

#   generates TIE-constraints for each contact definition involving layers is userContact = False
#
#   return  :   none
#
#   input   
#           model [model object]        : model
#           parts [part objects]        : all parts of the model
#           assembly [assembly objects] : model assembly
#           layerPartPrefix [string]    : name prefix of layer parts
#           useContact [Boolean]        : False -- Tie constraints are defined; True -- no Tie constraints are defined
#   
#   Remarks:
#       - At current state contact definitions are nor deleted neither suppressed by the script. This as to be done manully within the CAE!
#

    nLayers = getNumberOfLayerParts(layerPartPrefix, parts)

    for layer in range(nLayers):              
        
        contactKeys = getLayerContacts(model, layer)

        if len(contactKeys) > 0. and not useContact: # TIE should be defined

            print('# define TIEs from contacts')
            for contact in contactKeys:
                # get contact partners
                
                print('# get contact partners')
                
                masterPart, masterSurf, slavePart, slaveSurf = getContactPartners(model, contact)

                #slaveRegion = getAssemblyRegionFromPartAndSurface(slavePart, slaveSurf, assembly)                
                #masterRegion = getAssemblyRegionFromPartAndSurface(masterPart, masterSurf, assembly)                                

                slaveRegion = getAssemblyRegionFromPartAndSet(slavePart, slaveSurf, assembly, parts)        
                masterRegion = getAssemblyRegionFromPartAndSet(masterPart, masterSurf, assembly, parts)        

                # define TIE
                print('# define tie')
                model.Tie(name = contact, master = masterRegion, slave = slaveRegion, adjust=ON, tieRotations=ON)
                # supress contact
                #model.interactions[contact].suppress()

            print('At current state contact definitions are nor deleted neither suppressed by the script. This as to be done manully within the CAE!')
        

        if len(contactKeys) > 0. and  useContact: # Contact should be defined
                
            print('### redefine contacts')            

            
            for contact in contactKeys:                    
                print('###########  Processing Contact ', contact)                            
                masterPart, masterSurf, slavePart, slaveSurf = getContactPartners(model, contact)

                print('# Exclude edge with zero layer thickness from contact (exclude from slave)')                            
                #check if wedge elements are in slave part         
                print(slavePart+' constists of following element types', getElementtypesInPart(parts[slavePart]), C3D6 in getElementtypesInPart(parts[slavePart]))
                if C3D6 in getElementtypesInPart(parts[slavePart]):
                    print('- remove sharp edge from slave nodes of part', slavePart)
                    maxVertex = parts[slavePart].sets['MaxVertex'].vertices[0] # point/node that has been defined during remeshing lining on the "sharp edege"

                    maxVertex_x = maxVertex.pointOn[0][0]
                    maxVertex_y = maxVertex.pointOn[0][1]
                    maxVertex_z = maxVertex.pointOn[0][2]
                    rmaxVertex = np.sqrt(maxVertex_x**2. + maxVertex_z**2.)

                    
                    nodeSetListToRemove = parts[slavePart].nodes.getByBoundingCylinder(radius = rmaxVertex, center1 = (maxVertex_x, maxVertex_y-0.001, maxVertex_z), center2 = (maxVertex_x, maxVertex_y+0.001, maxVertex_z))  # all nodes on the "sharp edge"     
                    NodeSetsToRemove = list()
                    NodeSetsToRemove.append(parts[slavePart].Set(name = 'NodesToRemoveFromSlave', nodes = nodeSetListToRemove))
                                    
                    createNodeSetFromPartSurface(parts[slavePart], slaveSurf, slaveSurf)
                    removeNodesFromSet(parts, slavePart, slaveSurf, NodeSetsToRemove)             # remove these nodes from the set CylinderSymm, which is the set for symm. BC     
                    
                    # assign new node set as slave surface in contact
                    slaveRegion = getAssemblyRegionFromPartAndSet(slavePart, slaveSurf, assembly, parts) 
                    model.interactions[contact].setValues(slave=slaveRegion)

                print('# Create not set for slave node adjustment')                            
                # create node-set from slave-surface containing all nodes, also node for periodic BC
                #createNodeSetFromPartSurface(parts[slavePart], slaveSurf, slaveSurf+'_adjust')            
                # but no nodes that are not slave nodes for contact                    
                copyNodeSet(parts[slavePart], slaveSurf, slaveSurf+'_adjust')

                # assing nodeset for adjustment
                print("for contact "+contact+" define adjustment in nodeset "+slaveSurf+'_adjust'+" of part instance "+slavePart)
                model.interactions[contact].setValues(adjustMethod=SET, adjustSet=assembly.instances['Mandrel1_'+slavePart].sets[slaveSurf+'_adjust'])
    
        
            ### If Contact is used, remove slave nodes from symmetric boundary condition
            print('# remove slave nodes from symmetric boundary condition')                            
            
            part = parts['Layer_'+str(layer+1)]
            print('-- Remove slave nodes from set CylinderSymm for layer ', layer+1)
            setNameList = list()
            for setname in part.sets.keys():
                if "adjust" in setname:             # all sets named with "adjust" contains the slave nodes, that shalle be removed from node set for symm. BC
                    setNameList.append(setname)
            nodeSetListToRemove = getNodeSetListByContainingName(parts, part.name, setNameList)   # make node list from all sets with "adjust"     
            removeNodesFromSet(parts, part.name, 'CylinderSymm', nodeSetListToRemove)             # remove these nodes from the set CylinderSymm, which is the set for symm. BC 

        
    print('###### layer connection finished')

                

            
